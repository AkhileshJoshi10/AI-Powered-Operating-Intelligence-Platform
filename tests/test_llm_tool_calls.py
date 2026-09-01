from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.llm import (
    GroqProvider,
    LLMMessage,
    LLMProviderConfig,
    LLMProviderResponseError,
    LLMRequest,
    LLMRequestValidationError,
    LLMToolCall,
    LLMToolDefinition,
    MockLLMProvider,
)


class FakeCompletionsResource:
    """In-memory replacement for Groq chat.completions."""

    def __init__(
        self,
        completion: Any,
    ) -> None:
        self.completion = completion
        self.calls: list[
            dict[str, Any]
        ] = []

    async def create(
        self,
        **kwargs: Any,
    ) -> Any:
        self.calls.append(
            kwargs
        )
        return self.completion


class FakeGroqClient:
    """AsyncGroq-compatible test client."""

    def __init__(
        self,
        completion: Any,
    ) -> None:
        self.chat = SimpleNamespace(
            completions=FakeCompletionsResource(
                completion
            )
        )


def build_config(
    *,
    provider_name: str,
) -> LLMProviderConfig:
    return LLMProviderConfig(
        enabled=True,
        provider_name=provider_name,
        model_name=(
            "openai/gpt-oss-20b"
            if provider_name == "groq"
            else "mock-deterministic-v1"
        ),
        timeout_seconds=2.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        max_input_tokens=8000,
        max_output_tokens=500,
        max_estimated_cost_usd=0.02,
        temperature=0.0,
        mask_sensitive_data=True,
        allowed_tools=[
            "get_issue",
            "get_task",
        ],
    )


def build_tool(
    name: str = "get_issue",
) -> LLMToolDefinition:
    if name == "get_task":
        properties = {
            "task_id": {
                "type": "integer",
            },
        }
        required = [
            "task_id",
        ]
        description = "Read one validated business task."
    else:
        properties = {
            "issue_id": {
                "type": "string",
            },
        }
        required = [
            "issue_id",
        ]
        description = "Read one validated business issue."

    return LLMToolDefinition(
        name=name,
        description=description,
        parameters={
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    )


def build_request(
    *,
    messages: list[LLMMessage] | None = None,
    tools: list[LLMToolDefinition] | None = None,
    allowed_tools: list[str] | None = None,
    tool_choice: str = "auto",
    metadata: dict[str, Any] | None = None,
) -> LLMRequest:
    return LLMRequest(
        request_id="tool-request-001",
        agent_name="Root-Cause Agent",
        agent_version="1.0.0",
        prompt_name="root_cause_explanation",
        prompt_version="v1",
        messages=messages
        or [
            LLMMessage(
                role="system",
                content="Use tools only when required.",
            ),
            LLMMessage(
                role="user",
                content="Read the issue before answering.",
            ),
        ],
        response_schema_name="RootCauseEnhancementV1",
        model_name=(
            "openai/gpt-oss-20b"
        ),
        max_output_tokens=500,
        max_retries=0,
        max_estimated_cost_usd=0.02,
        allowed_tools=(
            allowed_tools
            if allowed_tools is not None
            else [
                "get_issue",
            ]
        ),
        tools=(
            tools
            if tools is not None
            else [
                build_tool()
            ]
        ),
        tool_choice=tool_choice,
        require_json_object=True,
        metadata=metadata or {},
    )


def build_completion(
    *,
    content: str | None = (
        '{"summary":"Controlled final response."}'
    ),
    finish_reason: str = "stop",
    tool_calls: list[Any] | None = None,
) -> Any:
    return SimpleNamespace(
        id="chatcmpl-tool-test",
        _request_id="request-header-tool-test",
        model="openai/gpt-oss-20b",
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=content,
                    refusal=None,
                    tool_calls=tool_calls,
                ),
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=500,
            completion_tokens=100,
            total_tokens=600,
        ),
    )


def test_tool_definition_must_be_inside_request_allowlist(
) -> None:
    with pytest.raises(
        ValueError,
        match="Tool definitions must also appear",
    ):
        build_request(
            allowed_tools=[],
            tools=[
                build_tool()
            ],
        )


