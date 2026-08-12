from __future__ import annotations

from backend.app.llm import (
    LLMMessage,
    LLMProviderConfig,
    LLMRequest,
    MockLLMProvider,
    mask_sensitive_text,
)


def build_config() -> LLMProviderConfig:
    """Build a controlled masking configuration."""

    return LLMProviderConfig(
        enabled=True,
        provider_name="mock",
        model_name="mock-deterministic-v1",
        timeout_seconds=1.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        max_input_tokens=4000,
        max_output_tokens=1000,
        max_estimated_cost_usd=0.02,
        temperature=0.0,
        mask_sensitive_data=True,
        allowed_tools=[],
    )


def test_phone_masking_still_masks_real_phone_numbers(
) -> None:
    """A standalone phone number must still be redacted."""

    masked = mask_sensitive_text(
        "Contact the manager at +91 98765 43210."
    )

    assert "+91 98765 43210" not in masked
    assert "<masked-phone>" in masked


def test_business_identifiers_with_periods_are_preserved(
) -> None:
    """Business finding IDs must not be mistaken for phone numbers."""

    identifiers = [
        "LOW-TARGET-S003-2026-06",
        "PRODUCT-UNDERPERFORMANCE-P017-2026-06",
        "LOW-STOCK-S003-P017-2026-06-30",
        "HIGH-FINANCIAL-RISK-S003-2026-06",
    ]

    for identifier in identifiers:
        assert (
            mask_sensitive_text(identifier)
            == identifier
        )


def test_json_dates_and_timestamps_are_preserved(
) -> None:
    """Quoted business dates must not be masked as phone numbers."""

    value = (
        '{"deadline":"2026-08-10",'
        '"generated_at":"2026-08-10T12:30:00"}'
    )

    assert mask_sensitive_text(value) == value


def test_prepare_request_preserves_schema_ids_and_masks_real_phone(
) -> None:
    """Masking must protect PII without corrupting strict schema enums."""

    provider = MockLLMProvider(
        build_config()
    )

    evidence_id = "LOW-TARGET-S003-2026-06"

    request = LLMRequest(
        request_id="masking-regression-request",
        agent_name="Monitoring Agent",
        agent_version="1.1.0",
        prompt_name="monitoring_summary",
        prompt_version="v1",
        messages=[
            LLMMessage(
                role="user",
                content=(
                    f"Use evidence {evidence_id}. "
                    "Private phone: +91 98765 43210."
                ),
            )
        ],
        require_json_object=True,
        metadata={
            "response_json_schema": {
                "type": "object",
                "properties": {
                    "evidence_ids": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                evidence_id,
                            ],
                        },
                    },
                    "deadline": {
                        "type": "string",
                        "enum": [
                            "2026-08-10",
                        ],
                    },
                },
            },
            "response_json_schema_strict": True,
        },
    )

    prepared = provider.prepare_request(
        request
    )

    message = prepared.messages[0].content
    schema = prepared.metadata[
        "response_json_schema"
    ]

    assert evidence_id in message
    assert "+91 98765 43210" not in message
    assert "<masked-phone>" in message

    assert (
        schema["properties"]["evidence_ids"]
        ["items"]["enum"]
        == [
            evidence_id,
        ]
    )
    assert (
        schema["properties"]["deadline"]["enum"]
        == [
            "2026-08-10",
        ]
    )
