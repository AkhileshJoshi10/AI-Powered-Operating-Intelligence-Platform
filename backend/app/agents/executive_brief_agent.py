from __future__ import annotations

import re
from typing import Any

from backend.app.agents.agent_context import AgentContext
from backend.app.agents.base_agent import BaseAgent
from backend.app.agents.llm_enhancement import (
    ExecutiveBriefEnhancementV1,
    attach_deterministic_fallback,
    build_attached_fallback_output,
    build_failed_execution_metadata,
    run_structured_enhancement,
)
from backend.app.core.config import settings
from backend.app.llm import (
    BaseLLMProvider,
    LLMError,
    LLMProviderResponseError,
    get_configured_provider,
)
from backend.app.schemas.executive_briefs import (
    GenerateExecutiveBriefResponse,
)
from backend.app.services.executive_brief_service import (
    generate_daily_executive_brief,
)


EXECUTIVE_BRIEF_PROMPT_NAME = "executive_brief_enhancement"
EXECUTIVE_BRIEF_PROMPT_VERSION = "v1"

MAXIMUM_KPI_REFERENCES = 20
MAXIMUM_ISSUE_REFERENCES = 10
MAXIMUM_RECOMMENDATION_REFERENCES = 10
MAXIMUM_TASK_REFERENCES = 20
MAXIMUM_ATTENTION_REFERENCES = 10


def clean_text(
    value: object,
) -> str:
    """Convert one value into compact normalized text."""

    if value is None:
        return ""

    return " ".join(
        str(value).split()
    )


def safe_int(
    value: object,
) -> int:
    """Convert a value safely to an integer."""

    if value is None or isinstance(value, bool):
        return 0

    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def get_mapping(
    value: object,
) -> dict[str, Any]:
    """Return a dictionary or an empty dictionary."""

    if isinstance(value, dict):
        return value

    return {}


def get_list(
    value: object,
) -> list[Any]:
    """Return a list or an empty list."""

    if isinstance(value, list):
        return value

    return []


def get_string_list(
    value: object,
) -> list[str]:
    """Return normalized non-empty strings without duplicates."""

    result: list[str] = []

    for item in get_list(value):
        cleaned_item = clean_text(
            item
        )

        if (
            cleaned_item
            and cleaned_item not in result
        ):
            result.append(
                cleaned_item
            )

    return result


def normalize_reference_component(
    value: object,
    *,
    fallback: str,
) -> str:
    """Create a stable readable component for one reference ID."""

    normalized = clean_text(
        value
    )

    if not normalized:
        normalized = fallback

    normalized = re.sub(
        r"[^A-Za-z0-9_.:-]+",
        "-",
        normalized,
    ).strip("-")

    return normalized or fallback


def add_evidence_reference(
    *,
    records: list[dict[str, str]],
    by_source: dict[str, list[str]],
    evidence_id: str,
    source_type: str,
    source_identifier: str,
    summary: str,
) -> None:
    """Add one unique deterministic Executive Brief reference."""

    if any(
        record["evidence_id"] == evidence_id
        for record in records
    ):
        return

    records.append(
        {
            "evidence_id": evidence_id,
            "source_type": source_type,
            "source_identifier": source_identifier,
            "summary": summary,
        }
    )

    by_source.setdefault(
        source_type,
        [],
    ).append(
        evidence_id
    )