def test_mock_provider_can_emit_tool_call_without_final_json(
) -> None:
    provider = MockLLMProvider(
        build_config(
            provider_name="mock"
        )
    )

    response = asyncio.run(
        provider.generate(
            build_request(
                metadata={
                    "mock_tool_calls": [
                        {
                            "tool_call_id": "call-mock-001",
                            "tool_name": "get_issue",
                            "arguments": {
                                "issue_id": "ISSUE-HIGH-001",
                            },
                        }
                    ],
                }
            )
        )
    )

    assert response.finish_reason == "tool_call"
    assert response.content == ""
    assert response.structured_output is None
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "get_issue"


def test_mock_provider_rejects_tool_not_exposed_this_turn(
) -> None:
    provider = MockLLMProvider(
        build_config(
            provider_name="mock"
        )
    )

    with pytest.raises(
        LLMProviderResponseError,
        match="unrequested tool",
    ):
        asyncio.run(
            provider.generate(
                build_request(
                    metadata={
                        "mock_tool_calls": [
                            {
                                "tool_call_id": "call-mock-002",
                                "tool_name": "get_task",
                                "arguments": {
                                    "task_id": 1,
                                },
                            }
                        ],
                    }
                )
            )
        )


def test_tool_call_arguments_are_masked_in_message_history(
) -> None:
    provider = MockLLMProvider(
        build_config(
            provider_name="mock"
        )
    )

    prepared = provider.prepare_request(
        build_request(
            messages=[
                LLMMessage(
                    role="user",
                    content="Read the issue.",
                ),
                LLMMessage(
                    role="assistant",
                    tool_calls=[
                        LLMToolCall(
                            tool_call_id="call-mask-001",
                            tool_name="get_issue",
                            arguments={
                                "contact": (
                                    "manager@example.com"
                                ),
                                "token_value": (
                                    "token=abc123"
                                ),
                            },
                        )
                    ],
                ),
            ],
        )
    )

    arguments = (
        prepared.messages[1]
        .tool_calls[0]
        .arguments
    )

    assert arguments[
        "contact"
    ] == "<masked-email>"
    assert "abc123" not in arguments[
        "token_value"
    ]


def test_groq_sends_local_tool_schema_and_choice(
) -> None:
    fake_client = FakeGroqClient(
        build_completion()
    )
    provider = GroqProvider(
        build_config(
            provider_name="groq"
        ),
        client=fake_client,
    )

    response = asyncio.run(
        provider.generate(
            build_request()
        )
    )

    assert response.finish_reason == "stop"

    sent = (
        fake_client.chat
        .completions.calls[0]
    )

    assert sent["tool_choice"] == "auto"
    assert sent[
        "parallel_tool_calls"
    ] is False
    assert sent["tools"][0][
        "function"
    ]["name"] == "get_issue"

    # The first tool-selection turn may return tool_calls with no text,
    # so final structured-output mode is deferred to the post-tool turn.
    assert "response_format" not in sent


def test_groq_parses_valid_local_tool_call(
) -> None:
    completion = build_completion(
        content=None,
        finish_reason="tool_calls",
        tool_calls=[
            SimpleNamespace(
                id="call-groq-001",
                type="function",
                function=SimpleNamespace(
                    name="get_issue",
                    arguments=(
                        '{"issue_id":"ISSUE-HIGH-001"}'
                    ),
                ),
            )
        ],
    )

    provider = GroqProvider(
        build_config(
            provider_name="groq"
        ),
        client=FakeGroqClient(
            completion
        ),
    )

    response = asyncio.run(
        provider.generate(
            build_request()
        )
    )

    assert response.finish_reason == "tool_call"
    assert response.content == ""
    assert response.structured_output is None
    assert response.tool_calls == [
        LLMToolCall(
            tool_call_id="call-groq-001",
            tool_name="get_issue",
            arguments={
                "issue_id": "ISSUE-HIGH-001",
            },
        )
    ]


