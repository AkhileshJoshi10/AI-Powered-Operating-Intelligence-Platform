from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any

import pandas as pd

from backend.analytics.recommendation_engine import (
    build_recommendations,
    load_recommendation_context,
    save_recommendations_to_database,
)
from backend.app.agents.agent_context import AgentContext
from backend.app.agents.base_agent import BaseAgent
from backend.app.agents.llm_enhancement import (
    RecommendationEnhancementV1,
    attach_deterministic_fallback,
    build_attached_fallback_output,
    build_failed_execution_metadata,
    run_structured_enhancement,
)
from backend.app.agents.root_cause_agent import (
    build_current_priority_reference,
    build_previous_priority_reference,
    build_requested_issue_reference,
)
from backend.app.core.config import settings
from backend.app.db.database import engine
from backend.app.llm import (
    BaseLLMProvider,
    LLMError,
    LLMProviderResponseError,
    get_configured_provider,
)


DEFAULT_RECOMMENDATION_LIMIT = 10
MAXIMUM_RECOMMENDATION_LIMIT = 50

RECOMMENDATION_PROMPT_NAME = "recommendation_enhancement"
RECOMMENDATION_PROMPT_VERSION = "v1"

MAXIMUM_LLM_RECOMMENDATION_ITEMS = 20
MAXIMUM_ACTION_STEPS_PER_RECOMMENDATION = 12


def current_utc_time() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(timezone.utc)


def clean_text(
    value: object,
) -> str:
    """Convert one value into normalized text."""

    if value is None:
        return ""

    return " ".join(
        str(value).split()
    )


def optional_float(
    value: object,
) -> float | None:
    """Convert one scalar to float when possible."""

    if value is None or isinstance(value, bool):
        return None

    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def extract_deterministic_action_steps(
    recommendation_text: object,
) -> list[str]:
    """Extract numbered deterministic actions from recommendation text."""

    normalized_text = clean_text(
        recommendation_text
    )

    if not normalized_text:
        return []

    marker = "Recommended action steps:"
    action_text = normalized_text

    if marker in normalized_text:
        action_text = normalized_text.split(
            marker,
            maxsplit=1,
        )[1].strip()

    matches = list(
        re.finditer(
            r"(?:^|\s)(\d+)\.\s+",
            action_text,
        )
    )

    if not matches:
        return [
            action_text
        ][:MAXIMUM_ACTION_STEPS_PER_RECOMMENDATION]

    action_steps: list[str] = []

    for index, match in enumerate(matches):
        start_index = match.end()
        end_index = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(action_text)
        )
        step_text = clean_text(
            action_text[
                start_index:end_index
            ]
        )

        if (
            step_text
            and step_text not in action_steps
        ):
            action_steps.append(
                step_text
            )

        if (
            len(action_steps)
            >= MAXIMUM_ACTION_STEPS_PER_RECOMMENDATION
        ):
            break

    return action_steps


def build_action_reference_map(
    recommendations: list[dict[str, object]],
) -> dict[str, Any]:
    """Build immutable step references for deterministic actions."""

    by_issue: dict[
        str,
        list[dict[str, object]],
    ] = {}
    included_count = 0

    for recommendation in recommendations:
        issue_id = clean_text(
            recommendation.get("issue_id")
        )

        if not issue_id:
            continue

        action_steps = extract_deterministic_action_steps(
            recommendation.get(
                "recommendation_text"
            )
        )

        references: list[dict[str, object]] = []

        for position, action_text in enumerate(
            action_steps,
            start=1,
        ):
            references.append(
                {
                    "step_id": (
                        f"{issue_id}:ACTION-{position:02d}"
                    ),
                    "action_text": action_text,
                    "original_position": position,
                }
            )

        by_issue[issue_id] = references
        included_count += len(
            references
        )

    return {
        "source_field": "recommendation_text",
        "selected_issue_count": len(
            by_issue
        ),
        "included_count": included_count,
        "by_issue": by_issue,
    }


