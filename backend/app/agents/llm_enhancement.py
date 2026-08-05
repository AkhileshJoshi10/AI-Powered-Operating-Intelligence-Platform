from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from backend.app.agents.agent_result import (
    AgentExecutionMetadata,
)
from backend.app.llm import (
    BaseLLMProvider,
    LLMError,
    LLMProviderResponseError,
    LLMRequest,
    default_prompt_registry,
)


ResponseModel = TypeVar(
    "ResponseModel",
    bound=BaseModel,
)

FALLBACK_OUTPUT_ATTRIBUTE = (
    "_agent_deterministic_fallback_output"
)
FALLBACK_METADATA_ATTRIBUTE = (
    "_agent_llm_execution_metadata"
)
LLM_RESPONSE_ATTRIBUTE = (
    "_agent_llm_provider_response"
)


def normalize_text(
    value: object,
) -> str:
    """Convert one value into compact normalized text."""

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


class MonitoringAttentionAreaV1(BaseModel):
    """One manager-facing business area requiring attention."""

    model_config = ConfigDict(
        extra="forbid",
    )

    business_area: str = Field(
        min_length=1,
        max_length=150,
    )
    urgency: str = Field(
        min_length=1,
        max_length=50,
    )
    reason: str = Field(
        min_length=1,
        max_length=2000,
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    @field_validator(
        "business_area",
        "urgency",
        "reason",
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
                "Monitoring attention text cannot be empty."
            )

        return normalized

    @field_validator("evidence_ids")
    @classmethod
    def normalize_evidence_ids(
        cls,
        values: list[str],
    ) -> list[str]:
        return normalize_text_list(
            list(values)
        )


class MonitoringSummaryV1(BaseModel):
    """Controlled schema for the Monitoring Agent LLM response."""

    model_config = ConfigDict(
        extra="forbid",
    )

    summary: str = Field(
        min_length=1,
        max_length=4000,
    )
    business_health_status: str = Field(
        min_length=1,
        max_length=50,
    )
    attention_areas: list[
        MonitoringAttentionAreaV1
    ] = Field(
        default_factory=list,
        max_length=20,
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        max_length=200,
    )
    confidence_score: float = Field(
        ge=0,
        le=100,
    )
    missing_evidence_warnings: list[str] = Field(
        default_factory=list,
        max_length=50,
    )

    @field_validator(
        "summary",
        "business_health_status",
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
                "Monitoring summary text cannot be empty."
            )

        return normalized

    @field_validator(
        "evidence_ids",
        "missing_evidence_warnings",
    )
    @classmethod
    def normalize_text_values(
        cls,
        values: list[str],
    ) -> list[str]:
        return normalize_text_list(
            list(values)
        )

    @model_validator(mode="after")
    def include_attention_evidence(
        self,
    ) -> "MonitoringSummaryV1":
        """Require attention-area references in the top-level list."""

        referenced_ids = {
            evidence_id
            for attention_area in self.attention_areas
            for evidence_id in attention_area.evidence_ids
        }

        missing_ids = sorted(
            referenced_ids.difference(
                self.evidence_ids
            )
        )

        if missing_ids:
            raise ValueError(
                "Attention-area evidence IDs must also appear "
                "in the top-level evidence_ids list: "
                + ", ".join(
                    missing_ids
                )
            )

        return self


class PriorityIssueExplanationV1(BaseModel):
    """One grounded explanation of a deterministic priority item."""

    model_config = ConfigDict(
        extra="forbid",
    )

    issue_id: str = Field(
        min_length=1,
        max_length=220,
    )
    deterministic_priority_level: str = Field(
        min_length=1,
        max_length=20,
    )
    deterministic_priority_score: float = Field(
        ge=0,
    )
    manager_rank: int | None = Field(
        default=None,
        ge=1,
    )
    executive_rank: int | None = Field(
        default=None,
        ge=1,
    )
    review_reason: str = Field(
        min_length=1,
        max_length=2500,
    )
    score_explanation: str = Field(
        min_length=1,
        max_length=2500,
    )
    priority_change_explanation: str = Field(
        min_length=1,
        max_length=2500,
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    confidence_score: float = Field(
        ge=0,
        le=100,
    )
    missing_evidence_warnings: list[str] = Field(
        default_factory=list,
        max_length=50,
    )

    @field_validator(
        "issue_id",
        "deterministic_priority_level",
        "review_reason",
        "score_explanation",
        "priority_change_explanation",
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
                "Priority explanation text cannot be empty."
            )

        return normalized

    @field_validator(
        "evidence_ids",
        "missing_evidence_warnings",
    )
    @classmethod
    def normalize_text_values(
        cls,
        values: list[str],
    ) -> list[str]:
        return normalize_text_list(
            list(values)
        )


class PriorityExplanationV1(BaseModel):
    """Controlled schema for the Priority Agent LLM response."""

    model_config = ConfigDict(
        extra="forbid",
    )

    summary: str = Field(
        min_length=1,
        max_length=5000,
    )
    review_first_issue_id: str = Field(
        min_length=1,
        max_length=220,
    )
    review_first_reason: str = Field(
        min_length=1,
        max_length=2500,
    )
    priority_explanations: list[
        PriorityIssueExplanationV1
    ] = Field(
        min_length=1,
        max_length=20,
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        max_length=300,
    )
    confidence_score: float = Field(
        ge=0,
        le=100,
    )
    missing_evidence_warnings: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    @field_validator(
        "summary",
        "review_first_issue_id",
        "review_first_reason",
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
                "Priority summary text cannot be empty."
            )

        return normalized

    @field_validator(
        "evidence_ids",
        "missing_evidence_warnings",
    )
    @classmethod
    def normalize_text_values(
        cls,
        values: list[str],
    ) -> list[str]:
        return normalize_text_list(
            list(values)
        )

    @model_validator(mode="after")
    def validate_internal_references(
        self,
    ) -> "PriorityExplanationV1":
        issue_ids = [
            explanation.issue_id
            for explanation in self.priority_explanations
        ]

        if len(issue_ids) != len(set(issue_ids)):
            raise ValueError(
                "Priority explanations cannot contain duplicate issue IDs."
            )

        if self.review_first_issue_id not in issue_ids:
            raise ValueError(
                "review_first_issue_id must appear in "
                "priority_explanations."
            )

        nested_evidence_ids = {
            evidence_id
            for explanation in self.priority_explanations
            for evidence_id in explanation.evidence_ids
        }

        missing_ids = sorted(
            nested_evidence_ids.difference(
                self.evidence_ids
            )
        )

        if missing_ids:
            raise ValueError(
                "Priority-item evidence IDs must also appear "
                "in the top-level evidence_ids list: "
                + ", ".join(missing_ids)
            )

        return self



class RootCauseIssueExplanationV1(BaseModel):
    """One evidence-grounded manager explanation of a root cause."""

    model_config = ConfigDict(
        extra="forbid",
    )

    issue_id: str = Field(
        min_length=1,
        max_length=220,
    )
    deterministic_root_cause_category: str = Field(
        min_length=1,
        max_length=250,
    )
    deterministic_root_cause_summary: str = Field(
        min_length=1,
        max_length=4000,
    )
    deterministic_confidence_score: float = Field(
        ge=0,
        le=100,
    )
    manager_friendly_explanation: str = Field(
        min_length=1,
        max_length=6000,
    )
    likely_contributing_factors: list[str] = Field(
        default_factory=list,
        max_length=20,
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    confidence_score: float = Field(
        ge=0,
        le=100,
    )
    missing_evidence_warnings: list[str] = Field(
        default_factory=list,
        max_length=50,
    )
    unsupported_claims_rejected: list[str] = Field(
        default_factory=list,
        max_length=50,
    )
    human_review_required: bool = True

    @field_validator(
        "issue_id",
        "deterministic_root_cause_category",
        "deterministic_root_cause_summary",
        "manager_friendly_explanation",
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
                "Root-cause explanation text cannot be empty."
            )

        return normalized

    @field_validator(
        "likely_contributing_factors",
        "evidence_ids",
        "missing_evidence_warnings",
        "unsupported_claims_rejected",
    )
    @classmethod
    def normalize_text_values(
        cls,
        values: list[str],
    ) -> list[str]:
        return normalize_text_list(
            list(values)
        )

    @model_validator(mode="after")
    def require_human_review(
        self,
    ) -> "RootCauseIssueExplanationV1":
        if not self.human_review_required:
            raise ValueError(
                "Root-cause explanations must require human review."
            )

        return self


class RootCauseExplanationV1(BaseModel):
    """Controlled schema for the Root-Cause Agent LLM response."""

    model_config = ConfigDict(
        extra="forbid",
    )

    summary: str = Field(
        min_length=1,
        max_length=6000,
    )
    root_cause_explanations: list[
        RootCauseIssueExplanationV1
    ] = Field(
        min_length=1,
        max_length=20,
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        max_length=300,
    )
    confidence_score: float = Field(
        ge=0,
        le=100,
    )
    missing_evidence_warnings: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    human_review_required: bool = True

    @field_validator("summary")
    @classmethod
    def normalize_summary(
        cls,
        value: str,
    ) -> str:
        normalized = normalize_text(
            value
        )

        if not normalized:
            raise ValueError(
                "Root-cause summary text cannot be empty."
            )

        return normalized

    @field_validator(
        "evidence_ids",
        "missing_evidence_warnings",
    )
    @classmethod
    def normalize_text_values(
        cls,
        values: list[str],
    ) -> list[str]:
        return normalize_text_list(
            list(values)
        )

    @model_validator(mode="after")
    def validate_internal_references(
        self,
    ) -> "RootCauseExplanationV1":
        issue_ids = [
            explanation.issue_id
            for explanation in self.root_cause_explanations
        ]

        if len(issue_ids) != len(set(issue_ids)):
            raise ValueError(
                "Root-cause explanations cannot contain duplicate "
                "issue IDs."
            )

        nested_evidence_ids = {
            evidence_id
            for explanation in self.root_cause_explanations
            for evidence_id in explanation.evidence_ids
        }

        missing_ids = sorted(
            nested_evidence_ids.difference(
                self.evidence_ids
            )
        )

        if missing_ids:
            raise ValueError(
                "Root-cause evidence IDs must also appear in the "
                "top-level evidence_ids list: "
                + ", ".join(
                    missing_ids
                )
            )

        if not self.human_review_required:
            raise ValueError(
                "Root-cause enhancement must require human review."
            )

        return self

def collect_evidence_ids(
    value: object,
) -> list[str]:
    """Collect every evidence_ids value from nested output."""

    collected_ids: list[str] = []

    if isinstance(value, BaseModel):
        return collect_evidence_ids(
            value.model_dump(
                mode="python"
            )
        )

    if isinstance(value, dict):
        for key, item in value.items():
            if (
                str(key) == "evidence_ids"
                and isinstance(item, list)
            ):
                for evidence_id in (
                    normalize_text_list(
                        list(item)
                    )
                ):
                    if (
                        evidence_id
                        not in collected_ids
                    ):
                        collected_ids.append(
                            evidence_id
                        )

            nested_ids = collect_evidence_ids(
                item
            )

            for evidence_id in nested_ids:
                if (
                    evidence_id
                    not in collected_ids
                ):
                    collected_ids.append(
                        evidence_id
                    )

    elif isinstance(value, list):
        for item in value:
            nested_ids = collect_evidence_ids(
                item
            )

            for evidence_id in nested_ids:
                if (
                    evidence_id
                    not in collected_ids
                ):
                    collected_ids.append(
                        evidence_id
                    )

    return collected_ids


def validate_evidence_references(
    *,
    structured_output: BaseModel,
    allowed_evidence_ids: list[str],
) -> None:
    """Reject evidence identifiers not supplied by deterministic data."""

    allowed_ids = set(
        normalize_text_list(
            list(
                allowed_evidence_ids
            )
        )
    )

    referenced_ids = set(
        collect_evidence_ids(
            structured_output
        )
    )

    unsupported_ids = sorted(
        referenced_ids.difference(
            allowed_ids
        )
    )

    if unsupported_ids:
        raise LLMProviderResponseError(
            "The LLM response referenced unsupported "
            "evidence identifiers: "
            + ", ".join(
                unsupported_ids
            )
        )



def collect_named_references(
    value: object,
    field_names: set[str],
) -> dict[str, list[str]]:
    """Collect controlled scalar or list references by field name."""

    collected = {
        field_name: []
        for field_name in field_names
    }

    if isinstance(value, BaseModel):
        return collect_named_references(
            value.model_dump(
                mode="python"
            ),
            field_names,
        )

    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key)

            if normalized_key in field_names:
                raw_values = (
                    item
                    if isinstance(item, list)
                    else [item]
                )

                for reference in normalize_text_list(
                    list(raw_values)
                ):
                    if reference not in collected[normalized_key]:
                        collected[normalized_key].append(
                            reference
                        )

            nested = collect_named_references(
                item,
                field_names,
            )

            for field_name, references in nested.items():
                for reference in references:
                    if reference not in collected[field_name]:
                        collected[field_name].append(
                            reference
                        )

    elif isinstance(value, list):
        for item in value:
            nested = collect_named_references(
                item,
                field_names,
            )

            for field_name, references in nested.items():
                for reference in references:
                    if reference not in collected[field_name]:
                        collected[field_name].append(
                            reference
                        )

    return collected


def validate_named_references(
    *,
    structured_output: BaseModel,
    allowed_references: dict[str, list[str]],
) -> None:
    """Reject controlled references absent from deterministic context."""

    normalized_allowed = {
        str(field_name): set(
            normalize_text_list(
                list(values)
            )
        )
        for field_name, values in allowed_references.items()
    }

    collected = collect_named_references(
        structured_output,
        set(normalized_allowed),
    )

    unsupported_messages: list[str] = []

    for field_name, references in collected.items():
        unsupported = sorted(
            set(references).difference(
                normalized_allowed[field_name]
            )
        )

        if unsupported:
            unsupported_messages.append(
                f"{field_name}: "
                + ", ".join(unsupported)
            )

    if unsupported_messages:
        raise LLMProviderResponseError(
            "The LLM response referenced unsupported "
            "controlled identifiers: "
            + "; ".join(unsupported_messages)
        )


def build_execution_metadata(
    *,
    response: Any,
    response_schema_name: str | None,
) -> AgentExecutionMetadata:
    """Convert one successful LLM response into agent metadata."""

    return AgentExecutionMetadata(
        model_provider=(
            response.provider_name
        ),
        model_name=response.model_name,
        prompt_name=response.prompt_name,
        prompt_version=(
            response.prompt_version
        ),
        input_tokens=(
            response.usage.input_tokens
        ),
        output_tokens=(
            response.usage.output_tokens
        ),
        total_tokens=(
            response.usage.total_tokens
        ),
        estimated_cost_usd=(
            response.usage.estimated_cost_usd
        ),
        llm_latency_ms=(
            response.latency_ms
        ),
        tool_calls=[],
        run_metadata={
            "llm_enhancement_status": (
                "Complete"
            ),
            "structured_output": True,
            "response_schema_name": (
                response_schema_name
            ),
            "request_id": (
                response.request_id
            ),
            "provider_response_id": (
                response.provider_response_id
            ),
            "finish_reason": (
                response.finish_reason
            ),
            "used_mock_provider": (
                response.used_mock_provider
            ),
            "provider_metadata": dict(
                response.metadata
            ),
        },
    )


def build_failed_execution_metadata(
    *,
    provider: BaseLLMProvider,
    prompt_name: str,
    prompt_version: str,
    error: Exception,
) -> AgentExecutionMetadata:
    """Build metadata for a failed optional LLM enhancement."""

    response = getattr(
        error,
        LLM_RESPONSE_ATTRIBUTE,
        None,
    )

    if response is not None:
        metadata = build_execution_metadata(
            response=response,
            response_schema_name=getattr(
                response,
                "response_schema_name",
                None,
            ),
        )

        metadata.run_metadata[
            "llm_enhancement_status"
        ] = "Fallback"

        metadata.llm_error_type = type(
            error
        ).__name__

        metadata.llm_error_message = (
            normalize_text(
                error
            )[:4000]
            or type(error).__name__
        )

        return metadata

    return AgentExecutionMetadata(
        model_provider=(
            provider.provider_name
        ),
        model_name=(
            provider.config.model_name
        ),
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        tool_calls=[],
        run_metadata={
            "llm_enhancement_status": (
                "Fallback"
            ),
            "structured_output": False,
        },
        llm_error_type=type(
            error
        ).__name__,
        llm_error_message=(
            normalize_text(
                error
            )[:4000]
            or type(error).__name__
        ),
    )


async def run_structured_enhancement(
    *,
    provider: BaseLLMProvider,
    agent_name: str,
    agent_version: str,
    prompt_name: str,
    prompt_version: str,
    validated_context: dict[str, Any],
    response_model: type[ResponseModel],
    allowed_evidence_ids: list[str],
    mock_structured_output: dict[
        str,
        Any,
    ] | None = None,
    request_metadata: dict[
        str,
        Any,
    ] | None = None,
    allowed_references: dict[
        str,
        list[str],
    ] | None = None,
    output_validator: Callable[
        [ResponseModel],
        None,
    ] | None = None,
) -> tuple[
    ResponseModel,
    AgentExecutionMetadata,
]:
    """
    Execute one grounded, structured, provider-independent LLM call.

    Prompt rendering, provider guardrails, schema validation, evidence
    validation and execution-metadata construction are centralized here.
    """

    prompt = default_prompt_registry.get(
        prompt_name,
        prompt_version,
    )

    messages = prompt.render(
        {
            "validated_context_json": (
                validated_context
            )
        }
    )

    metadata = dict(
        request_metadata
        or {}
    )

    if (
        provider.provider_name == "mock"
        and mock_structured_output
        is not None
    ):
        metadata[
            "mock_structured_output"
        ] = deepcopy(
            mock_structured_output
        )

    request = LLMRequest(
        agent_name=agent_name,
        agent_version=agent_version,
        prompt_name=prompt.name,
        prompt_version=prompt.version,
        messages=messages,
        response_schema_name=(
            prompt.response_schema_name
        ),
        model_name=(
            provider.config.model_name
        ),
        temperature=(
            provider.config.temperature
        ),
        max_output_tokens=(
            provider.config.max_output_tokens
        ),
        timeout_seconds=(
            provider.config.timeout_seconds
        ),
        max_retries=(
            provider.config.max_retries
        ),
        max_estimated_cost_usd=(
            provider.config.max_estimated_cost_usd
        ),
        allowed_tools=list(
            prompt.allowed_tools
        ),
        require_json_object=True,
        metadata=metadata,
    )

    response = await provider.generate(
        request
    )

    try:
        validated_output = (
            response_model.model_validate(
                response.structured_output
            )
        )

    except ValidationError as error:
        controlled_error = (
            LLMProviderResponseError(
                "The LLM response did not match "
                f"{response_model.__name__}."
            )
        )

        setattr(
            controlled_error,
            LLM_RESPONSE_ATTRIBUTE,
            response,
        )

        raise controlled_error from error

    try:
        validate_evidence_references(
            structured_output=validated_output,
            allowed_evidence_ids=(
                allowed_evidence_ids
            ),
        )

        if allowed_references:
            validate_named_references(
                structured_output=validated_output,
                allowed_references=allowed_references,
            )

        if output_validator is not None:
            output_validator(
                validated_output
            )

    except LLMError as error:
        setattr(
            error,
            LLM_RESPONSE_ATTRIBUTE,
            response,
        )

        raise

    except Exception as error:
        controlled_error = LLMProviderResponseError(
            "The LLM response failed controlled factual validation: "
            + (
                normalize_text(error)
                or type(error).__name__
            )
        )

        setattr(
            controlled_error,
            LLM_RESPONSE_ATTRIBUTE,
            response,
        )

        raise controlled_error from error

    execution_metadata = (
        build_execution_metadata(
            response=response,
            response_schema_name=(
                prompt.response_schema_name
            ),
        )
    )

    return (
        validated_output,
        execution_metadata,
    )


def attach_deterministic_fallback(
    *,
    error: LLMError,
    deterministic_output: dict[str, Any],
    execution_metadata: AgentExecutionMetadata,
) -> LLMError:
    """
    Attach already-created deterministic output to one LLM failure.

    BaseAgent will call the agent's fallback method with the original
    LLM exception, preserving its exact type in AgentResult.
    """

    setattr(
        error,
        FALLBACK_OUTPUT_ATTRIBUTE,
        deepcopy(
            deterministic_output
        ),
    )

    setattr(
        error,
        FALLBACK_METADATA_ATTRIBUTE,
        execution_metadata.model_copy(
            deep=True
        ),
    )

    return error


def build_attached_fallback_output(
    error: Exception,
) -> dict[str, Any] | None:
    """Build a deterministic fallback result attached to an LLM error."""

    deterministic_output = getattr(
        error,
        FALLBACK_OUTPUT_ATTRIBUTE,
        None,
    )

    execution_metadata = getattr(
        error,
        FALLBACK_METADATA_ATTRIBUTE,
        None,
    )

    if not isinstance(
        deterministic_output,
        dict,
    ):
        return None

    if not isinstance(
        execution_metadata,
        AgentExecutionMetadata,
    ):
        return None

    fallback_output = deepcopy(
        deterministic_output
    )

    fallback_output[
        "llm_enhancement"
    ] = {
        "status": "Fallback",
        "summary": (
            "The deterministic agent result was "
            "retained because LLM enhancement failed."
        ),
        "error_type": type(
            error
        ).__name__,
        "error_message": (
            normalize_text(
                error
            )[:1000]
            or type(error).__name__
        ),
    }

    fallback_output[
        "_execution_metadata"
    ] = execution_metadata.model_dump(
        mode="python"
    )

    return fallback_output