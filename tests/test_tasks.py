from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError


SAMPLE_TASK_ITEM = {
    "task_id": 201,
    "issue_id": "ISSUE-SALES-S003-2026-06",
    "recommendation_id": 101,
    "title": "Review the sales recovery plan for Store S003",
    "description": (
        "Review category performance and implement a focused "
        "store-level sales recovery plan."
    ),
    "assigned_to": None,
    "assigned_role": "Regional Sales Manager",
    "due_date": "2026-08-15",
    "priority_level": "High",
    "status": "To Do",
    "issue_title": "Significant sales decline at Store S003",
    "recommendation_title": (
        "Review the sales recovery plan for Store S003"
    ),
    "created_at": "2026-08-03T10:00:00",
    "updated_at": "2026-08-03T10:00:00",
}


def build_task_detail(
    *,
    task_status: str = "To Do",
    assigned_to: str | None = None,
    assigned_role: str | None = "Regional Sales Manager",
) -> dict[str, Any]:
    """Build one valid task-detail record."""

    return {
        **SAMPLE_TASK_ITEM,
        "status": task_status,
        "assigned_to": assigned_to,
        "assigned_role": assigned_role,
        "issue_type": "Store Sales Decline",
        "business_area": "Sales",
        "issue_status": "Open",
        "recommendation_status": "Converted to Task",
        "updated_at": "2026-08-03T10:30:00",
    }


def test_convert_recommendation_to_task_returns_created_task(
    client: Any,
    monkeypatch: Any,
) -> None:
    """An accepted recommendation should become a task."""

    def mock_convert_recommendation_to_task(
        recommendation_id: int,
    ) -> dict[str, Any]:
        assert recommendation_id == 101

        return {
            "outcome": "success",
            "response": {
                "status": "success",
                "message": (
                    "Recommendation converted into a task "
                    "successfully."
                ),
                "recommendation_status": "Converted to Task",
                "task": SAMPLE_TASK_ITEM,
            },
        }

    monkeypatch.setattr(
        "backend.app.routers.tasks."
        "convert_recommendation_to_task",
        mock_convert_recommendation_to_task,
    )

    response = client.post(
        "/api/recommendations/101/convert-to-task"
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["status"] == "success"
    assert (
        response_data["recommendation_status"]
        == "Converted to Task"
    )
    assert response_data["task"]["task_id"] == 201
    assert response_data["task"]["status"] == "To Do"
    assert response_data["task"]["priority_level"] == "High"


def test_convert_recommendation_to_task_returns_404_when_missing(
    client: Any,
    monkeypatch: Any,
) -> None:
    """An unknown recommendation should return 404."""

    def mock_convert_recommendation_to_task(
        recommendation_id: int,
    ) -> dict[str, str]:
        assert recommendation_id == 999

        return {"outcome": "not_found"}

    monkeypatch.setattr(
        "backend.app.routers.tasks."
        "convert_recommendation_to_task",
        mock_convert_recommendation_to_task,
    )

    response = client.post(
        "/api/recommendations/999/convert-to-task"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "The requested recommendation was not found."
    }


def test_convert_recommendation_to_task_rejects_invalid_status(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Only accepted recommendations may be converted."""

    def mock_convert_recommendation_to_task(
        recommendation_id: int,
    ) -> dict[str, str]:
        assert recommendation_id == 101

        return {
            "outcome": "invalid_status",
            "current_status": "Pending Review",
        }

    monkeypatch.setattr(
        "backend.app.routers.tasks."
        "convert_recommendation_to_task",
        mock_convert_recommendation_to_task,
    )

    response = client.post(
        "/api/recommendations/101/convert-to-task"
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "Only an Accepted recommendation can be converted "
            "into a task. The current status is "
            "'Pending Review'."
        )
    }


def test_convert_recommendation_to_task_prevents_duplicate_task(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A recommendation should not create more than one task."""

    def mock_convert_recommendation_to_task(
        recommendation_id: int,
    ) -> dict[str, Any]:
        assert recommendation_id == 101

        return {
            "outcome": "already_converted",
            "task_id": 201,
            "current_status": "Converted to Task",
        }

    monkeypatch.setattr(
        "backend.app.routers.tasks."
        "convert_recommendation_to_task",
        mock_convert_recommendation_to_task,
    )

    response = client.post(
        "/api/recommendations/101/convert-to-task"
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "This recommendation has already been converted "
            "into task 201."
        )
    }


def test_convert_recommendation_to_task_rejects_invalid_identifier(
    client: Any,
) -> None:
    """Recommendation identifiers must be positive integers."""

    response = client.post(
        "/api/recommendations/0/convert-to-task"
    )

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        "recommendation_id" in error["loc"]
        for error in error_details
    )


