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

from backend.app.llm import (
    BaseLLMProvider,
    LLMMessage,
    LLMProviderConfig,
    LLMRequest,
    LLMRequestValidationError,
    LLMResponse,
    LLMTokenUsage,
    LLMToolCall,
    LLMToolDefinition,
)
from backend.app.services.llm_tool_execution_service import (
    ControlledLLMToolExecutionService,
    ControlledLLMToolLoopError,
)
from backend.app.tools import (
    AgentToolExecutor,
    ToolAccessMode,
    ToolDefinition,
    ToolExecutionContext,
    ToolRegistry,
)
from backend.app.tools.llm_tool_adapter import (
    build_exposed_llm_tools,
)


class ReadInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    issue_id: str = Field(
        min_length=1,
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


def build_read_tool(
    *,
    name: str = "get_issue",
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
        name=name,
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


def build_llm_read_tool_definition(
) -> LLMToolDefinition:
    """Build the valid provider-side contract for get_issue."""

    return LLMToolDefinition(
        name="get_issue",
        description="Read one controlled issue record.",
        parameters=ReadInput.model_json_schema(),
    )


def build_write_tool(
) -> ToolDefinition:
    async def handler(
        arguments: WriteInput,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        del arguments
        del context

        return {
            "created": True,
        }

    return ToolDefinition(
        name="create_task_from_approved_recommendation",
        description="Create a task from an approved recommendation.",
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
    agent_name: str = "Root-Cause Agent",
    allowed_tools: list[str] | None = None,
    allow_write_tools: bool = False,
    approved_write_tools: list[str] | None = None,
) -> ToolExecutionContext:
    return ToolExecutionContext(
        run_id="RUN-LLM-TOOLS-001",
        agent_name=agent_name,
        requested_by="pytest",
        allowed_tools=(
            allowed_tools
            if allowed_tools is not None
            else [
                "get_issue",
            ]
        ),
        allow_write_tools=allow_write_tools,
        approved_write_tools=(
            approved_write_tools
            or []
        ),
    )


def build_config(
    *,
    allowed_tools: list[str],
) -> LLMProviderConfig:
    return LLMProviderConfig(
        enabled=True,
        provider_name="scripted",
        model_name="scripted-model",
        timeout_seconds=1.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        max_input_tokens=10000,
        max_output_tokens=1000,
        max_estimated_cost_usd=1.0,
        temperature=0.0,
        mask_sensitive_data=True,
        allowed_tools=allowed_tools,
    )


def build_request(
    *,
    agent_name: str = "Root-Cause Agent",
    allowed_tools: list[str] | None = None,
    tools: list[LLMToolDefinition] | None = None,
    tool_choice: str = "auto",
) -> LLMRequest:
    return LLMRequest(
        request_id="request-loop-001",
        agent_name=agent_name,
        agent_version="1.0.0",
        prompt_name="root_cause_explanation",
        prompt_version="v1",
        messages=[
            LLMMessage(
                role="system",
                content=(
                    "Use controlled tools only through "
                    "the supplied contracts."
                ),
            ),
            LLMMessage(
                role="user",
                content="Read the issue and then answer.",
            ),
        ],
        response_schema_name="RootCauseEnhancementV1",
        require_json_object=True,
        max_output_tokens=500,
        max_retries=0,
        max_estimated_cost_usd=1.0,
        allowed_tools=(
            allowed_tools
            if allowed_tools is not None
            else [
                "get_issue",
            ]
        ),
        tools=tools or [],
        tool_choice=tool_choice,
    )


def build_response(
    request: LLMRequest,
    *,
    finish_reason: str,
    tool_calls: list[LLMToolCall] | None = None,
    structured_output: dict[str, Any] | None = None,
    input_tokens: int = 10,
    output_tokens: int = 5,
) -> LLMResponse:
    return LLMResponse(
        request_id=request.request_id,
        provider_name="scripted",
        model_name="scripted-model",
        content=(
            ""
            if finish_reason == "tool_call"
            else json.dumps(
                structured_output
                or {
                    "summary": "Final grounded response.",
                }
            )
        ),
        structured_output=(
            None
            if finish_reason == "tool_call"
            else (
                structured_output
                or {
                    "summary": "Final grounded response.",
                }
            )
        ),
        tool_calls=tool_calls or [],
        usage=LLMTokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=(
                input_tokens
                + output_tokens
            ),
            estimated_cost_usd=0.001,
        ),
        latency_ms=2.0,
        finish_reason=finish_reason,
        prompt_name=request.prompt_name,
        prompt_version=request.prompt_version,
        agent_name=request.agent_name,
        agent_version=request.agent_version,
    )


class ScriptedProvider(
    BaseLLMProvider
):
    provider_name = "scripted"

    def __init__(
        self,
        config: LLMProviderConfig,
        builders: list[Any],
    ) -> None:
        super().__init__(
            config
        )
        self.builders = list(
            builders
        )
        self.requests: list[
            LLMRequest
        ] = []

    async def _generate_once(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        self.requests.append(
            request
        )

        if not self.builders:
            raise AssertionError(
                "Unexpected extra provider call."
            )

        builder = self.builders.pop(
            0
        )

        return builder(
            request
        )


def build_service(
    *,
    registry: ToolRegistry,
    provider: BaseLLMProvider,
    tools_enabled: bool = True,
    write_tools_enabled: bool = False,
    maximum_tool_rounds: int = 2,
    maximum_tool_result_characters: int = 20000,
) -> ControlledLLMToolExecutionService:
    executor = AgentToolExecutor(
        registry,
        tools_enabled=tools_enabled,
        write_tools_enabled=write_tools_enabled,
        timeout_seconds=1.0,
    )

    return ControlledLLMToolExecutionService(
        provider=provider,
        registry=registry,
        executor=executor,
        maximum_tool_rounds=(
            maximum_tool_rounds
        ),
        maximum_tool_result_characters=(
            maximum_tool_result_characters
        ),
    )


def test_adapter_exposes_only_currently_permitted_tool(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )
    registry.register(
        build_read_tool(
            name="get_disabled_issue",
            enabled=False,
        )
    )

    executor = AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=False,
        timeout_seconds=1.0,
    )

    exposed = build_exposed_llm_tools(
        registry=registry,
        executor=executor,
        context=build_context(
            allowed_tools=[
                "get_issue",
                "get_disabled_issue",
            ]
        ),
        requested_tool_names=[
            "get_issue",
            "get_disabled_issue",
        ],
    )

    assert [
        item.name
        for item in exposed
    ] == [
        "get_issue"
    ]

    assert exposed[
        0
    ].parameters["type"] == "object"


def test_adapter_does_not_expose_unapproved_write_tool(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_write_tool()
    )

    executor = AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=True,
        timeout_seconds=1.0,
    )

    exposed = build_exposed_llm_tools(
        registry=registry,
        executor=executor,
        context=build_context(
            agent_name="Recommendation Agent",
            allowed_tools=[
                "create_task_from_approved_recommendation"
            ],
            allow_write_tools=True,
            approved_write_tools=[],
        ),
        requested_tool_names=[
            "create_task_from_approved_recommendation"
        ],
    )

    assert exposed == []


def test_adapter_exposes_write_tool_only_after_all_write_gates(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_write_tool()
    )

    executor = AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=True,
        timeout_seconds=1.0,
    )

    exposed = build_exposed_llm_tools(
        registry=registry,
        executor=executor,
        context=build_context(
            agent_name="Recommendation Agent",
            allowed_tools=[
                "create_task_from_approved_recommendation"
            ],
            allow_write_tools=True,
            approved_write_tools=[
                "create_task_from_approved_recommendation"
            ],
        ),
        requested_tool_names=[
            "create_task_from_approved_recommendation"
        ],
    )

    assert [
        item.name
        for item in exposed
    ] == [
        "create_task_from_approved_recommendation"
    ]


