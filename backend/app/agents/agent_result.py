from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class AgentExecutionStatus(str, Enum):
    """Supported states for an agent execution."""

    SUCCESS = "Success"
    FAILED = "Failed"
    SKIPPED = "Skipped"


class AgentExecutionMetadata(BaseModel):
    """
    Optional LLM and tool metadata captured for one agent execution.

    Deterministic agents may leave these fields empty. LLM-supported
    agents can return this metadata through the reserved
    ``_execution_metadata`` output key.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    model_provider: str | None = Field(
        default=None,
        max_length=100,
    )

    model_name: str | None = Field(
        default=None,
        max_length=200,
    )

    prompt_name: str | None = Field(
        default=None,
        max_length=150,
    )

    prompt_version: str | None = Field(
        default=None,
        max_length=50,
    )

    input_tokens: int | None = Field(
        default=None,
        ge=0,
    )

    output_tokens: int | None = Field(
        default=None,
        ge=0,
    )

    total_tokens: int | None = Field(
        default=None,
        ge=0,
    )

    estimated_cost_usd: float | None = Field(
        default=None,
        ge=0,
    )

    llm_latency_ms: float | None = Field(
        default=None,
        ge=0,
    )

    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    run_metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    llm_error_type: str | None = Field(
        default=None,
        max_length=150,
    )

    llm_error_message: str | None = Field(
        default=None,
        max_length=4000,
    )

    @field_validator(
        "model_provider",
        "model_name",
        "prompt_name",
        "prompt_version",
        "llm_error_type",
        "llm_error_message",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = " ".join(
            value.split()
        )

        return normalized or None

    @model_validator(mode="after")
    def validate_token_usage(
        self,
    ) -> "AgentExecutionMetadata":
        token_values = (
            self.input_tokens,
            self.output_tokens,
            self.total_tokens,
        )

        supplied_count = sum(
            value is not None
            for value in token_values
        )

        if supplied_count not in {
            0,
            3,
        }:
            raise ValueError(
                "input_tokens, output_tokens, and total_tokens "
                "must be supplied together."
            )

        if supplied_count == 3:
            expected_total = (
                int(self.input_tokens or 0)
                + int(self.output_tokens or 0)
            )

            if self.total_tokens != expected_total:
                raise ValueError(
                    "total_tokens must equal input_tokens "
                    "plus output_tokens."
                )

        return self


class AgentResult(BaseModel):
    """
    Structured result returned by every agent.

    The same structure supports deterministic agents, LLM-supported
    agents, fallback execution, tool use, and execution logging.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    run_id: str = Field(
        min_length=1,
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

    run_type: str = Field(
        min_length=1,
        max_length=100,
    )

    execution_status: AgentExecutionStatus

    summary: str = ""

    output_data: dict[str, Any] = Field(
        default_factory=dict,
    )

    used_fallback: bool = False

    error_type: str | None = None

    error_message: str | None = None

    model_provider: str | None = Field(
        default=None,
        max_length=100,
    )

    model_name: str | None = Field(
        default=None,
        max_length=200,
    )

    prompt_name: str | None = Field(
        default=None,
        max_length=150,
    )

    prompt_version: str | None = Field(
        default=None,
        max_length=50,
    )

    input_tokens: int | None = Field(
        default=None,
        ge=0,
    )

    output_tokens: int | None = Field(
        default=None,
        ge=0,
    )

    total_tokens: int | None = Field(
        default=None,
        ge=0,
    )

    estimated_cost_usd: float | None = Field(
        default=None,
        ge=0,
    )

    llm_latency_ms: float | None = Field(
        default=None,
        ge=0,
    )

    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    run_metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    llm_error_type: str | None = Field(
        default=None,
        max_length=150,
    )

    llm_error_message: str | None = Field(
        default=None,
        max_length=4000,
    )

    started_at: datetime

    completed_at: datetime

    duration_ms: float = Field(
        ge=0,
    )

    agent_run_id: int | None = Field(
        default=None,
        ge=1,
    )

    log_persisted: bool = False

    logging_error: str | None = None

    @field_validator(
        "agent_name",
        "agent_version",
        "run_type",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(
            value.split()
        )

        if not normalized:
            raise ValueError(
                "Required AgentResult text fields "
                "cannot be empty."
            )

        return normalized

    @field_validator(
        "model_provider",
        "model_name",
        "prompt_name",
        "prompt_version",
        "llm_error_type",
        "llm_error_message",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = " ".join(
            value.split()
        )

        return normalized or None

    @model_validator(mode="after")
    def validate_token_usage(
        self,
    ) -> "AgentResult":
        token_values = (
            self.input_tokens,
            self.output_tokens,
            self.total_tokens,
        )

        supplied_count = sum(
            value is not None
            for value in token_values
        )

        if supplied_count not in {
            0,
            3,
        }:
            raise ValueError(
                "input_tokens, output_tokens, and total_tokens "
                "must be supplied together."
            )

        if supplied_count == 3:
            expected_total = (
                int(self.input_tokens or 0)
                + int(self.output_tokens or 0)
            )

            if self.total_tokens != expected_total:
                raise ValueError(
                    "total_tokens must equal input_tokens "
                    "plus output_tokens."
                )

        return self