from __future__ import annotations

import re
from typing import Any, Literal
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


TOOL_NAME_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{2,63}$"
)


class LLMToolCall(BaseModel):
    """Provider-independent request by a model to execute one tool."""

    model_config = ConfigDict(
        extra="forbid",
    )

    tool_call_id: str = Field(
        min_length=1,
        max_length=200,
    )
    tool_name: str = Field(
        min_length=3,
        max_length=64,
    )
    arguments: dict[str, Any] = Field(
        default_factory=dict,
    )

    @field_validator(
        "tool_call_id",
        "tool_name",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(
            str(value).split()
        )

        if not normalized:
            raise ValueError(
                "Tool-call identifiers and names cannot be empty."
            )

        return normalized

    @field_validator(
        "tool_name",
    )
    @classmethod
    def validate_tool_name(
        cls,
        value: str,
    ) -> str:
        if not TOOL_NAME_PATTERN.fullmatch(
            value
        ):
            raise ValueError(
                "Tool names must use lowercase letters, numbers, "
                "and underscores and must start with a letter."
            )

        return value


class LLMToolDefinition(BaseModel):
    """Tool definition exposed to an LLM provider."""

    model_config = ConfigDict(
        extra="forbid",
    )

    name: str = Field(
        min_length=3,
        max_length=64,
    )
    description: str = Field(
        min_length=5,
        max_length=1000,
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
    )

    @field_validator(
        "name",
        "description",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(
            str(value).split()
        )

        if not normalized:
            raise ValueError(
                "Tool definition text cannot be empty."
            )

        return normalized

    @field_validator(
        "name",
    )
    @classmethod
    def validate_tool_name(
        cls,
        value: str,
    ) -> str:
        if not TOOL_NAME_PATTERN.fullmatch(
            value
        ):
            raise ValueError(
                "Tool names must use lowercase letters, numbers, "
                "and underscores and must start with a letter."
            )

        return value

    @field_validator(
        "parameters",
    )
    @classmethod
    def validate_parameters_schema(
        cls,
        value: dict[str, Any],
    ) -> dict[str, Any]:
        if not value:
            return {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            }

        if value.get(
            "type"
        ) != "object":
            raise ValueError(
                "Tool parameter schema must have type='object'."
            )

        properties = value.get(
            "properties"
        )

        if not isinstance(
            properties,
            dict,
        ):
            raise ValueError(
                "Tool parameter schema must define object properties."
            )

        return value


class LLMMessage(BaseModel):
    """One provider-independent chat message."""

    model_config = ConfigDict(
        extra="forbid",
    )

    role: Literal[
        "system",
        "user",
        "assistant",
        "tool",
    ]
    content: str = Field(
        default="",
        max_length=50000,
    )
    name: str | None = Field(
        default=None,
        max_length=100,
    )
    tool_call_id: str | None = Field(
        default=None,
        max_length=200,
    )
    tool_calls: list[LLMToolCall] = Field(
        default_factory=list,
        max_length=5,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def validate_role_contract(
        self,
    ) -> "LLMMessage":
        has_content = bool(
            self.content.strip()
        )

        if self.role in {
            "system",
            "user",
        }:
            if not has_content:
                raise ValueError(
                    "System and user messages require content."
                )

            if (
                self.tool_call_id is not None
                or self.tool_calls
            ):
                raise ValueError(
                    "System and user messages cannot carry "
                    "tool-call metadata."
                )

        elif self.role == "assistant":
            if not has_content and not self.tool_calls:
                raise ValueError(
                    "Assistant messages require content or tool_calls."
                )

            if self.tool_call_id is not None:
                raise ValueError(
                    "Assistant messages cannot set tool_call_id."
                )

        elif self.role == "tool":
            if not has_content:
                raise ValueError(
                    "Tool-result messages require content."
                )

            if self.tool_calls:
                raise ValueError(
                    "Tool-result messages cannot request tools."
                )

            # tool_call_id is validated at the provider boundary.
            # Leaving it optional here preserves the old controlled
            # rejection test for unlinked tool-result messages.

        return self


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

    model_config = ConfigDict(
        extra="forbid",
    )

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
    tools: list[LLMToolDefinition] = Field(
        default_factory=list,
        max_length=5,
    )
    tool_choice: Literal[
        "auto",
        "none",
        "required",
    ] = "auto"
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

    @model_validator(mode="after")
    def validate_tool_contract(
        self,
    ) -> "LLMRequest":
        tool_names = [
            tool.name
            for tool in self.tools
        ]

        if len(
            tool_names
        ) != len(
            set(
                tool_names
            )
        ):
            raise ValueError(
                "LLM tool definitions must have unique names."
            )

        unallowed_definitions = [
            tool_name
            for tool_name in tool_names
            if tool_name not in self.allowed_tools
        ]

        if unallowed_definitions:
            raise ValueError(
                "Tool definitions must also appear in allowed_tools: "
                + ", ".join(
                    unallowed_definitions
                )
            )

        if (
            self.tool_choice == "required"
            and not self.tools
        ):
            raise ValueError(
                "tool_choice='required' requires at least one tool."
            )

        available_history_calls: dict[
            str,
            str,
        ] = {}
        completed_history_calls: set[
            str
        ] = set()

        for message in self.messages:
            if message.role == "assistant":
                for tool_call in message.tool_calls:
                    if (
                        tool_call.tool_call_id
                        in available_history_calls
                    ):
                        raise ValueError(
                            "Tool-call IDs must be unique in "
                            "message history."
                        )

                    if (
                        tool_call.tool_name
                        not in self.allowed_tools
                    ):
                        raise ValueError(
                            "Assistant history references a tool "
                            "outside allowed_tools."
                        )

                    available_history_calls[
                        tool_call.tool_call_id
                    ] = tool_call.tool_name

            elif (
                message.role == "tool"
                and message.tool_call_id
            ):
                tool_call_id = str(
                    message.tool_call_id
                )

                if (
                    tool_call_id
                    not in available_history_calls
                ):
                    raise ValueError(
                        "Tool-result message references an unknown "
                        "tool_call_id."
                    )

                if (
                    tool_call_id
                    in completed_history_calls
                ):
                    raise ValueError(
                        "A tool_call_id cannot have multiple "
                        "tool-result messages."
                    )

                expected_name = (
                    available_history_calls[
                        tool_call_id
                    ]
                )

                if (
                    message.name is not None
                    and message.name != expected_name
                ):
                    raise ValueError(
                        "Tool-result message name does not match "
                        "the assistant tool call."
                    )

                completed_history_calls.add(
                    tool_call_id
                )

        return self


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

    model_config = ConfigDict(
        extra="forbid",
    )

    request_id: str
    provider_name: str
    model_name: str
    execution_status: Literal["Success"] = "Success"

    content: str
    structured_output: dict[str, Any] | None = None
    tool_calls: list[LLMToolCall] = Field(
        default_factory=list,
        max_length=5,
    )

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

    @model_validator(mode="after")
    def validate_tool_call_state(
        self,
    ) -> "LLMResponse":
        if self.finish_reason == "tool_call":
            if not self.tool_calls:
                raise ValueError(
                    "tool_call finish reason requires tool_calls."
                )

            if self.structured_output is not None:
                raise ValueError(
                    "A tool-call response cannot also contain "
                    "final structured output."
                )

        elif self.tool_calls:
            raise ValueError(
                "tool_calls are only valid with "
                "finish_reason='tool_call'."
            )

        return self
