from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from backend.app.db.database import engine
from backend.app.services.issue_service import (
    get_issue_detail,
    get_issue_list,
)
from backend.app.services.kpi_service import (
    get_kpi_response,
)
from backend.app.services.recommendation_service import (
    get_recommendation_list,
)
from backend.app.services.task_service import (
    get_task_list,
)


DAILY_BRIEF_TYPE = "Daily Executive Brief"

TOP_ISSUE_LIMIT = 10
TOP_RECOMMENDATION_LIMIT = 10
TOP_TASK_LIMIT = 10
TASK_SCAN_LIMIT = 1000

AUTOMATION_RECENT_LIMIT = 10
AUTOMATION_CATEGORY_LIMIT = 5
DAILY_BRIEF_AUTOMATION_ACTION = "daily_executive_brief"


RECOMMENDATION_STATUSES = [
    "Pending Review",
    "Edited",
    "Accepted",
    "Rejected",
    "Converted to Task",
]


TASK_STATUSES = [
    "Unassigned",
    "To Do",
    "In Progress",
    "Blocked",
    "Completed",
]


def serialize_executive_brief(
    row: Mapping[str, Any],
) -> dict[str, Any]:
    """Convert a database row into API-compatible data."""

    brief_data = row["brief_data"]

    if brief_data is None:
        brief_data = {}

    return {
        "brief_id": int(
            row["brief_id"]
        ),
        "brief_date": row["brief_date"],
        "brief_type": str(
            row["brief_type"]
        ).strip(),
        "summary_text": str(
            row["summary_text"]
        ).strip(),
        "brief_data": brief_data,
        "status": str(
            row["status"]
        ).strip(),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def convert_to_json_safe(
    value: Any,
) -> Any:
    """Recursively convert values into JSON-compatible types."""

    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Mapping):
        return {
            str(key): convert_to_json_safe(
                item_value
            )
            for key, item_value in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            convert_to_json_safe(item)
            for item in value
        ]

    return str(value)


def get_latest_executive_brief() -> dict[str, Any] | None:
    """Return the latest stored Executive Brief."""

    query = text(
        """
        SELECT
            brief_id,
            brief_date,
            brief_type,
            summary_text,
            brief_data,
            status,
            created_at,
            updated_at
        FROM executive_briefs
        ORDER BY
            brief_date DESC,
            created_at DESC,
            brief_id DESC
        LIMIT 1;
        """
    )

    with engine.connect() as connection:
        row = (
            connection.execute(query)
            .mappings()
            .first()
        )

    if row is None:
        return None

    return {
        "status": "success",
        "generated_at": datetime.now(),
        "brief": serialize_executive_brief(
            row
        ),
    }


def get_recommendation_status_count(
    recommendation_status: str,
) -> int:
    """Return the number of recommendations in one status."""

    response = get_recommendation_list(
        recommendation_status=recommendation_status,
        owner_role=None,
        business_area=None,
        limit=1,
        offset=0,
    )

    return int(
        response["total_items"]
    )


def get_task_status_count(
    task_status: str,
) -> int:
    """Return the number of tasks in one Kanban status."""

    response = get_task_list(
        task_status=task_status,
        priority_level=None,
        assigned_role=None,
        limit=1,
        offset=0,
    )

    return int(
        response["total_items"]
    )


