from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from backend.app.schemas.tasks import (
    TaskItem,
)
from backend.app.services.task_service import (
    convert_recommendation_to_task,
)
from backend.app.tools.tool_models import (
    ToolAccessMode,
    ToolDefinition,
    ToolExecutionContext,
)


CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME = (
    "create_task_from_approved_recommendation"
)


class ApprovedRecommendationTaskInput(BaseModel):
    """
    Minimal reviewed task-conversion input.

    The model cannot provide task title, description, owner, due date,
    priority, status, or linked issue. Those values come only from the
    persisted recommendation inside task_service.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    recommendation_id: int = Field(
        ge=1,
    )


class ApprovedRecommendationTaskOutput(BaseModel):
    """Controlled business outcome returned by the conversion tool."""

    model_config = ConfigDict(
        extra="forbid",
    )

    status: Literal["success"] = "success"

    outcome: Literal[
        "converted",
        "not_found",
        "not_accepted",
        "already_converted",
    ]

    recommendation_id: int = Field(
        ge=1,
    )

    recommendation_status: str | None = None
    current_status: str | None = None

    task_id: int | None = Field(
        default=None,
        ge=1,
    )

    task: TaskItem | None = None
    message: str

    @model_validator(mode="after")
    def validate_outcome_shape(
        self,
    ) -> "ApprovedRecommendationTaskOutput":
        if self.outcome == "converted":
            if self.task is None:
                raise ValueError(
                    "Converted outcome requires a task."
                )

            if self.task_id != self.task.task_id:
                raise ValueError(
                    "task_id must match the returned task."
                )

            if (
                self.recommendation_status
                != "Converted to Task"
            ):
                raise ValueError(
                    "Converted outcome requires recommendation "
                    "status 'Converted to Task'."
                )

        elif self.task is not None:
            raise ValueError(
                "Non-converted outcomes cannot return a task."
            )

        return self


async def create_task_from_approved_recommendation_handler(
    arguments: ApprovedRecommendationTaskInput,
    context: ToolExecutionContext,
) -> ApprovedRecommendationTaskOutput:
    """
    Call the existing transactional conversion service.

    The generic executor has already enforced:
    - tool enabled
    - WRITE access mode
    - allowed agent
    - run-level write permission
    - explicit human approval for this exact tool
    """

    del context

    result = convert_recommendation_to_task(
        arguments.recommendation_id
    )

    outcome = str(
        result.get(
            "outcome",
            "",
        )
    )

    if outcome == "success":
        response = result.get(
            "response",
            {},
        )
        task_data = response.get(
            "task"
        )

        if not isinstance(
            task_data,
            dict,
        ):
            raise ValueError(
                "Task conversion service did not return task data."
            )

        task = TaskItem.model_validate(
            task_data
        )

        return ApprovedRecommendationTaskOutput(
            outcome="converted",
            recommendation_id=arguments.recommendation_id,
            recommendation_status=str(
                response.get(
                    "recommendation_status",
                    "",
                )
            ),
            task_id=task.task_id,
            task=task,
            message=str(
                response.get(
                    "message",
                    (
                        "Recommendation converted into "
                        "a task successfully."
                    ),
                )
            ),
        )

    if outcome == "not_found":
        return ApprovedRecommendationTaskOutput(
            outcome="not_found",
            recommendation_id=arguments.recommendation_id,
            message="The recommendation was not found.",
        )

    if outcome == "already_converted":
        raw_task_id = result.get(
            "task_id"
        )

        return ApprovedRecommendationTaskOutput(
            outcome="already_converted",
            recommendation_id=arguments.recommendation_id,
            current_status=(
                str(
                    result.get(
                        "current_status",
                        "",
                    )
                )
                or None
            ),
            task_id=(
                int(raw_task_id)
                if raw_task_id is not None
                else None
            ),
            message=(
                "The recommendation was already converted "
                "to a task."
            ),
        )

    if outcome == "invalid_status":
        return ApprovedRecommendationTaskOutput(
            outcome="not_accepted",
            recommendation_id=arguments.recommendation_id,
            current_status=(
                str(
                    result.get(
                        "current_status",
                        "",
                    )
                )
                or None
            ),
            message=(
                "The recommendation must already be Accepted "
                "before task conversion."
            ),
        )

    raise ValueError(
        "Task conversion service returned an unsupported outcome."
    )


def build_task_conversion_tool_definition(
    *,
    enabled: bool,
) -> ToolDefinition:
    """Build the separately gated recommendation-to-task write tool."""

    return ToolDefinition(
        name=(
            CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME
        ),
        description=(
            "Convert one already human-accepted persisted "
            "recommendation into a task. Task content comes only "
            "from the persisted accepted recommendation."
        ),
        input_model=ApprovedRecommendationTaskInput,
        output_model=ApprovedRecommendationTaskOutput,
        handler=(
            create_task_from_approved_recommendation_handler
        ),
        access_mode=ToolAccessMode.WRITE,
        allowed_agents=(
            "Recommendation Agent",
        ),
        requires_human_approval=True,
        enabled=enabled,
        disabled_reason=(
            None
            if enabled
            else (
                "Recommendation-to-task agent tool is disabled "
                "by application configuration."
            )
        ),
    )