def build_executive_brief_evidence_references(
    brief: dict[str, Any],
) -> dict[str, Any]:
    """Build controlled references from the persisted brief snapshot."""

    brief_data = get_mapping(
        brief.get("brief_data")
    )
    kpi_snapshot = get_mapping(
        brief_data.get("kpi_snapshot")
    )
    issue_snapshot = get_mapping(
        brief_data.get("issue_snapshot")
    )
    recommendation_snapshot = get_mapping(
        brief_data.get("recommendation_snapshot")
    )
    task_snapshot = get_mapping(
        brief_data.get("task_snapshot")
    )

    records: list[dict[str, str]] = []
    by_source: dict[str, list[str]] = {}

    for index, raw_kpi in enumerate(
        get_list(
            kpi_snapshot.get("kpis")
        )[:MAXIMUM_KPI_REFERENCES],
        start=1,
    ):
        kpi = get_mapping(
            raw_kpi
        )
        identifier = normalize_reference_component(
            kpi.get("kpi_key")
            or kpi.get("kpi_name"),
            fallback=f"KPI-{index}",
        )
        evidence_id = f"BRIEF-KPI:{identifier}"

        add_evidence_reference(
            records=records,
            by_source=by_source,
            evidence_id=evidence_id,
            source_type="KPI",
            source_identifier=identifier,
            summary=(
                clean_text(
                    kpi.get("kpi_name")
                )
                + ": "
                + clean_text(
                    kpi.get("display_value")
                    or kpi.get("value")
                )
            ).strip(": "),
        )

    for index, raw_issue in enumerate(
        get_list(
            issue_snapshot.get("top_open_issues")
        )[:MAXIMUM_ISSUE_REFERENCES],
        start=1,
    ):
        issue = get_mapping(
            raw_issue
        )
        identifier = normalize_reference_component(
            issue.get("issue_id"),
            fallback=f"ISSUE-{index}",
        )
        evidence_id = f"BRIEF-ISSUE:{identifier}"

        add_evidence_reference(
            records=records,
            by_source=by_source,
            evidence_id=evidence_id,
            source_type="Issue",
            source_identifier=identifier,
            summary=(
                clean_text(
                    issue.get("title")
                )
                or clean_text(
                    issue.get("summary")
                )
                or identifier
            ),
        )

    for index, raw_recommendation in enumerate(
        get_list(
            recommendation_snapshot.get("top_recommendations")
        )[:MAXIMUM_RECOMMENDATION_REFERENCES],
        start=1,
    ):
        recommendation = get_mapping(
            raw_recommendation
        )
        identifier = normalize_reference_component(
            recommendation.get("recommendation_id")
            or recommendation.get("issue_id"),
            fallback=f"RECOMMENDATION-{index}",
        )
        evidence_id = f"BRIEF-RECOMMENDATION:{identifier}"

        add_evidence_reference(
            records=records,
            by_source=by_source,
            evidence_id=evidence_id,
            source_type="Recommendation",
            source_identifier=identifier,
            summary=(
                clean_text(
                    recommendation.get("recommendation_title")
                )
                or clean_text(
                    recommendation.get("recommendation_text")
                )
                or identifier
            ),
        )

    task_records: list[dict[str, Any]] = []

    for section_name in (
        "overdue_tasks",
        "priority_tasks",
    ):
        for raw_task in get_list(
            task_snapshot.get(section_name)
        ):
            task = get_mapping(
                raw_task
            )

            if task not in task_records:
                task_records.append(
                    task
                )

            if len(task_records) >= MAXIMUM_TASK_REFERENCES:
                break

        if len(task_records) >= MAXIMUM_TASK_REFERENCES:
            break

    for index, task in enumerate(
        task_records,
        start=1,
    ):
        identifier = normalize_reference_component(
            task.get("task_id"),
            fallback=f"TASK-{index}",
        )
        evidence_id = f"BRIEF-TASK:{identifier}"

        add_evidence_reference(
            records=records,
            by_source=by_source,
            evidence_id=evidence_id,
            source_type="Task",
            source_identifier=identifier,
            summary=(
                clean_text(
                    task.get("task_title")
                    or task.get("title")
                )
                or identifier
            ),
        )

    management_attention = get_string_list(
        brief_data.get("management_attention")
    )

    for index, attention_text in enumerate(
        management_attention[:MAXIMUM_ATTENTION_REFERENCES],
        start=1,
    ):
        evidence_id = f"BRIEF-ATTENTION:{index:03d}"

        add_evidence_reference(
            records=records,
            by_source=by_source,
            evidence_id=evidence_id,
            source_type="Management Attention",
            source_identifier=f"ATTENTION-{index:03d}",
            summary=attention_text,
        )

    return {
        "source_field": "internal_brief_reference_id",
        "included_count": len(records),
        "by_source": by_source,
        "records": records,
    }


