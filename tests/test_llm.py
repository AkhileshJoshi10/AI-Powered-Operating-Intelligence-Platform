from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

import pytest

from backend.app.llm import (
    BaseLLMProvider,
    LLMConfigurationError,
    LLMCostLimitExceededError,
    LLMMessage,
    LLMProviderConfig,
    LLMProviderDisabledError,
    LLMProviderNotFoundError,
    LLMProviderRegistry,
    LLMProviderResponseError,
    LLMRateLimitError,
    LLMRequest,
    LLMRequestValidationError,
    LLMResponse,
    LLMTimeoutError,
    LLMTokenUsage,
    LLMToolPermissionError,
    MockLLMProvider,
    PromptRegistry,
    PromptTemplate,
    default_prompt_registry,
    estimate_tokens,
    mask_sensitive_text,
    mask_sensitive_value,
)


def build_request(
    *,
    messages: list[LLMMessage] | None = None,
    require_json_object: bool = True,
    max_output_tokens: int | None = None,
    timeout_seconds: float | None = None,
    max_retries: int | None = None,
    max_estimated_cost_usd: float | None = None,
    allowed_tools: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> LLMRequest:
    """Build one controlled provider-independent request."""

    return LLMRequest(
        request_id="request-001",
        agent_name="Executive Brief Agent",
        agent_version="1.0.0",
        prompt_name="executive_brief_enhancement",
        prompt_version="v1",
        messages=messages
        or [
            LLMMessage(
                role="system",
                content="Use only validated evidence.",
            ),
            LLMMessage(
                role="user",
                content="Create a controlled JSON response.",
            ),
        ],
        response_schema_name="ExecutiveBriefEnhancementV1",
        require_json_object=require_json_object,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        max_estimated_cost_usd=max_estimated_cost_usd,
        allowed_tools=allowed_tools or [],
        metadata=metadata or {},
    )


def build_config(
    **updates: Any,
) -> LLMProviderConfig:
    """Build enabled mock configuration for tests."""

    values: dict[str, Any] = {
        "enabled": True,
        "provider_name": "mock",
        "model_name": "mock-deterministic-v1",
        "timeout_seconds": 1.0,
        "max_retries": 0,
        "retry_backoff_seconds": 0.0,
        "max_input_tokens": 4000,
        "max_output_tokens": 1000,
        "max_estimated_cost_usd": 0.02,
        "temperature": 0.0,
        "mask_sensitive_data": True,
        "allowed_tools": [],
    }
    values.update(updates)

    return LLMProviderConfig(
        **values
    )


def build_response(
    request: LLMRequest,
    *,
    request_id: str | None = None,
    structured_output: dict[str, Any] | None = None,
    estimated_cost_usd: float = 0.0,
) -> LLMResponse:
    """Build one provider-compatible response."""

    output = (
        {"status": "success"}
        if structured_output is None
        else structured_output
    )

    return LLMResponse(
        request_id=request_id or request.request_id,
        provider_name="controlled",
        model_name="controlled-model",
        content='{"status":"success"}',
        structured_output=output,
        usage=LLMTokenUsage(
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            estimated_cost_usd=estimated_cost_usd,
        ),
        latency_ms=1.0,
        finish_reason="stop",
        prompt_name=request.prompt_name,
        prompt_version=request.prompt_version,
        agent_name=request.agent_name,
        agent_version=request.agent_version,
    )


class FixedResponseProvider(
    BaseLLMProvider
):
    """Return a controlled response for shared-guardrail tests."""

    provider_name = "controlled"

    def __init__(
        self,
        config: LLMProviderConfig,
        response_builder: Any,
    ) -> None:
        super().__init__(config)
        self.response_builder = response_builder
        self.attempt_count = 0

    async def _generate_once(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        self.attempt_count += 1
        return self.response_builder(
            request
        )


class RetryThenSuccessProvider(
    BaseLLMProvider
):
    """Fail once with a retryable error and then succeed."""

    provider_name = "retry-provider"

    def __init__(
        self,
        config: LLMProviderConfig,
    ) -> None:
        super().__init__(config)
        self.attempt_count = 0

    async def _generate_once(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        self.attempt_count += 1

        if self.attempt_count == 1:
            raise LLMRateLimitError(
                "Controlled rate limit."
            )

        return build_response(
            request
        )


class SlowProvider(
    BaseLLMProvider
):
    """Sleep long enough to trigger the shared timeout."""

    provider_name = "slow-provider"

    async def _generate_once(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        await asyncio.sleep(
            0.05
        )

        return build_response(
            request
        )


def test_default_prompt_registry_contains_five_agent_prompts(
) -> None:
    """The Day 29 prompt registry should expose all five prompts."""

    prompt_names = {
        item["name"]
        for item in default_prompt_registry.list_prompts()
    }

    assert prompt_names == {
        "monitoring_summary",
        "priority_explanation",
        "root_cause_explanation",
        "recommendation_enhancement",
        "executive_brief_enhancement",
    }


def test_prompt_template_renders_json_context(
) -> None:
    """Non-text context should be serialized into the user message."""

    prompt = default_prompt_registry.get(
        "priority_explanation",
        "v1",
    )

    messages = prompt.render(
        {
            "validated_context_json": {
                "issue_id": "ISSUE-001",
                "priority_score": 95.0,
            }
        }
    )

    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    assert "ISSUE-001" in messages[1].content
    assert "95.0" in messages[1].content


def test_prompt_template_rejects_missing_variable(
) -> None:
    """Required prompt variables must be supplied."""

    prompt = default_prompt_registry.get(
        "monitoring_summary",
        "v1",
    )

    with pytest.raises(
        LLMConfigurationError,
        match="Missing prompt variables",
    ):
        prompt.render({})


def test_prompt_registry_rejects_duplicate_prompt(
) -> None:
    """A prompt name/version pair must be unique."""

    registry = PromptRegistry()

    prompt = PromptTemplate(
        name="test_prompt",
        version="v1",
        description="Controlled prompt.",
        system_template="System instruction.",
        user_template="$validated_context_json",
        required_variables=[
            "validated_context_json",
        ],
    )

    registry.register(prompt)

    with pytest.raises(
        LLMConfigurationError,
        match="already registered",
    ):
        registry.register(prompt)


def test_provider_registry_creates_registered_provider(
) -> None:
    """The registry should construct a configured provider."""

    registry = LLMProviderRegistry()
    registry.register(
        "mock",
        MockLLMProvider,
    )

    provider = registry.create(
        build_config()
    )

    assert isinstance(
        provider,
        MockLLMProvider,
    )


def test_provider_registry_rejects_unknown_provider(
) -> None:
    """Unknown provider names should fail before any API call."""

    registry = LLMProviderRegistry()

    with pytest.raises(
        LLMProviderNotFoundError,
        match="not registered",
    ):
        registry.create(
            build_config(
                provider_name="unknown"
            )
        )


def test_provider_registry_rejects_duplicate_registration(
) -> None:
    """Provider names must be unique."""

    registry = LLMProviderRegistry()
    registry.register(
        "mock",
        MockLLMProvider,
    )

    with pytest.raises(
        LLMConfigurationError,
        match="already registered",
    ):
        registry.register(
            "MOCK",
            MockLLMProvider,
        )


def test_sensitive_text_masking(
) -> None:
    """Credentials and contact details should be masked."""

    value = (
        "password=secret123 "
        "api_key:abc123 "
        "Bearer token-value "
        "manager@example.com "
        "+91 98765 43210"
    )

    masked = mask_sensitive_text(
        value
    )

    assert "secret123" not in masked
    assert "abc123" not in masked
    assert "token-value" not in masked
    assert "manager@example.com" not in masked
    assert "98765 43210" not in masked
    assert "<masked>" in masked
    assert "<masked-email>" in masked
    assert "<masked-phone>" in masked


def test_sensitive_value_masking_is_recursive(
) -> None:
    """Nested metadata should also be masked."""

    masked = mask_sensitive_value(
        {
            "contact": "manager@example.com",
            "nested": [
                {
                    "token": "token=abc123",
                }
            ],
        }
    )

    assert masked["contact"] == "<masked-email>"
    assert (
        "abc123"
        not in masked["nested"][0]["token"]
    )


def test_token_estimation_is_stable(
) -> None:
    """The provider-independent estimator should return safe counts."""

    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcdefgh") == 2


def test_provider_rejects_execution_when_disabled(
) -> None:
    """LLM calls must stay disabled unless explicitly enabled."""

    provider = MockLLMProvider(
        build_config(
            enabled=False
        )
    )

    with pytest.raises(
        LLMProviderDisabledError,
        match="disabled",
    ):
        asyncio.run(
            provider.generate(
                build_request()
            )
        )


def test_provider_masks_request_before_execution(
) -> None:
    """The prepared provider request should not contain raw secrets."""

    provider = MockLLMProvider(
        build_config()
    )

    prepared_request = provider.prepare_request(
        build_request(
            messages=[
                LLMMessage(
                    role="user",
                    content=(
                        "Email manager@example.com "
                        "and use token=abc123."
                    ),
                )
            ],
            metadata={
                "contact": "owner@example.com",
            },
        )
    )

    assert (
        "manager@example.com"
        not in prepared_request.messages[0].content
    )
    assert (
        "abc123"
        not in prepared_request.messages[0].content
    )
    assert (
        prepared_request.metadata["contact"]
        == "<masked-email>"
    )


def test_provider_rejects_unauthorized_tool(
) -> None:
    """A requested tool must be present in the configured allowlist."""

    provider = MockLLMProvider(
        build_config(
            allowed_tools=[
                "read_kpi",
            ]
        )
    )

    with pytest.raises(
        LLMToolPermissionError,
        match="Unauthorized LLM tools",
    ):
        asyncio.run(
            provider.generate(
                build_request(
                    allowed_tools=[
                        "write_task",
                    ]
                )
            )
        )


def test_provider_rejects_excessive_input_tokens(
) -> None:
    """Estimated input tokens must respect the configured maximum."""

    provider = MockLLMProvider(
        build_config(
            max_input_tokens=100
        )
    )

    with pytest.raises(
        LLMRequestValidationError,
        match="Estimated input tokens",
    ):
        asyncio.run(
            provider.generate(
                build_request(
                    messages=[
                        LLMMessage(
                            role="user",
                            content="x" * 500,
                        )
                    ]
                )
            )
        )


def test_provider_rejects_excessive_requested_output_tokens(
) -> None:
    """Requested output tokens cannot exceed the provider limit."""

    provider = MockLLMProvider(
        build_config(
            max_output_tokens=100
        )
    )

    with pytest.raises(
        LLMRequestValidationError,
        match="Requested output tokens",
    ):
        asyncio.run(
            provider.generate(
                build_request(
                    max_output_tokens=101
                )
            )
        )


def test_mock_provider_returns_structured_zero_cost_response(
) -> None:
    """The mock provider should be deterministic and free."""

    provider = MockLLMProvider(
        build_config()
    )

    response = asyncio.run(
        provider.generate(
            build_request(
                metadata={
                    "mock_structured_output": {
                        "summary": (
                            "Controlled mock output."
                        ),
                        "evidence_warning": None,
                    }
                }
            )
        )
    )

    assert response.execution_status == "Success"
    assert response.provider_name == "mock"
    assert (
        response.model_name
        == "mock-deterministic-v1"
    )
    assert response.used_mock_provider is True
    assert (
        response.structured_output
        == {
            "summary": "Controlled mock output.",
            "evidence_warning": None,
        }
    )
    assert (
        response.usage.total_tokens
        == (
            response.usage.input_tokens
            + response.usage.output_tokens
        )
    )
    assert (
        response.usage.estimated_cost_usd
        == 0.0
    )


def test_provider_rejects_mismatched_request_id(
) -> None:
    """A provider response must belong to the current request."""

    provider = FixedResponseProvider(
        build_config(),
        lambda request: build_response(
            request,
            request_id="wrong-request-id",
        ),
    )

    with pytest.raises(
        LLMProviderResponseError,
        match="request ID",
    ):
        asyncio.run(
            provider.generate(
                build_request()
            )
        )


def test_provider_requires_structured_output(
) -> None:
    """JSON-object requests must return structured output."""

    def response_without_structure(
        request: LLMRequest,
    ) -> LLMResponse:
        response = build_response(
            request
        )

        return response.model_copy(
            update={
                "structured_output": None,
            }
        )

    provider = FixedResponseProvider(
        build_config(),
        response_without_structure,
    )

    with pytest.raises(
        LLMProviderResponseError,
        match="Structured JSON output",
    ):
        asyncio.run(
            provider.generate(
                build_request(
                    require_json_object=True
                )
            )
        )


def test_provider_enforces_estimated_cost_limit(
) -> None:
    """A response cannot exceed the configured cost ceiling."""

    provider = FixedResponseProvider(
        build_config(
            max_estimated_cost_usd=0.01
        ),
        lambda request: build_response(
            request,
            estimated_cost_usd=0.02,
        ),
    )

    with pytest.raises(
        LLMCostLimitExceededError,
        match="estimated-cost limit",
    ):
        asyncio.run(
            provider.generate(
                build_request()
            )
        )


def test_provider_retries_retryable_failure(
) -> None:
    """Retryable provider failures should use the shared retry policy."""

    provider = RetryThenSuccessProvider(
        build_config(
            provider_name="retry-provider",
            max_retries=1,
        )
    )

    response = asyncio.run(
        provider.generate(
            build_request(
                max_retries=1
            )
        )
    )

    assert response.execution_status == "Success"
    assert provider.attempt_count == 2


def test_provider_timeout_is_controlled(
) -> None:
    """A slow provider should raise the shared timeout exception."""

    provider = SlowProvider(
        build_config(
            provider_name="slow-provider",
            timeout_seconds=0.01,
            max_retries=0,
        )
    )

    started_at = perf_counter()

    with pytest.raises(
        LLMTimeoutError,
        match="timed out",
    ):
        asyncio.run(
            provider.generate(
                build_request(
                    timeout_seconds=0.01,
                    max_retries=0,
                )
            )
        )

    assert (
        perf_counter()
        - started_at
        < 1.0
    )


@pytest.mark.parametrize(
    (
        "mock_error",
        "expected_exception",
    ),
    [
        pytest.param(
            "authentication",
            "LLMAuthenticationError",
            id="authentication",
        ),
        pytest.param(
            "rate_limit",
            "LLMRateLimitError",
            id="rate-limit",
        ),
        pytest.param(
            "provider_response",
            "LLMProviderResponseError",
            id="provider-response",
        ),
    ],
)
def test_mock_provider_exposes_controlled_failures(
    mock_error: str,
    expected_exception: str,
) -> None:
    """The mock provider should support deterministic failure tests."""

    provider = MockLLMProvider(
        build_config(
            max_retries=0
        )
    )

    with pytest.raises(
        Exception
    ) as captured:
        asyncio.run(
            provider.generate(
                build_request(
                    max_retries=0,
                    metadata={
                        "mock_error": mock_error,
                    },
                )
            )
        )

    assert (
        type(captured.value).__name__
        == expected_exception
    )
