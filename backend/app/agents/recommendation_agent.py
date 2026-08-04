from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pandas as pd

from backend.analytics.recommendation_engine import (
    build_recommendations,
    load_recommendation_context,
    save_recommendations_to_database,
)
from backend.app.agents.agent_context import AgentContext
from backend.app.agents.base_agent import BaseAgent
from backend.app.agents.root_cause_agent import (
    build_current_priority_reference,
    build_previous_priority_reference,
    build_requested_issue_reference,
)
from backend.app.db.database import engine


DEFAULT_RECOMMENDATION_LIMIT = 10
MAXIMUM_RECOMMENDATION_LIMIT = 50


def current_utc_time() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(timezone.utc)


def get_recommendation_limit(
    context: AgentContext,
) -> int:
    """Read and validate the maximum recommendation count."""

    configured_value = context.input_data.get(
        "recommendation_limit",
        DEFAULT_RECOMMENDATION_LIMIT,
    )

    if isinstance(configured_value, bool):
        raise ValueError(
            "recommendation_limit must be an integer."
        )

    try:
        recommendation_limit = int(
            configured_value
        )

    except (TypeError, ValueError) as error:
        raise ValueError(
            "recommendation_limit must be an integer."
        ) from error

    if recommendation_limit < 1:
        raise ValueError(
            "recommendation_limit must be at least 1."
        )

    if recommendation_limit > MAXIMUM_RECOMMENDATION_LIMIT:
        raise ValueError(
            "recommendation_limit cannot be greater than "
            f"{MAXIMUM_RECOMMENDATION_LIMIT}."
        )

    return recommendation_limit


def build_previous_root_cause_reference(
    *,
    context: AgentContext,
    recommendation_limit: int,
) -> pd.DataFrame | None:
    """
    Read issue ranking information from the previous Root-Cause Agent.

    The previous root-cause result is preferred because it confirms
    which executive issues received an analysis during this sequence.
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

    root_cause_result = previous_results.get(
        "Root-Cause Agent"
    )

    if not isinstance(
        root_cause_result,
        dict,
    ):
        return None

    output_data = root_cause_result.get(
        "output_data",
        {},
    )

    if not isinstance(
        output_data,
        dict,
    ):
        return None

    analysis_items = output_data.get(
        "analyses",
        [],
    )

    if not isinstance(
        analysis_items,
        list,
    ) or not analysis_items:
        return None

    priority_reference = pd.DataFrame(
        analysis_items
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

    priority_reference["issue_id"] = (
        priority_reference["issue_id"]
        .astype(str)
        .str.strip()
    )

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

    priority_reference = priority_reference[
        priority_reference["issue_id"].ne("")
    ]

    priority_reference = (
        priority_reference
        .drop_duplicates(
            subset=["issue_id"],
            keep="first",
        )
        .sort_values("executive_rank")
        .head(recommendation_limit)
        .reset_index(drop=True)
    )

    if priority_reference.empty:
        return None

    return priority_reference


def build_recommendation_reference(
    *,
    context: AgentContext,
    recommendation_limit: int,
) -> tuple[pd.DataFrame, str]:
    """Resolve the issues that should receive recommendations."""

    if context.issue_ids:
        return (
            build_requested_issue_reference(
                issue_ids=context.issue_ids,
                analysis_limit=recommendation_limit,
            ),
            "Requested issue IDs",
        )

    root_cause_reference = (
        build_previous_root_cause_reference(
            context=context,
            recommendation_limit=recommendation_limit,
        )
    )

    if root_cause_reference is not None:
        return (
            root_cause_reference,
            "Root-Cause Agent output",
        )

    priority_reference = (
        build_previous_priority_reference(
            context=context,
            analysis_limit=recommendation_limit,
        )
    )

    if priority_reference is not None:
        return (
            priority_reference,
            "Priority Agent output",
        )

    return (
        build_current_priority_reference(
            analysis_limit=recommendation_limit,
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
    recommendations: pd.DataFrame,
) -> dict[str, float]:
    """Return recommendation-confidence statistics."""

    confidence_values = pd.to_numeric(
        recommendations["confidence_score"],
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


class RecommendationAgent(BaseAgent):
    """
    Generate deterministic management recommendations.

    The agent reuses the existing recommendation engine and preserves
    recommendations that were already accepted, edited, or converted
    into tasks.
    """

    name = "Recommendation Agent"

    description = (
        "Converts eligible root-cause analyses into proposed "
        "management actions with owners, deadlines, impact, and "
        "confidence for human review."
    )

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        """Generate recommendations for selected business issues."""

        recommendation_limit = (
            get_recommendation_limit(
                context
            )
        )

        priority_reference, selection_source = (
            build_recommendation_reference(
                context=context,
                recommendation_limit=recommendation_limit,
            )
        )

        selected_issue_ids = (
            priority_reference["issue_id"]
            .astype(str)
            .tolist()
        )

        recommendation_context = (
            load_recommendation_context(
                engine,
                priority_reference,
            )
        )

        if recommendation_context.empty:
            raise RuntimeError(
                "No eligible root-cause analyses matched the "
                "selected issues. Run the Root-Cause Agent first."
            )

        eligible_issue_ids = (
            recommendation_context["issue_id"]
            .astype(str)
            .tolist()
        )

        eligible_issue_id_set = set(
            eligible_issue_ids
        )

        unavailable_issue_ids = [
            issue_id
            for issue_id in selected_issue_ids
            if issue_id not in eligible_issue_id_set
        ]

        recommendations, database_records = (
            build_recommendations(
                recommendation_context
            )
        )

        if recommendations.empty:
            raise RuntimeError(
                "No recommendations were generated."
            )

        inserted_count, preserved_count = (
            save_recommendations_to_database(
                engine,
                database_records,
            )
        )

        confidence_summary = (
            build_confidence_summary(
                recommendations
            )
        )

        recommendation_status = (
            "Complete"
            if not unavailable_issue_ids
            else "Partial"
        )

        summary = (
            f"Recommendation generation created "
            f"{len(recommendations)} proposed management actions. "
            f"{inserted_count} recommendations were inserted or "
            f"refreshed, and {preserved_count} reviewed "
            f"recommendations were preserved. Average confidence "
            f"was {confidence_summary['average']:.2f}%."
        )

        if unavailable_issue_ids:
            summary += (
                f" {len(unavailable_issue_ids)} selected issues "
                "did not have an eligible root-cause analysis."
            )

        return {
            "summary": summary,
            "recommendation_status": recommendation_status,
            "generated_at": current_utc_time(),
            "selection": {
                "source": selection_source,
                "requested_limit": recommendation_limit,
                "selected_issue_count": len(
                    selected_issue_ids
                ),
                "eligible_issue_count": len(
                    eligible_issue_ids
                ),
                "issue_ids": eligible_issue_ids,
                "unavailable_issue_ids": (
                    unavailable_issue_ids
                ),
            },
            "generation": {
                "generated_count": len(
                    recommendations
                ),
                "generation_method": (
                    "Rule-Based Root-Cause and "
                    "Issue Analysis"
                ),
                "confidence": confidence_summary,
                "initial_review_status": (
                    "Pending Review"
                ),
            },
            "database": {
                "persisted": True,
                "table": "recommendations",
                "inserted_or_refreshed_count": (
                    inserted_count
                ),
                "reviewed_recommendations_preserved": (
                    preserved_count
                ),
            },
            "human_review": {
                "required": True,
                "allowed_actions": [
                    "Accept",
                    "Edit",
                    "Reject",
                ],
            },
            "recommendations": dataframe_to_records(
                recommendations
            ),
        }