def build_deterministic_executive_brief_output(
    context: AgentContext,
) -> dict[str, Any]:
    """Generate, validate, persist and format today's deterministic brief."""

    del context

    response_data = (
        generate_daily_executive_brief()
    )

    validated_response = (
        GenerateExecutiveBriefResponse(
            **response_data
        )
    )

    response_json = (
        validated_response.model_dump(
            mode="json"
        )
    )

    brief = get_mapping(
        response_json.get("brief")
    )
    brief_data = get_mapping(
        brief.get("brief_data")
    )

    kpi_snapshot = get_mapping(
        brief_data.get("kpi_snapshot")
    )
    issue_snapshot = get_mapping(
        brief_data.get("issue_snapshot")
    )
    recommendation_snapshot = get_mapping(
        brief_data.get("recommendation_snapshot")
    )
    task_snapshot = get_mapping(
        brief_data.get("task_snapshot")
    )

    management_attention = get_string_list(
        brief_data.get("management_attention")
    )

    snapshot = {
        "total_kpis": safe_int(
            kpi_snapshot.get("total_kpis")
        ),
        "open_issue_count": safe_int(
            issue_snapshot.get("open_issue_count")
        ),
        "high_priority_open_issue_count": safe_int(
            issue_snapshot.get(
                "high_priority_open_issue_count"
            )
        ),
        "recommendations_needing_review": safe_int(
            recommendation_snapshot.get(
                "recommendations_needing_review"
            )
        ),
        "active_task_count": safe_int(
            task_snapshot.get("active_task_count")
        ),
        "blocked_task_count": safe_int(
            task_snapshot.get("blocked_task_count")
        ),
        "overdue_task_count": safe_int(
            task_snapshot.get("overdue_task_count")
        ),
    }

    action = clean_text(
        response_json.get("action")
    )

    summary = (
        f"Daily Executive Brief {action} with "
        f"{snapshot['total_kpis']} KPIs, "
        f"{snapshot['open_issue_count']} open issues, "
        f"{snapshot['high_priority_open_issue_count']} "
        f"high-priority open issues, and "
        f"{snapshot['recommendations_needing_review']} "
        f"recommendations requiring management review. "
        f"The task workflow contains "
        f"{snapshot['active_task_count']} active tasks, including "
        f"{snapshot['blocked_task_count']} blocked and "
        f"{snapshot['overdue_task_count']} overdue."
    )

    return {
        "summary": summary,
        "brief_status": "Complete",
        "generated_at": response_json["generated_at"],
        "generation": {
            "method": (
                "Deterministic Current-State "
                "Business Aggregation"
            ),
            "action": action,
            "message": response_json["message"],
            "brief_version": brief_data.get(
                "brief_version"
            ),
        },
        "snapshot": snapshot,
        "management_attention": management_attention,
        "database": {
            "persisted": True,
            "table": "executive_briefs",
            "brief_id": brief.get("brief_id"),
            "brief_date": brief.get("brief_date"),
            "brief_type": brief.get("brief_type"),
            "record_status": brief.get("status"),
            "same_day_behavior": (
                "Create the first daily record or "
                "update the existing record"
            ),
        },
        "llm_protection": {
            "deterministic_brief_persisted_first": True,
            "llm_enhancement_persisted_to_executive_briefs": False,
            "database_record_remains_authoritative": True,
            "workflow_actions_performed": False,
            "historical_comparison_available": False,
        },
        "evidence_references": (
            build_executive_brief_evidence_references(
                brief
            )
        ),
        "brief": brief,
    }


def get_allowed_executive_brief_evidence_ids(
    deterministic_output: dict[str, Any],
) -> list[str]:
    """Return deterministic internal references the LLM may cite."""

    evidence_section = get_mapping(
        deterministic_output.get(
            "evidence_references"
        )
    )

    evidence_ids: list[str] = []

    for raw_record in get_list(
        evidence_section.get("records")
    ):
        record = get_mapping(
            raw_record
        )
        evidence_id = clean_text(
            record.get("evidence_id")
        )

        if (
            evidence_id
            and evidence_id not in evidence_ids
        ):
            evidence_ids.append(
                evidence_id
            )

    return evidence_ids


def build_attention_reference_items(
    deterministic_output: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build deterministic attention IDs and relevant evidence IDs."""

    evidence_section = get_mapping(
        deterministic_output.get(
            "evidence_references"
        )
    )
    by_source = get_mapping(
        evidence_section.get("by_source")
    )

    issue_ids = get_string_list(
        by_source.get("Issue")
    )
    recommendation_ids = get_string_list(
        by_source.get("Recommendation")
    )
    task_ids = get_string_list(
        by_source.get("Task")
    )
    kpi_ids = get_string_list(
        by_source.get("KPI")
    )
    attention_evidence_ids = get_string_list(
        by_source.get("Management Attention")
    )

    items: list[dict[str, Any]] = []

    for index, attention_text in enumerate(
        get_string_list(
            deterministic_output.get(
                "management_attention"
            )
        ),
        start=1,
    ):
        normalized_attention = attention_text.casefold()
        relevant_ids: list[str] = []

        if (
            "issue" in normalized_attention
            or "priority" in normalized_attention
        ):
            relevant_ids.extend(
                issue_ids
            )

        if "recommendation" in normalized_attention:
            relevant_ids.extend(
                recommendation_ids
            )

        if (
            "task" in normalized_attention
            or "blocked" in normalized_attention
            or "overdue" in normalized_attention
        ):
            relevant_ids.extend(
                task_ids
            )

        if "kpi" in normalized_attention:
            relevant_ids.extend(
                kpi_ids
            )

        attention_reference = (
            f"BRIEF-ATTENTION:{index:03d}"
        )

        if attention_reference in attention_evidence_ids:
            relevant_ids.insert(
                0,
                attention_reference,
            )

        deduplicated_ids: list[str] = []

        for evidence_id in relevant_ids:
            if evidence_id not in deduplicated_ids:
                deduplicated_ids.append(
                    evidence_id
                )

        items.append(
            {
                "attention_id": f"ATTENTION-{index:03d}",
                "deterministic_attention_text": attention_text,
                "evidence_ids": deduplicated_ids[:20],
            }
        )

    return items


def build_executive_brief_llm_context(
    deterministic_output: dict[str, Any],
) -> dict[str, Any]:
    """Create compact grounded context for Executive Brief enhancement."""

    brief = get_mapping(
        deterministic_output.get("brief")
    )

    return {
        "deterministic_summary": deterministic_output.get(
            "summary"
        ),
        "deterministic_brief_summary_text": brief.get(
            "summary_text"
        ),
        "generation": deterministic_output.get(
            "generation",
            {},
        ),
        "snapshot": deterministic_output.get(
            "snapshot",
            {},
        ),
        "management_attention": (
            build_attention_reference_items(
                deterministic_output
            )
        ),
        "database": {
            "brief_date": get_mapping(
                deterministic_output.get(
                    "database"
                )
            ).get("brief_date"),
            "brief_type": get_mapping(
                deterministic_output.get(
                    "database"
                )
            ).get("brief_type"),
            "record_status": get_mapping(
                deterministic_output.get(
                    "database"
                )
            ).get("record_status"),
        },
        "evidence_references": get_mapping(
            deterministic_output.get(
                "evidence_references"
            )
        ).get("records", []),
        "comparison_policy": {
            "historical_comparison_available": False,
            "instruction": (
                "Do not claim a trend, increase, decrease, or "
                "change because no prior-period brief is supplied."
            ),
        },
        "control_policy": deterministic_output.get(
            "llm_protection",
            {},
        ),
    }


def build_mock_executive_brief_output(
    deterministic_output: dict[str, Any],
) -> dict[str, Any]:
    """Build grounded structured output for the mock provider."""

    snapshot = get_mapping(
        deterministic_output.get("snapshot")
    )
    database = get_mapping(
        deterministic_output.get("database")
    )
    generation = get_mapping(
        deterministic_output.get("generation")
    )
    brief = get_mapping(
        deterministic_output.get("brief")
    )

    attention_items = (
        build_attention_reference_items(
            deterministic_output
        )
    )

    management_attention: list[
        dict[str, Any]
    ] = []

    all_evidence_ids: list[str] = []

    for item in attention_items:
        evidence_ids = list(
            item["evidence_ids"]
        )

        for evidence_id in evidence_ids:
            if evidence_id not in all_evidence_ids:
                all_evidence_ids.append(
                    evidence_id
                )

        management_attention.append(
            {
                "attention_id": item["attention_id"],
                "deterministic_attention_text": (
                    item[
                        "deterministic_attention_text"
                    ]
                ),
                "executive_context": (
                    item[
                        "deterministic_attention_text"
                    ]
                    + " Management review remains required "
                    "before any workflow action is taken."
                ),
                "evidence_ids": evidence_ids,
            }
        )

    warnings = [
        (
            "Historical comparison was not supplied, so no trend "
            "or change claim was generated."
        )
    ]

    if not all_evidence_ids:
        warnings.append(
            "No internal brief reference identifiers were available."
        )

    narrative = (
        clean_text(
            brief.get("summary_text")
        )
        or clean_text(
            deterministic_output.get(
                "summary"
            )
        )
    )

    return {
        "summary": (
            "Prepared a manager-facing narrative from the persisted "
            "deterministic Executive Brief without changing its "
            "counts, status, database record, or workflow state."
        ),
        "headline": (
            "Current operating priorities require management review"
        ),
        "executive_narrative": narrative,
        "deterministic_brief_action": clean_text(
            generation.get("action")
        ),
        "deterministic_brief_date": clean_text(
            database.get("brief_date")
        ),
        "deterministic_record_status": clean_text(
            database.get("record_status")
        ),
        "deterministic_snapshot": {
            key: safe_int(value)
            for key, value in snapshot.items()
        },
        "management_attention": management_attention,
        "evidence_ids": all_evidence_ids,
        "comparison_available": False,
        "change_summary": (
            "Historical comparison was not available in the "
            "deterministic brief, so no trend or change claim "
            "was made."
        ),
        "missing_evidence_warnings": warnings,
        "human_review_required": True,
        "database_update_performed": False,
        "workflow_action_performed": False,
    }


def validate_executive_brief_enhancement_facts(
    *,
    enhancement: ExecutiveBriefEnhancementV1,
    deterministic_output: dict[str, Any],
) -> None:
    """Reject changed counts, status, references, or control flags."""

    expected_snapshot = {
        key: safe_int(value)
        for key, value in get_mapping(
            deterministic_output.get(
                "snapshot"
            )
        ).items()
    }

    returned_snapshot = (
        enhancement.deterministic_snapshot.model_dump(
            mode="python"
        )
    )

    if returned_snapshot != expected_snapshot:
        raise LLMProviderResponseError(
            "The LLM changed the deterministic Executive Brief "
            "snapshot counts."
        )

    generation = get_mapping(
        deterministic_output.get("generation")
    )
    database = get_mapping(
        deterministic_output.get("database")
    )

    if (
        enhancement.deterministic_brief_action
        != clean_text(
            generation.get("action")
        )
    ):
        raise LLMProviderResponseError(
            "The LLM changed the deterministic Executive Brief action."
        )

    if (
        enhancement.deterministic_brief_date
        != clean_text(
            database.get("brief_date")
        )
    ):
        raise LLMProviderResponseError(
            "The LLM changed the deterministic Executive Brief date."
        )

    if (
        enhancement.deterministic_record_status
        != clean_text(
            database.get("record_status")
        )
    ):
        raise LLMProviderResponseError(
            "The LLM changed the deterministic Executive Brief "
            "record status."
        )

    expected_attention = (
        build_attention_reference_items(
            deterministic_output
        )
    )

    expected_attention_ids = [
        item["attention_id"]
        for item in expected_attention
    ]
    returned_attention_ids = [
        item.attention_id
        for item in enhancement.management_attention
    ]

    if returned_attention_ids != expected_attention_ids:
        raise LLMProviderResponseError(
            "The LLM changed or reordered the deterministic "
            "management-attention sequence."
        )

    expected_by_id = {
        item["attention_id"]: item
        for item in expected_attention
    }

    for attention in enhancement.management_attention:
        expected = expected_by_id[
            attention.attention_id
        ]

        if (
            attention.deterministic_attention_text
            != expected[
                "deterministic_attention_text"
            ]
        ):
            raise LLMProviderResponseError(
                "The LLM changed deterministic management-attention "
                f"text for {attention.attention_id}."
            )

        unsupported_ids = sorted(
            set(
                attention.evidence_ids
            ).difference(
                expected["evidence_ids"]
            )
        )

        if unsupported_ids:
            raise LLMProviderResponseError(
                "The LLM cited evidence outside the deterministic "
                f"attention context for {attention.attention_id}: "
                + ", ".join(
                    unsupported_ids
                )
            )

    if enhancement.comparison_available:
        raise LLMProviderResponseError(
            "The LLM claimed a historical comparison even though "
            "the deterministic brief supplied no prior-period data."
        )


class ExecutiveBriefAgent(BaseAgent):
    """
    Persist the deterministic brief and optionally enhance its narrative.

    Deterministic KPI, issue, recommendation and task values, database
    persistence, same-day update behaviour, record status and management
    workflow remain authoritative.
    """

    name = "Executive Brief Agent"
    version = "1.1.0"

    description = (
        "Generates or updates the deterministic Daily Executive Brief "
        "and optionally adds a grounded manager-facing narrative "
        "without changing business values or workflow state."
    )

    def __init__(
        self,
        llm_provider: BaseLLMProvider | None = None,
    ) -> None:
        """Initialize with an optional provider for injection/testing."""

        super().__init__()

        self._llm_provider = llm_provider

        if self._llm_provider is None and settings.llm_enabled:
            self._llm_provider = get_configured_provider()

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        """Run deterministic brief generation and optional enhancement."""

        deterministic_output = (
            build_deterministic_executive_brief_output(
                context
            )
        )

        provider = self._llm_provider

        if provider is None or not provider.config.enabled:
            return deterministic_output

        try:
            validated_context = (
                build_executive_brief_llm_context(
                    deterministic_output
                )
            )
            allowed_evidence_ids = (
                get_allowed_executive_brief_evidence_ids(
                    deterministic_output
                )
            )
            mock_structured_output = (
                build_mock_executive_brief_output(
                    deterministic_output
                )
                if provider.provider_name == "mock"
                else None
            )

            enhancement, execution_metadata = (
                await run_structured_enhancement(
                    provider=provider,
                    agent_name=self.name,
                    agent_version=self.version,
                    prompt_name=(
                        EXECUTIVE_BRIEF_PROMPT_NAME
                    ),
                    prompt_version=(
                        EXECUTIVE_BRIEF_PROMPT_VERSION
                    ),
                    validated_context=validated_context,
                    response_model=(
                        ExecutiveBriefEnhancementV1
                    ),
                    allowed_evidence_ids=(
                        allowed_evidence_ids
                    ),
                    mock_structured_output=(
                        mock_structured_output
                    ),
                    request_metadata={
                        "run_id": context.run_id,
                        "run_type": context.run_type,
                    },
                    output_validator=lambda output: (
                        validate_executive_brief_enhancement_facts(
                            enhancement=output,
                            deterministic_output=(
                                deterministic_output
                            ),
                        )
                    ),
                )
            )

        except LLMError as error:
            failed_metadata = (
                build_failed_execution_metadata(
                    provider=provider,
                    prompt_name=(
                        EXECUTIVE_BRIEF_PROMPT_NAME
                    ),
                    prompt_version=(
                        EXECUTIVE_BRIEF_PROMPT_VERSION
                    ),
                    error=error,
                )
            )

            raise attach_deterministic_fallback(
                error=error,
                deterministic_output=deterministic_output,
                execution_metadata=failed_metadata,
            )

        except Exception as error:
            controlled_error = LLMProviderResponseError(
                "Executive Brief LLM enhancement preparation failed: "
                + (
                    clean_text(error)
                    or type(error).__name__
                )
            )
            failed_metadata = (
                build_failed_execution_metadata(
                    provider=provider,
                    prompt_name=(
                        EXECUTIVE_BRIEF_PROMPT_NAME
                    ),
                    prompt_version=(
                        EXECUTIVE_BRIEF_PROMPT_VERSION
                    ),
                    error=controlled_error,
                )
            )

            raise attach_deterministic_fallback(
                error=controlled_error,
                deterministic_output=deterministic_output,
                execution_metadata=failed_metadata,
            )

        enhanced_output = dict(
            deterministic_output
        )
        enhanced_output["summary"] = (
            enhancement.summary
        )
        enhanced_output["llm_enhancement"] = {
            "status": "Complete",
            "schema_name": (
                ExecutiveBriefEnhancementV1.__name__
            ),
            "deterministic_summary": (
                deterministic_output["summary"]
            ),
            "persisted_to_executive_briefs": False,
            "database_record_authoritative": True,
            **enhancement.model_dump(
                mode="python"
            ),
        }
        enhanced_output["_execution_metadata"] = (
            execution_metadata.model_dump(
                mode="python"
            )
        )

        return enhanced_output

    async def fallback(
        self,
        context: AgentContext,
        error: Exception,
    ) -> dict[str, Any] | None:
        """Return the already-persisted deterministic brief."""

        del context

        return build_attached_fallback_output(
            error
        )