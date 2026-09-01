from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


def current_utc_time() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(
        timezone.utc
    )


def generate_tool_call_id() -> str:
    """Generate a unique identifier for one tool-call attempt."""

    return uuid4().hex


def normalize_text(
    value: object,
) -> str:
    """Convert one value into normalized single-line text."""

    if value is None:
        return ""

    return " ".join(
        str(value).split()
    )


def normalize_text_list(
    values: list[object],
) -> list[str]:
    """Normalize and deduplicate a list of text values."""

    normalized_values: list[str] = []

    for value in values:
        normalized = normalize_text(
            value
        )

        if (
            normalized
            and normalized not in normalized_values
        ):
            normalized_values.append(
                normalized
            )

    return normalized_values


class ToolAccessMode(str, Enum):
    """Authority level assigned to one registered tool."""

    READ_ONLY = "Read Only"
    WRITE = "Write"


class ToolExecutionStatus(str, Enum):
    """Controlled tool-call execution states."""

    SUCCESS = "Success"
    DENIED = "Denied"
    FAILED = "Failed"


class ToolExecutionContext(BaseModel):
    """
    Permission context for one controlled agent tool call.

    Write permission is deliberately separate from the general tool
    allowlist. A write-capable tool must pass every write gate.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    run_id: str = Field(
        min_length=1,
        max_length=100,
    )
    agent_name: str = Field(
        min_length=1,
        max_length=150,
    )
    requested_by: str | None = Field(
        default=None,
        max_length=150,
    )
    allowed_tools: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    allow_write_tools: bool = False
    approved_write_tools: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    @field_validator(
        "run_id",
        "agent_name",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        normalized = normalize_text(
            value
        )

        if not normalized:
            raise ValueError(
                "Tool execution context text cannot be empty."
            )

        return normalized

    @field_validator(
        "requested_by",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        normalized = normalize_text(
            value
        )

        return normalized or None

    @field_validator(
        "allowed_tools",
        "approved_write_tools",
    )
    @classmethod
    def normalize_tool_names(
        cls,
        values: list[str],
    ) -> list[str]:
        return normalize_text_list(
            list(values)
        )


class ToolCallRecord(BaseModel):
    """
    Audit-safe metadata for one attempted tool call.

    Raw argument values and raw output values are intentionally not
    stored here. Business-sensitive data belongs in the authorized
    tool result, not the generic audit envelope.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    tool_call_id: str = Field(
        default_factory=generate_tool_call_id,
        min_length=1,
        max_length=100,
    )
    run_id: str = Field(
        min_length=1,
        max_length=100,
    )
    agent_name: str = Field(
        min_length=1,
        max_length=150,
    )
    tool_name: str = Field(
        min_length=1,
        max_length=100,
    )
    access_mode: ToolAccessMode | None = None
    status: ToolExecutionStatus
    input_field_names: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    output_schema_name: str | None = Field(
        default=None,
        max_length=150,
    )
    permission_reason: str | None = Field(
        default=None,
        max_length=1000,
    )
    error_type: str | None = Field(
        default=None,
        max_length=150,
    )
    error_message: str | None = Field(
        default=None,
        max_length=2000,
    )
    started_at: datetime = Field(
        default_factory=current_utc_time,
    )
    completed_at: datetime = Field(
        default_factory=current_utc_time,
    )
    duration_ms: float = Field(
        default=0.0,
        ge=0,
    )

    @field_validator(
        "output_schema_name",
        "permission_reason",
        "error_type",
        "error_message",
    )
    @classmethod
    def normalize_optional_fields(
        cls,
        value: str | None,
    ) -> str | None:
        normalized = normalize_text(
            value
        )

        return normalized or None

    @field_validator(
        "input_field_names",
    )
    @classmethod
    def normalize_input_fields(
        cls,
        values: list[str],
    ) -> list[str]:
        return normalize_text_list(
            list(values)
        )


class ToolExecutionResult(BaseModel):
    """Validated result returned by the controlled tool executor."""

    model_config = ConfigDict(
        extra="forbid",
    )

    status: ToolExecutionStatus
    output: dict[str, Any] | None = None
    call_record: ToolCallRecord


ToolHandler = Callable[
    [BaseModel, ToolExecutionContext],
    (
        BaseModel
        | dict[str, Any]
        | Awaitable[
            BaseModel
            | dict[str, Any]
        ]
    ),
]


@dataclass(
    frozen=True,
)
class ToolDefinition:
    """Internal definition of one explicitly registered agent tool."""

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: ToolHandler
    access_mode: ToolAccessMode = (
        ToolAccessMode.READ_ONLY
    )
    allowed_agents: tuple[str, ...] = ()
    requires_human_approval: bool = False
    enabled: bool = True
    disabled_reason: str | None = None

    def input_json_schema(
        self,
    ) -> dict[str, Any]:
        """Return the Pydantic argument schema."""

        return self.input_model.model_json_schema()

    def output_json_schema(
        self,
    ) -> dict[str, Any]:
        """Return the Pydantic result schema."""

        return self.output_model.model_json_schema()
