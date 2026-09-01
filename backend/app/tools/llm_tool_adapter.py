from __future__ import annotations

from backend.app.llm import (
    LLMRequestValidationError,
    LLMToolDefinition,
)
from backend.app.tools.tool_executor import (
    AgentToolExecutor,
)
from backend.app.tools.tool_exceptions import (
    ToolNotFoundError,
)
from backend.app.tools.tool_models import (
    ToolExecutionContext,
)
from backend.app.tools.tool_registry import (
    ToolRegistry,
)


MAXIMUM_EXPOSED_LLM_TOOLS = 5


def build_exposed_llm_tools(
    *,
    registry: ToolRegistry,
    executor: AgentToolExecutor,
    context: ToolExecutionContext,
    requested_tool_names: list[str],
) -> list[LLMToolDefinition]:
    """
    Convert only currently executable registry tools into LLM contracts.

    This is a pre-exposure filter. AgentToolExecutor.execute() repeats
    every permission check immediately before real execution.
    """

    unique_requested_names: list[str] = []

    for raw_name in requested_tool_names:
        normalized_name = " ".join(
            str(raw_name).split()
        )

        if (
            normalized_name
            and normalized_name
            not in unique_requested_names
        ):
            unique_requested_names.append(
                normalized_name
            )

    exposed_tools: list[
        LLMToolDefinition
    ] = []

    for tool_name in unique_requested_names:
        try:
            definition = registry.get(
                tool_name
            )

        except ToolNotFoundError as error:
            raise LLMRequestValidationError(
                "Requested LLM tool is not registered: "
                f"{tool_name}"
            ) from error

        permission_reason = executor.permission_reason(
            definition=definition,
            context=context,
        )

        if permission_reason is not None:
            continue

        exposed_tools.append(
            LLMToolDefinition(
                name=definition.name,
                description=definition.description,
                parameters=(
                    definition.input_json_schema()
                ),
            )
        )

    if len(
        exposed_tools
    ) > MAXIMUM_EXPOSED_LLM_TOOLS:
        raise LLMRequestValidationError(
            "At most five executable tools may be exposed "
            "to one LLM request."
        )

    return exposed_tools
