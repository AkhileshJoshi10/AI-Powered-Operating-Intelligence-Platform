from __future__ import annotations

import asyncio
import time
from typing import Any

from pydantic import BaseModel, Field

from backend.app.tools import (
    AgentToolExecutor,
    ToolAccessMode,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolRegistry,
)
from backend.app.tools.tool_exceptions import (
    ToolRegistrationError,
)


class LookupInput(BaseModel):
    issue_id: str = Field(min_length=1)


class LookupOutput(BaseModel):
    issue_id: str
    status: str


class WriteInput(BaseModel):
    recommendation_id: int = Field(ge=1)


class WriteOutput(BaseModel):
    created: bool


def build_context(
    *,
    allowed_tools: list[str],
    agent_name: str = "Root-Cause Agent",
    allow_write_tools: bool = False,
    approved_write_tools: list[str] | None = None,
) -> ToolExecutionContext:
    return ToolExecutionContext(
        run_id="RUN-TOOL-001",
        agent_name=agent_name,
        requested_by="pytest",
        allowed_tools=allowed_tools,
        allow_write_tools=allow_write_tools,
        approved_write_tools=approved_write_tools or [],
    )


def build_read_definition() -> ToolDefinition:
    async def handler(
        arguments: LookupInput,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        del context
        return {
            "issue_id": arguments.issue_id,
            "status": "Open",
        }

    return ToolDefinition(
        name="get_issue",
        description="Read one validated business issue.",
        input_model=LookupInput,
        output_model=LookupOutput,
        handler=handler,
        access_mode=ToolAccessMode.READ_ONLY,
        allowed_agents=(
            "Root-Cause Agent",
            "Recommendation Agent",
        ),
    )


def build_write_definition() -> ToolDefinition:
    async def handler(
        arguments: WriteInput,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        del arguments
        del context
        return {"created": True}

    return ToolDefinition(
        name="create_task_from_approved_recommendation",
        description="Create a task from an approved recommendation.",
        input_model=WriteInput,
        output_model=WriteOutput,
        handler=handler,
        access_mode=ToolAccessMode.WRITE,
        allowed_agents=("Recommendation Agent",),
        requires_human_approval=True,
    )


def test_registry_registers_read_tool() -> None:
    registry = ToolRegistry()
    registry.register(build_read_definition())
    assert registry.names() == ["get_issue"]


def test_registry_rejects_duplicate_tool() -> None:
    registry = ToolRegistry()
    definition = build_read_definition()
    registry.register(definition)

    try:
        registry.register(definition)
    except ToolRegistrationError as error:
        assert "already registered" in str(error)
    else:
        raise AssertionError("Duplicate tool registration was accepted.")


def test_registry_rejects_write_tool_without_human_approval() -> None:
    async def handler(
        arguments: WriteInput,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        del arguments
        del context
        return {"created": True}

    registry = ToolRegistry()

    try:
        registry.register(
            ToolDefinition(
                name="unsafe_write",
                description="Unsafe write.",
                input_model=WriteInput,
                output_model=WriteOutput,
                handler=handler,
                access_mode=ToolAccessMode.WRITE,
                requires_human_approval=False,
            )
        )
    except ToolRegistrationError as error:
        assert "human approval" in str(error)
    else:
        raise AssertionError("Unsafe write registration was accepted.")


def test_read_tool_executes_after_permission_gates() -> None:
    registry = ToolRegistry()
    registry.register(build_read_definition())
    executor = AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=False,
        timeout_seconds=1.0,
    )

    result = asyncio.run(
        executor.execute(
            tool_name="get_issue",
            arguments={"issue_id": "ISSUE-HIGH-001"},
            context=build_context(
                allowed_tools=["get_issue"]
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output == {
        "issue_id": "ISSUE-HIGH-001",
        "status": "Open",
    }


def test_tool_execution_denied_when_tools_disabled() -> None:
    registry = ToolRegistry()
    registry.register(build_read_definition())
    executor = AgentToolExecutor(
        registry,
        tools_enabled=False,
        write_tools_enabled=False,
        timeout_seconds=1.0,
    )

    result = asyncio.run(
        executor.execute(
            tool_name="get_issue",
            arguments={"issue_id": "ISSUE-HIGH-001"},
            context=build_context(
                allowed_tools=["get_issue"]
            ),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED
    assert "disabled by configuration" in (
        result.call_record.permission_reason or ""
    )


def test_tool_execution_denied_when_not_in_run_allowlist() -> None:
    registry = ToolRegistry()
    registry.register(build_read_definition())
    executor = AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=False,
        timeout_seconds=1.0,
    )

    result = asyncio.run(
        executor.execute(
            tool_name="get_issue",
            arguments={"issue_id": "ISSUE-HIGH-001"},
            context=build_context(allowed_tools=[]),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED
    assert "not allowed" in (
        result.call_record.permission_reason or ""
    )


def test_tool_execution_denied_for_unapproved_agent() -> None:
    registry = ToolRegistry()
    registry.register(build_read_definition())
    executor = AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=False,
        timeout_seconds=1.0,
    )

    result = asyncio.run(
        executor.execute(
            tool_name="get_issue",
            arguments={"issue_id": "ISSUE-HIGH-001"},
            context=build_context(
                allowed_tools=["get_issue"],
                agent_name="Monitoring Agent",
            ),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED
    assert "not permitted" in (
        result.call_record.permission_reason or ""
    )


def test_write_tool_denied_when_application_write_gate_disabled() -> None:
    registry = ToolRegistry()
    registry.register(build_write_definition())
    executor = AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=False,
        timeout_seconds=1.0,
    )

    result = asyncio.run(
        executor.execute(
            tool_name="create_task_from_approved_recommendation",
            arguments={"recommendation_id": 21},
            context=build_context(
                allowed_tools=[
                    "create_task_from_approved_recommendation"
                ],
                agent_name="Recommendation Agent",
                allow_write_tools=True,
                approved_write_tools=[
                    "create_task_from_approved_recommendation"
                ],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED
    assert "disabled by application configuration" in (
        result.call_record.permission_reason or ""
    )


def test_write_tool_denied_without_run_write_permission() -> None:
    registry = ToolRegistry()
    registry.register(build_write_definition())
    executor = AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=True,
        timeout_seconds=1.0,
    )

    result = asyncio.run(
        executor.execute(
            tool_name="create_task_from_approved_recommendation",
            arguments={"recommendation_id": 21},
            context=build_context(
                allowed_tools=[
                    "create_task_from_approved_recommendation"
                ],
                agent_name="Recommendation Agent",
                allow_write_tools=False,
                approved_write_tools=[
                    "create_task_from_approved_recommendation"
                ],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED
    assert "not granted write-tool permission" in (
        result.call_record.permission_reason or ""
    )


def test_write_tool_denied_without_human_approval() -> None:
    registry = ToolRegistry()
    registry.register(build_write_definition())
    executor = AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=True,
        timeout_seconds=1.0,
    )

    result = asyncio.run(
        executor.execute(
            tool_name="create_task_from_approved_recommendation",
            arguments={"recommendation_id": 21},
            context=build_context(
                allowed_tools=[
                    "create_task_from_approved_recommendation"
                ],
                agent_name="Recommendation Agent",
                allow_write_tools=True,
                approved_write_tools=[],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED
    assert "explicit human approval" in (
        result.call_record.permission_reason or ""
    )


def test_write_tool_executes_only_after_all_gates() -> None:
    registry = ToolRegistry()
    registry.register(build_write_definition())
    executor = AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=True,
        timeout_seconds=1.0,
    )

    result = asyncio.run(
        executor.execute(
            tool_name="create_task_from_approved_recommendation",
            arguments={"recommendation_id": 21},
            context=build_context(
                allowed_tools=[
                    "create_task_from_approved_recommendation"
                ],
                agent_name="Recommendation Agent",
                allow_write_tools=True,
                approved_write_tools=[
                    "create_task_from_approved_recommendation"
                ],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output == {"created": True}


def test_invalid_input_fails_before_handler() -> None:
    calls: list[str] = []

    async def handler(
        arguments: LookupInput,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        del arguments
        del context
        calls.append("called")
        return {
            "issue_id": "x",
            "status": "Open",
        }

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="get_issue",
            description="Read one issue.",
            input_model=LookupInput,
            output_model=LookupOutput,
            handler=handler,
        )
    )
    executor = AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=False,
        timeout_seconds=1.0,
    )

    result = asyncio.run(
        executor.execute(
            tool_name="get_issue",
            arguments={"issue_id": ""},
            context=build_context(
                allowed_tools=["get_issue"]
            ),
        )
    )

    assert result.status == ToolExecutionStatus.FAILED
    assert result.call_record.error_type == "ToolInputValidationError"
    assert calls == []


def test_invalid_output_is_rejected() -> None:
    async def handler(
        arguments: LookupInput,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        del arguments
        del context
        return {"issue_id": "ISSUE-HIGH-001"}

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="get_issue",
            description="Read one issue.",
            input_model=LookupInput,
            output_model=LookupOutput,
            handler=handler,
        )
    )
    executor = AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=False,
        timeout_seconds=1.0,
    )

    result = asyncio.run(
        executor.execute(
            tool_name="get_issue",
            arguments={"issue_id": "ISSUE-HIGH-001"},
            context=build_context(
                allowed_tools=["get_issue"]
            ),
        )
    )

    assert result.status == ToolExecutionStatus.FAILED
    assert result.call_record.error_type == "ToolOutputValidationError"


def test_sync_tool_timeout_is_controlled() -> None:
    def handler(
        arguments: LookupInput,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        del arguments
        del context
        time.sleep(0.05)
        return {
            "issue_id": "ISSUE-HIGH-001",
            "status": "Open",
        }

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="get_issue",
            description="Slow sync read.",
            input_model=LookupInput,
            output_model=LookupOutput,
            handler=handler,
        )
    )
    executor = AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=False,
        timeout_seconds=0.01,
    )

    result = asyncio.run(
        executor.execute(
            tool_name="get_issue",
            arguments={"issue_id": "ISSUE-HIGH-001"},
            context=build_context(
                allowed_tools=["get_issue"]
            ),
        )
    )

    assert result.status == ToolExecutionStatus.FAILED
    assert result.call_record.error_type == "ToolTimeoutError"


def test_unknown_tool_returns_controlled_failure() -> None:
    executor = AgentToolExecutor(
        ToolRegistry(),
        tools_enabled=True,
        write_tools_enabled=False,
        timeout_seconds=1.0,
    )

    result = asyncio.run(
        executor.execute(
            tool_name="invented_tool",
            arguments={},
            context=build_context(
                allowed_tools=["invented_tool"]
            ),
        )
    )

    assert result.status == ToolExecutionStatus.FAILED
    assert result.call_record.error_type == "ToolNotFoundError"


def test_audit_record_does_not_store_raw_argument_values() -> None:
    registry = ToolRegistry()
    registry.register(build_read_definition())
    executor = AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=False,
        timeout_seconds=1.0,
    )

    secret_value = "SENSITIVE-ISSUE-VALUE"

    result = asyncio.run(
        executor.execute(
            tool_name="get_issue",
            arguments={"issue_id": secret_value},
            context=build_context(
                allowed_tools=["get_issue"]
            ),
        )
    )

    audit_dump = str(
        result.call_record.model_dump(
            mode="python"
        )
    )

    assert secret_value not in audit_dump
    assert result.call_record.input_field_names == ["issue_id"]
