from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pandas as pd

from backend.analytics.complaint_analysis import (
    run_complaint_analysis,
)
from backend.analytics.executive_priority_selector import (
    load_active_issues,
    select_executive_priorities,
)
from backend.analytics.inventory_analysis import (
    run_inventory_analysis,
)
from backend.analytics.manager_priority_list import (
    load_active_issue_summary,
    load_manager_priorities,
)
from backend.analytics.priority_engine import (
    COMMON_COLUMNS,
    build_priority_outputs,
    save_to_database,
)
from backend.analytics.sales_analysis import (
    run_sales_analysis,
)
from backend.app.agents.agent_context import AgentContext
from backend.app.agents.base_agent import BaseAgent
from backend.app.agents.llm_enhancement import (
    PriorityExplanationV1,
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
from backend.app.db.database import engine
from backend.app.services.vendor_finance_analytics_service import (
    run_finance_analysis,
    run_vendor_analysis,
)


DEFAULT_MANAGER_LIMIT = 15
DEFAULT_EXECUTIVE_LIMIT = 10

MAXIMUM_MANAGER_LIMIT = 100
MAXIMUM_EXECUTIVE_LIMIT = 50

PRIORITY_PROMPT_NAME = "priority_explanation"
PRIORITY_PROMPT_VERSION = "v1"
MAXIMUM_LLM_PRIORITY_ITEMS = 20
MAXIMUM_EVIDENCE_IDS_PER_ISSUE = 12


def current_utc_time() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(timezone.utc)


def get_positive_limit(
    context: AgentContext,
    *,
    setting_name: str,
    default_value: int,
    maximum_value: int,
) -> int:
    """Read and validate a positive integer limit."""

    configured_value = context.input_data.get(
        setting_name,
        default_value,
    )

    if isinstance(configured_value, bool):
        raise ValueError(
            f"{setting_name} must be an integer."
        )

    try:
        limit = int(configured_value)

    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{setting_name} must be an integer."
        ) from error

    if limit < 1:
        raise ValueError(
            f"{setting_name} must be at least 1."
        )

    if limit > maximum_value:
        raise ValueError(
            f"{setting_name} cannot be greater than "
            f"{maximum_value}."
        )

    return limit


def normalize_findings(
    *,
    findings: pd.DataFrame,
    source_module: str,
    source_report: str,
) -> pd.DataFrame:
    """
    Normalize one analytics DataFrame for the existing priority engine.

    Missing common columns are added without changing the underlying
    analytics findings.
    """

    if not isinstance(findings, pd.DataFrame):
        raise TypeError(
            f"{source_module} analytics must return a DataFrame."
        )

    normalized_findings = findings.copy()

    for column_name in COMMON_COLUMNS:
        if column_name not in normalized_findings.columns:
            normalized_findings[column_name] = None

    normalized_findings = normalized_findings[
        COMMON_COLUMNS
    ].copy()

    normalized_findings["source_module"] = source_module
    normalized_findings["source_report"] = source_report

    return normalized_findings


