from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from typing import Any

from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.db.database import engine
from backend.app.services.n8n_client import (
    N8NClient,
    N8NClientConfigurationError,
    N8NClientError,
)


AUTOMATION_LOG_COLUMNS = """
    automation_log_id,
    task_id,
    issue_id,
    workflow_name,
    action_type,
    execution_status,
    idempotency_key,
    n8n_execution_id,
    attempt_count,
    http_status_code,
    message,
    error_type,
    error_message,
    request_metadata,
    executed_at
"""

TERMINAL_AUTOMATION_STATUSES = {
    "Succeeded",
    "Failed",
    "Skipped",
}


def _json_safe(
    value: Any,
) -> Any:
    if value is None or isinstance(
        value,
        (
            bool,
            int,
            float,
            str,
        ),
    ):
        return value

    if isinstance(
        value,
        Decimal,
    ):
        return float(
            value
        )

    if isinstance(
        value,
        (
            date,
            datetime,
        ),
    ):
        return value.isoformat()

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): _json_safe(
                nested_value
            )
            for key, nested_value in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        return [
            _json_safe(
                item
            )
            for item in value
        ]

    return str(
        value
    )


def _make_idempotency_key(
    *parts: object,
) -> str:
    normalized = "|".join(
        str(part)
        for part in parts
    )

    digest = hashlib.sha256(
        normalized.encode(
            "utf-8"
        )
    ).hexdigest()

    return f"automation-{digest}"


def _build_n8n_client() -> N8NClient:
    return N8NClient(
        base_url=settings.n8n_webhook_base_url,
        auth_token=settings.n8n_outbound_auth_token,
        timeout_seconds=settings.n8n_timeout_seconds,
        max_retries=settings.n8n_max_retries,
        retry_backoff_seconds=(
            settings.n8n_retry_backoff_seconds
        ),
    )


