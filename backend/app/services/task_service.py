from __future__ import annotations

from sqlalchemy import text

from backend.app.db.database import engine


TASK_LIST_COLUMNS = """
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
    i.title AS issue_title,
    r.recommendation_title,
    t.created_at,
    t.updated_at
"""


ALLOWED_TASK_TRANSITIONS = {
    "Unassigned": {
        "To Do",
    },
    "To Do": {
        "In Progress",
        "Blocked",
    },
    "In Progress": {
        "To Do",
        "Blocked",
        "Completed",
    },
    "Blocked": {
        "To Do",
        "In Progress",
    },
    "Completed": set(),
}


def convert_recommendation_to_task(
    recommendation_id: int,
) -> dict:
    """
    Convert one accepted recommendation into a task.

    The recommendation update, task creation, and audit logging
    are completed inside one PostgreSQL transaction.
    """

    recommendation_query = text(
        """
        SELECT
            r.recommendation_id,
            r.issue_id,
            r.recommendation_title,
            r.recommendation_text,
            r.suggested_owner_role,
            r.suggested_deadline,
            r.status AS recommendation_status,
            i.priority_level
        FROM recommendations AS r
        INNER JOIN issues AS i
            ON i.issue_id = r.issue_id
        WHERE r.recommendation_id = :recommendation_id
        FOR UPDATE OF r;
        """
    )

    existing_task_query = text(
        """
        SELECT task_id
        FROM tasks
        WHERE recommendation_id = :recommendation_id;
        """
    )

    create_task_query = text(
        """
        INSERT INTO tasks (
            issue_id,
            recommendation_id,
            title,
            description,
            assigned_to,
            assigned_role,
            due_date,
            priority_level,
            status
        )
        VALUES (
            :issue_id,
            :recommendation_id,
            :title,
            :description,
            NULL,
            :assigned_role,
            :due_date,
            :priority_level,
            'To Do'
        )
        RETURNING
            task_id,
            issue_id,
            recommendation_id,
            title,
            description,
            assigned_to,
            assigned_role,
            due_date,
            priority_level,
            status,
            created_at,
            updated_at;
        """
    )

    update_recommendation_query = text(
        """
        UPDATE recommendations
        SET
            status = 'Converted to Task',
            updated_at = CURRENT_TIMESTAMP
        WHERE recommendation_id = :recommendation_id;
        """
    )

    recommendation_audit_query = text(
        """
        INSERT INTO audit_logs (
            entity_type,
            entity_id,
            action_type,
            actor_name,
            old_value,
            new_value
        )
        VALUES (
            'Recommendation',
            CAST(:recommendation_id AS VARCHAR),
            'Converted to Task',
            'API User',
            jsonb_build_object(
                'status',
                :old_recommendation_status
            ),
            jsonb_build_object(
                'status',
                'Converted to Task',
                'task_id',
                :task_id
            )
        );
        """
    )

    task_audit_query = text(
        """
        INSERT INTO audit_logs (
            entity_type,
            entity_id,
            action_type,
            actor_name,
            old_value,
            new_value
        )
        VALUES (
            'Task',
            CAST(:task_id AS VARCHAR),
            'Created from Recommendation',
            'API User',
            NULL,
            jsonb_build_object(
                'task_id',
                :task_id,
                'recommendation_id',
                :recommendation_id,
                'status',
                'To Do',
                'title',
                :title
            )
        );
        """
    )

    parameters = {
        "recommendation_id": recommendation_id,
    }

    with engine.begin() as connection:
        recommendation = connection.execute(
            recommendation_query,
            parameters,
        ).mappings().one_or_none()

        if recommendation is None:
            return {
                "outcome": "not_found",
            }

        existing_task = connection.execute(
            existing_task_query,
            parameters,
        ).mappings().one_or_none()

        if existing_task is not None:
            return {
                "outcome": "already_converted",
                "task_id": int(existing_task["task_id"]),
                "current_status": str(
                    recommendation["recommendation_status"]
                ),
            }

        current_status = str(
            recommendation["recommendation_status"]
        )

        if current_status != "Accepted":
            return {
                "outcome": "invalid_status",
                "current_status": current_status,
            }

        task_parameters = {
            "issue_id": recommendation["issue_id"],
            "recommendation_id": recommendation_id,
            "title": recommendation["recommendation_title"],
            "description": recommendation["recommendation_text"],
            "assigned_role": recommendation[
                "suggested_owner_role"
            ],
            "due_date": recommendation["suggested_deadline"],
            "priority_level": recommendation["priority_level"],
        }

        task = connection.execute(
            create_task_query,
            task_parameters,
        ).mappings().one()

        task_data = dict(task)
        task_id = int(task_data["task_id"])

        connection.execute(
            update_recommendation_query,
            {
                "recommendation_id": recommendation_id,
            },
        )

        audit_parameters = {
            "recommendation_id": recommendation_id,
            "task_id": task_id,
            "title": recommendation["recommendation_title"],
            "old_recommendation_status": current_status,
        }

        connection.execute(
            recommendation_audit_query,
            audit_parameters,
        )

        connection.execute(
            task_audit_query,
            audit_parameters,
        )

    return {
        "outcome": "success",
        "response": {
            "status": "success",
            "message": (
                "Recommendation converted into a task successfully."
            ),
            "recommendation_status": "Converted to Task",
            "task": task_data,
        },
    }