def build_detailed_findings(
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Run all deterministic analytics and build the priority input.

    This avoids depending on previously generated CSV report files.
    """

    sales_findings = normalize_findings(
        findings=run_sales_analysis(engine),
        source_module="sales",
        source_report="sales_analysis.csv",
    )

    inventory_findings = normalize_findings(
        findings=run_inventory_analysis(engine),
        source_module="inventory",
        source_report="inventory_analysis.csv",
    )

    complaint_findings = normalize_findings(
        findings=run_complaint_analysis(engine),
        source_module="complaints",
        source_report="complaint_analysis.csv",
    )

    vendor_findings = normalize_findings(
        findings=run_vendor_analysis(),
        source_module="vendors",
        source_report="vendor_finance_analysis.csv",
    )

    finance_findings = normalize_findings(
        findings=run_finance_analysis(),
        source_module="finance",
        source_report="vendor_finance_analysis.csv",
    )

    source_dataframes = {
        "sales": sales_findings,
        "inventory": inventory_findings,
        "complaints": complaint_findings,
        "vendors": vendor_findings,
        "finance": finance_findings,
    }

    source_finding_counts = {
        source_name: len(source_dataframe)
        for source_name, source_dataframe
        in source_dataframes.items()
    }

    detailed_findings = pd.concat(
        list(source_dataframes.values()),
        ignore_index=True,
    )

    return detailed_findings, source_finding_counts


def clean_scalar(value: object) -> object:
    """Convert pandas and NumPy scalar values to JSON-safe values."""

    if value is None:
        return None

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    try:
        missing_result = pd.isna(value)

        if isinstance(missing_result, bool) and missing_result:
            return None

    except (TypeError, ValueError):
        pass

    item_method = getattr(
        value,
        "item",
        None,
    )

    if callable(item_method):
        try:
            return item_method()
        except (TypeError, ValueError):
            pass

    return value


def dataframe_to_records(
    dataframe: pd.DataFrame,
) -> list[dict[str, object]]:
    """Convert a DataFrame into JSON-safe records."""

    records: list[dict[str, object]] = []

    for record in dataframe.to_dict(
        orient="records"
    ):
        cleaned_record = {
            str(key): clean_scalar(value)
            for key, value in record.items()
        }

        records.append(cleaned_record)

    return records


def build_priority_counts(
    issues_dataframe: pd.DataFrame,
) -> dict[str, int]:
    """Build issue counts for High, Medium, and Low priorities."""

    priority_counts = {
        "High": 0,
        "Medium": 0,
        "Low": 0,
    }

    if issues_dataframe.empty:
        return priority_counts

    calculated_counts = (
        issues_dataframe.groupby(
            "priority_level"
        )
        .size()
        .to_dict()
    )

    for priority_level, issue_count in (
        calculated_counts.items()
    ):
        priority_counts[
            str(priority_level)
        ] = int(issue_count)

    return priority_counts


def build_active_issue_counts(
    active_issue_summary: pd.DataFrame,
) -> dict[str, int]:
    """Convert the active-issue summary into a dictionary."""

    active_issue_counts = {
        "High": 0,
        "Medium": 0,
        "Low": 0,
    }

    if active_issue_summary.empty:
        return active_issue_counts

    for row in active_issue_summary.itertuples(
        index=False
    ):
        priority_level = str(
            row.priority_level
        )

        active_issue_counts[
            priority_level
        ] = int(row.issue_count)

    return active_issue_counts


def get_previous_monitoring_total(
    context: AgentContext,
) -> int | None:
    """Read the Monitoring Agent total when run in a sequence."""

    previous_results = context.metadata.get(
        "previous_agent_results",
        {},
    )

    if not isinstance(previous_results, dict):
        return None

    monitoring_result = previous_results.get(
        "Monitoring Agent"
    )

    if not isinstance(monitoring_result, dict):
        return None

    output_data = monitoring_result.get(
        "output_data",
        {},
    )

    if not isinstance(output_data, dict):
        return None

    finding_totals = output_data.get(
        "finding_totals",
        {},
    )

    if not isinstance(finding_totals, dict):
        return None

    total_value = finding_totals.get(
        "total"
    )

    if total_value is None:
        return None

    try:
        return int(total_value)

    except (TypeError, ValueError):
        return None



def clean_text(
    value: object,
) -> str:
    """Convert one value into normalized text."""

    if value is None:
        return ""

    return " ".join(
        str(value).split()
    )


def optional_integer(
    value: object,
) -> int | None:
    """Convert a value to an integer when possible."""

    if value is None or isinstance(value, bool):
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def optional_float(
    value: object,
) -> float | None:
    """Convert a value to a float when possible."""

    if value is None or isinstance(value, bool):
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_evidence_reference_map(
    *,
    evidence_dataframe: pd.DataFrame,
    selected_issue_ids: list[str],
) -> dict[str, Any]:
    """Build compact source-finding references for selected issues."""

    normalized_issue_ids = [
        clean_text(issue_id)
        for issue_id in selected_issue_ids
        if clean_text(issue_id)
    ]

    by_issue: dict[str, list[str]] = {}

    required_columns = {
        "issue_id",
        "source_finding_id",
    }

    if (
        evidence_dataframe.empty
        or not required_columns.issubset(
            evidence_dataframe.columns
        )
    ):
        return {
            "source_field": "source_finding_id",
            "selected_issue_count": len(normalized_issue_ids),
            "total_available": len(evidence_dataframe),
            "included_count": 0,
            "by_issue": by_issue,
        }

    included_count = 0

    for issue_id in normalized_issue_ids:
        issue_rows = evidence_dataframe[
            evidence_dataframe["issue_id"]
            .astype(str)
            .str.strip()
            .eq(issue_id)
        ]

        evidence_ids: list[str] = []

        for raw_value in issue_rows[
            "source_finding_id"
        ].tolist():
            evidence_id = clean_text(raw_value)

            if (
                evidence_id
                and evidence_id not in evidence_ids
            ):
                evidence_ids.append(evidence_id)

            if len(evidence_ids) >= MAXIMUM_EVIDENCE_IDS_PER_ISSUE:
                break

        by_issue[issue_id] = evidence_ids
        included_count += len(evidence_ids)

    return {
        "source_field": "source_finding_id",
        "selected_issue_count": len(normalized_issue_ids),
        "total_available": len(evidence_dataframe),
        "included_count": included_count,
        "by_issue": by_issue,
    }


def build_deterministic_priority_output(
    context: AgentContext,
) -> dict[str, Any]:
    """Run the existing deterministic priority-management pipeline."""

    manager_limit = get_positive_limit(
        context,
        setting_name="manager_limit",
        default_value=DEFAULT_MANAGER_LIMIT,
        maximum_value=MAXIMUM_MANAGER_LIMIT,
    )

    executive_limit = get_positive_limit(
        context,
        setting_name="executive_limit",
        default_value=DEFAULT_EXECUTIVE_LIMIT,
        maximum_value=MAXIMUM_EXECUTIVE_LIMIT,
    )

    detailed_findings, source_finding_counts = (
        build_detailed_findings()
    )

    issues_dataframe, evidence_dataframe = (
        build_priority_outputs(
            detailed_findings
        )
    )

    if issues_dataframe.empty:
        raise RuntimeError(
            "The priority engine did not create any issues."
        )

    save_to_database(
        engine,
        issues_dataframe,
        evidence_dataframe,
    )

    manager_priorities = load_manager_priorities(
        engine,
        manager_limit,
    )

    active_issue_summary = load_active_issue_summary(
        engine
    )

    active_issues = load_active_issues(
        engine
    )

    executive_priorities = select_executive_priorities(
        active_issues=active_issues,
        limit=executive_limit,
    )

    total_findings = len(detailed_findings)
    total_issues = len(issues_dataframe)
    total_evidence_records = len(evidence_dataframe)

    priority_counts = build_priority_counts(
        issues_dataframe
    )

    active_issue_counts = build_active_issue_counts(
        active_issue_summary
    )

    previous_monitoring_total = get_previous_monitoring_total(
        context
    )

    monitoring_comparison = {
        "available": previous_monitoring_total is not None,
        "monitoring_finding_total": previous_monitoring_total,
        "priority_input_finding_total": total_findings,
        "totals_match": (
            previous_monitoring_total == total_findings
            if previous_monitoring_total is not None
            else None
        ),
    }

    manager_records = dataframe_to_records(
        manager_priorities
    )
    executive_records = dataframe_to_records(
        executive_priorities
    )

    selected_issue_ids: list[str] = []

    for record in [
        *executive_records,
        *manager_records,
    ]:
        issue_id = clean_text(
            record.get("issue_id")
        )

        if issue_id and issue_id not in selected_issue_ids:
            selected_issue_ids.append(issue_id)

        if len(selected_issue_ids) >= MAXIMUM_LLM_PRIORITY_ITEMS:
            break

    evidence_references = build_evidence_reference_map(
        evidence_dataframe=evidence_dataframe,
        selected_issue_ids=selected_issue_ids,
    )

    summary = (
        f"Priority analysis consolidated {total_findings} findings "
        f"into {total_issues} business issues: "
        f"{priority_counts['High']} High, "
        f"{priority_counts['Medium']} Medium, and "
        f"{priority_counts['Low']} Low. "
        f"{len(executive_priorities)} executive priorities "
        "were selected."
    )

    return {
        "summary": summary,
        "priority_status": "Complete",
        "generated_at": current_utc_time(),
        "database_persisted": True,
        "detailed_findings": {
            "total": total_findings,
            "by_source": source_finding_counts,
        },
        "issues": {
            "total_created": total_issues,
            "by_priority": priority_counts,
            "active_by_priority": active_issue_counts,
        },
        "evidence_records": {
            "total": total_evidence_records,
        },
        "manager_priorities": {
            "requested_limit": manager_limit,
            "returned_count": len(manager_priorities),
            "items": manager_records,
        },
        "executive_priorities": {
            "requested_limit": executive_limit,
            "returned_count": len(executive_priorities),
            "items": executive_records,
        },
        "monitoring_comparison": monitoring_comparison,
        "evidence_references": evidence_references,
    }


def compact_priority_item(
    item: dict[str, Any],
) -> dict[str, Any]:
    """Keep only validated fields needed for priority explanation."""

    allowed_fields = (
        "issue_id",
        "title",
        "issue_type",
        "business_area",
        "priority_level",
        "priority_score",
        "priority_reason",
        "manager_rank",
        "executive_rank",
        "executive_score",
        "critical_evidence_score",
        "finding_count",
        "high_finding_count",
        "medium_finding_count",
        "low_finding_count",
        "summary",
        "evidence_summary",
        "status",
        "entity_type",
        "entity_id",
        "store_id",
        "product_id",
        "vendor_id",
        "period_label",
    )

    return {
        field_name: item.get(field_name)
        for field_name in allowed_fields
        if field_name in item
    }


def build_priority_reference_items(
    deterministic_output: dict[str, Any],
) -> list[dict[str, Any]]:
    """Merge manager and executive records without changing rank values."""

    manager_section = deterministic_output.get(
        "manager_priorities",
        {},
    )
    executive_section = deterministic_output.get(
        "executive_priorities",
        {},
    )

    manager_items = (
        manager_section.get("items", [])
        if isinstance(manager_section, dict)
        else []
    )
    executive_items = (
        executive_section.get("items", [])
        if isinstance(executive_section, dict)
        else []
    )

    if not isinstance(manager_items, list):
        manager_items = []
    if not isinstance(executive_items, list):
        executive_items = []

    merged_by_issue: dict[str, dict[str, Any]] = {}
    ordered_issue_ids: list[str] = []

    for raw_item in [
        *executive_items,
        *manager_items,
    ]:
        if not isinstance(raw_item, dict):
            continue

        issue_id = clean_text(
            raw_item.get("issue_id")
        )

        if not issue_id:
            continue

        if issue_id not in ordered_issue_ids:
            ordered_issue_ids.append(issue_id)

        existing = merged_by_issue.setdefault(
            issue_id,
            {"issue_id": issue_id},
        )

        for key, value in compact_priority_item(
            raw_item
        ).items():
            if value is not None and value != "":
                existing[key] = value

    evidence_section = deterministic_output.get(
        "evidence_references",
        {},
    )
    evidence_by_issue = (
        evidence_section.get("by_issue", {})
        if isinstance(evidence_section, dict)
        else {}
    )

    reference_items: list[dict[str, Any]] = []

    for issue_id in ordered_issue_ids[:MAXIMUM_LLM_PRIORITY_ITEMS]:
        item = dict(
            merged_by_issue[issue_id]
        )
        raw_evidence_ids = (
            evidence_by_issue.get(issue_id, [])
            if isinstance(evidence_by_issue, dict)
            else []
        )
        item["evidence_ids"] = [
            clean_text(value)
            for value in raw_evidence_ids
            if clean_text(value)
        ]
        reference_items.append(item)

    return reference_items


def build_priority_llm_context(
    deterministic_output: dict[str, Any],
) -> dict[str, Any]:
    """Create compact evidence-grounded priority context for the LLM."""

    return {
        "deterministic_summary": deterministic_output.get(
            "summary"
        ),
        "priority_status": deterministic_output.get(
            "priority_status"
        ),
        "detailed_findings": deterministic_output.get(
            "detailed_findings",
            {},
        ),
        "issues": deterministic_output.get(
            "issues",
            {},
        ),
        "evidence_records": deterministic_output.get(
            "evidence_records",
            {},
        ),
        "monitoring_comparison": deterministic_output.get(
            "monitoring_comparison",
            {},
        ),
        "priority_items": build_priority_reference_items(
            deterministic_output
        ),
    }


def build_priority_change_explanation(
    item: dict[str, Any],
) -> str:
    """Explain change only when historical deterministic values exist."""

    previous_score = optional_float(
        item.get("previous_priority_score")
    )
    current_score = optional_float(
        item.get("priority_score")
    )

    if previous_score is None or current_score is None:
        return (
            "No previous deterministic priority score or rank was "
            "supplied, so a priority change cannot be confirmed."
        )

    difference = round(
        current_score - previous_score,
        2,
    )

    if difference > 0:
        return (
            f"The deterministic priority score increased by "
            f"{difference:.2f}, from {previous_score:.2f} to "
            f"{current_score:.2f}."
        )

    if difference < 0:
        return (
            f"The deterministic priority score decreased by "
            f"{abs(difference):.2f}, from {previous_score:.2f} "
            f"to {current_score:.2f}."
        )

    return (
        f"The deterministic priority score remained "
        f"{current_score:.2f}."
    )


def build_mock_priority_output(
    deterministic_output: dict[str, Any],
) -> dict[str, Any]:
    """Build grounded structured output for the mock provider."""

    reference_items = build_priority_reference_items(
        deterministic_output
    )

    if not reference_items:
        raise RuntimeError(
            "No deterministic priority items were available "
            "for explanation."
        )

    priority_explanations: list[dict[str, Any]] = []
    all_evidence_ids: list[str] = []
    top_level_warnings: list[str] = []

    for item in reference_items:
        issue_id = clean_text(
            item.get("issue_id")
        )
        priority_level = clean_text(
            item.get("priority_level")
        ) or "Unknown"
        priority_score = optional_float(
            item.get("priority_score")
        )

        if priority_score is None:
            priority_score = 0.0

        evidence_ids = [
            clean_text(value)
            for value in item.get(
                "evidence_ids",
                [],
            )
            if clean_text(value)
        ]

        for evidence_id in evidence_ids:
            if evidence_id not in all_evidence_ids:
                all_evidence_ids.append(evidence_id)

        warnings: list[str] = []

        if not evidence_ids:
            warnings.append(
                "No source-finding identifiers were supplied "
                "for this issue."
            )

        warnings.append(
            "No historical deterministic priority score or rank "
            "was supplied for change comparison."
        )

        title = clean_text(
            item.get("title")
        ) or issue_id
        priority_reason = clean_text(
            item.get("priority_reason")
        )
        evidence_summary = clean_text(
            item.get("evidence_summary")
        )

        review_reason = (
            priority_reason
            or evidence_summary
            or (
                f"{title} is ranked as {priority_level} with "
                f"deterministic score {priority_score:.2f}."
            )
        )

        score_explanation = (
            f"The existing deterministic engine assigned "
            f"priority level {priority_level} and score "
            f"{priority_score:.2f}. "
            + (
                priority_reason
                if priority_reason
                else "No additional deterministic score reason was supplied."
            )
        )

        priority_explanations.append(
            {
                "issue_id": issue_id,
                "deterministic_priority_level": priority_level,
                "deterministic_priority_score": priority_score,
                "manager_rank": optional_integer(
                    item.get("manager_rank")
                ),
                "executive_rank": optional_integer(
                    item.get("executive_rank")
                ),
                "review_reason": review_reason,
                "score_explanation": score_explanation,
                "priority_change_explanation": (
                    build_priority_change_explanation(item)
                ),
                "evidence_ids": evidence_ids,
                "confidence_score": (
                    92.0 if evidence_ids else 72.0
                ),
                "missing_evidence_warnings": warnings,
            }
        )

    review_first = priority_explanations[0]

    if not all_evidence_ids:
        top_level_warnings.append(
            "No source-finding identifiers were available for "
            "the selected priority items."
        )

    top_level_warnings.append(
        "Historical priority values were not supplied, so the "
        "agent cannot confirm why priorities changed over time."
    )

    confidence_score = round(
        sum(
            explanation["confidence_score"]
            for explanation in priority_explanations
        ) / len(priority_explanations),
        2,
    )

    return {
        "summary": (
            "The deterministic ranking was retained without "
            "recalculation. Review "
            f"{review_first['issue_id']} first, followed by the "
            "remaining issues in their existing rank order."
        ),
        "review_first_issue_id": review_first["issue_id"],
        "review_first_reason": review_first["review_reason"],
        "priority_explanations": priority_explanations,
        "evidence_ids": all_evidence_ids,
        "confidence_score": confidence_score,
        "missing_evidence_warnings": top_level_warnings,
    }


def get_allowed_priority_issue_ids(
    deterministic_output: dict[str, Any],
) -> list[str]:
    """Return deterministic issue IDs the LLM may reference."""

    return [
        clean_text(item.get("issue_id"))
        for item in build_priority_reference_items(
            deterministic_output
        )
        if clean_text(item.get("issue_id"))
    ]


def get_allowed_priority_evidence_ids(
    deterministic_output: dict[str, Any],
) -> list[str]:
    """Return source-finding IDs the LLM may cite."""

    evidence_ids: list[str] = []

    for item in build_priority_reference_items(
        deterministic_output
    ):
        for raw_value in item.get(
            "evidence_ids",
            [],
        ):
            evidence_id = clean_text(raw_value)

            if evidence_id and evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)

    return evidence_ids


def validate_priority_explanation_facts(
    *,
    enhancement: PriorityExplanationV1,
    deterministic_output: dict[str, Any],
) -> None:
    """Ensure the LLM did not alter scores, levels, or ranks."""

    reference_items = build_priority_reference_items(
        deterministic_output
    )

    reference_by_issue = {
        clean_text(item.get("issue_id")): item
        for item in reference_items
        if clean_text(item.get("issue_id"))
    }

    expected_issue_ids = list(reference_by_issue)

    if not expected_issue_ids:
        raise LLMProviderResponseError(
            "No deterministic issue references were available."
        )

    if enhancement.review_first_issue_id != expected_issue_ids[0]:
        raise LLMProviderResponseError(
            "The LLM changed the deterministic first-review issue."
        )

    returned_issue_ids = [
        explanation.issue_id
        for explanation in enhancement.priority_explanations
    ]

    if returned_issue_ids != expected_issue_ids:
        raise LLMProviderResponseError(
            "The LLM changed or reordered the deterministic "
            "priority item sequence."
        )

    for explanation in enhancement.priority_explanations:
        reference = reference_by_issue[
            explanation.issue_id
        ]

        expected_level = clean_text(
            reference.get("priority_level")
        ) or "Unknown"
        expected_score = optional_float(
            reference.get("priority_score")
        )

        if expected_score is None:
            expected_score = 0.0

        if (
            explanation.deterministic_priority_level
            != expected_level
        ):
            raise LLMProviderResponseError(
                "The LLM changed the deterministic priority "
                f"level for {explanation.issue_id}."
            )

        if abs(
            explanation.deterministic_priority_score
            - expected_score
        ) > 0.000001:
            raise LLMProviderResponseError(
                "The LLM changed the deterministic priority "
                f"score for {explanation.issue_id}."
            )

        expected_manager_rank = optional_integer(
            reference.get("manager_rank")
        )
        expected_executive_rank = optional_integer(
            reference.get("executive_rank")
        )

        if explanation.manager_rank != expected_manager_rank:
            raise LLMProviderResponseError(
                "The LLM changed the deterministic manager rank "
                f"for {explanation.issue_id}."
            )

        if explanation.executive_rank != expected_executive_rank:
            raise LLMProviderResponseError(
                "The LLM changed the deterministic executive rank "
                f"for {explanation.issue_id}."
            )


class PriorityAgent(BaseAgent):
    """
    Consolidate deterministic findings and optionally explain priority.

    Deterministic issue creation, scores, levels, manager ranks, and
    executive ranks remain authoritative. The optional LLM may explain
    those values but cannot recalculate, replace, or reorder them.
    """

    name = "Priority Agent"
    version = "1.1.0"

    description = (
        "Consolidates deterministic business findings into issues, "
        "stores supporting evidence, selects manager and executive "
        "priorities, and optionally explains the existing ranking."
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
        """Run deterministic priority logic and optional explanation."""

        deterministic_output = build_deterministic_priority_output(
            context
        )

        provider = self._llm_provider

        if provider is None or not provider.config.enabled:
            return deterministic_output

        validated_context = build_priority_llm_context(
            deterministic_output
        )
        allowed_issue_ids = get_allowed_priority_issue_ids(
            deterministic_output
        )
        allowed_evidence_ids = get_allowed_priority_evidence_ids(
            deterministic_output
        )
        mock_structured_output = build_mock_priority_output(
            deterministic_output
        )

        try:
            enhancement, execution_metadata = (
                await run_structured_enhancement(
                    provider=provider,
                    agent_name=self.name,
                    agent_version=self.version,
                    prompt_name=PRIORITY_PROMPT_NAME,
                    prompt_version=PRIORITY_PROMPT_VERSION,
                    validated_context=validated_context,
                    response_model=PriorityExplanationV1,
                    allowed_evidence_ids=allowed_evidence_ids,
                    mock_structured_output=mock_structured_output,
                    request_metadata={
                        "run_id": context.run_id,
                        "run_type": context.run_type,
                    },
                    allowed_references={
                        "issue_id": allowed_issue_ids,
                        "review_first_issue_id": allowed_issue_ids,
                    },
                    output_validator=lambda output: (
                        validate_priority_explanation_facts(
                            enhancement=output,
                            deterministic_output=deterministic_output,
                        )
                    ),
                )
            )

        except LLMError as error:
            failed_metadata = build_failed_execution_metadata(
                provider=provider,
                prompt_name=PRIORITY_PROMPT_NAME,
                prompt_version=PRIORITY_PROMPT_VERSION,
                error=error,
            )

            raise attach_deterministic_fallback(
                error=error,
                deterministic_output=deterministic_output,
                execution_metadata=failed_metadata,
            )

        enhanced_output = dict(
            deterministic_output
        )
        enhanced_output["summary"] = enhancement.summary
        enhanced_output["llm_enhancement"] = {
            "status": "Complete",
            "schema_name": PriorityExplanationV1.__name__,
            "deterministic_summary": deterministic_output["summary"],
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
        """Return the already-created deterministic priority output."""

        del context

        return build_attached_fallback_output(
            error
        )