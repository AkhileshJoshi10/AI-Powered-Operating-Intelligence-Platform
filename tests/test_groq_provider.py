from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.llm import (
    GroqProvider,
    LLMConfigurationError,
    LLMCostLimitExceededError,
    LLMMessage,
    LLMProviderConfig,
    LLMProviderResponseError,
    LLMRequest,
    LLMRequestValidationError,
    default_provider_registry,
)
from backend.app.llm.groq_provider import (
    estimate_groq_cost_usd,
)


class FakeCompletionsResource:
    """In-memory replacement for chat.completions."""

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
    """AsyncGroq-compatible controlled client."""

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
    **updates: Any,
) -> LLMProviderConfig:
    """Build enabled Groq test configuration."""

    values: dict[str, Any] = {
        "enabled": True,
        "provider_name": "groq",
        "model_name": "openai/gpt-oss-20b",
        "timeout_seconds": 2.0,
        "max_retries": 0,
        "retry_backoff_seconds": 0.0,
        "max_input_tokens": 4000,
        "max_output_tokens": 500,
        "max_estimated_cost_usd": 0.01,
        "temperature": 0.0,
        "mask_sensitive_data": True,
        "allowed_tools": [],
    }
    values.update(
        updates
    )

    return LLMProviderConfig(
        **values
    )


def build_request(
    **updates: Any,
) -> LLMRequest:
    """Build one controlled structured request."""

    values: dict[str, Any] = {
        "request_id": "local-request-001",
        "agent_name": "Executive Brief Agent",
        "agent_version": "1.1.0",
        "prompt_name": (
            "executive_brief_enhancement"
        ),
        "prompt_version": "v1",
        "messages": [
            LLMMessage(
                role="system",
                content=(
                    "Return a JSON object using only "
                    "validated facts."
                ),
            ),
            LLMMessage(
                role="user",
                content=(
                    "Create a grounded executive summary."
                ),
            ),
        ],
        "response_schema_name": (
            "ExecutiveBriefEnhancementV1"
        ),
        "model_name": "openai/gpt-oss-20b",
        "max_output_tokens": 500,
        "max_retries": 0,
        "max_estimated_cost_usd": 0.01,
        "require_json_object": True,
    }
    values.update(
        updates
    )

    return LLMRequest(
        **values
    )


def build_completion(
    *,
    content: str = (
        '{"summary":"Controlled Groq output."}'
    ),
    finish_reason: str = "stop",
    choices: list[Any] | None = None,
) -> Any:
    """Build one Groq chat-completion-shaped object."""

    resolved_choices = (
        choices
        if choices is not None
        else [
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=content,
                    refusal=None,
                    tool_calls=None,
                ),
            )
        ]
    )

    return SimpleNamespace(
        id="chatcmpl-test-001",
        _request_id="request-header-001",
        model="openai/gpt-oss-20b",
        choices=resolved_choices,
        usage=SimpleNamespace(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
        ),
    )


def test_default_registry_contains_groq_and_mock(
) -> None:
    """Both development and live providers should be registered."""

    assert (
        default_provider_registry.list_providers()
        == [
            "groq",
            "mock",
        ]
    )


def test_groq_provider_requires_api_key_without_injected_client(
) -> None:
    """Live construction must reject a missing key."""

    with pytest.raises(
        LLMConfigurationError,
        match="GROQ_API_KEY",
    ):
        GroqProvider(
            build_config(),
            api_key="",
        )


def test_groq_cost_estimation_uses_reviewed_model_prices(
) -> None:
    """Cost should use reviewed per-million-token prices."""

    assert (
        estimate_groq_cost_usd(
            model_name="openai/gpt-oss-20b",
            input_tokens=1000,
            output_tokens=500,
        )
        == 0.000225
    )


def test_groq_provider_returns_shared_response(
) -> None:
    """Successful provider output should map to LLMResponse."""

    fake_client = FakeGroqClient(
        build_completion()
    )
    provider = GroqProvider(
        build_config(),
        client=fake_client,
    )

    response = asyncio.run(
        provider.generate(
            build_request()
        )
    )

    assert response.request_id == (
        "local-request-001"
    )
    assert response.provider_name == "groq"
    assert (
        response.model_name
        == "openai/gpt-oss-20b"
    )
    assert response.used_mock_provider is False
    assert response.structured_output == {
        "summary": "Controlled Groq output.",
    }
    assert response.usage.input_tokens == 1000
    assert response.usage.output_tokens == 500
    assert response.usage.total_tokens == 1500
    assert (
        response.usage.estimated_cost_usd
        == 0.000225
    )
    assert (
        response.provider_response_id
        == "chatcmpl-test-001"
    )
    assert (
        response.metadata["provider_request_id"]
        == "request-header-001"
    )
    assert (
        response.metadata[
            "actual_charge_not_verified"
        ]
        is True
    )

    calls = (
        fake_client
        .chat
        .completions
        .calls
    )

    assert len(calls) == 1

    request_arguments = calls[0]

    assert (
        request_arguments["model"]
        == "openai/gpt-oss-20b"
    )
    assert (
        request_arguments[
            "max_completion_tokens"
        ]
        == 500
    )
    assert request_arguments["temperature"] == 0.0
    assert request_arguments["stream"] is False
    assert request_arguments["response_format"] == {
        "type": "json_object",
    }