def test_convert_recommendation_to_task_returns_503_on_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A conversion database failure should return 503."""

    def raise_database_error(
        recommendation_id: int,
    ) -> dict[str, Any]:
        del recommendation_id

        raise SQLAlchemyError(
            "Simulated task-conversion failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.tasks."
        "convert_recommendation_to_task",
        raise_database_error,
    )

    response = client.post(
        "/api/recommendations/101/convert-to-task"
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "The task could not be created because the "
            "database operation failed."
        )
    }


def test_list_tasks_returns_paginated_response(
    client: Any,
    monkeypatch: Any,
) -> None:
    """The task-list endpoint should return valid paginated data."""

    def mock_get_task_list(
        *,
        task_status: str | None,
        priority_level: str | None,
        assigned_role: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        assert task_status is None
        assert priority_level is None
        assert assigned_role is None
        assert limit == 20
        assert offset == 0

        return {
            "status": "success",
            "total_items": 1,
            "limit": 20,
            "offset": 0,
            "items": [SAMPLE_TASK_ITEM],
        }

    monkeypatch.setattr(
        "backend.app.routers.tasks.get_task_list",
        mock_get_task_list,
    )

    response = client.get("/api/tasks")

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "success"
    assert response_data["total_items"] == 1
    assert response_data["limit"] == 20
    assert response_data["offset"] == 0
    assert len(response_data["items"]) == 1
    assert response_data["items"][0]["task_id"] == 201
    assert response_data["items"][0]["status"] == "To Do"


def test_list_tasks_forwards_filters_and_pagination(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Task filters and pagination should reach the service."""

    captured_parameters: dict[str, Any] = {}

    def mock_get_task_list(
        *,
        task_status: str | None,
        priority_level: str | None,
        assigned_role: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        captured_parameters.update(
            {
                "task_status": task_status,
                "priority_level": priority_level,
                "assigned_role": assigned_role,
                "limit": limit,
                "offset": offset,
            }
        )

        return {
            "status": "success",
            "total_items": 1,
            "limit": limit,
            "offset": offset,
            "items": [SAMPLE_TASK_ITEM],
        }

    monkeypatch.setattr(
        "backend.app.routers.tasks.get_task_list",
        mock_get_task_list,
    )

    response = client.get(
        "/api/tasks",
        params={
            "status": "To Do",
            "priority": "High",
            "assigned_role": "Regional Sales Manager",
            "limit": 10,
            "offset": 5,
        },
    )

    assert response.status_code == 200

    assert captured_parameters == {
        "task_status": "To Do",
        "priority_level": "High",
        "assigned_role": "Regional Sales Manager",
        "limit": 10,
        "offset": 5,
    }


def test_list_tasks_accepts_empty_result(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A valid search with no task matches should return an empty list."""

    def mock_get_task_list(
        *,
        task_status: str | None,
        priority_level: str | None,
        assigned_role: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        del task_status
        del priority_level
        del assigned_role

        return {
            "status": "success",
            "total_items": 0,
            "limit": limit,
            "offset": offset,
            "items": [],
        }

    monkeypatch.setattr(
        "backend.app.routers.tasks.get_task_list",
        mock_get_task_list,
    )

    response = client.get(
        "/api/tasks",
        params={"status": "Completed"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "total_items": 0,
        "limit": 20,
        "offset": 0,
        "items": [],
    }


@pytest.mark.parametrize(
    ("query_parameters", "invalid_field"),
    [
        ({"status": "Pending"}, "status"),
        ({"priority": "Critical"}, "priority"),
        ({"assigned_role": ""}, "assigned_role"),
        ({"limit": 0}, "limit"),
        ({"limit": 101}, "limit"),
        ({"offset": -1}, "offset"),
    ],
)
def test_list_tasks_rejects_invalid_parameters(
    client: Any,
    query_parameters: dict[str, Any],
    invalid_field: str,
) -> None:
    """Invalid task filters and pagination should return 422."""

    response = client.get(
        "/api/tasks",
        params=query_parameters,
    )

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        invalid_field in error["loc"]
        for error in error_details
    )


def test_list_tasks_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A task-list database failure should return 503."""

    def raise_database_error(
        **_: Any,
    ) -> dict[str, Any]:
        raise SQLAlchemyError(
            "Simulated task-list failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.tasks.get_task_list",
        raise_database_error,
    )

    response = client.get("/api/tasks")

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "Tasks could not be loaded because the "
            "database operation failed."
        )
    }


