from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError


GENERATED_AT = "2026-08-03T13:00:00"


SAMPLE_BRIEF = {
    "brief_id": 301,
    "brief_date": "2026-08-03",
    "brief_type": "Daily Executive Brief",
    "summary_text": (
        "The current operating snapshot contains 12 open business "
        "issues, including 4 high-priority issues. Three "
        "recommendations are awaiting management review."
    ),
    "brief_data": {
        "brief_version": 1,
        "generated_at": GENERATED_AT,
        "kpi_snapshot": {
            "total_kpis": 3,
            "kpis": [
                {
                    "kpi_key": "sales_growth",
                    "kpi_name": "Sales Growth",
                    "value": -6.81,
                    "display_value": "-6.81%",
                    "unit": "Percent",
                    "reference_period": "Latest Month",
                    "description": "Month-over-month sales growth.",
                    "calculated_at": GENERATED_AT,
                }
            ],
            "latest_store_target_achievement": [],
        },
        "issue_snapshot": {
            "open_issue_count": 12,
            "high_priority_open_issue_count": 4,
            "in_progress_issue_count": 2,
            "top_open_issues": [
                {
                    "issue_id": "ISSUE-SALES-S003-2026-06",
                    "title": "Significant sales decline at Store S003",
                    "issue_type": "Store Sales Decline",
                    "business_area": "Sales",
                    "priority_level": "High",
                    "priority_score": 91.50,
                    "priority_reason": "High financial impact.",
                    "status": "Open",
                    "entity_type": "Store",
                    "entity_id": "S003",
                    "summary": (
                        "Store S003 sales declined significantly."
                    ),
                    "evidence_count": 3,
                    "root_cause": {
                        "root_cause_category": (
                            "Demand and Operational Performance"
                        ),
                        "root_cause_summary": (
                            "Demand and operational weakness "
                            "reduced sales."
                        ),
                        "confidence_score": 88.50,
                        "review_status": "Pending Review",
                    },
                }
            ],
        },
        "recommendation_snapshot": {
            "total_recommendations": 8,
            "recommendations_needing_review": 3,
            "status_counts": {
                "Pending Review": 2,
                "Edited": 1,
                "Accepted": 2,
                "Rejected": 1,
                "Converted to Task": 2,
            },
            "top_recommendations": [],
        },
        "task_snapshot": {
            "total_tasks": 6,
            "active_task_count": 4,
            "blocked_task_count": 1,
            "overdue_task_count": 1,
            "status_counts": {
                "Unassigned": 0,
                "To Do": 2,
                "In Progress": 1,
                "Blocked": 1,
                "Completed": 2,
            },
            "overdue_tasks": [],
            "priority_tasks": [],
        },
        "management_attention": [
            "Review 4 high-priority open business issues.",
            "Complete management review for 3 recommendations.",
            "Resolve blockers affecting 1 tasks.",
            "Address 1 overdue tasks.",
        ],
    },
    "status": "Draft",
    "created_at": "2026-08-03T12:55:00",
    "updated_at": "2026-08-03T13:00:00",
}


def build_latest_response() -> dict[str, Any]:
    """Build a valid response for the latest brief endpoint."""

    return {
        "status": "success",
        "generated_at": GENERATED_AT,
        "brief": SAMPLE_BRIEF,
    }


def build_generate_response(
    action: str,
) -> dict[str, Any]:
    """Build a valid response for the brief generation endpoint."""

    return {
        "status": "success",
        "generated_at": GENERATED_AT,
        "action": action,
        "message": (
            f"Daily Executive Brief {action} successfully."
        ),
        "brief": SAMPLE_BRIEF,
    }


def test_latest_executive_brief_returns_stored_brief(
    client: Any,
    monkeypatch: Any,
) -> None:
    """The latest endpoint should return the newest stored brief."""

    def mock_get_latest_executive_brief() -> dict[str, Any]:
        return build_latest_response()

    monkeypatch.setattr(
        "backend.app.routers.executive_briefs."
        "get_latest_executive_brief",
        mock_get_latest_executive_brief,
    )

    response = client.get("/api/executive-brief/latest")

    assert response.status_code == 200

    response_data = response.json()
    brief = response_data["brief"]
    brief_data = brief["brief_data"]

    assert response_data["status"] == "success"
    assert response_data["generated_at"] == GENERATED_AT
    assert brief["brief_id"] == 301
    assert brief["brief_date"] == "2026-08-03"
    assert brief["brief_type"] == "Daily Executive Brief"
    assert brief["status"] == "Draft"

    assert brief_data["brief_version"] == 1
    assert brief_data["kpi_snapshot"]["total_kpis"] == 3

    assert (
        brief_data["issue_snapshot"][
            "high_priority_open_issue_count"
        ]
        == 4
    )

    assert (
        brief_data["recommendation_snapshot"][
            "recommendations_needing_review"
        ]
        == 3
    )

    assert (
        brief_data["task_snapshot"]["blocked_task_count"]
        == 1
    )

    assert len(
        brief_data["management_attention"]
    ) == 4


