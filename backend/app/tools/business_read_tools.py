from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.schemas.executive_briefs import (
    ExecutiveBriefItem,
    LatestExecutiveBriefResponse,
)
from backend.app.schemas.issues import (
    IssueDetailResponse,
    IssueEvidenceItem,
    IssueItem,
    RootCauseItem,
)
from backend.app.schemas.recommendations import (
    RecommendationDetail,
    RecommendationDetailResponse,
)
from backend.app.schemas.tasks import (
    TaskDetail,
    TaskDetailResponse,
)
from backend.app.services.executive_brief_service import (
    get_latest_executive_brief,
)
from backend.app.services.issue_service import get_issue_detail
from backend.app.services.recommendation_service import (
    get_recommendation_detail,
)
from backend.app.services.task_service import get_task_detail
from backend.app.tools.tool_models import (
    ToolAccessMode,
    ToolDefinition,
    ToolExecutionContext,
)
from backend.app.tools.tool_registry import ToolRegistry


GET_ISSUE_TOOL_NAME = "get_issue"
GET_ISSUE_EVIDENCE_TOOL_NAME = "get_issue_evidence"
GET_ROOT_CAUSE_TOOL_NAME = "get_root_cause"
GET_RECOMMENDATION_TOOL_NAME = "get_recommendation"
GET_TASK_TOOL_NAME = "get_task"
GET_EXECUTIVE_BRIEF_TOOL_NAME = "get_executive_brief"

READ_ONLY_BUSINESS_TOOL_NAMES = (
    GET_ISSUE_TOOL_NAME,
    GET_ISSUE_EVIDENCE_TOOL_NAME,
    GET_ROOT_CAUSE_TOOL_NAME,
    GET_RECOMMENDATION_TOOL_NAME,
    GET_TASK_TOOL_NAME,
    GET_EXECUTIVE_BRIEF_TOOL_NAME,
)


class IssueLookupInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    issue_id: str = Field(min_length=1, max_length=150)


class RecommendationLookupInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recommendation_id: int = Field(ge=1)


class TaskLookupInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: int = Field(ge=1)


class ExecutiveBriefLookupInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IssueToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["success"] = "success"
    found: bool
    issue: IssueItem | None = None

    @model_validator(mode="after")
    def validate_found_state(self) -> "IssueToolOutput":
        if self.found != (self.issue is not None):
            raise ValueError("found must match whether issue is present.")
        return self


class IssueEvidenceToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["success"] = "success"
    found: bool
    issue_id: str
    evidence_count: int = Field(ge=0)
    evidence: list[IssueEvidenceItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_evidence_result(self) -> "IssueEvidenceToolOutput":
        if self.evidence_count != len(self.evidence):
            raise ValueError("evidence_count must match the evidence list.")
        if not self.found and self.evidence:
            raise ValueError("A missing issue cannot return evidence.")
        return self


class RootCauseToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["success"] = "success"
    found: bool
    issue_id: str
    root_cause: RootCauseItem | None = None

    @model_validator(mode="after")
    def validate_root_cause_state(self) -> "RootCauseToolOutput":
        if not self.found and self.root_cause is not None:
            raise ValueError("A missing issue cannot return a root cause.")
        return self


class RecommendationToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["success"] = "success"
    found: bool
    recommendation: RecommendationDetail | None = None

    @model_validator(mode="after")
    def validate_found_state(self) -> "RecommendationToolOutput":
        if self.found != (self.recommendation is not None):
            raise ValueError(
                "found must match whether recommendation is present."
            )
        return self


class TaskToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["success"] = "success"
    found: bool
    task: TaskDetail | None = None

    @model_validator(mode="after")
    def validate_found_state(self) -> "TaskToolOutput":
        if self.found != (self.task is not None):
            raise ValueError("found must match whether task is present.")
        return self


class ExecutiveBriefToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["success"] = "success"
    found: bool
    generated_at: datetime | None = None
    brief: ExecutiveBriefItem | None = None

    @model_validator(mode="after")
    def validate_found_state(self) -> "ExecutiveBriefToolOutput":
        if self.found != (self.brief is not None):
            raise ValueError(
                "found must match whether Executive Brief is present."
            )
        if self.found and self.generated_at is None:
            raise ValueError(
                "generated_at is required when a brief is returned."
            )
        return self


async def get_issue_handler(
    arguments: IssueLookupInput,
    context: ToolExecutionContext,
) -> IssueToolOutput:
    del context
    raw = get_issue_detail(arguments.issue_id)
    if raw is None:
        return IssueToolOutput(found=False, issue=None)

    validated = IssueDetailResponse.model_validate(raw)
    return IssueToolOutput(found=True, issue=validated.issue)


async def get_issue_evidence_handler(
    arguments: IssueLookupInput,
    context: ToolExecutionContext,
) -> IssueEvidenceToolOutput:
    del context
    raw = get_issue_detail(arguments.issue_id)
    if raw is None:
        return IssueEvidenceToolOutput(
            found=False,
            issue_id=arguments.issue_id,
            evidence_count=0,
            evidence=[],
        )

    validated = IssueDetailResponse.model_validate(raw)
    return IssueEvidenceToolOutput(
        found=True,
        issue_id=validated.issue.issue_id,
        evidence_count=validated.evidence_count,
        evidence=validated.evidence,
    )


async def get_root_cause_handler(
    arguments: IssueLookupInput,
    context: ToolExecutionContext,
) -> RootCauseToolOutput:
    del context
    raw = get_issue_detail(arguments.issue_id)
    if raw is None:
        return RootCauseToolOutput(
            found=False,
            issue_id=arguments.issue_id,
            root_cause=None,
        )

    validated = IssueDetailResponse.model_validate(raw)
    return RootCauseToolOutput(
        found=True,
        issue_id=validated.issue.issue_id,
        root_cause=validated.root_cause,
    )


async def get_recommendation_handler(
    arguments: RecommendationLookupInput,
    context: ToolExecutionContext,
) -> RecommendationToolOutput:
    del context
    raw = get_recommendation_detail(arguments.recommendation_id)
    if raw is None:
        return RecommendationToolOutput(
            found=False,
            recommendation=None,
        )

    validated = RecommendationDetailResponse.model_validate(raw)
    return RecommendationToolOutput(
        found=True,
        recommendation=validated.recommendation,
    )


async def get_task_handler(
    arguments: TaskLookupInput,
    context: ToolExecutionContext,
) -> TaskToolOutput:
    del context
    raw = get_task_detail(arguments.task_id)
    if raw is None:
        return TaskToolOutput(found=False, task=None)

    validated = TaskDetailResponse.model_validate(raw)
    return TaskToolOutput(found=True, task=validated.task)


async def get_executive_brief_handler(
    arguments: ExecutiveBriefLookupInput,
    context: ToolExecutionContext,
) -> ExecutiveBriefToolOutput:
    del arguments
    del context

    raw = get_latest_executive_brief()
    if raw is None:
        return ExecutiveBriefToolOutput(
            found=False,
            generated_at=None,
            brief=None,
        )

    validated = LatestExecutiveBriefResponse.model_validate(raw)
    return ExecutiveBriefToolOutput(
        found=True,
        generated_at=validated.generated_at,
        brief=validated.brief,
    )


def build_read_only_business_tool_definitions() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name=GET_ISSUE_TOOL_NAME,
            description="Read one persisted business issue by issue_id.",
            input_model=IssueLookupInput,
            output_model=IssueToolOutput,
            handler=get_issue_handler,
            access_mode=ToolAccessMode.READ_ONLY,
            allowed_agents=(
                "Priority Agent",
                "Root-Cause Agent",
                "Recommendation Agent",
                "Executive Brief Agent",
            ),
        ),
        ToolDefinition(
            name=GET_ISSUE_EVIDENCE_TOOL_NAME,
            description="Read persisted deterministic evidence for one issue.",
            input_model=IssueLookupInput,
            output_model=IssueEvidenceToolOutput,
            handler=get_issue_evidence_handler,
            access_mode=ToolAccessMode.READ_ONLY,
            allowed_agents=(
                "Root-Cause Agent",
                "Recommendation Agent",
            ),
        ),
        ToolDefinition(
            name=GET_ROOT_CAUSE_TOOL_NAME,
            description="Read the persisted root-cause analysis for one issue.",
            input_model=IssueLookupInput,
            output_model=RootCauseToolOutput,
            handler=get_root_cause_handler,
            access_mode=ToolAccessMode.READ_ONLY,
            allowed_agents=(
                "Recommendation Agent",
                "Executive Brief Agent",
            ),
        ),
        ToolDefinition(
            name=GET_RECOMMENDATION_TOOL_NAME,
            description="Read one persisted recommendation by recommendation_id.",
            input_model=RecommendationLookupInput,
            output_model=RecommendationToolOutput,
            handler=get_recommendation_handler,
            access_mode=ToolAccessMode.READ_ONLY,
            allowed_agents=(
                "Recommendation Agent",
                "Executive Brief Agent",
            ),
        ),
        ToolDefinition(
            name=GET_TASK_TOOL_NAME,
            description="Read one persisted task by task_id.",
            input_model=TaskLookupInput,
            output_model=TaskToolOutput,
            handler=get_task_handler,
            access_mode=ToolAccessMode.READ_ONLY,
            allowed_agents=("Executive Brief Agent",),
        ),
        ToolDefinition(
            name=GET_EXECUTIVE_BRIEF_TOOL_NAME,
            description=(
                "Read the latest stored Executive Brief without "
                "generating or updating it."
            ),
            input_model=ExecutiveBriefLookupInput,
            output_model=ExecutiveBriefToolOutput,
            handler=get_executive_brief_handler,
            access_mode=ToolAccessMode.READ_ONLY,
            allowed_agents=("Executive Brief Agent",),
        ),
    ]


def register_read_only_business_tools(registry: ToolRegistry) -> None:
    for definition in build_read_only_business_tool_definitions():
        registry.register(definition)
