from __future__ import annotations

import asyncio
import inspect
from datetime import datetime
from time import perf_counter
from typing import Any

from pydantic import (
    BaseModel,
    ValidationError,
)

from backend.app.tools.tool_exceptions import (
    ToolExecutionError,
    ToolInputValidationError,
    ToolNotFoundError,
    ToolOutputValidationError,
    ToolPermissionError,
    ToolTimeoutError,
)
from backend.app.tools.tool_models import (
    ToolAccessMode,
    ToolCallRecord,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolExecutionStatus,
    current_utc_time,
)
from backend.app.tools.tool_registry import (
    ToolRegistry,
)


def normalize_error_message(
    error: Exception,
) -> str:
    """Return a bounded single-line error message."""

    normalized = " ".join(
        str(error).split()
    )

    return (
        normalized
        or type(error).__name__
    )[:2000]


def build_input_field_names(
    arguments: dict[str, Any],
) -> list[str]:
    """
    Return argument field names without persisting raw values.

    This keeps the generic audit envelope free of credentials and
    business-sensitive argument values.
    """

    return sorted(
        {
            str(key)
            for key in arguments
        }
    )


class AgentToolExecutor:
    """Fail-closed executor for registered and permissioned agent tools."""

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        tools_enabled: bool,
        write_tools_enabled: bool,
        timeout_seconds: float,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError(
                "Tool timeout must be greater than zero."
            )

        self.registry = registry
        self.tools_enabled = bool(
            tools_enabled
        )
        self.write_tools_enabled = bool(
            write_tools_enabled
        )
        self.timeout_seconds = float(
            timeout_seconds
        )

    def _permission_reason(
        self,
        *,
        definition: ToolDefinition,
        context: ToolExecutionContext,
    ) -> str | None:
        """Return a denial reason or None when every gate passes."""

        if not self.tools_enabled:
            return (
                "Agent tool execution is disabled by configuration."
            )

        if not definition.enabled:
            return (
                definition.disabled_reason
                or (
                    f"Tool '{definition.name}' is disabled "
                    "by configuration."
                )
            )

        if (
            definition.name
            not in context.allowed_tools
        ):
            return (
                f"Tool '{definition.name}' is not allowed for this "
                "agent execution."
            )

        if (
            definition.allowed_agents
            and context.agent_name
            not in definition.allowed_agents
        ):
            return (
                f"Agent '{context.agent_name}' is not permitted "
                f"to use tool '{definition.name}'."
            )

        if (
            definition.access_mode
            == ToolAccessMode.WRITE
        ):
            if not self.write_tools_enabled:
                return (
                    "Write-capable agent tools are disabled "
                    "by application configuration."
                )

            if not context.allow_write_tools:
                return (
                    "This agent execution was not granted "
                    "write-tool permission."
                )

            if (
                definition.requires_human_approval
                and definition.name
                not in context.approved_write_tools
            ):
                return (
                    f"Write tool '{definition.name}' requires "
                    "explicit human approval for this execution."
                )

        return None

    def permission_reason(
        self,
        *,
        definition: ToolDefinition,
        context: ToolExecutionContext,
    ) -> str | None:
        """
        Return the same fail-closed permission decision used by execute().

        This is used only to decide which tools are safe to expose to an
        LLM. The executor repeats the check immediately before execution.
        """

        return self._permission_reason(
            definition=definition,
            context=context,
        )

    async def execute(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        """Validate registration, permission, input, execution, and output."""

        started_at = current_utc_time()
        timer_started_at = perf_counter()
        input_field_names = build_input_field_names(
            arguments
        )

        try:
            definition = self.registry.get(
                tool_name
            )

        except ToolNotFoundError as error:
            return self._failed_unregistered_result(
                tool_name=tool_name,
                context=context,
                input_field_names=input_field_names,
                started_at=started_at,
                timer_started_at=timer_started_at,
                error=error,
            )

        permission_reason = self._permission_reason(
            definition=definition,
            context=context,
        )

        if permission_reason is not None:
            completed_at = current_utc_time()

            return ToolExecutionResult(
                status=ToolExecutionStatus.DENIED,
                output=None,
                call_record=ToolCallRecord(
                    run_id=context.run_id,
                    agent_name=context.agent_name,
                    tool_name=definition.name,
                    access_mode=definition.access_mode,
                    status=ToolExecutionStatus.DENIED,
                    input_field_names=input_field_names,
                    output_schema_name=(
                        definition.output_model.__name__
                    ),
                    permission_reason=permission_reason,
                    error_type=(
                        ToolPermissionError.__name__
                    ),
                    error_message=permission_reason,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=self._duration_ms(
                        timer_started_at
                    ),
                ),
            )

        try:
            validated_input = (
                definition.input_model.model_validate(
                    arguments
                )
            )

        except ValidationError:
            controlled_error = ToolInputValidationError(
                "Tool arguments did not match the declared "
                f"schema for '{definition.name}'."
            )

            return self._failed_registered_result(
                definition=definition,
                context=context,
                input_field_names=input_field_names,
                started_at=started_at,
                timer_started_at=timer_started_at,
                error=controlled_error,
            )

        try:
            raw_output = await self._execute_handler(
                definition=definition,
                validated_input=validated_input,
                context=context,
            )

        except asyncio.TimeoutError:
            controlled_error = ToolTimeoutError(
                f"Tool '{definition.name}' exceeded its "
                "execution timeout."
            )

            return self._failed_registered_result(
                definition=definition,
                context=context,
                input_field_names=input_field_names,
                started_at=started_at,
                timer_started_at=timer_started_at,
                error=controlled_error,
            )

        except Exception as error:
            controlled_error = ToolExecutionError(
                f"Tool '{definition.name}' failed during execution: "
                + normalize_error_message(
                    error
                )
            )

            return self._failed_registered_result(
                definition=definition,
                context=context,
                input_field_names=input_field_names,
                started_at=started_at,
                timer_started_at=timer_started_at,
                error=controlled_error,
            )

        try:
            if isinstance(
                raw_output,
                BaseModel,
            ):
                raw_output = raw_output.model_dump(
                    mode="python"
                )

            validated_output = (
                definition.output_model.model_validate(
                    raw_output
                )
            )

        except ValidationError:
            controlled_error = ToolOutputValidationError(
                "Tool output did not match the declared "
                f"schema for '{definition.name}'."
            )

            return self._failed_registered_result(
                definition=definition,
                context=context,
                input_field_names=input_field_names,
                started_at=started_at,
                timer_started_at=timer_started_at,
                error=controlled_error,
            )

        completed_at = current_utc_time()

        return ToolExecutionResult(
            status=ToolExecutionStatus.SUCCESS,
            output=validated_output.model_dump(
                mode="python"
            ),
            call_record=ToolCallRecord(
                run_id=context.run_id,
                agent_name=context.agent_name,
                tool_name=definition.name,
                access_mode=definition.access_mode,
                status=ToolExecutionStatus.SUCCESS,
                input_field_names=input_field_names,
                output_schema_name=(
                    definition.output_model.__name__
                ),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=self._duration_ms(
                    timer_started_at
                ),
            ),
        )

    async def _execute_handler(
        self,
        *,
        definition: ToolDefinition,
        validated_input: BaseModel,
        context: ToolExecutionContext,
    ) -> BaseModel | dict[str, Any]:
        """Run sync or async handlers under one timeout boundary."""

        if inspect.iscoroutinefunction(
            definition.handler
        ):
            return await asyncio.wait_for(
                definition.handler(
                    validated_input,
                    context,
                ),
                timeout=self.timeout_seconds,
            )

        return await asyncio.wait_for(
            asyncio.to_thread(
                definition.handler,
                validated_input,
                context,
            ),
            timeout=self.timeout_seconds,
        )

    def _failed_unregistered_result(
        self,
        *,
        tool_name: str,
        context: ToolExecutionContext,
        input_field_names: list[str],
        started_at: datetime,
        timer_started_at: float,
        error: Exception,
    ) -> ToolExecutionResult:
        """Build a controlled failure for unknown tool names."""

        completed_at = current_utc_time()

        return ToolExecutionResult(
            status=ToolExecutionStatus.FAILED,
            output=None,
            call_record=ToolCallRecord(
                run_id=context.run_id,
                agent_name=context.agent_name,
                tool_name=(
                    " ".join(
                        str(tool_name).split()
                    )[:100]
                    or "unknown_tool"
                ),
                access_mode=None,
                status=ToolExecutionStatus.FAILED,
                input_field_names=input_field_names,
                error_type=type(error).__name__,
                error_message=normalize_error_message(
                    error
                ),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=self._duration_ms(
                    timer_started_at
                ),
            ),
        )

    def _failed_registered_result(
        self,
        *,
        definition: ToolDefinition,
        context: ToolExecutionContext,
        input_field_names: list[str],
        started_at: datetime,
        timer_started_at: float,
        error: Exception,
    ) -> ToolExecutionResult:
        """Build a controlled failure for a registered tool."""

        completed_at = current_utc_time()

        return ToolExecutionResult(
            status=ToolExecutionStatus.FAILED,
            output=None,
            call_record=ToolCallRecord(
                run_id=context.run_id,
                agent_name=context.agent_name,
                tool_name=definition.name,
                access_mode=definition.access_mode,
                status=ToolExecutionStatus.FAILED,
                input_field_names=input_field_names,
                output_schema_name=(
                    definition.output_model.__name__
                ),
                error_type=type(error).__name__,
                error_message=normalize_error_message(
                    error
                ),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=self._duration_ms(
                    timer_started_at
                ),
            ),
        )

    @staticmethod
    def _duration_ms(
        timer_started_at: float,
    ) -> float:
        """Return elapsed tool execution time in milliseconds."""

        return round(
            (
                perf_counter()
                - timer_started_at
            )
            * 1000,
            2,
        )
