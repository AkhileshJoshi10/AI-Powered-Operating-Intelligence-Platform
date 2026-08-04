from __future__ import annotations

from typing import Any

from backend.app.agents.agent_context import AgentContext
from backend.app.agents.base_agent import BaseAgent
from backend.app.schemas.executive_briefs import (
    GenerateExecutiveBriefResponse,
)
from backend.app.services.executive_brief_service import (
    generate_daily_executive_brief,
)


def safe_int(
    value: object,
) -> int:
    """Convert a value safely to an integer."""

    if value is None:
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


def get_string_list(
    value: object,
) -> list[str]:
    """Return a normalized list of non-empty strings."""

    if not isinstance(value, list):
        return []

    result: list[str] = []

    for item in value:
        cleaned_item = " ".join(
            str(item).split()
        )

        if cleaned_item:
            result.append(
                cleaned_item
            )

    return result


class ExecutiveBriefAgent(BaseAgent):
    """
    Generate and store the deterministic Daily Executive Brief.

    The agent reuses the existing Executive Brief service, which
    combines current KPIs, issues, root causes, recommendations,
    tasks, and management-attention points.
    """

    name = "Executive Brief Agent"

    description = (
        "Generates or updates the Daily Executive Brief from "
        "current business KPIs, issues, recommendations, and "
        "task workflow data."
    )

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        """Generate and store today's Daily Executive Brief."""

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
            response_json.get(
                "brief"
            )
        )

        brief_data = get_mapping(
            brief.get(
                "brief_data"
            )
        )

        kpi_snapshot = get_mapping(
            brief_data.get(
                "kpi_snapshot"
            )
        )

        issue_snapshot = get_mapping(
            brief_data.get(
                "issue_snapshot"
            )
        )

        recommendation_snapshot = get_mapping(
            brief_data.get(
                "recommendation_snapshot"
            )
        )

        task_snapshot = get_mapping(
            brief_data.get(
                "task_snapshot"
            )
        )

        management_attention = get_string_list(
            brief_data.get(
                "management_attention"
            )
        )

        total_kpis = safe_int(
            kpi_snapshot.get(
                "total_kpis"
            )
        )

        open_issue_count = safe_int(
            issue_snapshot.get(
                "open_issue_count"
            )
        )

        high_priority_issue_count = safe_int(
            issue_snapshot.get(
                "high_priority_open_issue_count"
            )
        )

        recommendations_needing_review = safe_int(
            recommendation_snapshot.get(
                "recommendations_needing_review"
            )
        )

        active_task_count = safe_int(
            task_snapshot.get(
                "active_task_count"
            )
        )

        blocked_task_count = safe_int(
            task_snapshot.get(
                "blocked_task_count"
            )
        )

        overdue_task_count = safe_int(
            task_snapshot.get(
                "overdue_task_count"
            )
        )

        action = str(
            response_json.get(
                "action",
                "",
            )
        ).strip()

        summary = (
            f"Daily Executive Brief {action} with "
            f"{total_kpis} KPIs, {open_issue_count} open issues, "
            f"{high_priority_issue_count} high-priority open "
            f"issues, and {recommendations_needing_review} "
            f"recommendations requiring management review. "
            f"The task workflow contains {active_task_count} "
            f"active tasks, including {blocked_task_count} "
            f"blocked and {overdue_task_count} overdue."
        )

        return {
            "summary": summary,
            "brief_status": "Complete",
            "generated_at": response_json[
                "generated_at"
            ],
            "generation": {
                "method": (
                    "Deterministic Current-State "
                    "Business Aggregation"
                ),
                "action": action,
                "message": response_json[
                    "message"
                ],
                "brief_version": brief_data.get(
                    "brief_version"
                ),
            },
            "snapshot": {
                "total_kpis": total_kpis,
                "open_issue_count": (
                    open_issue_count
                ),
                "high_priority_open_issue_count": (
                    high_priority_issue_count
                ),
                "recommendations_needing_review": (
                    recommendations_needing_review
                ),
                "active_task_count": (
                    active_task_count
                ),
                "blocked_task_count": (
                    blocked_task_count
                ),
                "overdue_task_count": (
                    overdue_task_count
                ),
            },
            "management_attention": (
                management_attention
            ),
            "database": {
                "persisted": True,
                "table": "executive_briefs",
                "brief_id": brief.get(
                    "brief_id"
                ),
                "brief_date": brief.get(
                    "brief_date"
                ),
                "brief_type": brief.get(
                    "brief_type"
                ),
                "record_status": brief.get(
                    "status"
                ),
                "same_day_behavior": (
                    "Create the first daily record or "
                    "update the existing record"
                ),
            },
            "brief": brief,
        }
    