def test_get_task_detail_returns_linked_context(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Task details should include issue and recommendation context."""

    def mock_get_task_detail(
        task_id: int,
    ) -> dict[str, Any]:
        assert task_id == 201

        return {
            "status": "success",
            "task": build_task_detail(),
        }

    monkeypatch.setattr(
        "backend.app.routers.tasks.get_task_detail",
        mock_get_task_detail,
    )

    response = client.get("/api/tasks/201")

    assert response.status_code == 200

    task = response.json()["task"]

    assert task["task_id"] == 201
    assert task["business_area"] == "Sales"
    assert task["issue_status"] == "Open"
    assert task["recommendation_status"] == "Converted to Task"


def test_get_task_detail_returns_404_when_missing(
    client: Any,
    monkeypatch: Any,
) -> None:
    """An unknown task should return 404."""

    def mock_get_task_detail(
        task_id: int,
    ) -> None:
        assert task_id == 999

        return None

    monkeypatch.setattr(
        "backend.app.routers.tasks.get_task_detail",
        mock_get_task_detail,
    )

    response = client.get("/api/tasks/999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "The requested task was not found."
    }


def test_get_task_detail_rejects_invalid_identifier(
    client: Any,
) -> None:
    """Task identifiers must be positive integers."""

    response = client.get("/api/tasks/0")

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        "task_id" in error["loc"]
        for error in error_details
    )


def test_get_task_detail_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A task-detail database failure should return 503."""

    def raise_database_error(
        task_id: int,
    ) -> dict[str, Any]:
        del task_id

        raise SQLAlchemyError(
            "Simulated task-detail failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.tasks.get_task_detail",
        raise_database_error,
    )

    response = client.get("/api/tasks/201")

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "The task could not be loaded because the "
            "database operation failed."
        )
    }