def get_task_list(
    *,
    task_status: str | None,
    priority_level: str | None,
    assigned_role: str | None,
    limit: int,
    offset: int,
) -> dict:
    """Return filtered and paginated tasks."""

    count_query = text(
        """
        SELECT COUNT(*)
        FROM tasks AS t
        WHERE
            (
                :task_status IS NULL
                OR t.status = :task_status
            )
            AND (
                :priority_level IS NULL
                OR t.priority_level = :priority_level
            )
            AND (
                :assigned_role IS NULL
                OR t.assigned_role = :assigned_role
            );
        """
    )

    task_query = text(
        f"""
        SELECT
            {TASK_LIST_COLUMNS}
        FROM tasks AS t

        LEFT JOIN issues AS i
            ON i.issue_id = t.issue_id

        LEFT JOIN recommendations AS r
            ON r.recommendation_id = t.recommendation_id

        WHERE
            (
                :task_status IS NULL
                OR t.status = :task_status
            )
            AND (
                :priority_level IS NULL
                OR t.priority_level = :priority_level
            )
            AND (
                :assigned_role IS NULL
                OR t.assigned_role = :assigned_role
            )

        ORDER BY
            CASE t.status
                WHEN 'Blocked' THEN 1
                WHEN 'In Progress' THEN 2
                WHEN 'To Do' THEN 3
                WHEN 'Unassigned' THEN 4
                WHEN 'Completed' THEN 5
                ELSE 6
            END,
            CASE t.priority_level
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 4
            END,
            t.due_date ASC NULLS LAST,
            t.task_id

        LIMIT :limit
        OFFSET :offset;
        """
    )

    parameters = {
        "task_status": task_status,
        "priority_level": priority_level,
        "assigned_role": assigned_role,
        "limit": limit,
        "offset": offset,
    }

    with engine.connect() as connection:
        total_items = connection.execute(
            count_query,
            parameters,
        ).scalar_one()

        task_rows = connection.execute(
            task_query,
            parameters,
        ).mappings().all()

    return {
        "status": "success",
        "total_items": int(total_items),
        "limit": limit,
        "offset": offset,
        "items": [
            dict(task_row)
            for task_row in task_rows
        ],
    }


def get_task_detail(task_id: int) -> dict | None:
    """Return one task with linked issue and recommendation context."""

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

            i.title AS issue_title,
            i.issue_type,
            i.business_area,
            i.status AS issue_status,

            r.recommendation_title,
            r.status AS recommendation_status,

            t.created_at,
            t.updated_at

        FROM tasks AS t

        LEFT JOIN issues AS i
            ON i.issue_id = t.issue_id

        LEFT JOIN recommendations AS r
            ON r.recommendation_id = t.recommendation_id

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

    return {
        "status": "success",
        "task": dict(row),
    }


def update_task_status(
    task_id: int,
    target_status: str,
) -> dict:
    """Move one task to another valid Kanban status."""

    lock_query = text(
        """
        SELECT status
        FROM tasks
        WHERE task_id = :task_id
        FOR UPDATE;
        """
    )

    update_query = text(
        """
        UPDATE tasks
        SET
            status = :target_status,
            updated_at = CURRENT_TIMESTAMP
        WHERE task_id = :task_id;
        """
    )

    audit_query = text(
        """
        INSERT INTO audit_logs (
            entity_type,
            entity_id,
            action_type,
            actor_name,
            old_value,
            new_value
        )
        VALUES (
            'Task',
            CAST(:task_id AS VARCHAR),
            'Status Updated',
            'API User',
            jsonb_build_object(
                'status',
                :current_status
            ),
            jsonb_build_object(
                'status',
                :target_status
            )
        );
        """
    )

    with engine.begin() as connection:
        task_row = connection.execute(
            lock_query,
            {
                "task_id": task_id,
            },
        ).mappings().one_or_none()

        if task_row is None:
            return {
                "outcome": "not_found",
            }

        current_status = str(task_row["status"])

        if current_status == target_status:
            return {
                "outcome": "no_change",
                "current_status": current_status,
            }

        allowed_statuses = ALLOWED_TASK_TRANSITIONS.get(
            current_status,
            set(),
        )

        if target_status not in allowed_statuses:
            return {
                "outcome": "invalid_transition",
                "current_status": current_status,
                "target_status": target_status,
                "allowed_statuses": sorted(allowed_statuses),
            }

        parameters = {
            "task_id": task_id,
            "current_status": current_status,
            "target_status": target_status,
        }

        connection.execute(
            update_query,
            parameters,
        )

        connection.execute(
            audit_query,
            parameters,
        )

    updated_task = get_task_detail(task_id)

    if updated_task is None:
        return {
            "outcome": "not_found",
        }

    return {
        "outcome": "success",
        "response": {
            "status": "success",
            "message": (
                f"Task status changed from '{current_status}' "
                f"to '{target_status}'."
            ),
            "task": updated_task["task"],
        },
    }