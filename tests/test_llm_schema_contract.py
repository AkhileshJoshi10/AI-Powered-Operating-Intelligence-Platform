from __future__ import annotations

import asyncio
from typing import Any

import backend.app.llm.base_provider as base_provider_module
from backend.app.agents.llm_enhancement import (
    MonitoringSummaryV1,
    prepare_strict_response_json_schema,
    run_structured_enhancement,
)
from backend.app.llm import (
    BaseLLMProvider,
    LLMMessage,
    LLMProviderConfig,
    LLMRateLimitError,
    LLMRequest,
    LLMResponse,
    LLMTokenUsage,
    MockLLMProvider,
)


class CapturingMockProvider(MockLLMProvider):
    """Capture the prepared request before returning mock output."""

    def __init__(
        self,
        config: LLMProviderConfig,
    ) -> None:
        super().__init__(config)
        self.captured_request: LLMRequest | None = None

    async def _generate_once(
        self,
        request: LLMRequest,
    ) -> Any:
        self.captured_request = request.model_copy(
            deep=True
        )

        return await super()._generate_once(
            request
        )


class RetryAfterProvider(
    BaseLLMProvider
):
    """Return one rate limit with provider timing, then succeed."""

    provider_name = "retry-after-test"

    def __init__(
        self,
        config: LLMProviderConfig,
    ) -> None:
        super().__init__(
            config
        )
        self.attempt_count = 0

    async def _generate_once(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        self.attempt_count += 1

        if self.attempt_count == 1:
            error = LLMRateLimitError(
                "Controlled rate limit."
            )
            setattr(
                error,
                "retry_after_seconds",
                7.5,
            )
            raise error

        return LLMResponse(
            request_id=request.request_id,
            provider_name=self.provider_name,
            model_name=self.config.model_name,
            content='{"status":"ready"}',
            structured_output={
                "status": "ready",
            },
            usage=LLMTokenUsage(
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
                estimated_cost_usd=0.0,
            ),
            latency_ms=1.0,
            finish_reason="stop",
            prompt_name=request.prompt_name,
            prompt_version=request.prompt_version,
            agent_name=request.agent_name,
            agent_version=request.agent_version,
        )


def build_config(
    *,
    provider_name: str = "mock",
    model_name: str = "mock-deterministic-v1",
    max_retries: int = 0,
    retry_backoff_seconds: float = 0.0,
) -> LLMProviderConfig:
    """Build one enabled controlled configuration."""

    return LLMProviderConfig(
        enabled=True,
        provider_name=provider_name,
        model_name=model_name,
        timeout_seconds=1.0,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
        max_input_tokens=4000,
        max_output_tokens=1000,
        max_estimated_cost_usd=0.02,
        temperature=0.0,
        mask_sensitive_data=True,
        allowed_tools=[],
    )


def find_enum_values(
    node: object,
    *,
    property_name: str,
) -> list[list[str]]:
    """Collect enum lists attached to one JSON Schema property."""

    found: list[
        list[str]
    ] = []

    if isinstance(
        node,
        dict,
    ):
        properties = node.get(
            "properties"
        )

        if isinstance(
            properties,
            dict,
        ):
            property_schema = properties.get(
                property_name
            )

            if isinstance(
                property_schema,
                dict,
            ):
                if (
                    property_schema.get(
                        "type"
                    )
                    == "array"
                ):
                    items = property_schema.get(
                        "items"
                    )

                    if (
                        isinstance(
                            items,
                            dict,
                        )
                        and isinstance(
                            items.get(
                                "enum"
                            ),
                            list,
                        )
                    ):
                        found.append(
                            list(
                                items[
                                    "enum"
                                ]
                            )
                        )

                elif isinstance(
                    property_schema.get(
                        "enum"
                    ),
                    list,
                ):
                    found.append(
                        list(
                            property_schema[
                                "enum"
                            ]
                        )
                    )

        for child in node.values():
            found.extend(
                find_enum_values(
                    child,
                    property_name=(
                        property_name
                    ),
                )
            )

    elif isinstance(
        node,
        list,
    ):
        for child in node:
            found.extend(
                find_enum_values(
                    child,
                    property_name=(
                        property_name
                    ),
                )
            )

    return found


def test_shared_enhancement_attaches_runtime_identifier_contract(
) -> None:
    """The provider request should carry exact runtime ID constraints."""

    provider = CapturingMockProvider(
        build_config()
    )

    structured_output = {
        "summary": "Controlled monitoring summary.",
        "business_health_status": "At Risk",
        "attention_areas": [
            {
                "business_area": "Sales",
                "urgency": "High",
                "reason": "Validated sales evidence.",
                "evidence_ids": [
                    "LOW-TARGET-S003",
                ],
            }
        ],
        "evidence_ids": [
            "LOW-TARGET-S003",
            "PRODUCT-UNDERPERFORMANCE-P017",
        ],
        "confidence_score": 90.0,
        "missing_evidence_warnings": [],
    }

    asyncio.run(
        run_structured_enhancement(
            provider=provider,
            agent_name="Monitoring Agent",
            agent_version="1.1.0",
            prompt_name="monitoring_summary",
            prompt_version="v1",
            validated_context={
                "top_findings": [
                    {
                        "finding_id": "LOW-TARGET-S003",
                    },
                    {
                        "finding_id": (
                            "PRODUCT-UNDERPERFORMANCE-P017"
                        ),
                    },
                ],
            },
            response_model=MonitoringSummaryV1,
            allowed_evidence_ids=[
                "LOW-TARGET-S003",
                "PRODUCT-UNDERPERFORMANCE-P017",
            ],
            mock_structured_output=structured_output,
        )
    )

    request = provider.captured_request

    assert request is not None
    assert request.metadata[
        "response_json_schema_name"
    ] == "MonitoringSummaryV1"

    schema = request.metadata[
        "response_json_schema"
    ]

    assert (
        request.metadata[
            "response_json_schema_strict"
        ]
        is True
    )

    expected_ids = [
        "LOW-TARGET-S003",
        "PRODUCT-UNDERPERFORMANCE-P017",
    ]

    evidence_enums = find_enum_values(
        schema,
        property_name="evidence_ids",
    )

    assert evidence_enums
    assert all(
        enum_values
        == expected_ids
        for enum_values in evidence_enums
    )

    prompt_text = "\n".join(
        message.content
        for message in request.messages
    )

    assert (
        "copy one of the allowed strings exactly"
        in prompt_text
    )
    assert "LOW-TARGET-S003" in prompt_text
    assert (
        "PRODUCT-UNDERPERFORMANCE-P017"
        in prompt_text
    )


def test_shared_retry_respects_provider_retry_after(
    monkeypatch: Any,
) -> None:
    """Provider retry timing must override a shorter local backoff."""

    recorded_delays: list[
        float
    ] = []

    async def fake_sleep(
        seconds: float,
    ) -> None:
        recorded_delays.append(
            seconds
        )

    monkeypatch.setattr(
        base_provider_module.asyncio,
        "sleep",
        fake_sleep,
    )

    provider = RetryAfterProvider(
        build_config(
            provider_name="retry-after-test",
            model_name="controlled-model",
            max_retries=1,
            retry_backoff_seconds=0.5,
        )
    )

    request = LLMRequest(
        request_id="retry-after-request",
        agent_name="Retry Test Agent",
        agent_version="1.0.0",
        prompt_name="retry_after_test",
        prompt_version="v1",
        messages=[
            LLMMessage(
                role="user",
                content="Return controlled JSON.",
            )
        ],
        require_json_object=True,
        max_retries=1,
    )

    response = asyncio.run(
        provider.generate(
            request
        )
    )

    assert response.structured_output == {
        "status": "ready",
    }
    assert provider.attempt_count == 2
    assert recorded_delays == [
        7.5,
    ]



def assert_strict_object_contract(
    node: object,
) -> None:
    """Verify strict requirements recursively for every schema object."""

    if isinstance(
        node,
        dict,
    ):
        properties = node.get(
            "properties"
        )

        if isinstance(
            properties,
            dict,
        ):
            assert node.get(
                "additionalProperties"
            ) is False
            assert node.get(
                "required"
            ) == list(
                properties.keys()
            )

        for removed_keyword in {
            "default",
            "examples",
            "minLength",
            "maxLength",
            "minItems",
            "maxItems",
        }:
            assert (
                removed_keyword
                not in node
            )

        for child in node.values():
            assert_strict_object_contract(
                child
            )

    elif isinstance(
        node,
        list,
    ):
        for child in node:
            assert_strict_object_contract(
                child
            )


def test_strict_schema_preparation_closes_objects_and_requires_fields(
) -> None:
    """Pydantic output schemas should become strict-provider compatible."""

    strict_schema = (
        prepare_strict_response_json_schema(
            MonitoringSummaryV1.model_json_schema()
        )
    )

    assert_strict_object_contract(
        strict_schema
    )

    assert strict_schema[
        "required"
    ] == list(
        strict_schema[
            "properties"
        ].keys()
    )


def test_strict_schema_preserves_runtime_evidence_enums(
) -> None:
    """Strict conversion must not remove evidence allowlists."""

    provider = CapturingMockProvider(
        build_config()
    )

    structured_output = {
        "summary": "Controlled monitoring summary.",
        "business_health_status": "At Risk",
        "attention_areas": [],
        "evidence_ids": [
            "FINDING-001",
        ],
        "confidence_score": 90.0,
        "missing_evidence_warnings": [],
    }

    asyncio.run(
        run_structured_enhancement(
            provider=provider,
            agent_name="Monitoring Agent",
            agent_version="1.1.0",
            prompt_name="monitoring_summary",
            prompt_version="v1",
            validated_context={
                "top_findings": [
                    {
                        "finding_id": "FINDING-001",
                    }
                ],
            },
            response_model=MonitoringSummaryV1,
            allowed_evidence_ids=[
                "FINDING-001",
            ],
            mock_structured_output=structured_output,
        )
    )

    request = provider.captured_request

    assert request is not None

    evidence_enums = find_enum_values(
        request.metadata[
            "response_json_schema"
        ],
        property_name="evidence_ids",
    )

    assert evidence_enums
    assert all(
        values == [
            "FINDING-001",
        ]
        for values in evidence_enums
    )

    prompt_text = "\n".join(
        message.content
        for message in request.messages
    )

    assert (
        "Any output field whose name begins with deterministic_"
        in prompt_text
    )