def test_change_task_status_updates_valid_transition(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A valid Kanban transition should update the task."""

    captured_parameters: dict[str, Any] = {}

    def mock_update_task_status(
        *,
        task_id: int,
        target_status: str,
    ) -> dict[str, Any]:
        captured_parameters.update(
            {
                "task_id": task_id,
                "target_status": target_status,
            }
        )

        return {
            "outcome": "success",
            "response": {
                "status": "success",
                "message": (
                    "Task status changed from 'To Do' "
                    "to 'In Progress'."
                ),
                "task": build_task_detail(
                    task_status="In Progress"
                ),
            },
        }

    monkeypatch.setattr(
        "backend.app.routers.tasks.update_task_status",
        mock_update_task_status,
    )

    response = client.patch(
        "/api/tasks/201/status",
        json={"status": "In Progress"},
    )

    assert response.status_code == 200

    assert captured_parameters == {
        "task_id": 201,
        "target_status": "In Progress",
    }
    assert response.json()["task"]["status"] == "In Progress"


def test_change_task_status_returns_404_when_missing(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Changing an unknown task should return 404."""

    def mock_update_task_status(
        *,
        task_id: int,
        target_status: str,
    ) -> dict[str, str]:
        del task_id
        del target_status

        return {"outcome": "not_found"}

    monkeypatch.setattr(
        "backend.app.routers.tasks.update_task_status",
        mock_update_task_status,
    )

    response = client.patch(
        "/api/tasks/999/status",
        json={"status": "In Progress"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "The requested task was not found."
    }


def test_change_task_status_returns_409_when_unchanged(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Requesting the current status should return a conflict."""

    def mock_update_task_status(
        *,
        task_id: int,
        target_status: str,
    ) -> dict[str, str]:
        del task_id
        del target_status

        return {
            "outcome": "no_change",
            "current_status": "To Do",
        }

    monkeypatch.setattr(
        "backend.app.routers.tasks.update_task_status",
        mock_update_task_status,
    )

    response = client.patch(
        "/api/tasks/201/status",
        json={"status": "To Do"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "The task is already in status 'To Do'."
    }


def test_change_task_status_rejects_invalid_transition(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A disallowed Kanban transition should return a conflict."""

    def mock_update_task_status(
        *,
        task_id: int,
        target_status: str,
    ) -> dict[str, Any]:
        del task_id
        del target_status

        return {
            "outcome": "invalid_transition",
            "current_status": "To Do",
            "target_status": "Completed",
            "allowed_statuses": ["Blocked", "In Progress"],
        }

    monkeypatch.setattr(
        "backend.app.routers.tasks.update_task_status",
        mock_update_task_status,
    )

    response = client.patch(
        "/api/tasks/201/status",
        json={"status": "Completed"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "The task cannot move from 'To Do' to 'Completed'. "
            "Allowed next statuses: Blocked, In Progress."
        )
    }


def test_change_completed_task_reports_no_allowed_statuses(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Completed tasks should report that no next status is allowed."""

    def mock_update_task_status(
        *,
        task_id: int,
        target_status: str,
    ) -> dict[str, Any]:
        del task_id
        del target_status

        return {
            "outcome": "invalid_transition",
            "current_status": "Completed",
            "target_status": "To Do",
            "allowed_statuses": [],
        }

    monkeypatch.setattr(
        "backend.app.routers.tasks.update_task_status",
        mock_update_task_status,
    )

    response = client.patch(
        "/api/tasks/201/status",
        json={"status": "To Do"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "The task cannot move from 'Completed' to 'To Do'. "
            "Allowed next statuses: none."
        )
    }


@pytest.mark.parametrize(
    "request_payload",
    [
        {"status": "Pending"},
        {},
    ],
)
def test_change_task_status_validates_request_body(
    client: Any,
    request_payload: dict[str, Any],
) -> None:
    """Missing or unsupported task statuses should return 422."""

    response = client.patch(
        "/api/tasks/201/status",
        json=request_payload,
    )

    assert response.status_code == 422


def test_change_task_status_rejects_invalid_identifier(
    client: Any,
) -> None:
    """The status endpoint requires a positive task ID."""

    response = client.patch(
        "/api/tasks/0/status",
        json={"status": "To Do"},
    )

    assert response.status_code == 422


def test_change_task_status_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A status-update database failure should return 503."""

    def raise_database_error(
        **_: Any,
    ) -> dict[str, Any]:
        raise SQLAlchemyError(
            "Simulated task-status failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.tasks.update_task_status",
        raise_database_error,
    )

    response = client.patch(
        "/api/tasks/201/status",
        json={"status": "In Progress"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "The task status could not be changed because "
            "the database operation failed."
        )
    }


def test_assign_task_updates_employee_and_role(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Assignment data should be stripped and sent to the service."""

    captured_parameters: dict[str, Any] = {}

    def mock_assign_task(
        *,
        task_id: int,
        assigned_to: str,
        assigned_role: str | None,
    ) -> dict[str, Any]:
        captured_parameters.update(
            {
                "task_id": task_id,
                "assigned_to": assigned_to,
                "assigned_role": assigned_role,
            }
        )

        return {
            "outcome": "success",
            "response": {
                "status": "success",
                "message": (
                    "Task assigned to 'EMP003' successfully."
                ),
                "task": build_task_detail(
                    assigned_to="EMP003",
                    assigned_role="Store Manager",
                ),
            },
        }

    monkeypatch.setattr(
        "backend.app.routers.tasks.assign_task",
        mock_assign_task,
    )

    response = client.patch(
        "/api/tasks/201/assignment",
        json={
            "assigned_to": "  EMP003  ",
            "assigned_role": "  Store Manager  ",
        },
    )

    assert response.status_code == 200

    assert captured_parameters == {
        "task_id": 201,
        "assigned_to": "EMP003",
        "assigned_role": "Store Manager",
    }
    assert response.json()["task"]["assigned_to"] == "EMP003"
    assert response.json()["task"]["assigned_role"] == "Store Manager"


def test_assign_task_allows_omitted_role(
    client: Any,
    monkeypatch: Any,
) -> None:
    """The assigned role may be omitted during reassignment."""

    captured_parameters: dict[str, Any] = {}

    def mock_assign_task(
        *,
        task_id: int,
        assigned_to: str,
        assigned_role: str | None,
    ) -> dict[str, Any]:
        captured_parameters.update(
            {
                "task_id": task_id,
                "assigned_to": assigned_to,
                "assigned_role": assigned_role,
            }
        )

        return {
            "outcome": "success",
            "response": {
                "status": "success",
                "message": (
                    "Task assigned to 'EMP004' successfully."
                ),
                "task": build_task_detail(
                    assigned_to="EMP004"
                ),
            },
        }

    monkeypatch.setattr(
        "backend.app.routers.tasks.assign_task",
        mock_assign_task,
    )

    response = client.patch(
        "/api/tasks/201/assignment",
        json={"assigned_to": "EMP004"},
    )

    assert response.status_code == 200

    assert captured_parameters == {
        "task_id": 201,
        "assigned_to": "EMP004",
        "assigned_role": None,
    }


def test_assign_task_returns_404_when_missing(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Assigning an unknown task should return 404."""

    def mock_assign_task(
        *,
        task_id: int,
        assigned_to: str,
        assigned_role: str | None,
    ) -> dict[str, str]:
        del task_id
        del assigned_to
        del assigned_role

        return {"outcome": "not_found"}

    monkeypatch.setattr(
        "backend.app.routers.tasks.assign_task",
        mock_assign_task,
    )

    response = client.patch(
        "/api/tasks/999/assignment",
        json={"assigned_to": "EMP003"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "The requested task was not found."
    }


def test_assign_task_rejects_completed_task(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A completed task cannot be assigned again."""

    def mock_assign_task(
        *,
        task_id: int,
        assigned_to: str,
        assigned_role: str | None,
    ) -> dict[str, str]:
        del task_id
        del assigned_to
        del assigned_role

        return {"outcome": "completed"}

    monkeypatch.setattr(
        "backend.app.routers.tasks.assign_task",
        mock_assign_task,
    )

    response = client.patch(
        "/api/tasks/201/assignment",
        json={"assigned_to": "EMP003"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "A completed task cannot be assigned or reassigned."
        )
    }


@pytest.mark.parametrize(
    ("request_payload", "invalid_field"),
    [
        (
            {},
            "assigned_to",
        ),
        (
            {"assigned_to": "A"},
            "assigned_to",
        ),
        (
            {
                "assigned_to": "EMP003",
                "assigned_role": "A",
            },
            "assigned_role",
        ),
    ],
)
def test_assign_task_validates_request_body(
    client: Any,
    request_payload: dict[str, Any],
    invalid_field: str,
) -> None:
    """Invalid assignment fields should return 422."""

    response = client.patch(
        "/api/tasks/201/assignment",
        json=request_payload,
    )

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        invalid_field in error["loc"]
        for error in error_details
    )


def test_assign_task_rejects_invalid_identifier(
    client: Any,
) -> None:
    """The assignment endpoint requires a positive task ID."""

    response = client.patch(
        "/api/tasks/0/assignment",
        json={"assigned_to": "EMP003"},
    )

    assert response.status_code == 422


def test_assign_task_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    """An assignment database failure should return 503."""

    def raise_database_error(
        **_: Any,
    ) -> dict[str, Any]:
        raise SQLAlchemyError(
            "Simulated task-assignment failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.tasks.assign_task",
        raise_database_error,
    )

    response = client.patch(
        "/api/tasks/201/assignment",
        json={"assigned_to": "EMP003"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "The task could not be assigned because the "
            "database operation failed."
        )
    }