def test_adapter_rejects_unknown_requested_tool(
) -> None:
    executor = AgentToolExecutor(
        ToolRegistry(),
        tools_enabled=True,
        write_tools_enabled=False,
        timeout_seconds=1.0,
    )

    with pytest.raises(
        LLMRequestValidationError,
        match="not registered",
    ):
        build_exposed_llm_tools(
            registry=ToolRegistry(),
            executor=executor,
            context=build_context(
                allowed_tools=[
                    "invented_tool",
                ]
            ),
            requested_tool_names=[
                "invented_tool",
            ],
        )


def test_loop_returns_direct_final_response_without_tool_execution(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )

    provider = ScriptedProvider(
        build_config(
            allowed_tools=[
                "get_issue",
            ]
        ),
        [
            lambda request: build_response(
                request,
                finish_reason="stop",
            )
        ],
    )

    result = asyncio.run(
        build_service(
            registry=registry,
            provider=provider,
        ).run(
            request=build_request(),
            context=build_context(),
        )
    )

    assert result.provider_call_count == 1
    assert result.tool_round_count == 0
    assert result.tool_call_records == []
    assert result.exposed_tools == [
        "get_issue"
    ]


def test_loop_executes_read_tool_and_returns_final_grounded_response(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )

    provider = ScriptedProvider(
        build_config(
            allowed_tools=[
                "get_issue",
            ]
        ),
        [
            lambda request: build_response(
                request,
                finish_reason="tool_call",
                tool_calls=[
                    LLMToolCall(
                        tool_call_id="call-001",
                        tool_name="get_issue",
                        arguments={
                            "issue_id": "ISSUE-HIGH-001",
                        },
                    )
                ],
            ),
            lambda request: build_response(
                request,
                finish_reason="stop",
                structured_output={
                    "summary": (
                        "Issue ISSUE-HIGH-001 is open."
                    ),
                },
            ),
        ],
    )

    result = asyncio.run(
        build_service(
            registry=registry,
            provider=provider,
        ).run(
            request=build_request(),
            context=build_context(),
        )
    )

    assert result.provider_call_count == 2
    assert result.tool_round_count == 1
    assert result.total_usage.input_tokens == 20
    assert result.total_usage.output_tokens == 10
    assert result.total_usage.total_tokens == 30
    assert result.total_usage.estimated_cost_usd == 0.002
    assert result.final_response.structured_output == {
        "summary": "Issue ISSUE-HIGH-001 is open.",
    }

    second_request = provider.requests[
        1
    ]

    assert second_request.messages[
        -2
    ].role == "assistant"
    assert second_request.messages[
        -2
    ].tool_calls[
        0
    ].tool_call_id == "call-001"

    assert second_request.messages[
        -1
    ].role == "tool"
    assert second_request.messages[
        -1
    ].tool_call_id == "call-001"

    payload = json.loads(
        second_request.messages[
            -1
        ].content
    )

    assert payload[
        "execution_status"
    ] == "Success"
    assert payload[
        "output"
    ]["issue_id"] == "ISSUE-HIGH-001"


