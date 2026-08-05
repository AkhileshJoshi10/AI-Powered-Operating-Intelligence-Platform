from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any

import pandas as pd

from backend.analytics.executive_priority_selector import (
    load_active_issues,
    select_executive_priorities,
)
from backend.analytics.root_cause_analysis import (
    build_root_cause_outputs,
    load_selected_evidence,
    load_selected_issues,
    save_root_causes_to_database,
)
from backend.app.agents.agent_context import AgentContext
from backend.app.agents.base_agent import BaseAgent
from backend.app.agents.llm_enhancement import (
    RootCauseExplanationV1,
    attach_deterministic_fallback,
    build_attached_fallback_output,
    build_failed_execution_metadata,
    run_structured_enhancement,
)
from backend.app.core.config import settings
from backend.app.db.database import engine
from backend.app.llm import (
    BaseLLMProvider,
    LLMError,
    LLMProviderResponseError,
    get_configured_provider,
)


DEFAULT_ANALYSIS_LIMIT = 10
MAXIMUM_ANALYSIS_LIMIT = 50

ROOT_CAUSE_PROMPT_NAME = "root_cause_explanation"
ROOT_CAUSE_PROMPT_VERSION = "v1"
MAXIMUM_LLM_ROOT_CAUSE_ITEMS = 20
MAXIMUM_EVIDENCE_IDS_PER_ISSUE = 12
MAXIMUM_FACTORS_PER_ISSUE = 8


def current_utc_time() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(timezone.utc)


def clean_text(value: object) -> str:
    """Convert a value into normalized text."""

    if value is None:
        return ""

    return " ".join(str(value).split())


def get_analysis_limit(
    context: AgentContext,
) -> int:
    """Read and validate the maximum number of issues to analyze."""

    configured_value = context.input_data.get(
        "analysis_limit",
        DEFAULT_ANALYSIS_LIMIT,
    )

    if isinstance(configured_value, bool):
        raise ValueError(
            "analysis_limit must be an integer."
        )

    try:
        analysis_limit = int(
            configured_value
        )

    except (TypeError, ValueError) as error:
        raise ValueError(
            "analysis_limit must be an integer."
        ) from error

    if analysis_limit < 1:
        raise ValueError(
            "analysis_limit must be at least 1."
        )

    if analysis_limit > MAXIMUM_ANALYSIS_LIMIT:
        raise ValueError(
            "analysis_limit cannot be greater than "
            f"{MAXIMUM_ANALYSIS_LIMIT}."
        )

    return analysis_limit


def build_requested_issue_reference(
    *,
    issue_ids: list[str],
    analysis_limit: int,
) -> pd.DataFrame:
    """
    Build a root-cause reference for explicitly requested issues.

    Active issue information is loaded from PostgreSQL so the agent
    does not trust issue details supplied by an external caller.
    """

    if len(issue_ids) > analysis_limit:
        raise ValueError(
            f"{len(issue_ids)} issue IDs were requested, but "
            f"analysis_limit is {analysis_limit}."
        )

    active_issues = load_active_issues(
        engine
    )

    if active_issues.empty:
        raise RuntimeError(
            "No active issues are available for root-cause analysis."
        )

    available_issue_ids = set(
        active_issues["issue_id"]
        .astype(str)
        .tolist()
    )

    missing_issue_ids = [
        issue_id
        for issue_id in issue_ids
        if issue_id not in available_issue_ids
    ]

    if missing_issue_ids:
        raise ValueError(
            "Requested issues were not found in the active issue "
            "register: "
            + ", ".join(missing_issue_ids)
        )

    requested_order = {
        issue_id: index
        for index, issue_id in enumerate(
            issue_ids,
            start=1,
        )
    }

    selected_issues = active_issues[
        active_issues["issue_id"].isin(
            issue_ids
        )
    ].copy()

    selected_issues["requested_order"] = (
        selected_issues["issue_id"].map(
            requested_order
        )
    )

    selected_issues = selected_issues.sort_values(
        "requested_order"
    ).reset_index(drop=True)

    priority_scores = pd.to_numeric(
        selected_issues["priority_score"],
        errors="coerce",
    ).fillna(0.0)

    critical_evidence_scores = pd.to_numeric(
        selected_issues.get(
            "critical_evidence_score",
            0.0,
        ),
        errors="coerce",
    ).fillna(0.0)

    selected_issues["executive_rank"] = range(
        1,
        len(selected_issues) + 1,
    )

    selected_issues["executive_score"] = (
        priority_scores
        + critical_evidence_scores
    ).round(2)

    return selected_issues[
        [
            "issue_id",
            "executive_rank",
            "executive_score",
        ]
    ].copy()


def build_previous_priority_reference(
    *,
    context: AgentContext,
    analysis_limit: int,
) -> pd.DataFrame | None:
    """
    Read the previous Priority Agent's executive selections.

    This is used when the agents are executed through an orchestrated
    Monitoring → Priority → Root-Cause sequence.
    """

    previous_results = context.metadata.get(
        "previous_agent_results",
        {},
    )

    if not isinstance(
        previous_results,
        dict,
    ):
        return None

    priority_result = previous_results.get(
        "Priority Agent"
    )

    if not isinstance(
        priority_result,
        dict,
    ):
        return None

    output_data = priority_result.get(
        "output_data",
        {},
    )

    if not isinstance(
        output_data,
        dict,
    ):
        return None

    executive_output = output_data.get(
        "executive_priorities",
        {},
    )

    if not isinstance(
        executive_output,
        dict,
    ):
        return None

    priority_items = executive_output.get(
        "items",
        [],
    )

    if not isinstance(
        priority_items,
        list,
    ) or not priority_items:
        return None

    priority_reference = pd.DataFrame(
        priority_items
    )

    required_columns = {
        "issue_id",
        "executive_rank",
        "executive_score",
    }

    if not required_columns.issubset(
        priority_reference.columns
    ):
        return None

    priority_reference = priority_reference[
        [
            "issue_id",
            "executive_rank",
            "executive_score",
        ]
    ].copy()

    priority_reference["executive_rank"] = (
        pd.to_numeric(
            priority_reference["executive_rank"],
            errors="coerce",
        )
    )

    priority_reference["executive_score"] = (
        pd.to_numeric(
            priority_reference["executive_score"],
            errors="coerce",
        )
    )

    priority_reference = priority_reference.dropna(
        subset=[
            "issue_id",
            "executive_rank",
        ]
    )

    if priority_reference.empty:
        return None

    return (
        priority_reference.sort_values(
            "executive_rank"
        )
        .head(analysis_limit)
        .reset_index(drop=True)
    )


def build_current_priority_reference(
    *,
    analysis_limit: int,
) -> pd.DataFrame:
    """Generate the current executive selection from PostgreSQL."""

    active_issues = load_active_issues(
        engine
    )

    if active_issues.empty:
        raise RuntimeError(
            "No active issues are available for root-cause analysis."
        )

    executive_priorities = (
        select_executive_priorities(
            active_issues=active_issues,
            limit=analysis_limit,
        )
    )

    if executive_priorities.empty:
        raise RuntimeError(
            "No executive priorities were selected for "
            "root-cause analysis."
        )

    return executive_priorities[
        [
            "issue_id",
            "executive_rank",
            "executive_score",
        ]
    ].copy()


def build_priority_reference(
    *,
    context: AgentContext,
    analysis_limit: int,
) -> tuple[pd.DataFrame, str]:
    """Resolve which issues the Root-Cause Agent should analyze."""

    if context.issue_ids:
        return (
            build_requested_issue_reference(
                issue_ids=context.issue_ids,
                analysis_limit=analysis_limit,
            ),
            "Requested issue IDs",
        )

    previous_priority_reference = (
        build_previous_priority_reference(
            context=context,
            analysis_limit=analysis_limit,
        )
    )

    if previous_priority_reference is not None:
        return (
            previous_priority_reference,
            "Priority Agent output",
        )

    return (
        build_current_priority_reference(
            analysis_limit=analysis_limit,
        ),
        "Current executive ranking",
    )


def clean_scalar(
    value: object,
) -> object:
    """Convert pandas and NumPy values into JSON-safe values."""

    if value is None:
        return None

    if isinstance(value, dict):
        return {
            str(key): clean_scalar(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            clean_scalar(item)
            for item in value
        ]

    if isinstance(
        value,
        (pd.Timestamp, datetime, date),
    ):
        return value.isoformat()

    try:
        if bool(pd.isna(value)):
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
    """Convert a DataFrame into JSON-safe dictionaries."""

    records: list[dict[str, object]] = []

    for record in dataframe.to_dict(
        orient="records"
    ):
        records.append(
            {
                str(key): clean_scalar(value)
                for key, value in record.items()
            }
        )

    return records


def build_confidence_summary(
    analyses: pd.DataFrame,
) -> dict[str, float]:
    """Return aggregate confidence statistics."""

    confidence_values = pd.to_numeric(
        analyses["confidence_score"],
        errors="coerce",
    ).dropna()

    if confidence_values.empty:
        return {
            "average": 0.0,
            "minimum": 0.0,
            "maximum": 0.0,
        }

    return {
        "average": round(
            float(confidence_values.mean()),
            2,
        ),
        "minimum": round(
            float(confidence_values.min()),
            2,
        ),
        "maximum": round(
            float(confidence_values.max()),
            2,
        ),
    }



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


def split_contributing_factors(
    value: object,
) -> list[str]:
    """Split deterministic factor text into controlled statements."""

    factor_text = clean_text(
        value
    )

    if not factor_text:
        return []

    factors = [
        clean_text(part)
        for part in re.split(
            r"(?<=[.!?])\s+",
            factor_text,
        )
        if clean_text(part)
    ]

    unique_factors: list[str] = []

    for factor in factors:
        if factor not in unique_factors:
            unique_factors.append(
                factor
            )

        if len(unique_factors) >= MAXIMUM_FACTORS_PER_ISSUE:
            break

    return unique_factors


def build_root_cause_evidence_reference_map(
    *,
    selected_evidence: pd.DataFrame,
    selected_issue_ids: list[str],
) -> dict[str, Any]:
    """Build source-finding references for each analyzed issue."""

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
        selected_evidence.empty
        or not required_columns.issubset(
            selected_evidence.columns
        )
    ):
        return {
            "source_field": "source_finding_id",
            "selected_issue_count": len(normalized_issue_ids),
            "total_available": len(selected_evidence),
            "included_count": 0,
            "by_issue": by_issue,
        }

    included_count = 0

    for issue_id in normalized_issue_ids:
        issue_rows = selected_evidence[
            selected_evidence["issue_id"]
            .astype(str)
            .str.strip()
            .eq(issue_id)
        ]

        evidence_ids: list[str] = []

        for raw_value in issue_rows[
            "source_finding_id"
        ].tolist():
            evidence_id = clean_text(
                raw_value
            )

            if (
                evidence_id
                and evidence_id not in evidence_ids
            ):
                evidence_ids.append(
                    evidence_id
                )

            if len(evidence_ids) >= MAXIMUM_EVIDENCE_IDS_PER_ISSUE:
                break

        by_issue[issue_id] = evidence_ids
        included_count += len(evidence_ids)

    return {
        "source_field": "source_finding_id",
        "selected_issue_count": len(normalized_issue_ids),
        "total_available": len(selected_evidence),
        "included_count": included_count,
        "by_issue": by_issue,
    }


def build_deterministic_root_cause_output(
    context: AgentContext,
) -> dict[str, Any]:
    """Run the existing deterministic root-cause pipeline."""

    analysis_limit = get_analysis_limit(
        context
    )

    priority_reference, selection_source = (
        build_priority_reference(
            context=context,
            analysis_limit=analysis_limit,
        )
    )

    selected_issues = load_selected_issues(
        engine,
        priority_reference,
    )

    if selected_issues.empty:
        raise RuntimeError(
            "No active issues matched the selected root-cause "
            "analysis reference."
        )

    selected_issue_ids = (
        selected_issues["issue_id"]
        .astype(str)
        .tolist()
    )

    selected_evidence = load_selected_evidence(
        engine,
        selected_issue_ids,
    )

    analyses, database_records = build_root_cause_outputs(
        engine,
        selected_issues,
        selected_evidence,
    )

    if analyses.empty:
        raise RuntimeError(
            "No root-cause analyses were generated."
        )

    save_root_causes_to_database(
        engine,
        database_records,
    )

    technical_review_count = int(
        analyses["root_cause_category"]
        .astype(str)
        .eq("Technical Review Required")
        .sum()
    )

    zero_evidence_count = int(
        pd.to_numeric(
            analyses["evidence_count"],
            errors="coerce",
        )
        .fillna(0)
        .eq(0)
        .sum()
    )

    confidence_summary = build_confidence_summary(
        analyses
    )

    total_evidence_records = int(
        pd.to_numeric(
            analyses["evidence_count"],
            errors="coerce",
        )
        .fillna(0)
        .sum()
    )

    root_cause_status = (
        "Complete"
        if technical_review_count == 0
        else "Partial"
    )

    summary = (
        f"Root-cause analysis generated {len(analyses)} "
        f"evidence-based assessments from "
        f"{total_evidence_records} linked evidence records. "
        f"Average confidence was "
        f"{confidence_summary['average']:.2f}%."
    )

    if technical_review_count > 0:
        summary += (
            f" {technical_review_count} assessments require "
            "technical review."
        )

    evidence_references = build_root_cause_evidence_reference_map(
        selected_evidence=selected_evidence,
        selected_issue_ids=selected_issue_ids,
    )

    return {
        "summary": summary,
        "root_cause_status": root_cause_status,
        "generated_at": current_utc_time(),
        "selection": {
            "source": selection_source,
            "requested_limit": analysis_limit,
            "selected_issue_count": len(selected_issues),
            "issue_ids": selected_issue_ids,
        },
        "analysis": {
            "generated_count": len(analyses),
            "analysis_method": (
                "Rule-Based Database and Evidence Analysis"
            ),
            "technical_review_required_count": technical_review_count,
            "zero_evidence_count": zero_evidence_count,
            "confidence": confidence_summary,
        },
        "evidence": {
            "selected_evidence_records": len(selected_evidence),
            "evidence_records_used": total_evidence_records,
        },
        "database": {
            "persisted": True,
            "table": "root_cause_analyses",
            "review_status": "Pending Review",
        },
        "review_protection": {
            "human_review_required": True,
            "llm_enhancement_persisted_to_root_cause_table": False,
            "accepted_or_edited_records_preserved": True,
        },
        "evidence_references": evidence_references,
        "analyses": dataframe_to_records(
            analyses
        ),
    }


def build_root_cause_reference_items(
    deterministic_output: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build compact deterministic RCA items for LLM explanation."""

    analyses = deterministic_output.get(
        "analyses",
        [],
    )

    if not isinstance(analyses, list):
        analyses = []

    evidence_section = deterministic_output.get(
        "evidence_references",
        {},
    )
    evidence_by_issue = (
        evidence_section.get("by_issue", {})
        if isinstance(evidence_section, dict)
        else {}
    )

    allowed_fields = (
        "issue_id",
        "executive_rank",
        "title",
        "issue_type",
        "business_area",
        "priority_level",
        "priority_score",
        "root_cause_category",
        "root_cause_summary",
        "root_cause_explanation",
        "contributing_factors",
        "evidence_summary",
        "investigation_focus",
        "confidence_score",
        "evidence_count",
        "evidence_types",
        "analysis_method",
        "analysis_status",
        "review_status",
    )

    reference_items: list[dict[str, Any]] = []

    for raw_analysis in analyses[:MAXIMUM_LLM_ROOT_CAUSE_ITEMS]:
        if not isinstance(raw_analysis, dict):
            continue

        issue_id = clean_text(
            raw_analysis.get("issue_id")
        )

        if not issue_id:
            continue

        item = {
            field_name: raw_analysis.get(field_name)
            for field_name in allowed_fields
            if field_name in raw_analysis
        }
        item["issue_id"] = issue_id

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
        item["deterministic_factor_statements"] = (
            split_contributing_factors(
                item.get("contributing_factors")
            )
        )

        reference_items.append(
            item
        )

    return reference_items


def build_root_cause_llm_context(
    deterministic_output: dict[str, Any],
) -> dict[str, Any]:
    """Create compact evidence-grounded RCA context for the LLM."""

    return {
        "deterministic_summary": deterministic_output.get(
            "summary"
        ),
        "root_cause_status": deterministic_output.get(
            "root_cause_status"
        ),
        "selection": deterministic_output.get(
            "selection",
            {},
        ),
        "analysis": deterministic_output.get(
            "analysis",
            {},
        ),
        "evidence": deterministic_output.get(
            "evidence",
            {},
        ),
        "review_policy": deterministic_output.get(
            "review_protection",
            {},
        ),
        "root_cause_items": build_root_cause_reference_items(
            deterministic_output
        ),
    }


def build_mock_root_cause_output(
    deterministic_output: dict[str, Any],
) -> dict[str, Any]:
    """Build grounded structured RCA output for the mock provider."""

    reference_items = build_root_cause_reference_items(
        deterministic_output
    )

    if not reference_items:
        raise LLMProviderResponseError(
            "No deterministic root-cause items were available "
            "for explanation."
        )

    explanations: list[dict[str, Any]] = []
    all_evidence_ids: list[str] = []
    top_level_warnings: list[str] = []

    for item in reference_items:
        issue_id = clean_text(
            item.get("issue_id")
        )
        category = clean_text(
            item.get("root_cause_category")
        ) or "Technical Review Required"
        deterministic_summary = clean_text(
            item.get("root_cause_summary")
        ) or (
            "The deterministic analysis did not provide a "
            "root-cause summary."
        )
        confidence = optional_float(
            item.get("confidence_score")
        )

        if confidence is None:
            confidence = 0.0

        evidence_ids = [
            clean_text(value)
            for value in item.get("evidence_ids", [])
            if clean_text(value)
        ]

        for evidence_id in evidence_ids:
            if evidence_id not in all_evidence_ids:
                all_evidence_ids.append(
                    evidence_id
                )

        factors = list(
            item.get(
                "deterministic_factor_statements",
                [],
            )
        )

        manager_explanation = clean_text(
            item.get("root_cause_explanation")
        ) or deterministic_summary

        warnings: list[str] = []

        if not evidence_ids:
            warnings.append(
                "No source-finding identifiers were supplied for "
                "this root-cause assessment."
            )

        if not factors:
            warnings.append(
                "No distinct deterministic contributing-factor "
                "statements were supplied."
            )

        if category == "Technical Review Required":
            warnings.append(
                "The deterministic analysis requires technical review "
                "before a cause can be confirmed."
            )

        explanations.append(
            {
                "issue_id": issue_id,
                "deterministic_root_cause_category": category,
                "deterministic_root_cause_summary": deterministic_summary,
                "deterministic_confidence_score": confidence,
                "manager_friendly_explanation": manager_explanation,
                "likely_contributing_factors": factors,
                "evidence_ids": evidence_ids,
                "confidence_score": confidence,
                "missing_evidence_warnings": warnings,
                "unsupported_claims_rejected": [
                    "Claims not grounded in the deterministic analysis "
                    "or linked evidence were excluded."
                ],
                "human_review_required": True,
            }
        )

    if not all_evidence_ids:
        top_level_warnings.append(
            "No source-finding identifiers were available for the "
            "selected root-cause assessments."
        )

    confidence_score = round(
        sum(
            explanation["confidence_score"]
            for explanation in explanations
        ) / len(explanations),
        2,
    )

    return {
        "summary": (
            f"Prepared manager-friendly explanations for "
            f"{len(explanations)} deterministic root-cause "
            "assessments without changing their categories or "
            "confidence values. Human review remains required."
        ),
        "root_cause_explanations": explanations,
        "evidence_ids": all_evidence_ids,
        "confidence_score": confidence_score,
        "missing_evidence_warnings": top_level_warnings,
        "human_review_required": True,
    }


def get_allowed_root_cause_issue_ids(
    deterministic_output: dict[str, Any],
) -> list[str]:
    """Return issue IDs the RCA enhancement may reference."""

    return [
        clean_text(item.get("issue_id"))
        for item in build_root_cause_reference_items(
            deterministic_output
        )
        if clean_text(item.get("issue_id"))
    ]


def get_allowed_root_cause_evidence_ids(
    deterministic_output: dict[str, Any],
) -> list[str]:
    """Return source-finding IDs the RCA enhancement may cite."""

    evidence_ids: list[str] = []

    for item in build_root_cause_reference_items(
        deterministic_output
    ):
        for raw_value in item.get("evidence_ids", []):
            evidence_id = clean_text(
                raw_value
            )

            if evidence_id and evidence_id not in evidence_ids:
                evidence_ids.append(
                    evidence_id
                )

    return evidence_ids


def validate_root_cause_explanation_facts(
    *,
    enhancement: RootCauseExplanationV1,
    deterministic_output: dict[str, Any],
) -> None:
    """Reject changed categories, confidence, factors, or ordering."""

    reference_items = build_root_cause_reference_items(
        deterministic_output
    )

    reference_by_issue = {
        clean_text(item.get("issue_id")): item
        for item in reference_items
        if clean_text(item.get("issue_id"))
    }

    expected_issue_ids = list(
        reference_by_issue
    )

    if not expected_issue_ids:
        raise LLMProviderResponseError(
            "No deterministic root-cause references were available."
        )

    returned_issue_ids = [
        explanation.issue_id
        for explanation in enhancement.root_cause_explanations
    ]

    if returned_issue_ids != expected_issue_ids:
        raise LLMProviderResponseError(
            "The LLM changed or reordered the deterministic "
            "root-cause issue sequence."
        )

    for explanation in enhancement.root_cause_explanations:
        reference = reference_by_issue[
            explanation.issue_id
        ]

        expected_category = clean_text(
            reference.get("root_cause_category")
        ) or "Technical Review Required"
        expected_summary = clean_text(
            reference.get("root_cause_summary")
        ) or (
            "The deterministic analysis did not provide a "
            "root-cause summary."
        )
        expected_confidence = optional_float(
            reference.get("confidence_score")
        )

        if expected_confidence is None:
            expected_confidence = 0.0

        if (
            explanation.deterministic_root_cause_category
            != expected_category
        ):
            raise LLMProviderResponseError(
                "The LLM changed the deterministic root-cause "
                f"category for {explanation.issue_id}."
            )

        if (
            explanation.deterministic_root_cause_summary
            != expected_summary
        ):
            raise LLMProviderResponseError(
                "The LLM changed the deterministic root-cause "
                f"summary for {explanation.issue_id}."
            )

        if abs(
            explanation.deterministic_confidence_score
            - expected_confidence
        ) > 0.000001:
            raise LLMProviderResponseError(
                "The LLM changed the deterministic confidence "
                f"for {explanation.issue_id}."
            )

        if abs(
            explanation.confidence_score
            - expected_confidence
        ) > 0.000001:
            raise LLMProviderResponseError(
                "The LLM returned a confidence value different "
                f"from the deterministic score for "
                f"{explanation.issue_id}."
            )

        allowed_factors = set(
            reference.get(
                "deterministic_factor_statements",
                [],
            )
        )
        unsupported_factors = sorted(
            set(
                explanation.likely_contributing_factors
            ).difference(
                allowed_factors
            )
        )

        if unsupported_factors:
            raise LLMProviderResponseError(
                "The LLM introduced unsupported contributing "
                f"factors for {explanation.issue_id}: "
                + "; ".join(
                    unsupported_factors
                )
            )

        allowed_issue_evidence = set(
            reference.get("evidence_ids", [])
        )
        unsupported_evidence = sorted(
            set(explanation.evidence_ids).difference(
                allowed_issue_evidence
            )
        )

        if unsupported_evidence:
            raise LLMProviderResponseError(
                "The LLM cited evidence belonging outside the "
                f"deterministic context for {explanation.issue_id}: "
                + ", ".join(
                    unsupported_evidence
                )
            )

        if not explanation.human_review_required:
            raise LLMProviderResponseError(
                "The LLM removed the human-review requirement "
                f"for {explanation.issue_id}."
            )

    expected_average = round(
        sum(
            optional_float(
                reference.get("confidence_score")
            ) or 0.0
            for reference in reference_items
        ) / len(reference_items),
        2,
    )

    if abs(
        enhancement.confidence_score
        - expected_average
    ) > 0.000001:
        raise LLMProviderResponseError(
            "The LLM changed the aggregate deterministic "
            "root-cause confidence."
        )


class RootCauseAgent(BaseAgent):
    """
    Generate deterministic RCA and optionally enhance its explanation.

    Deterministic categories, confidence scores, evidence references,
    database records, and review state remain authoritative. The LLM
    may improve explanation quality but cannot overwrite reviewed RCA.
    """

    name = "Root-Cause Agent"
    version = "1.1.0"

    description = (
        "Analyzes prioritized issues using linked evidence and live "
        "business data, stores deterministic likely causes for human "
        "review, and optionally creates grounded manager explanations."
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
        """Run deterministic RCA and optional LLM explanation."""

        deterministic_output = build_deterministic_root_cause_output(
            context
        )

        provider = self._llm_provider

        if provider is None or not provider.config.enabled:
            return deterministic_output

        try:
            validated_context = build_root_cause_llm_context(
                deterministic_output
            )
            allowed_issue_ids = get_allowed_root_cause_issue_ids(
                deterministic_output
            )
            allowed_evidence_ids = get_allowed_root_cause_evidence_ids(
                deterministic_output
            )
            mock_structured_output = (
                build_mock_root_cause_output(
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
                    prompt_name=ROOT_CAUSE_PROMPT_NAME,
                    prompt_version=ROOT_CAUSE_PROMPT_VERSION,
                    validated_context=validated_context,
                    response_model=RootCauseExplanationV1,
                    allowed_evidence_ids=allowed_evidence_ids,
                    mock_structured_output=mock_structured_output,
                    request_metadata={
                        "run_id": context.run_id,
                        "run_type": context.run_type,
                    },
                    allowed_references={
                        "issue_id": allowed_issue_ids,
                    },
                    output_validator=lambda output: (
                        validate_root_cause_explanation_facts(
                            enhancement=output,
                            deterministic_output=deterministic_output,
                        )
                    ),
                )
            )

        except LLMError as error:
            failed_metadata = build_failed_execution_metadata(
                provider=provider,
                prompt_name=ROOT_CAUSE_PROMPT_NAME,
                prompt_version=ROOT_CAUSE_PROMPT_VERSION,
                error=error,
            )

            raise attach_deterministic_fallback(
                error=error,
                deterministic_output=deterministic_output,
                execution_metadata=failed_metadata,
            )

        except Exception as error:
            controlled_error = LLMProviderResponseError(
                "Root-cause LLM enhancement preparation failed: "
                + (
                    clean_text(error)
                    or type(error).__name__
                )
            )
            failed_metadata = build_failed_execution_metadata(
                provider=provider,
                prompt_name=ROOT_CAUSE_PROMPT_NAME,
                prompt_version=ROOT_CAUSE_PROMPT_VERSION,
                error=controlled_error,
            )

            raise attach_deterministic_fallback(
                error=controlled_error,
                deterministic_output=deterministic_output,
                execution_metadata=failed_metadata,
            )

        enhanced_output = dict(
            deterministic_output
        )
        enhanced_output["summary"] = enhancement.summary
        enhanced_output["llm_enhancement"] = {
            "status": "Complete",
            "schema_name": RootCauseExplanationV1.__name__,
            "deterministic_summary": deterministic_output["summary"],
            "persisted_to_root_cause_table": False,
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
        """Return the already-created deterministic RCA output."""

        del context

        return build_attached_fallback_output(
            error
        )