def get_automation_log_list(
    *,
    execution_status: str | None,
    action_type: str | None,
    workflow_name: str | None,
    task_id: int | None,
    issue_id: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Return filtered and paginated automation execution history."""

    count_query = text(
        """
        SELECT COUNT(*)
        FROM automation_logs
        WHERE
            (
                :execution_status IS NULL
                OR execution_status = :execution_status
            )
            AND (
                :action_type IS NULL
                OR action_type = :action_type
            )
            AND (
                :workflow_name IS NULL
                OR workflow_name = :workflow_name
            )
            AND (
                :task_id IS NULL
                OR task_id = :task_id
            )
            AND (
                :issue_id IS NULL
                OR issue_id = :issue_id
            );
        """
    )

    list_query = text(
        f"""
        SELECT
            {AUTOMATION_LOG_COLUMNS}
        FROM automation_logs
        WHERE
            (
                :execution_status IS NULL
                OR execution_status = :execution_status
            )
            AND (
                :action_type IS NULL
                OR action_type = :action_type
            )
            AND (
                :workflow_name IS NULL
                OR workflow_name = :workflow_name
            )
            AND (
                :task_id IS NULL
                OR task_id = :task_id
            )
            AND (
                :issue_id IS NULL
                OR issue_id = :issue_id
            )
        ORDER BY
            executed_at DESC,
            automation_log_id DESC
        LIMIT :limit
        OFFSET :offset;
        """
    )

    parameters = {
        "execution_status": execution_status,
        "action_type": action_type,
        "workflow_name": workflow_name,
        "task_id": task_id,
        "issue_id": issue_id,
        "limit": limit,
        "offset": offset,
    }

    with engine.connect() as connection:
        total_items = connection.execute(
            count_query,
            parameters,
        ).scalar_one()

        rows = connection.execute(
            list_query,
            parameters,
        ).mappings().all()

    return {
        "status": "success",
        "total_items": int(
            total_items
        ),
        "limit": limit,
        "offset": offset,
        "items": [
            dict(row)
            for row in rows
        ],
    }


def get_automation_log_detail(
    automation_log_id: int,
) -> dict[str, Any] | None:
    """Return one automation log."""

    query = text(
        f"""
        SELECT
            {AUTOMATION_LOG_COLUMNS}
        FROM automation_logs
        WHERE automation_log_id = :automation_log_id;
        """
    )

    with engine.connect() as connection:
        row = connection.execute(
            query,
            {
                "automation_log_id": automation_log_id,
            },
        ).mappings().one_or_none()

    if row is None:
        return None

    return {
        "status": "success",
        "automation_log": dict(
            row
        ),
    }


def _load_issue_for_alert(
    issue_id: str,
) -> dict[str, Any] | None:
    query = text(
        """
        SELECT
            issue_id,
            title,
            issue_type,
            business_area,
            priority_level,
            priority_score,
            priority_reason,
            status,
            store_id,
            product_id,
            vendor_id,
            summary,
            last_detected_at
        FROM issues
        WHERE issue_id = :issue_id;
        """
    )

    with engine.connect() as connection:
        row = connection.execute(
            query,
            {
                "issue_id": issue_id,
            },
        ).mappings().one_or_none()

    if row is None:
        return None

    return dict(
        row
    )


def _load_task_for_automation(
    task_id: int,
) -> dict[str, Any] | None:
    query = text(
        """
        SELECT
            t.task_id,
            t.issue_id,
            t.recommendation_id,
            t.title,
            t.description,
            t.assigned_to,
            t.assigned_role,
            t.due_date,
            t.priority_level,
            t.status,
            t.updated_at,
            i.title AS issue_title,
            i.business_area
        FROM tasks AS t
        LEFT JOIN issues AS i
            ON i.issue_id = t.issue_id
        WHERE t.task_id = :task_id;
        """
    )

    with engine.connect() as connection:
        row = connection.execute(
            query,
            {
                "task_id": task_id,
            },
        ).mappings().one_or_none()

    if row is None:
        return None

    return dict(
        row
    )


def _insert_pending_log(
    *,
    task_id: int | None,
    issue_id: str | None,
    workflow_name: str,
    action_type: str,
    idempotency_key: str,
    request_metadata: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    insert_query = text(
        f"""
        INSERT INTO automation_logs (
            task_id,
            issue_id,
            workflow_name,
            action_type,
            execution_status,
            idempotency_key,
            request_metadata
        )
        VALUES (
            :task_id,
            :issue_id,
            :workflow_name,
            :action_type,
            'Pending',
            :idempotency_key,
            CAST(:request_metadata AS JSONB)
        )
        ON CONFLICT (idempotency_key)
        DO NOTHING
        RETURNING
            {AUTOMATION_LOG_COLUMNS};
        """
    )

    existing_query = text(
        f"""
        SELECT
            {AUTOMATION_LOG_COLUMNS}
        FROM automation_logs
        WHERE idempotency_key = :idempotency_key;
        """
    )

    parameters = {
        "task_id": task_id,
        "issue_id": issue_id,
        "workflow_name": workflow_name,
        "action_type": action_type,
        "idempotency_key": idempotency_key,
        "request_metadata": json.dumps(
            _json_safe(
                request_metadata
            ),
            ensure_ascii=False,
        ),
    }

    with engine.begin() as connection:
        created = connection.execute(
            insert_query,
            parameters,
        ).mappings().one_or_none()

        if created is not None:
            return dict(
                created
            ), False

        existing = connection.execute(
            existing_query,
            {
                "idempotency_key": idempotency_key,
            },
        ).mappings().one()

    return dict(
        existing
    ), True


def _mark_triggered(
    *,
    automation_log_id: int,
    n8n_execution_id: str | None,
    attempt_count: int,
    http_status_code: int,
) -> dict[str, Any]:
    query = text(
        f"""
        UPDATE automation_logs
        SET
            execution_status = CASE
                WHEN execution_status = 'Pending' THEN 'Triggered'
                ELSE execution_status
            END,
            n8n_execution_id = COALESCE(
                :n8n_execution_id,
                n8n_execution_id
            ),
            attempt_count = GREATEST(
                attempt_count,
                :attempt_count
            ),
            http_status_code = :http_status_code,
            message = CASE
                WHEN execution_status = 'Pending'
                    THEN 'Workflow request accepted by n8n.'
                ELSE message
            END,
            error_type = CASE
                WHEN execution_status = 'Pending' THEN NULL
                ELSE error_type
            END,
            error_message = CASE
                WHEN execution_status = 'Pending' THEN NULL
                ELSE error_message
            END,
            executed_at = CURRENT_TIMESTAMP
        WHERE automation_log_id = :automation_log_id
        RETURNING
            {AUTOMATION_LOG_COLUMNS};
        """
    )

    with engine.begin() as connection:
        row = connection.execute(
            query,
            {
                "automation_log_id": automation_log_id,
                "n8n_execution_id": n8n_execution_id,
                "attempt_count": attempt_count,
                "http_status_code": http_status_code,
            },
        ).mappings().one()

    return dict(
        row
    )


def _mark_delivery_failed(
    *,
    automation_log_id: int,
    error: N8NClientError,
) -> dict[str, Any]:
    query = text(
        f"""
        UPDATE automation_logs
        SET
            execution_status = CASE
                WHEN execution_status IN ('Succeeded', 'Failed', 'Skipped')
                    THEN execution_status
                ELSE 'Failed'
            END,
            attempt_count = GREATEST(
                attempt_count,
                :attempt_count
            ),
            http_status_code = :http_status_code,
            message = CASE
                WHEN execution_status IN ('Succeeded', 'Failed', 'Skipped')
                    THEN message
                ELSE 'Workflow request could not be delivered to n8n.'
            END,
            error_type = CASE
                WHEN execution_status IN ('Succeeded', 'Failed', 'Skipped')
                    THEN error_type
                ELSE :error_type
            END,
            error_message = CASE
                WHEN execution_status IN ('Succeeded', 'Failed', 'Skipped')
                    THEN error_message
                ELSE :error_message
            END,
            executed_at = CURRENT_TIMESTAMP
        WHERE automation_log_id = :automation_log_id
        RETURNING
            {AUTOMATION_LOG_COLUMNS};
        """
    )

    with engine.begin() as connection:
        row = connection.execute(
            query,
            {
                "automation_log_id": automation_log_id,
                "attempt_count": max(
                    1,
                    error.attempts,
                ),
                "http_status_code": error.http_status_code,
                "error_type": error.error_type,
                "error_message": str(
                    error
                )[:4000],
            },
        ).mappings().one()

    return dict(
        row
    )


def _trigger(
    *,
    task_id: int | None,
    issue_id: str | None,
    workflow_name: str,
    action_type: str,
    webhook_path: str,
    idempotency_key: str,
    business_payload: dict[str, Any],
) -> dict[str, Any]:
    if not settings.automation_enabled:
        return {
            "outcome": "disabled",
        }

    try:
        client = _build_n8n_client()
    except N8NClientConfigurationError:
        return {
            "outcome": "not_configured",
        }

    safe_business_payload = _json_safe(
        business_payload
    )

    log_row, duplicate = _insert_pending_log(
        task_id=task_id,
        issue_id=issue_id,
        workflow_name=workflow_name,
        action_type=action_type,
        idempotency_key=idempotency_key,
        request_metadata={
            "source": "FastAPI",
            "payload_version": "v1",
        },
    )

    if duplicate:
        return {
            "outcome": "duplicate",
            "response": {
                "status": "success",
                "message": (
                    "An automation request with the same idempotency "
                    "key already exists; no duplicate workflow was sent."
                ),
                "duplicate": True,
                "automation_log": log_row,
            },
        }

    webhook_payload = {
        "event_type": action_type,
        "idempotency_key": idempotency_key,
        "automation_log_id": log_row[
            "automation_log_id"
        ],
        "data": safe_business_payload,
    }

    try:
        delivery = client.post_webhook(
            webhook_path=webhook_path,
            payload=webhook_payload,
            idempotency_key=idempotency_key,
        )
    except N8NClientError as error:
        failed_log = _mark_delivery_failed(
            automation_log_id=int(
                log_row[
                    "automation_log_id"
                ]
            ),
            error=error,
        )

        return {
            "outcome": "delivery_failed",
            "automation_log": failed_log,
        }

    triggered_log = _mark_triggered(
        automation_log_id=int(
            log_row[
                "automation_log_id"
            ]
        ),
        n8n_execution_id=(
            delivery.n8n_execution_id
        ),
        attempt_count=(
            delivery.attempt_count
        ),
        http_status_code=(
            delivery.http_status_code
        ),
    )

    return {
        "outcome": "success",
        "response": {
            "status": "success",
            "message": (
                "The workflow request was accepted by n8n."
            ),
            "duplicate": False,
            "automation_log": triggered_log,
        },
    }


def trigger_high_priority_alert(
    issue_id: str,
) -> dict[str, Any]:
    """Trigger a controlled high-priority issue alert."""

    issue = _load_issue_for_alert(
        issue_id
    )

    if issue is None:
        return {
            "outcome": "not_found",
        }

    if (
        issue["priority_level"] != "High"
        or issue["status"] not in {
            "Open",
            "In Progress",
        }
    ):
        return {
            "outcome": "invalid_state",
            "reason": (
                "Only active High-priority issues can trigger this "
                "workflow."
            ),
        }

    idempotency_key = _make_idempotency_key(
        "high-priority-alert",
        issue["issue_id"],
        issue["last_detected_at"],
    )

    return _trigger(
        task_id=None,
        issue_id=str(
            issue["issue_id"]
        ),
        workflow_name="High Priority Alert",
        action_type="high_priority_alert",
        webhook_path=(
            settings.n8n_high_priority_alert_path
        ),
        idempotency_key=idempotency_key,
        business_payload={
            "issue": issue,
        },
    )


def trigger_task_reminder(
    task_id: int,
) -> dict[str, Any]:
    """Trigger one daily reminder for an active task."""

    task = _load_task_for_automation(
        task_id
    )

    if task is None:
        return {
            "outcome": "not_found",
        }

    if task["status"] == "Completed":
        return {
            "outcome": "invalid_state",
            "reason": (
                "Completed tasks cannot receive reminders."
            ),
        }

    idempotency_key = _make_idempotency_key(
        "task-reminder",
        task["task_id"],
        date.today().isoformat(),
    )

    return _trigger(
        task_id=int(
            task["task_id"]
        ),
        issue_id=(
            str(task["issue_id"])
            if task["issue_id"] is not None
            else None
        ),
        workflow_name="Task Reminder",
        action_type="task_reminder",
        webhook_path=(
            settings.n8n_task_reminder_path
        ),
        idempotency_key=idempotency_key,
        business_payload={
            "task": task,
        },
    )


def trigger_overdue_escalation(
    task_id: int,
) -> dict[str, Any]:
    """Trigger one daily escalation for a currently overdue task."""

    task = _load_task_for_automation(
        task_id
    )

    if task is None:
        return {
            "outcome": "not_found",
        }

    due_date = task[
        "due_date"
    ]

    if (
        task["status"] == "Completed"
        or due_date is None
        or due_date >= date.today()
    ):
        return {
            "outcome": "invalid_state",
            "reason": (
                "Only incomplete tasks with a due date before today "
                "can be escalated."
            ),
        }

    idempotency_key = _make_idempotency_key(
        "overdue-escalation",
        task["task_id"],
        date.today().isoformat(),
    )

    return _trigger(
        task_id=int(
            task["task_id"]
        ),
        issue_id=(
            str(task["issue_id"])
            if task["issue_id"] is not None
            else None
        ),
        workflow_name="Overdue Task Escalation",
        action_type="overdue_escalation",
        webhook_path=(
            settings.n8n_overdue_escalation_path
        ),
        idempotency_key=idempotency_key,
        business_payload={
            "task": task,
        },
    )


def record_n8n_callback(
    *,
    idempotency_key: str,
    execution_status: str,
    n8n_execution_id: str | None,
    message: str | None,
    error_type: str | None,
    error_message: str | None,
) -> dict[str, Any]:
    """Apply one authenticated n8n execution callback idempotently."""

    lock_query = text(
        f"""
        SELECT
            {AUTOMATION_LOG_COLUMNS}
        FROM automation_logs
        WHERE idempotency_key = :idempotency_key
        FOR UPDATE;
        """
    )

    update_query = text(
        f"""
        UPDATE automation_logs
        SET
            execution_status = :execution_status,
            n8n_execution_id = COALESCE(
                :n8n_execution_id,
                n8n_execution_id
            ),
            message = :message,
            error_type = :error_type,
            error_message = :error_message,
            executed_at = CURRENT_TIMESTAMP
        WHERE automation_log_id = :automation_log_id
        RETURNING
            {AUTOMATION_LOG_COLUMNS};
        """
    )

    with engine.begin() as connection:
        current = connection.execute(
            lock_query,
            {
                "idempotency_key": idempotency_key,
            },
        ).mappings().one_or_none()

        if current is None:
            return {
                "outcome": "not_found",
            }

        current_status = str(
            current[
                "execution_status"
            ]
        )

        if current_status in TERMINAL_AUTOMATION_STATUSES:
            if current_status == execution_status:
                return {
                    "outcome": "duplicate",
                    "response": {
                        "status": "success",
                        "message": (
                            "The callback was already recorded; no "
                            "duplicate update was applied."
                        ),
                        "duplicate": True,
                        "automation_log": dict(
                            current
                        ),
                    },
                }

            return {
                "outcome": "conflict",
                "current_status": current_status,
            }

        normalized_error_type = (
            error_type
            if execution_status == "Failed"
            else None
        )
        normalized_error_message = (
            error_message
            if execution_status == "Failed"
            else None
        )

        updated = connection.execute(
            update_query,
            {
                "automation_log_id": current[
                    "automation_log_id"
                ],
                "execution_status": execution_status,
                "n8n_execution_id": n8n_execution_id,
                "message": message,
                "error_type": normalized_error_type,
                "error_message": normalized_error_message,
            },
        ).mappings().one()

    return {
        "outcome": "success",
        "response": {
            "status": "success",
            "message": (
                "The automation execution result was recorded."
            ),
            "duplicate": False,
            "automation_log": dict(
                updated
            ),
        },
    }