def test_invalid_tool_arguments_are_not_executed_and_force_final_turn(
) -> None:
    calls: list[str] = []

    class CountingInput(BaseModel):
        model_config = ConfigDict(
            extra="forbid",
        )

        issue_id: str = Field(
            min_length=2,
        )

    async def handler(
        arguments: CountingInput,
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
            input_model=CountingInput,
            output_model=ReadOutput,
            handler=handler,
            allowed_agents=(
                "Root-Cause Agent",
            ),
        )
    )

    provider = ScriptedProvider(
        build_config(
            allowed_tools=[
                "get_issue",
            ]
        ),
        [
            lambda request: build_response(
                request,
                finish_reason="tool_call",
                tool_calls=[
                    LLMToolCall(
                        tool_call_id="call-invalid",
                        tool_name="get_issue",
                        arguments={
                            "issue_id": "",
                        },
                    )
                ],
            ),
            lambda request: build_response(
                request,
                finish_reason="stop",
            ),
        ],
    )

    result = asyncio.run(
        build_service(
            registry=registry,
            provider=provider,
        ).run(
            request=build_request(),
            context=build_context(),
        )
    )

    assert calls == []
    assert result.tool_call_records[
        0
    ]["execution_status"] == "Failed"
    assert provider.requests[
        1
    ].tool_choice == "none"


def test_tool_call_record_does_not_store_raw_arguments_or_output(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )

    secret_value = "SENSITIVE-ISSUE-VALUE"

    provider = ScriptedProvider(
        build_config(
            allowed_tools=[
                "get_issue",
            ]
        ),
        [
            lambda request: build_response(
                request,
                finish_reason="tool_call",
                tool_calls=[
                    LLMToolCall(
                        tool_call_id="call-secret",
                        tool_name="get_issue",
                        arguments={
                            "issue_id": secret_value,
                        },
                    )
                ],
            ),
            lambda request: build_response(
                request,
                finish_reason="stop",
            ),
        ],
    )

    result = asyncio.run(
        build_service(
            registry=registry,
            provider=provider,
        ).run(
            request=build_request(),
            context=build_context(),
        )
    )

    audit_text = json.dumps(
        result.tool_call_records,
        sort_keys=True,
    )

    assert secret_value not in audit_text
    assert (
        result.tool_call_records[
            0
        ]["provider_tool_call_id"]
        == "call-secret"
    )


