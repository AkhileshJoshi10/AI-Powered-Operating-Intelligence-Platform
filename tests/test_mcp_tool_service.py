from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from backend.app.services.mcp_tool_service import (
    ControlledMCPToolService,
    MCPToolUnavailableError,
)
from backend.app.tools.mcp_models import (
    MCP_PROTOCOL_TARGET,
)
from backend.app.tools.tool_executor import (
    AgentToolExecutor,
)
from backend.app.tools.tool_models import (
    ToolAccessMode,
    ToolDefinition,
    ToolExecutionContext,
)
from backend.app.tools.tool_registry import (
    ToolRegistry,
)


class ReadInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    issue_id: str = Field(
        min_length=2,
    )


class ReadOutput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    issue_id: str
    status: str


class WriteInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    recommendation_id: int = Field(
        ge=1,
    )


class WriteOutput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    created: bool
    recommendation_id: int


def build_read_tool(
    *,
    enabled: bool = True,
) -> ToolDefinition:
    async def handler(
        arguments: ReadInput,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        del context

        return {
            "issue_id": arguments.issue_id,
            "status": "Open",
        }

    return ToolDefinition(
        name="get_issue",
        description="Read one controlled issue record.",
        input_model=ReadInput,
        output_model=ReadOutput,
        handler=handler,
        access_mode=ToolAccessMode.READ_ONLY,
        allowed_agents=(
            "Root-Cause Agent",
        ),
        enabled=enabled,
        disabled_reason=(
            None
            if enabled
            else "Read tool disabled for test."
        ),
    )


def build_write_tool(
) -> ToolDefinition:
    async def handler(
        arguments: WriteInput,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        del context

        return {
            "created": True,
            "recommendation_id": (
                arguments.recommendation_id
            ),
        }

    return ToolDefinition(
        name=(
            "create_task_from_approved_recommendation"
        ),
        description=(
            "Create one controlled task from an "
            "approved recommendation."
        ),
        input_model=WriteInput,
        output_model=WriteOutput,
        handler=handler,
        access_mode=ToolAccessMode.WRITE,
        allowed_agents=(
            "Recommendation Agent",
        ),
        requires_human_approval=True,
        enabled=True,
    )


def build_context(
    *,
    agent_name: str,
    allowed_tools: list[str],
    allow_write_tools: bool = False,
    approved_write_tools: list[str] | None = None,
) -> ToolExecutionContext:
    return ToolExecutionContext(
        run_id="RUN-MCP-001",
        agent_name=agent_name,
        requested_by="pytest",
        allowed_tools=allowed_tools,
        allow_write_tools=allow_write_tools,
        approved_write_tools=(
            approved_write_tools
            or []
        ),
    )


def build_service(
    registry: ToolRegistry,
    *,
    tools_enabled: bool = True,
    write_tools_enabled: bool = False,
) -> ControlledMCPToolService:
    executor = AgentToolExecutor(
        registry,
        tools_enabled=tools_enabled,
        write_tools_enabled=write_tools_enabled,
        timeout_seconds=1.0,
    )

    return ControlledMCPToolService(
        registry=registry,
        executor=executor,
    )


def test_adapter_targets_current_mcp_revision(
) -> None:
    assert MCP_PROTOCOL_TARGET == "2026-07-28"


def test_list_tools_returns_modern_private_uncached_shape(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )

    result = build_service(
        registry
    ).list_tools(
        context=build_context(
            agent_name="Root-Cause Agent",
            allowed_tools=[
                "get_issue",
            ],
        )
    )

    payload = result.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )

    assert payload[
        "resultType"
    ] == "complete"
    assert payload[
        "ttlMs"
    ] == 0
    assert payload[
        "cacheScope"
    ] == "private"
    assert [
        tool[
            "name"
        ]
        for tool in payload[
            "tools"
        ]
    ] == [
        "get_issue"
    ]


def test_list_tools_is_deterministic_and_filters_disabled_tools(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )

    async def second_handler(
        arguments: ReadInput,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        del context

        return {
            "issue_id": arguments.issue_id,
            "status": "Open",
        }

    registry.register(
        ToolDefinition(
            name="get_disabled_issue",
            description="Disabled controlled issue tool.",
            input_model=ReadInput,
            output_model=ReadOutput,
            handler=second_handler,
            allowed_agents=(
                "Root-Cause Agent",
            ),
            enabled=False,
            disabled_reason="Disabled for test.",
        )
    )

    result = build_service(
        registry
    ).list_tools(
        context=build_context(
            agent_name="Root-Cause Agent",
            allowed_tools=[
                "get_disabled_issue",
                "get_issue",
            ],
        )
    )

    assert [
        item.name
        for item in result.tools
    ] == [
        "get_issue"
    ]


def test_mcp_descriptor_reuses_internal_input_and_output_schemas(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )

    result = build_service(
        registry
    ).list_tools(
        context=build_context(
            agent_name="Root-Cause Agent",
            allowed_tools=[
                "get_issue",
            ],
        )
    )

    descriptor = result.tools[
        0
    ]

    assert descriptor.input_schema[
        "properties"
    ]["issue_id"][
        "minLength"
    ] == 2

    assert descriptor.output_schema[
        "properties"
    ]["status"][
        "type"
    ] == "string"

    # Execution-context fields are injected by the server and never
    # become model/MCP arguments.
    input_schema_text = json.dumps(
        descriptor.input_schema,
        sort_keys=True,
    )

    assert "agent_name" not in input_schema_text
    assert "allowed_tools" not in input_schema_text
    assert "approved_write_tools" not in input_schema_text


def test_read_tool_annotations_are_conservative(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )

    descriptor = build_service(
        registry
    ).list_tools(
        context=build_context(
            agent_name="Root-Cause Agent",
            allowed_tools=[
                "get_issue",
            ],
        )
    ).tools[
        0
    ]

    payload = descriptor.annotations.model_dump(
        mode="json",
        by_alias=True,
    )

    assert payload == {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }


def test_write_tool_is_hidden_until_every_write_gate_passes(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_write_tool()
    )

    service = build_service(
        registry,
        write_tools_enabled=True,
    )

    hidden = service.list_tools(
        context=build_context(
            agent_name="Recommendation Agent",
            allowed_tools=[
                "create_task_from_approved_recommendation",
            ],
            allow_write_tools=True,
            approved_write_tools=[],
        )
    )

    assert hidden.tools == []

    visible = service.list_tools(
        context=build_context(
            agent_name="Recommendation Agent",
            allowed_tools=[
                "create_task_from_approved_recommendation",
            ],
            allow_write_tools=True,
            approved_write_tools=[
                "create_task_from_approved_recommendation",
            ],
        )
    )

    assert [
        item.name
        for item in visible.tools
    ] == [
        "create_task_from_approved_recommendation"
    ]

    annotations = visible.tools[
        0
    ].annotations

    assert annotations.read_only_hint is False
    assert annotations.destructive_hint is True
    assert annotations.idempotent_hint is False
    assert annotations.open_world_hint is False


def test_successful_call_returns_structured_content_and_safe_meta(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )

    result = asyncio.run(
        build_service(
            registry
        ).call_tool(
            name="get_issue",
            arguments={
                "issue_id": "ISSUE-001",
            },
            context=build_context(
                agent_name="Root-Cause Agent",
                allowed_tools=[
                    "get_issue",
                ],
            ),
        )
    )

    payload = result.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )

    assert payload[
        "resultType"
    ] == "complete"
    assert payload[
        "isError"
    ] is False
    assert payload[
        "structuredContent"
    ] == {
        "issue_id": "ISSUE-001",
        "status": "Open",
    }

    assert payload[
        "content"
    ][0][
        "type"
    ] == "text"

    assert payload[
        "_meta"
    ][
        "toolName"
    ] == "get_issue"

    meta_text = json.dumps(
        payload[
            "_meta"
        ],
        sort_keys=True,
    )

    assert "ISSUE-001" not in meta_text


def test_invalid_arguments_return_mcp_tool_error_without_handler_call(
) -> None:
    calls: list[str] = []

    async def handler(
        arguments: ReadInput,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        del arguments
        del context
        calls.append(
            "called"
        )

        return {
            "issue_id": "ISSUE",
            "status": "Open",
        }

    registry = ToolRegistry()

    registry.register(
        ToolDefinition(
            name="get_issue",
            description="Read one controlled issue record.",
            input_model=ReadInput,
            output_model=ReadOutput,
            handler=handler,
            allowed_agents=(
                "Root-Cause Agent",
            ),
        )
    )

    result = asyncio.run(
        build_service(
            registry
        ).call_tool(
            name="get_issue",
            arguments={
                "issue_id": "",
            },
            context=build_context(
                agent_name="Root-Cause Agent",
                allowed_tools=[
                    "get_issue",
                ],
            ),
        )
    )

    assert calls == []
    assert result.is_error is True
    assert result.structured_content is None

    content_text = result.content[
        0
    ].text

    assert "ToolInputValidationError" in content_text
    assert 'issue_id": ""' not in content_text


def test_unknown_and_unauthorized_tools_share_generic_protocol_error(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )

    service = build_service(
        registry
    )

    context = build_context(
        agent_name="Root-Cause Agent",
        allowed_tools=[],
    )

    with pytest.raises(
        MCPToolUnavailableError,
        match="unavailable",
    ):
        asyncio.run(
            service.call_tool(
                name="get_issue",
                arguments={
                    "issue_id": "ISSUE-001",
                },
                context=context,
            )
        )

    with pytest.raises(
        MCPToolUnavailableError,
        match="unavailable",
    ):
        asyncio.run(
            service.call_tool(
                name="invented_tool",
                arguments={},
                context=context,
            )
        )


def test_write_call_still_executes_only_through_write_gates(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_write_tool()
    )

    service = build_service(
        registry,
        write_tools_enabled=True,
    )

    result = asyncio.run(
        service.call_tool(
            name="create_task_from_approved_recommendation",
            arguments={
                "recommendation_id": 21,
            },
            context=build_context(
                agent_name="Recommendation Agent",
                allowed_tools=[
                    "create_task_from_approved_recommendation",
                ],
                allow_write_tools=True,
                approved_write_tools=[
                    "create_task_from_approved_recommendation",
                ],
            ),
        )
    )

    assert result.is_error is False
    assert result.structured_content == {
        "created": True,
        "recommendation_id": 21,
    }


def test_globally_disabled_tools_produce_empty_list(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )

    result = build_service(
        registry,
        tools_enabled=False,
    ).list_tools(
        context=build_context(
            agent_name="Root-Cause Agent",
            allowed_tools=[
                "get_issue",
            ],
        )
    )

    assert result.tools == []


def test_mcp_serialization_uses_protocol_camel_case_fields(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )

    descriptor = build_service(
        registry
    ).list_tools(
        context=build_context(
            agent_name="Root-Cause Agent",
            allowed_tools=[
                "get_issue",
            ],
        )
    ).tools[
        0
    ]

    payload = descriptor.model_dump(
        mode="json",
        by_alias=True,
    )

    assert "inputSchema" in payload
    assert "outputSchema" in payload
    assert "input_schema" not in payload
    assert "output_schema" not in payload

    assert payload[
        "annotations"
    ][
        "readOnlyHint"
    ] is True
