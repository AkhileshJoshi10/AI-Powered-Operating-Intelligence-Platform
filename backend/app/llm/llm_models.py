from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)


class LLMMessage(BaseModel):
    """One provider-independent chat message."""

    role: Literal[
        "system",
        "user",
        "assistant",
        "tool",
    ]
    content: str = Field(
        min_length=1,
        max_length=50000,
    )
    name: str | None = Field(
        default=None,
        max_length=100,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class LLMProviderConfig(BaseModel):
    """Controlled configuration shared by all LLM providers."""

    enabled: bool = False
    provider_name: str = Field(
        default="mock",
        min_length=1,
        max_length=100,
    )
    model_name: str = Field(
        default="mock-deterministic-v1",
        min_length=1,
        max_length=200,
    )
    timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        le=300,
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
    )
    retry_backoff_seconds: float = Field(
        default=0.25,
        ge=0,
        le=10,
    )
    max_input_tokens: int = Field(
        default=4000,
        ge=100,
        le=1000000,
    )
    max_output_tokens: int = Field(
        default=1000,
        ge=1,
        le=100000,
    )
    max_estimated_cost_usd: float = Field(
        default=0.02,
        ge=0,
        le=1000,
    )
    temperature: float = Field(
        default=0.0,
        ge=0,
        le=2,
    )
    mask_sensitive_data: bool = True
    allowed_tools: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    @field_validator(
        "provider_name",
        "model_name",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError(
                "Provider and model names cannot be empty."
            )

        return normalized

    @field_validator("allowed_tools")
    @classmethod
    def normalize_allowed_tools(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized_values: list[str] = []

        for value in values:
            normalized = " ".join(str(value).split())

            if (
                normalized
                and normalized not in normalized_values
            ):
                normalized_values.append(normalized)

        return normalized_values


class LLMRequest(BaseModel):
    """One structured request sent through an LLM provider."""

    request_id: str = Field(
        default_factory=lambda: uuid4().hex,
        min_length=1,
        max_length=100,
    )
    agent_name: str = Field(
        min_length=1,
        max_length=150,
    )
    agent_version: str = Field(
        default="1.0.0",
        min_length=1,
        max_length=50,
    )
    prompt_name: str = Field(
        min_length=1,
        max_length=150,
    )
    prompt_version: str = Field(
        min_length=1,
        max_length=50,
    )
    messages: list[LLMMessage] = Field(
        min_length=1,
        max_length=100,
    )
    response_schema_name: str | None = Field(
        default=None,
        max_length=150,
    )
    model_name: str | None = Field(
        default=None,
        max_length=200,
    )
    temperature: float | None = Field(
        default=None,
        ge=0,
        le=2,
    )
    max_output_tokens: int | None = Field(
        default=None,
        ge=1,
        le=100000,
    )
    timeout_seconds: float | None = Field(
        default=None,
        gt=0,
        le=300,
    )
    max_retries: int | None = Field(
        default=None,
        ge=0,
        le=5,
    )
    max_estimated_cost_usd: float | None = Field(
        default=None,
        ge=0,
        le=1000,
    )
    allowed_tools: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    require_json_object: bool = True
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    @field_validator(
        "agent_name",
        "agent_version",
        "prompt_name",
        "prompt_version",
    )
    @classmethod
    def normalize_controlled_text(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError(
                "Controlled LLM text fields cannot be empty."
            )

        return normalized

    @field_validator("allowed_tools")
    @classmethod
    def normalize_requested_tools(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized_values: list[str] = []

        for value in values:
            normalized = " ".join(str(value).split())

            if (
                normalized
                and normalized not in normalized_values
            ):
                normalized_values.append(normalized)

        return normalized_values


class LLMTokenUsage(BaseModel):
    """Token and cost metadata returned by a provider."""

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(
        default=0.0,
        ge=0,
    )

    @model_validator(mode="after")
    def validate_total_tokens(
        self,
    ) -> "LLMTokenUsage":
        expected_total = (
            self.input_tokens
            + self.output_tokens
        )

        if self.total_tokens != expected_total:
            raise ValueError(
                "total_tokens must equal input_tokens "
                "plus output_tokens."
            )

        return self


class LLMResponse(BaseModel):
    """Provider-independent successful LLM response."""

    request_id: str
    provider_name: str
    model_name: str
    execution_status: Literal["Success"] = "Success"

    content: str
    structured_output: dict[str, Any] | None = None

    usage: LLMTokenUsage
    latency_ms: float = Field(ge=0)
    finish_reason: Literal[
        "stop",
        "length",
        "content_filter",
        "tool_call",
    ] = "stop"

    prompt_name: str
    prompt_version: str
    agent_name: str
    agent_version: str

    provider_response_id: str | None = None
    used_mock_provider: bool = False
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )
