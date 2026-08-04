from __future__ import annotations

from datetime import date, datetime, timezone
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
from backend.app.db.database import engine


DEFAULT_ANALYSIS_LIMIT = 10
MAXIMUM_ANALYSIS_LIMIT = 50


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


class RootCauseAgent(BaseAgent):
    """
    Generate evidence-based likely-cause assessments.

    The agent reuses the existing deterministic root-cause rules,
    live PostgreSQL context, confidence calculation, supporting
    evidence serialization, and human-review workflow.
    """

    name = "Root-Cause Agent"

    description = (
        "Analyzes prioritized issues using linked evidence and "
        "live business data, then stores likely root causes for "
        "human review."
    )

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        """Run root-cause analysis for selected priority issues."""

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

        selected_evidence = (
            load_selected_evidence(
                engine,
                selected_issue_ids,
            )
        )

        analyses, database_records = (
            build_root_cause_outputs(
                engine,
                selected_issues,
                selected_evidence,
            )
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
            analyses[
                "root_cause_category"
            ]
            .astype(str)
            .eq(
                "Technical Review Required"
            )
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

        confidence_summary = (
            build_confidence_summary(
                analyses
            )
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
            f"Root-cause analysis generated "
            f"{len(analyses)} evidence-based assessments "
            f"from {total_evidence_records} linked evidence "
            f"records. Average confidence was "
            f"{confidence_summary['average']:.2f}%."
        )

        if technical_review_count > 0:
            summary += (
                f" {technical_review_count} assessments require "
                "technical review."
            )

        return {
            "summary": summary,
            "root_cause_status": root_cause_status,
            "generated_at": current_utc_time(),
            "selection": {
                "source": selection_source,
                "requested_limit": analysis_limit,
                "selected_issue_count": len(
                    selected_issues
                ),
                "issue_ids": selected_issue_ids,
            },
            "analysis": {
                "generated_count": len(
                    analyses
                ),
                "analysis_method": (
                    "Rule-Based Database and "
                    "Evidence Analysis"
                ),
                "technical_review_required_count": (
                    technical_review_count
                ),
                "zero_evidence_count": (
                    zero_evidence_count
                ),
                "confidence": (
                    confidence_summary
                ),
            },
            "evidence": {
                "selected_evidence_records": len(
                    selected_evidence
                ),
                "evidence_records_used": (
                    total_evidence_records
                ),
            },
            "database": {
                "persisted": True,
                "table": (
                    "root_cause_analyses"
                ),
                "review_status": (
                    "Pending Review"
                ),
            },
            "analyses": dataframe_to_records(
                analyses
            ),
        }