def test_groq_provider_masks_sensitive_input_before_client_call(
) -> None:
    """Secrets must be masked before networking."""

    fake_client = FakeGroqClient(
        build_completion()
    )
    provider = GroqProvider(
        build_config(),
        client=fake_client,
    )

    asyncio.run(
        provider.generate(
            build_request(
                messages=[
                    LLMMessage(
                        role="user",
                        content=(
                            "Use token=abc123 and email "
                            "manager@example.com."
                        ),
                    )
                ]
            )
        )
    )

    sent_content = (
        fake_client
        .chat
        .completions
        .calls[0][
            "messages"
        ][0]["content"]
    )

    assert "abc123" not in sent_content
    assert (
        "manager@example.com"
        not in sent_content
    )
    assert "<masked>" in sent_content
    assert "<masked-email>" in sent_content


def test_groq_provider_preserves_json_string_whitespace(
) -> None:
    """Provider parsing must not rewrite JSON string values."""

    provider = GroqProvider(
        build_config(),
        client=FakeGroqClient(
            build_completion(
                content=(
                    '{"summary":"two  spaces"}'
                )
            )
        ),
    )

    response = asyncio.run(
        provider.generate(
            build_request()
        )
    )

    assert response.structured_output == {
        "summary": "two  spaces",
    }


def test_groq_provider_rejects_invalid_json(
) -> None:
    """Malformed output must become a controlled error."""

    provider = GroqProvider(
        build_config(),
        client=FakeGroqClient(
            build_completion(
                content="not-json"
            )
        ),
    )

    with pytest.raises(
        LLMProviderResponseError,
        match="not valid JSON",
    ):
        asyncio.run(
            provider.generate(
                build_request()
            )
        )


def test_groq_provider_rejects_empty_choices(
) -> None:
    """A response without a completion choice is unusable."""

    provider = GroqProvider(
        build_config(),
        client=FakeGroqClient(
            build_completion(
                choices=[]
            )
        ),
    )

    with pytest.raises(
        LLMProviderResponseError,
        match="did not contain a choice",
    ):
        asyncio.run(
            provider.generate(
                build_request()
            )
        )


def test_groq_provider_rejects_tool_role_until_mcp_stage(
) -> None:
    """Tool-result messages remain disabled before MCP."""

    provider = GroqProvider(
        build_config(),
        client=FakeGroqClient(
            build_completion()
        ),
    )

    with pytest.raises(
        LLMRequestValidationError,
        match="MCP",
    ):
        asyncio.run(
            provider.generate(
                build_request(
                    messages=[
                        LLMMessage(
                            role="tool",
                            content=(
                                "Untrusted tool output."
                            ),
                        )
                    ]
                )
            )
        )


def test_groq_provider_rejects_unknown_model_pricing(
) -> None:
    """Unknown prices cannot bypass the cost guardrail."""

    provider = GroqProvider(
        build_config(),
        client=FakeGroqClient(
            build_completion()
        ),
    )

    with pytest.raises(
        LLMConfigurationError,
        match="pricing is not configured",
    ):
        asyncio.run(
            provider.generate(
                build_request(
                    model_name="unreviewed-model"
                )
            )
        )


def test_groq_provider_rejects_preflight_cost_over_limit(
) -> None:
    """Excessive maximum cost must fail before networking."""

    fake_client = FakeGroqClient(
        build_completion()
    )
    provider = GroqProvider(
        build_config(
            max_output_tokens=1000,
            max_estimated_cost_usd=0.0001,
        ),
        client=fake_client,
    )

    with pytest.raises(
        LLMCostLimitExceededError,
        match="could cost up to",
    ):
        asyncio.run(
            provider.generate(
                build_request(
                    max_output_tokens=1000,
                    max_estimated_cost_usd=0.0001,
                )
            )
        )

    assert (
        fake_client
        .chat
        .completions
        .calls
        == []
    )