def test_groq_rejects_malformed_tool_arguments(
) -> None:
    completion = build_completion(
        content=None,
        finish_reason="tool_calls",
        tool_calls=[
            SimpleNamespace(
                id="call-groq-bad-json",
                type="function",
                function=SimpleNamespace(
                    name="get_issue",
                    arguments="{not-json",
                ),
            )
        ],
    )

    provider = GroqProvider(
        build_config(
            provider_name="groq"
        ),
        client=FakeGroqClient(
            completion
        ),
    )

    with pytest.raises(
        LLMProviderResponseError,
        match="invalid JSON tool arguments",
    ):
        asyncio.run(
            provider.generate(
                build_request()
            )
        )


def test_groq_rejects_unexposed_tool_name(
) -> None:
    completion = build_completion(
        content=None,
        finish_reason="tool_calls",
        tool_calls=[
            SimpleNamespace(
                id="call-groq-task",
                type="function",
                function=SimpleNamespace(
                    name="get_task",
                    arguments='{"task_id":1}',
                ),
            )
        ],
    )

    provider = GroqProvider(
        build_config(
            provider_name="groq"
        ),
        client=FakeGroqClient(
            completion
        ),
    )

    with pytest.raises(
        LLMProviderResponseError,
        match="unapproved tool",
    ):
        asyncio.run(
            provider.generate(
                build_request()
            )
        )


def test_linked_tool_result_is_sent_back_to_groq(
) -> None:
    fake_client = FakeGroqClient(
        build_completion()
    )
    provider = GroqProvider(
        build_config(
            provider_name="groq"
        ),
        client=fake_client,
    )

    response = asyncio.run(
        provider.generate(
            build_request(
                tool_choice="none",
                messages=[
                    LLMMessage(
                        role="user",
                        content="Read issue ISSUE-HIGH-001.",
                    ),
                    LLMMessage(
                        role="assistant",
                        tool_calls=[
                            LLMToolCall(
                                tool_call_id="call-history-001",
                                tool_name="get_issue",
                                arguments={
                                    "issue_id": "ISSUE-HIGH-001",
                                },
                            )
                        ],
                    ),
                    LLMMessage(
                        role="tool",
                        content=(
                            '{"found":true,'
                            '"issue":{"issue_id":'
                            '"ISSUE-HIGH-001"}}'
                        ),
                        name="get_issue",
                        tool_call_id="call-history-001",
                    ),
                ],
            )
        )
    )

    assert response.finish_reason == "stop"

    sent = (
        fake_client.chat
        .completions.calls[0]
    )

    assert sent["tool_choice"] == "none"
    assert (
        sent["messages"][1][
            "tool_calls"
        ][0]["id"]
        == "call-history-001"
    )
    assert (
        sent["messages"][2][
            "tool_call_id"
        ]
        == "call-history-001"
    )
    assert sent[
        "response_format"
    ] == {
        "type": "json_object",
    }


def test_unlinked_tool_result_preserves_controlled_rejection(
) -> None:
    """Backwards-compatible guard for unvalidated tool-result messages."""

    provider = GroqProvider(
        build_config(
            provider_name="groq"
        ),
        client=FakeGroqClient(
            build_completion()
        ),
    )

    with pytest.raises(
        LLMRequestValidationError,
        match="controlled tool execution is disabled",
    ):
        asyncio.run(
            provider.generate(
                LLMRequest(
                    request_id="unlinked-tool-result",
                    agent_name="Root-Cause Agent",
                    prompt_name="root_cause_explanation",
                    prompt_version="v1",
                    messages=[
                        LLMMessage(
                            role="tool",
                            content="Untrusted tool output.",
                        )
                    ],
                    require_json_object=True,
                )
            )
        )


def test_tool_choice_none_rejects_unexpected_tool_call(
) -> None:
    completion = build_completion(
        content=None,
        finish_reason="tool_calls",
        tool_calls=[
            SimpleNamespace(
                id="call-unexpected-001",
                type="function",
                function=SimpleNamespace(
                    name="get_issue",
                    arguments=(
                        '{"issue_id":"ISSUE-HIGH-001"}'
                    ),
                ),
            )
        ],
    )

    provider = GroqProvider(
        build_config(
            provider_name="groq"
        ),
        client=FakeGroqClient(
            completion
        ),
    )

    with pytest.raises(
        LLMProviderResponseError,
        match="tool_choice='none'",
    ):
        asyncio.run(
            provider.generate(
                build_request(
                    tool_choice="none",
                )
            )
        )