def build_issue_snapshot() -> dict[str, Any]:
    """Build the issue and root-cause section of the brief."""

    open_issues_response = get_issue_list(
        priority=None,
        business_area=None,
        issue_status="Open",
        limit=TOP_ISSUE_LIMIT,
        offset=0,
    )

    high_priority_response = get_issue_list(
        priority="High",
        business_area=None,
        issue_status="Open",
        limit=1,
        offset=0,
    )

    in_progress_response = get_issue_list(
        priority=None,
        business_area=None,
        issue_status="In Progress",
        limit=1,
        offset=0,
    )

    top_issue_records = []

    for issue in open_issues_response["items"]:
        issue_id = str(
            issue["issue_id"]
        )

        detail_response = get_issue_detail(
            issue_id
        )

        root_cause = None
        evidence_count = 0

        if detail_response is not None:
            root_cause = detail_response.get(
                "root_cause"
            )

            evidence_count = int(
                detail_response.get(
                    "evidence_count",
                    0,
                )
            )

        top_issue_records.append(
            {
                "issue_id": issue_id,
                "title": issue.get("title"),
                "issue_type": issue.get(
                    "issue_type"
                ),
                "business_area": issue.get(
                    "business_area"
                ),
                "priority_level": issue.get(
                    "priority_level"
                ),
                "priority_score": issue.get(
                    "priority_score"
                ),
                "priority_reason": issue.get(
                    "priority_reason"
                ),
                "status": issue.get(
                    "status"
                ),
                "entity_type": issue.get(
                    "entity_type"
                ),
                "entity_id": issue.get(
                    "entity_id"
                ),
                "summary": issue.get(
                    "summary"
                ),
                "evidence_count": evidence_count,
                "root_cause": (
                    {
                        "root_cause_category": (
                            root_cause.get(
                                "root_cause_category"
                            )
                        ),
                        "root_cause_summary": (
                            root_cause.get(
                                "root_cause_summary"
                            )
                        ),
                        "confidence_score": (
                            root_cause.get(
                                "confidence_score"
                            )
                        ),
                        "review_status": (
                            root_cause.get(
                                "review_status"
                            )
                        ),
                    }
                    if root_cause is not None
                    else None
                ),
            }
        )

    return {
        "open_issue_count": int(
            open_issues_response[
                "total_items"
            ]
        ),
        "high_priority_open_issue_count": int(
            high_priority_response[
                "total_items"
            ]
        ),
        "in_progress_issue_count": int(
            in_progress_response[
                "total_items"
            ]
        ),
        "top_open_issues": top_issue_records,
    }


def build_recommendation_snapshot() -> dict[str, Any]:
    """Build recommendation counts and priority recommendations."""

    recommendation_status_counts = {
        recommendation_status:
        get_recommendation_status_count(
            recommendation_status
        )
        for recommendation_status
        in RECOMMENDATION_STATUSES
    }

    top_recommendations_response = (
        get_recommendation_list(
            recommendation_status=None,
            owner_role=None,
            business_area=None,
            limit=TOP_RECOMMENDATION_LIMIT,
            offset=0,
        )
    )

    recommendations_needing_review = (
        recommendation_status_counts[
            "Pending Review"
        ]
        + recommendation_status_counts[
            "Edited"
        ]
    )

    return {
        "total_recommendations": int(
            top_recommendations_response[
                "total_items"
            ]
        ),
        "recommendations_needing_review": (
            recommendations_needing_review
        ),
        "status_counts": (
            recommendation_status_counts
        ),
        "top_recommendations": (
            top_recommendations_response[
                "items"
            ]
        ),
    }


def build_task_snapshot() -> dict[str, Any]:
    """Build task progress, blocked-task and overdue-task details."""

    task_status_counts = {
        task_status: get_task_status_count(
            task_status
        )
        for task_status in TASK_STATUSES
    }

    task_response = get_task_list(
        task_status=None,
        priority_level=None,
        assigned_role=None,
        limit=TASK_SCAN_LIMIT,
        offset=0,
    )

    today = date.today()

    overdue_tasks = []

    for task in task_response["items"]:
        due_date = task.get(
            "due_date"
        )

        task_status = str(
            task.get(
                "status",
                "",
            )
        )

        if (
            due_date is not None
            and due_date < today
            and task_status != "Completed"
        ):
            overdue_tasks.append(
                task
            )

    overdue_tasks.sort(
        key=lambda task: (
            task.get("due_date"),
            task.get("task_id"),
        )
    )

    active_task_count = (
        task_status_counts[
            "Unassigned"
        ]
        + task_status_counts[
            "To Do"
        ]
        + task_status_counts[
            "In Progress"
        ]
        + task_status_counts[
            "Blocked"
        ]
    )

    return {
        "total_tasks": int(
            task_response[
                "total_items"
            ]
        ),
        "active_task_count": (
            active_task_count
        ),
        "blocked_task_count": (
            task_status_counts[
                "Blocked"
            ]
        ),
        "overdue_task_count": len(
            overdue_tasks
        ),
        "status_counts": (
            task_status_counts
        ),
        "overdue_tasks": overdue_tasks[
            :TOP_TASK_LIMIT
        ],
        "priority_tasks": task_response[
            "items"
        ][:TOP_TASK_LIMIT],
    }