def build_deterministic_recommendation_output(
    context: AgentContext,
) -> dict[str, Any]:
    """Run the authoritative deterministic recommendation pipeline."""

    recommendation_limit = get_recommendation_limit(
        context
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

    recommendation_context = load_recommendation_context(
        engine,
        priority_reference,
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

    confidence_summary = build_confidence_summary(
        recommendations
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

    recommendation_records = dataframe_to_records(
        recommendations
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
        "review_protection": {
            "llm_enhancement_persisted_to_recommendations_table": False,
            "accepted_edited_or_task_converted_records_preserved": True,
            "automatic_approval_performed": False,
            "automatic_task_creation_performed": False,
        },
        "action_references": build_action_reference_map(
            recommendation_records
        ),
        "recommendations": recommendation_records,
    }


def build_recommendation_reference_items(
    deterministic_output: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build compact deterministic recommendation references."""

    recommendations = deterministic_output.get(
        "recommendations",
        [],
    )

    if not isinstance(
        recommendations,
        list,
    ):
        recommendations = []

    action_reference_section = deterministic_output.get(
        "action_references",
        {},
    )
    action_by_issue = (
        action_reference_section.get(
            "by_issue",
            {},
        )
        if isinstance(
            action_reference_section,
            dict,
        )
        else {}
    )

    allowed_fields = (
        "issue_id",
        "executive_rank",
        "issue_title",
        "issue_type",
        "business_area",
        "priority_level",
        "priority_score",
        "executive_score",
        "root_cause_category",
        "root_cause_summary",
        "root_cause_confidence_score",
        "recommendation_title",
        "recommendation_text",
        "suggested_owner_role",
        "suggested_deadline",
        "expected_impact",
        "confidence_score",
        "status",
    )

    reference_items: list[dict[str, Any]] = []

    for raw_recommendation in recommendations[
        :MAXIMUM_LLM_RECOMMENDATION_ITEMS
    ]:
        if not isinstance(
            raw_recommendation,
            dict,
        ):
            continue

        issue_id = clean_text(
            raw_recommendation.get(
                "issue_id"
            )
        )

        if not issue_id:
            continue

        item = {
            field_name: raw_recommendation.get(
                field_name
            )
            for field_name in allowed_fields
            if field_name in raw_recommendation
        }
        item["issue_id"] = issue_id

        raw_actions = (
            action_by_issue.get(
                issue_id,
                [],
            )
            if isinstance(
                action_by_issue,
                dict,
            )
            else []
        )

        item["action_steps"] = [
            {
                "step_id": clean_text(
                    action.get(
                        "step_id"
                    )
                ),
                "action_text": clean_text(
                    action.get(
                        "action_text"
                    )
                ),
                "original_position": action.get(
                    "original_position"
                ),
            }
            for action in raw_actions
            if (
                isinstance(action, dict)
                and clean_text(
                    action.get(
                        "step_id"
                    )
                )
                and clean_text(
                    action.get(
                        "action_text"
                    )
                )
            )
        ]

        reference_items.append(
            item
        )

    return reference_items


def build_recommendation_llm_context(
    deterministic_output: dict[str, Any],
) -> dict[str, Any]:
    """Create compact grounded recommendation context for the LLM."""

    return {
        "deterministic_summary": deterministic_output.get(
            "summary"
        ),
        "recommendation_status": deterministic_output.get(
            "recommendation_status"
        ),
        "selection": deterministic_output.get(
            "selection",
            {},
        ),
        "generation": deterministic_output.get(
            "generation",
            {},
        ),
        "review_policy": {
            "human_review_required": True,
            "allowed_review_actions": [
                "Accept",
                "Edit",
                "Reject",
            ],
            "automatic_approval_allowed": False,
            "automatic_execution_allowed": False,
            "automatic_task_creation_allowed": False,
            "llm_output_persisted_to_recommendations_table": False,
        },
        "recommendation_items": build_recommendation_reference_items(
            deterministic_output
        ),
    }


def build_mock_recommendation_output(
    deterministic_output: dict[str, Any],
) -> dict[str, Any]:
    """Build grounded structured output for the mock provider."""

    reference_items = build_recommendation_reference_items(
        deterministic_output
    )

    if not reference_items:
        raise LLMProviderResponseError(
            "No deterministic recommendations were available "
            "for enhancement."
        )

    enhancements: list[dict[str, Any]] = []
    top_level_warnings: list[str] = []

    for item in reference_items:
        issue_id = clean_text(
            item.get(
                "issue_id"
            )
        )
        title = clean_text(
            item.get(
                "recommendation_title"
            )
        ) or issue_id
        owner = clean_text(
            item.get(
                "suggested_owner_role"
            )
        ) or "Management Review Required"
        deadline = clean_text(
            item.get(
                "suggested_deadline"
            )
        ) or "Not supplied"
        impact = clean_text(
            item.get(
                "expected_impact"
            )
        ) or (
            "Expected impact was not supplied by the "
            "deterministic recommendation."
        )
        status = clean_text(
            item.get(
                "status"
            )
        ) or "Pending Review"
        confidence = optional_float(
            item.get(
                "confidence_score"
            )
        )

        if confidence is None:
            confidence = 0.0

        action_steps = list(
            item.get(
                "action_steps",
                [],
            )
        )
        sequenced_actions = [
            {
                "step_id": action["step_id"],
                "action_text": action["action_text"],
                "sequence_position": position,
            }
            for position, action in enumerate(
                action_steps,
                start=1,
            )
        ]

        warnings: list[str] = []

        if not sequenced_actions:
            warnings.append(
                "No distinct deterministic action steps were "
                "available for sequencing."
            )

        if deadline == "Not supplied":
            warnings.append(
                "No deterministic deadline was supplied."
            )

        manager_summary = (
            f"{title} remains a proposed management action for "
            f"{issue_id}. The deterministic owner is {owner}, "
            f"the proposed deadline is {deadline}, and human "
            "review is required before approval or execution."
        )

        enhancements.append(
            {
                "issue_id": issue_id,
                "deterministic_recommendation_title": title,
                "deterministic_owner_role": owner,
                "deterministic_deadline": deadline,
                "deterministic_expected_impact": impact,
                "deterministic_confidence_score": confidence,
                "deterministic_status": status,
                "manager_friendly_summary": manager_summary,
                "sequenced_actions": sequenced_actions,
                "sequencing_rationale": (
                    "The deterministic action order was retained "
                    "because no validated dependency required "
                    "reordering."
                ),
                "missing_information_warnings": warnings,
                "human_review_required": True,
                "approval_or_execution_performed": False,
            }
        )

        for warning in warnings:
            if warning not in top_level_warnings:
                top_level_warnings.append(
                    warning
                )

    confidence_score = round(
        sum(
            enhancement[
                "deterministic_confidence_score"
            ]
            for enhancement in enhancements
        ) / len(enhancements),
        2,
    )

    return {
        "summary": (
            f"Prepared manager-facing sequencing for "
            f"{len(enhancements)} deterministic recommendations "
            "without changing owners, deadlines, expected impacts, "
            "confidence values, or review status."
        ),
        "recommendation_enhancements": enhancements,
        "confidence_score": confidence_score,
        "missing_information_warnings": top_level_warnings,
        "human_review_required": True,
        "recommendations_approved": False,
        "tasks_created": False,
    }


def get_allowed_recommendation_issue_ids(
    deterministic_output: dict[str, Any],
) -> list[str]:
    """Return issue IDs the enhancement may reference."""

    return [
        clean_text(
            item.get(
                "issue_id"
            )
        )
        for item in build_recommendation_reference_items(
            deterministic_output
        )
        if clean_text(
            item.get(
                "issue_id"
            )
        )
    ]


def get_allowed_action_step_ids(
    deterministic_output: dict[str, Any],
) -> list[str]:
    """Return deterministic action-step IDs the LLM may use."""

    step_ids: list[str] = []

    for item in build_recommendation_reference_items(
        deterministic_output
    ):
        for action in item.get(
            "action_steps",
            [],
        ):
            step_id = clean_text(
                action.get(
                    "step_id"
                )
            )

            if (
                step_id
                and step_id not in step_ids
            ):
                step_ids.append(
                    step_id
                )

    return step_ids


def validate_recommendation_enhancement_facts(
    *,
    enhancement: RecommendationEnhancementV1,
    deterministic_output: dict[str, Any],
) -> None:
    """Reject changed actions, owners, deadlines, facts, or status."""

    reference_items = build_recommendation_reference_items(
        deterministic_output
    )

    reference_by_issue = {
        clean_text(
            item.get(
                "issue_id"
            )
        ): item
        for item in reference_items
        if clean_text(
            item.get(
                "issue_id"
            )
        )
    }

    expected_issue_ids = list(
        reference_by_issue
    )

    if not expected_issue_ids:
        raise LLMProviderResponseError(
            "No deterministic recommendation references "
            "were available."
        )

    returned_issue_ids = [
        item.issue_id
        for item in enhancement.recommendation_enhancements
    ]

    if returned_issue_ids != expected_issue_ids:
        raise LLMProviderResponseError(
            "The LLM changed or reordered the deterministic "
            "recommendation issue sequence."
        )

    for item in enhancement.recommendation_enhancements:
        reference = reference_by_issue[
            item.issue_id
        ]

        exact_text_fields = (
            (
                "deterministic_recommendation_title",
                "recommendation_title",
                "recommendation title",
            ),
            (
                "deterministic_owner_role",
                "suggested_owner_role",
                "suggested owner",
            ),
            (
                "deterministic_deadline",
                "suggested_deadline",
                "suggested deadline",
            ),
            (
                "deterministic_expected_impact",
                "expected_impact",
                "expected impact",
            ),
            (
                "deterministic_status",
                "status",
                "review status",
            ),
        )

        for (
            output_field,
            reference_field,
            description,
        ) in exact_text_fields:
            expected_value = clean_text(
                reference.get(
                    reference_field
                )
            )
            returned_value = clean_text(
                getattr(
                    item,
                    output_field,
                )
            )

            if returned_value != expected_value:
                raise LLMProviderResponseError(
                    "The LLM changed the deterministic "
                    f"{description} for {item.issue_id}."
                )

        expected_confidence = optional_float(
            reference.get(
                "confidence_score"
            )
        )

        if expected_confidence is None:
            expected_confidence = 0.0

        if abs(
            item.deterministic_confidence_score
            - expected_confidence
        ) > 0.000001:
            raise LLMProviderResponseError(
                "The LLM changed the deterministic confidence "
                f"for {item.issue_id}."
            )

        expected_actions = {
            clean_text(
                action.get(
                    "step_id"
                )
            ): clean_text(
                action.get(
                    "action_text"
                )
            )
            for action in reference.get(
                "action_steps",
                [],
            )
            if clean_text(
                action.get(
                    "step_id"
                )
            )
        }

        returned_step_ids = [
            action.step_id
            for action in item.sequenced_actions
        ]

        if (
            len(returned_step_ids)
            != len(expected_actions)
            or set(returned_step_ids)
            != set(expected_actions)
        ):
            raise LLMProviderResponseError(
                "The LLM added, removed, or duplicated "
                f"deterministic action steps for {item.issue_id}."
            )

        for action in item.sequenced_actions:
            expected_action_text = expected_actions[
                action.step_id
            ]

            if (
                action.action_text
                != expected_action_text
            ):
                raise LLMProviderResponseError(
                    "The LLM changed a deterministic action "
                    f"for {item.issue_id}: {action.step_id}."
                )

    expected_average = round(
        sum(
            optional_float(
                reference.get(
                    "confidence_score"
                )
            )
            or 0.0
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
            "recommendation confidence."
        )


class RecommendationAgent(BaseAgent):
    """
    Generate deterministic recommendations and optional sequencing.

    Deterministic actions, owners, deadlines, expected impacts,
    confidence values, database records, and human-review state remain
    authoritative. The LLM cannot approve, execute, or create tasks.
    """

    name = "Recommendation Agent"
    version = "1.1.0"

    description = (
        "Converts eligible root-cause analyses into deterministic "
        "management actions and optionally improves their manager-facing "
        "sequencing without approving or executing them."
    )

    def __init__(
        self,
        llm_provider: BaseLLMProvider | None = None,
    ) -> None:
        """Initialize with an optional provider for injection/testing."""

        super().__init__()

        self._llm_provider = llm_provider

        if (
            self._llm_provider is None
            and settings.llm_enabled
        ):
            self._llm_provider = get_configured_provider()

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        """Run deterministic recommendations and optional enhancement."""

        deterministic_output = (
            build_deterministic_recommendation_output(
                context
            )
        )

        provider = self._llm_provider

        if (
            provider is None
            or not provider.config.enabled
        ):
            return deterministic_output

        try:
            validated_context = (
                build_recommendation_llm_context(
                    deterministic_output
                )
            )
            allowed_issue_ids = (
                get_allowed_recommendation_issue_ids(
                    deterministic_output
                )
            )
            allowed_step_ids = (
                get_allowed_action_step_ids(
                    deterministic_output
                )
            )
            mock_structured_output = (
                build_mock_recommendation_output(
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
                    prompt_name=RECOMMENDATION_PROMPT_NAME,
                    prompt_version=RECOMMENDATION_PROMPT_VERSION,
                    validated_context=validated_context,
                    response_model=RecommendationEnhancementV1,
                    allowed_evidence_ids=[],
                    mock_structured_output=mock_structured_output,
                    request_metadata={
                        "run_id": context.run_id,
                        "run_type": context.run_type,
                    },
                    allowed_references={
                        "issue_id": allowed_issue_ids,
                        "step_id": allowed_step_ids,
                    },
                    output_validator=lambda output: (
                        validate_recommendation_enhancement_facts(
                            enhancement=output,
                            deterministic_output=deterministic_output,
                        )
                    ),
                )
            )

        except LLMError as error:
            failed_metadata = build_failed_execution_metadata(
                provider=provider,
                prompt_name=RECOMMENDATION_PROMPT_NAME,
                prompt_version=RECOMMENDATION_PROMPT_VERSION,
                error=error,
            )

            raise attach_deterministic_fallback(
                error=error,
                deterministic_output=deterministic_output,
                execution_metadata=failed_metadata,
            )

        except Exception as error:
            controlled_error = LLMProviderResponseError(
                "Recommendation LLM enhancement preparation failed: "
                + (
                    clean_text(
                        error
                    )
                    or type(
                        error
                    ).__name__
                )
            )
            failed_metadata = build_failed_execution_metadata(
                provider=provider,
                prompt_name=RECOMMENDATION_PROMPT_NAME,
                prompt_version=RECOMMENDATION_PROMPT_VERSION,
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
        enhanced_output["summary"] = (
            enhancement.summary
        )
        enhanced_output["llm_enhancement"] = {
            "status": "Complete",
            "schema_name": (
                RecommendationEnhancementV1.__name__
            ),
            "deterministic_summary": (
                deterministic_output["summary"]
            ),
            "persisted_to_recommendations_table": False,
            "recommendations_approved": False,
            "tasks_created": False,
            **enhancement.model_dump(
                mode="python"
            ),
        }
        enhanced_output[
            "_execution_metadata"
        ] = execution_metadata.model_dump(
            mode="python"
        )

        return enhanced_output

    async def fallback(
        self,
        context: AgentContext,
        error: Exception,
    ) -> dict[str, Any] | None:
        """Return the already-created deterministic recommendations."""

        del context

        return build_attached_fallback_output(
            error
        )