def test_duplicate_provider_tool_call_id_is_rejected(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )

    duplicate_call = LLMToolCall(
        tool_call_id="call-repeat",
        tool_name="get_issue",
        arguments={
            "issue_id": "ISSUE-001",
        },
    )

    provider = ScriptedProvider(
        build_config(
            allowed_tools=[
                "get_issue",
            ]
        ),
        [
            lambda request: build_response(
                request,
                finish_reason="tool_call",
                tool_calls=[
                    duplicate_call
                ],
            ),
            lambda request: build_response(
                request,
                finish_reason="tool_call",
                tool_calls=[
                    duplicate_call
                ],
            ),
        ],
    )

    with pytest.raises(
        ControlledLLMToolLoopError,
        match="reused a tool_call_id",
    ):
        asyncio.run(
            build_service(
                registry=registry,
                provider=provider,
                maximum_tool_rounds=2,
            ).run(
                request=build_request(),
                context=build_context(),
            )
        )


def test_maximum_tool_rounds_forces_final_provider_turn(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )

    provider = ScriptedProvider(
        build_config(
            allowed_tools=[
                "get_issue",
            ]
        ),
        [
            lambda request: build_response(
                request,
                finish_reason="tool_call",
                tool_calls=[
                    LLMToolCall(
                        tool_call_id="call-round-1",
                        tool_name="get_issue",
                        arguments={
                            "issue_id": "ISSUE-001",
                        },
                    )
                ],
            ),
            lambda request: build_response(
                request,
                finish_reason="stop",
            ),
        ],
    )

    result = asyncio.run(
        build_service(
            registry=registry,
            provider=provider,
            maximum_tool_rounds=1,
        ).run(
            request=build_request(),
            context=build_context(),
        )
    )

    assert result.tool_round_count == 1
    assert provider.requests[
        1
    ].tool_choice == "none"


def test_oversized_tool_result_is_omitted_and_forces_final_turn(
) -> None:
    class LargeOutput(BaseModel):
        model_config = ConfigDict(
            extra="forbid",
        )

        text: str

    async def large_handler(
        arguments: ReadInput,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        del arguments
        del context

        return {
            "text": "x" * 5000,
        }

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="get_issue",
            description="Read one large controlled record.",
            input_model=ReadInput,
            output_model=LargeOutput,
            handler=large_handler,
            allowed_agents=(
                "Root-Cause Agent",
            ),
        )
    )

    provider = ScriptedProvider(
        build_config(
            allowed_tools=[
                "get_issue",
            ]
        ),
        [
            lambda request: build_response(
                request,
                finish_reason="tool_call",
                tool_calls=[
                    LLMToolCall(
                        tool_call_id="call-large",
                        tool_name="get_issue",
                        arguments={
                            "issue_id": "ISSUE-001",
                        },
                    )
                ],
            ),
            lambda request: build_response(
                request,
                finish_reason="stop",
            ),
        ],
    )

    result = asyncio.run(
        build_service(
            registry=registry,
            provider=provider,
            maximum_tool_result_characters=1000,
        ).run(
            request=build_request(),
            context=build_context(),
        )
    )

    assert (
        result.tool_call_records[
            0
        ]["delivery_status"]
        == "ResultTooLarge"
    )

    tool_payload = json.loads(
        provider.requests[
            1
        ].messages[
            -1
        ].content
    )

    assert tool_payload[
        "error"
    ]["error_type"] == "ToolResultTooLarge"
    assert provider.requests[
        1
    ].tool_choice == "none"


def test_request_and_tool_context_agent_names_must_match(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool()
    )

    provider = ScriptedProvider(
        build_config(
            allowed_tools=[
                "get_issue",
            ]
        ),
        [
            lambda request: build_response(
                request,
                finish_reason="stop",
            )
        ],
    )

    with pytest.raises(
        LLMRequestValidationError,
        match="agent_name must match",
    ):
        asyncio.run(
            build_service(
                registry=registry,
                provider=provider,
            ).run(
                request=build_request(
                    agent_name="Root-Cause Agent"
                ),
                context=build_context(
                    agent_name="Monitoring Agent"
                ),
            )
        )


def test_required_tool_choice_fails_when_no_tool_is_permitted(
) -> None:
    registry = ToolRegistry()
    registry.register(
        build_read_tool(
            enabled=False
        )
    )

    provider = ScriptedProvider(
        build_config(
            allowed_tools=[
                "get_issue",
            ]
        ),
        [],
    )

    with pytest.raises(
        LLMRequestValidationError,
        match="no currently permitted tool",
    ):
        asyncio.run(
            build_service(
                registry=registry,
                provider=provider,
            ).run(
                request=build_request(
                    tools=[
                        build_llm_read_tool_definition()
                    ],
                    tool_choice="required",
                ),
                context=build_context(),
            )
        )