def serialize_automation_log(
    row: Mapping[str, Any],
) -> dict[str, Any]:
    """Convert one automation log row into brief-safe data."""

    return {
        "automation_log_id": int(row["automation_log_id"]),
        "task_id": (
            int(row["task_id"])
            if row["task_id"] is not None
            else None
        ),
        "issue_id": row["issue_id"],
        "workflow_name": str(row["workflow_name"]).strip(),
        "action_type": str(row["action_type"]).strip(),
        "execution_status": str(row["execution_status"]).strip(),
        "n8n_execution_id": row["n8n_execution_id"],
        "attempt_count": int(row["attempt_count"] or 0),
        "http_status_code": (
            int(row["http_status_code"])
            if row["http_status_code"] is not None
            else None
        ),
        "message": row["message"],
        "error_type": row["error_type"],
        "error_message": row["error_message"],
        "executed_at": row["executed_at"],
    }


def get_recent_automation_logs(
    *,
    action_type: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    """
    Return recent operational automation logs.

    Explicit manual failure-path validation records are excluded so
    controlled test activity does not distort the Executive Brief.
    """

    query = text(
        """
        SELECT
            automation_log_id,
            task_id,
            issue_id,
            workflow_name,
            action_type,
            execution_status,
            n8n_execution_id,
            attempt_count,
            http_status_code,
            message,
            error_type,
            error_message,
            executed_at
        FROM automation_logs
        WHERE
            COALESCE(request_metadata ->> 'source', '') <> 'manual_validation'
            AND COALESCE(request_metadata ->> 'purpose', '') <> 'failure_path_test'
            AND (
                :action_type IS NULL
                OR action_type = :action_type
            )
        ORDER BY
            executed_at DESC,
            automation_log_id DESC
        LIMIT :limit;
        """
    )

    with engine.connect() as connection:
        rows = (
            connection.execute(
                query,
                {
                    "action_type": action_type,
                    "limit": int(limit),
                },
            )
            .mappings()
            .all()
        )

    return [
        serialize_automation_log(row)
        for row in rows
    ]


def build_automation_snapshot() -> dict[str, Any]:
    """Build recent automation activity for the Executive Brief."""

    count_query = text(
        """
        SELECT
            COUNT(*) AS total_workflow_count,
            COUNT(*) FILTER (
                WHERE execution_status = 'Succeeded'
            ) AS successful_workflow_count,
            COUNT(*) FILTER (
                WHERE execution_status = 'Failed'
            ) AS failed_workflow_count,
            COUNT(*) FILTER (
                WHERE execution_status = 'Skipped'
            ) AS skipped_workflow_count,
            COUNT(*) FILTER (
                WHERE execution_status IN ('Pending', 'Triggered')
            ) AS in_progress_workflow_count
        FROM automation_logs
        WHERE
            executed_at::date = CURRENT_DATE
            AND COALESCE(request_metadata ->> 'source', '') <> 'manual_validation'
            AND COALESCE(request_metadata ->> 'purpose', '') <> 'failure_path_test';
        """
    )

    latest_brief_delivery_query = text(
        """
        SELECT
            automation_log_id,
            task_id,
            issue_id,
            workflow_name,
            action_type,
            execution_status,
            n8n_execution_id,
            attempt_count,
            http_status_code,
            message,
            error_type,
            error_message,
            executed_at
        FROM automation_logs
        WHERE
            action_type = :action_type
            AND COALESCE(request_metadata ->> 'source', '') <> 'manual_validation'
            AND COALESCE(request_metadata ->> 'purpose', '') <> 'failure_path_test'
        ORDER BY
            executed_at DESC,
            automation_log_id DESC
        LIMIT 1;
        """
    )

    with engine.connect() as connection:
        count_row = (
            connection.execute(count_query)
            .mappings()
            .one()
        )

        latest_brief_delivery_row = (
            connection.execute(
                latest_brief_delivery_query,
                {
                    "action_type": DAILY_BRIEF_AUTOMATION_ACTION,
                },
            )
            .mappings()
            .one_or_none()
        )

    recent_workflow_executions = get_recent_automation_logs(
        action_type=None,
        limit=AUTOMATION_RECENT_LIMIT,
    )

    recent_alerts = get_recent_automation_logs(
        action_type="high_priority_alert",
        limit=AUTOMATION_CATEGORY_LIMIT,
    )

    recent_reminders = get_recent_automation_logs(
        action_type="task_reminder",
        limit=AUTOMATION_CATEGORY_LIMIT,
    )

    recent_escalations = get_recent_automation_logs(
        action_type="overdue_escalation",
        limit=AUTOMATION_CATEGORY_LIMIT,
    )

    last_executive_brief_delivery = (
        serialize_automation_log(latest_brief_delivery_row)
        if latest_brief_delivery_row is not None
        else None
    )

    return {
        "count_window": "today",
        "total_workflow_count": int(
            count_row["total_workflow_count"] or 0
        ),
        "successful_workflow_count": int(
            count_row["successful_workflow_count"] or 0
        ),
        "failed_workflow_count": int(
            count_row["failed_workflow_count"] or 0
        ),
        "skipped_workflow_count": int(
            count_row["skipped_workflow_count"] or 0
        ),
        "in_progress_workflow_count": int(
            count_row["in_progress_workflow_count"] or 0
        ),
        "recent_workflow_executions": recent_workflow_executions,
        "recent_alerts": recent_alerts,
        "recent_reminders": recent_reminders,
        "recent_escalations": recent_escalations,
        "last_executive_brief_delivery_status": (
            last_executive_brief_delivery["execution_status"]
            if last_executive_brief_delivery is not None
            else None
        ),
        "last_executive_brief_delivery": last_executive_brief_delivery,
    }


def find_kpi_display_value(
    kpis: list[dict[str, Any]],
    search_terms: list[str],
) -> str | None:
    """Find a KPI display value using its key or readable name."""

    normalized_terms = [
        search_term.casefold()
        for search_term in search_terms
    ]

    for kpi in kpis:
        kpi_key = str(
            kpi.get(
                "kpi_key",
                "",
            )
        ).casefold()

        kpi_name = str(
            kpi.get(
                "kpi_name",
                "",
            )
        ).casefold()

        if any(
            search_term in kpi_key
            or search_term in kpi_name
            for search_term
            in normalized_terms
        ):
            display_value = str(
                kpi.get(
                    "display_value",
                    "",
                )
            ).strip()

            if display_value:
                return display_value

    return None


def build_management_attention(
    *,
    issue_snapshot: dict[str, Any],
    recommendation_snapshot: dict[str, Any],
    task_snapshot: dict[str, Any],
    automation_snapshot: dict[str, Any],
) -> list[str]:
    """Create deterministic executive attention points."""

    attention_points = []

    high_priority_issue_count = int(
        issue_snapshot[
            "high_priority_open_issue_count"
        ]
    )

    if high_priority_issue_count > 0:
        attention_points.append(
            f"Review {high_priority_issue_count} "
            "high-priority open business issues."
        )

    recommendations_needing_review = int(
        recommendation_snapshot[
            "recommendations_needing_review"
        ]
    )

    if recommendations_needing_review > 0:
        attention_points.append(
            f"Complete management review for "
            f"{recommendations_needing_review} recommendations."
        )

    blocked_task_count = int(
        task_snapshot[
            "blocked_task_count"
        ]
    )

    if blocked_task_count > 0:
        attention_points.append(
            f"Resolve blockers affecting "
            f"{blocked_task_count} tasks."
        )

    overdue_task_count = int(
        task_snapshot[
            "overdue_task_count"
        ]
    )

    if overdue_task_count > 0:
        attention_points.append(
            f"Address {overdue_task_count} overdue tasks."
        )

    failed_workflow_count = int(
        automation_snapshot["failed_workflow_count"]
    )

    if failed_workflow_count > 0:
        attention_points.append(
            f"Review {failed_workflow_count} failed "
            "automation executions recorded today."
        )

    if not attention_points:
        attention_points.append(
            "No immediate critical workflow action was detected."
        )

    return attention_points


def build_summary_text(
    *,
    kpi_response: dict[str, Any],
    issue_snapshot: dict[str, Any],
    recommendation_snapshot: dict[str, Any],
    task_snapshot: dict[str, Any],
    automation_snapshot: dict[str, Any],
) -> str:
    """Build a deterministic Executive Brief summary paragraph."""

    kpis = kpi_response.get(
        "kpis",
        [],
    )

    high_priority_issues = int(
        issue_snapshot[
            "high_priority_open_issue_count"
        ]
    )

    open_issues = int(
        issue_snapshot[
            "open_issue_count"
        ]
    )

    recommendations_needing_review = int(
        recommendation_snapshot[
            "recommendations_needing_review"
        ]
    )

    active_tasks = int(
        task_snapshot[
            "active_task_count"
        ]
    )

    blocked_tasks = int(
        task_snapshot[
            "blocked_task_count"
        ]
    )

    overdue_tasks = int(
        task_snapshot[
            "overdue_task_count"
        ]
    )

    successful_automations = int(
        automation_snapshot["successful_workflow_count"]
    )

    failed_automations = int(
        automation_snapshot["failed_workflow_count"]
    )

    summary_parts = [
        (
            f"The current operating snapshot contains "
            f"{open_issues} open business issues, including "
            f"{high_priority_issues} high-priority issues."
        ),
        (
            f"{recommendations_needing_review} recommendations "
            f"are awaiting management review."
        ),
        (
            f"There are {active_tasks} active tasks, including "
            f"{blocked_tasks} blocked and {overdue_tasks} overdue tasks."
        ),
        (
            f"Today's automation activity includes "
            f"{successful_automations} successful and "
            f"{failed_automations} failed workflow executions."
        ),
    ]

    sales_growth = find_kpi_display_value(
        kpis,
        [
            "sales growth",
            "sales_growth",
        ],
    )

    target_achievement = find_kpi_display_value(
        kpis,
        [
            "target achievement",
            "target_achievement",
        ],
    )

    operating_profit = find_kpi_display_value(
        kpis,
        [
            "operating profit",
            "operating_profit",
        ],
    )

    kpi_parts = []

    if sales_growth is not None:
        kpi_parts.append(
            f"sales growth is {sales_growth}"
        )

    if target_achievement is not None:
        kpi_parts.append(
            f"target achievement is {target_achievement}"
        )

    if operating_profit is not None:
        kpi_parts.append(
            f"operating profit is {operating_profit}"
        )

    if kpi_parts:
        summary_parts.append(
            "Key performance indicators show that "
            + ", ".join(kpi_parts)
            + "."
        )

    return " ".join(
        summary_parts
    )


def build_executive_brief_data() -> tuple[str, dict[str, Any]]:
    """Build the deterministic data and summary for the daily brief."""

    kpi_response = get_kpi_response()

    issue_snapshot = (
        build_issue_snapshot()
    )

    recommendation_snapshot = (
        build_recommendation_snapshot()
    )

    task_snapshot = (
        build_task_snapshot()
    )

    automation_snapshot = (
        build_automation_snapshot()
    )

    management_attention = (
        build_management_attention(
            issue_snapshot=issue_snapshot,
            recommendation_snapshot=(
                recommendation_snapshot
            ),
            task_snapshot=task_snapshot,
            automation_snapshot=automation_snapshot,
        )
    )

    summary_text = build_summary_text(
        kpi_response=kpi_response,
        issue_snapshot=issue_snapshot,
        recommendation_snapshot=(
            recommendation_snapshot
        ),
        task_snapshot=task_snapshot,
        automation_snapshot=automation_snapshot,
    )

    brief_data = {
        "brief_version": 2,
        "generated_at": (
            datetime.now().isoformat()
        ),
        "kpi_snapshot": {
            "total_kpis": kpi_response.get(
                "total_kpis",
                0,
            ),
            "kpis": kpi_response.get(
                "kpis",
                [],
            ),
            "latest_store_target_achievement": (
                kpi_response.get(
                    "latest_store_target_achievement",
                    [],
                )
            ),
        },
        "issue_snapshot": (
            issue_snapshot
        ),
        "recommendation_snapshot": (
            recommendation_snapshot
        ),
        "task_snapshot": (
            task_snapshot
        ),
        "automation_snapshot": (
            automation_snapshot
        ),
        "management_attention": (
            management_attention
        ),
    }

    return (
        summary_text,
        convert_to_json_safe(
            brief_data
        ),
    )


def save_daily_executive_brief(
    *,
    summary_text: str,
    brief_data: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """
    Create or update today's Daily Executive Brief.

    A table lock prevents duplicate daily records during concurrent
    generation requests.
    """

    brief_date = date.today()

    existing_brief_query = text(
        """
        SELECT
            brief_id
        FROM executive_briefs
        WHERE
            brief_date = :brief_date
            AND brief_type = :brief_type
        ORDER BY
            brief_id DESC
        LIMIT 1
        FOR UPDATE;
        """
    )

    insert_query = text(
        """
        INSERT INTO executive_briefs (
            brief_date,
            brief_type,
            summary_text,
            brief_data,
            status
        )
        VALUES (
            :brief_date,
            :brief_type,
            :summary_text,
            CAST(:brief_data AS JSONB),
            'Draft'
        )
        RETURNING
            brief_id,
            brief_date,
            brief_type,
            summary_text,
            brief_data,
            status,
            created_at,
            updated_at;
        """
    )

    update_query = text(
        """
        UPDATE executive_briefs
        SET
            summary_text = :summary_text,
            brief_data = CAST(:brief_data AS JSONB),
            updated_at = CURRENT_TIMESTAMP
        WHERE brief_id = :brief_id
        RETURNING
            brief_id,
            brief_date,
            brief_type,
            summary_text,
            brief_data,
            status,
            created_at,
            updated_at;
        """
    )

    parameters = {
        "brief_date": brief_date,
        "brief_type": DAILY_BRIEF_TYPE,
        "summary_text": summary_text,
        "brief_data": json.dumps(
            brief_data,
            ensure_ascii=False,
        ),
    }

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                LOCK TABLE executive_briefs
                IN SHARE ROW EXCLUSIVE MODE;
                """
            )
        )

        existing_brief = (
            connection.execute(
                existing_brief_query,
                parameters,
            )
            .mappings()
            .one_or_none()
        )

        if existing_brief is None:
            row = (
                connection.execute(
                    insert_query,
                    parameters,
                )
                .mappings()
                .one()
            )

            action = "created"

        else:
            update_parameters = {
                **parameters,
                "brief_id": int(
                    existing_brief[
                        "brief_id"
                    ]
                ),
            }

            row = (
                connection.execute(
                    update_query,
                    update_parameters,
                )
                .mappings()
                .one()
            )

            action = "updated"

    return (
        action,
        serialize_executive_brief(
            row
        ),
    )


def generate_daily_executive_brief() -> dict[str, Any]:
    """Generate and store today's deterministic Executive Brief."""

    (
        summary_text,
        brief_data,
    ) = build_executive_brief_data()

    (
        action,
        stored_brief,
    ) = save_daily_executive_brief(
        summary_text=summary_text,
        brief_data=brief_data,
    )

    return {
        "status": "success",
        "generated_at": datetime.now(),
        "action": action,
        "message": (
            "Daily Executive Brief "
            f"{action} successfully."
        ),
        "brief": stored_brief,
    }