def test_latest_executive_brief_returns_404_when_missing(
    client: Any,
    monkeypatch: Any,
) -> None:
    """The endpoint should return 404 before any brief is stored."""

    def mock_get_latest_executive_brief() -> None:
        return None

    monkeypatch.setattr(
        "backend.app.routers.executive_briefs."
        "get_latest_executive_brief",
        mock_get_latest_executive_brief,
    )

    response = client.get("/api/executive-brief/latest")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "No Executive Brief has been generated yet."
    }


def test_latest_executive_brief_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A latest-brief database failure should return HTTP 503."""

    def raise_database_error() -> dict[str, Any]:
        raise SQLAlchemyError(
            "Simulated latest-brief database failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.executive_briefs."
        "get_latest_executive_brief",
        raise_database_error,
    )

    response = client.get("/api/executive-brief/latest")

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "The latest Executive Brief could not be loaded "
            "because the database operation failed."
        )
    }


@pytest.mark.parametrize(
    "exception_type",
    [
        pytest.param(
            KeyError,
            id="key-error",
        ),
        pytest.param(
            TypeError,
            id="type-error",
        ),
        pytest.param(
            ValueError,
            id="value-error",
        ),
    ],
)
def test_latest_executive_brief_returns_500_on_processing_failure(
    client: Any,
    monkeypatch: Any,
    exception_type: type[Exception],
) -> None:
    """Unexpected latest-brief processing failures should return 500."""

    def raise_processing_error() -> dict[str, Any]:
        raise exception_type(
            "Simulated latest-brief processing failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.executive_briefs."
        "get_latest_executive_brief",
        raise_processing_error,
    )

    response = client.get("/api/executive-brief/latest")

    assert response.status_code == 500
    assert response.json() == {
        "detail": (
            "The latest Executive Brief could not be processed."
        )
    }


@pytest.mark.parametrize(
    "action",
    [
        pytest.param(
            "created",
            id="created",
        ),
        pytest.param(
            "updated",
            id="updated",
        ),
    ],
)
def test_generate_executive_brief_returns_created_or_updated_brief(
    client: Any,
    monkeypatch: Any,
    action: str,
) -> None:
    """Generation should report whether today's brief was saved."""

    def mock_generate_daily_executive_brief() -> dict[str, Any]:
        return build_generate_response(action)

    monkeypatch.setattr(
        "backend.app.routers.executive_briefs."
        "generate_daily_executive_brief",
        mock_generate_daily_executive_brief,
    )

    response = client.post(
        "/api/executive-brief/generate"
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "success"
    assert response_data["generated_at"] == GENERATED_AT
    assert response_data["action"] == action

    assert response_data["message"] == (
        f"Daily Executive Brief {action} successfully."
    )

    assert response_data["brief"]["brief_id"] == 301

    assert (
        response_data["brief"]["brief_data"][
            "issue_snapshot"
        ]["open_issue_count"]
        == 12
    )


def test_generate_executive_brief_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A generation database failure should return HTTP 503."""

    def raise_database_error() -> dict[str, Any]:
        raise SQLAlchemyError(
            "Simulated brief-generation database failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.executive_briefs."
        "generate_daily_executive_brief",
        raise_database_error,
    )

    response = client.post(
        "/api/executive-brief/generate"
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "The Daily Executive Brief could not be generated "
            "because a database operation failed."
        )
    }


@pytest.mark.parametrize(
    "exception_type",
    [
        pytest.param(
            KeyError,
            id="key-error",
        ),
        pytest.param(
            TypeError,
            id="type-error",
        ),
        pytest.param(
            ValueError,
            id="value-error",
        ),
    ],
)
def test_generate_executive_brief_returns_500_on_processing_failure(
    client: Any,
    monkeypatch: Any,
    exception_type: type[Exception],
) -> None:
    """Unexpected generation failures should return HTTP 500."""

    def raise_processing_error() -> dict[str, Any]:
        raise exception_type(
            "Simulated brief-generation processing failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.executive_briefs."
        "generate_daily_executive_brief",
        raise_processing_error,
    )

    response = client.post(
        "/api/executive-brief/generate"
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": (
            "The Daily Executive Brief could not be generated "
            "from the current business data."
        )
    }