from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError


SAMPLE_RECOMMENDATION_ITEM = {
    "recommendation_id": 101,
    "issue_id": "ISSUE-SALES-S003-2026-06",
    "recommendation_title": (
        "Review the sales recovery plan for Store S003"
    ),
    "suggested_owner_role": "Regional Sales Manager",
    "suggested_deadline": "2026-08-15",
    "expected_impact": (
        "Improve sales performance and target achievement."
    ),
    "confidence_score": 88.50,
    "status": "Pending Review",
    "issue_title": "Significant sales decline at Store S003",
    "business_area": "Sales",
    "priority_level": "High",
    "priority_score": 91.50,
    "created_at": "2026-08-03T09:00:00",
    "updated_at": "2026-08-03T09:30:00",
}


SAMPLE_RECOMMENDATION_DETAIL = {
    "recommendation_id": 101,
    "issue_id": "ISSUE-SALES-S003-2026-06",
    "recommendation_title": (
        "Review the sales recovery plan for Store S003"
    ),
    "recommendation_text": (
        "Review the store-level sales decline, identify the "
        "underperforming categories, and implement a focused "
        "sales recovery plan."
    ),
    "suggested_owner_role": "Regional Sales Manager",
    "suggested_deadline": "2026-08-15",
    "expected_impact": (
        "Improve sales performance and target achievement."
    ),
    "confidence_score": 88.50,
    "status": "Pending Review",
    "issue_title": "Significant sales decline at Store S003",
    "issue_type": "Store Sales Decline",
    "business_area": "Sales",
    "priority_level": "High",
    "priority_score": 91.50,
    "issue_status": "Open",
    "root_cause_category": (
        "Demand and Operational Performance"
    ),
    "root_cause_summary": (
        "Reduced demand and operational issues contributed "
        "to the sales decline."
    ),
    "root_cause_explanation": (
        "Sales performance, target achievement, and related "
        "operational evidence indicate a store-level decline."
    ),
    "root_cause_confidence": 88.50,
    "root_cause_review_status": "Pending Review",
    "created_at": "2026-08-03T09:00:00",
    "updated_at": "2026-08-03T09:30:00",
}


def build_detail_response(
    *,
    recommendation_status: str = "Pending Review",
    recommendation_title: str | None = None,
    recommendation_text: str | None = None,
    suggested_owner_role: str | None = None,
    suggested_deadline: str | None = None,
    expected_impact: str | None = None,
) -> dict[str, Any]:
    """Build a valid recommendation-detail service response."""

    recommendation = {
        **SAMPLE_RECOMMENDATION_DETAIL,
        "status": recommendation_status,
    }

    if recommendation_title is not None:
        recommendation["recommendation_title"] = (
            recommendation_title
        )

    if recommendation_text is not None:
        recommendation["recommendation_text"] = (
            recommendation_text
        )

    if suggested_owner_role is not None:
        recommendation["suggested_owner_role"] = (
            suggested_owner_role
        )

    if suggested_deadline is not None:
        recommendation["suggested_deadline"] = (
            suggested_deadline
        )

    if expected_impact is not None:
        recommendation["expected_impact"] = expected_impact

    return {
        "status": "success",
        "recommendation": recommendation,
    }


def test_list_recommendations_returns_paginated_response(
    client: Any,
    monkeypatch: Any,
) -> None:
    """The list endpoint should return valid recommendation data."""

    def mock_get_recommendation_list(
        *,
        recommendation_status: str | None,
        owner_role: str | None,
        business_area: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        assert recommendation_status is None
        assert owner_role is None
        assert business_area is None
        assert limit == 20
        assert offset == 0

        return {
            "status": "success",
            "total_items": 1,
            "limit": 20,
            "offset": 0,
            "items": [SAMPLE_RECOMMENDATION_ITEM],
        }

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "get_recommendation_list",
        mock_get_recommendation_list,
    )

    response = client.get("/api/recommendations")

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "success"
    assert response_data["total_items"] == 1
    assert response_data["limit"] == 20
    assert response_data["offset"] == 0
    assert len(response_data["items"]) == 1

    recommendation = response_data["items"][0]

    assert recommendation["recommendation_id"] == 101
    assert (
        recommendation["issue_id"]
        == "ISSUE-SALES-S003-2026-06"
    )
    assert recommendation["business_area"] == "Sales"
    assert recommendation["priority_level"] == "High"
    assert recommendation["status"] == "Pending Review"


def test_list_recommendations_forwards_filters_and_pagination(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Filters and pagination should reach the service correctly."""

    captured_parameters: dict[str, Any] = {}

    def mock_get_recommendation_list(
        *,
        recommendation_status: str | None,
        owner_role: str | None,
        business_area: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        captured_parameters.update(
            {
                "recommendation_status": recommendation_status,
                "owner_role": owner_role,
                "business_area": business_area,
                "limit": limit,
                "offset": offset,
            }
        )

        return {
            "status": "success",
            "total_items": 1,
            "limit": limit,
            "offset": offset,
            "items": [SAMPLE_RECOMMENDATION_ITEM],
        }

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "get_recommendation_list",
        mock_get_recommendation_list,
    )

    response = client.get(
        "/api/recommendations",
        params={
            "status": "Pending Review",
            "owner_role": "Regional Sales Manager",
            "business_area": "Sales",
            "limit": 10,
            "offset": 5,
        },
    )

    assert response.status_code == 200

    assert captured_parameters == {
        "recommendation_status": "Pending Review",
        "owner_role": "Regional Sales Manager",
        "business_area": "Sales",
        "limit": 10,
        "offset": 5,
    }

    response_data = response.json()

    assert response_data["limit"] == 10
    assert response_data["offset"] == 5


def test_list_recommendations_accepts_empty_result(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A valid query with no matches should return an empty list."""

    def mock_get_recommendation_list(
        *,
        recommendation_status: str | None,
        owner_role: str | None,
        business_area: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        del recommendation_status
        del owner_role
        del business_area

        return {
            "status": "success",
            "total_items": 0,
            "limit": limit,
            "offset": offset,
            "items": [],
        }

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "get_recommendation_list",
        mock_get_recommendation_list,
    )

    response = client.get(
        "/api/recommendations",
        params={"status": "Rejected"},
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
        (
            {"status": "Unknown"},
            "status",
        ),
        (
            {"owner_role": ""},
            "owner_role",
        ),
        (
            {"business_area": ""},
            "business_area",
        ),
        (
            {"limit": 0},
            "limit",
        ),
        (
            {"limit": 101},
            "limit",
        ),
        (
            {"offset": -1},
            "offset",
        ),
    ],
)
def test_list_recommendations_rejects_invalid_parameters(
    client: Any,
    query_parameters: dict[str, Any],
    invalid_field: str,
) -> None:
    """Invalid list parameters should return HTTP 422."""

    response = client.get(
        "/api/recommendations",
        params=query_parameters,
    )

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        invalid_field in error["loc"]
        for error in error_details
    )


def test_list_recommendations_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A list database failure should return a controlled 503."""

    def raise_database_error(
        **_: Any,
    ) -> dict[str, Any]:
        raise SQLAlchemyError(
            "Simulated recommendation-list failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "get_recommendation_list",
        raise_database_error,
    )

    response = client.get("/api/recommendations")

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "Recommendations could not be loaded because "
            "the database is unavailable."
        )
    }


def test_get_recommendation_detail_returns_context(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Recommendation details should include supporting context."""

    def mock_get_recommendation_detail(
        recommendation_id: int,
    ) -> dict[str, Any]:
        assert recommendation_id == 101

        return build_detail_response()

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "get_recommendation_detail",
        mock_get_recommendation_detail,
    )

    response = client.get("/api/recommendations/101")

    assert response.status_code == 200

    response_data = response.json()
    recommendation = response_data["recommendation"]

    assert response_data["status"] == "success"
    assert recommendation["recommendation_id"] == 101
    assert recommendation["business_area"] == "Sales"
    assert recommendation["priority_level"] == "High"
    assert recommendation["issue_status"] == "Open"
    assert (
        recommendation["root_cause_category"]
        == "Demand and Operational Performance"
    )
    assert recommendation["root_cause_confidence"] == 88.50


def test_get_recommendation_returns_404_when_not_found(
    client: Any,
    monkeypatch: Any,
) -> None:
    """An unknown recommendation should return HTTP 404."""

    def mock_get_recommendation_detail(
        recommendation_id: int,
    ) -> None:
        assert recommendation_id == 999

        return None

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "get_recommendation_detail",
        mock_get_recommendation_detail,
    )

    response = client.get("/api/recommendations/999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": (
            "The requested recommendation was not found."
        )
    }


def test_get_recommendation_rejects_invalid_identifier(
    client: Any,
) -> None:
    """Recommendation identifiers must be positive integers."""

    response = client.get("/api/recommendations/0")

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        "recommendation_id" in error["loc"]
        for error in error_details
    )


def test_get_recommendation_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A detail database failure should return HTTP 503."""

    def raise_database_error(
        recommendation_id: int,
    ) -> dict[str, Any]:
        del recommendation_id

        raise SQLAlchemyError(
            "Simulated recommendation-detail failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "get_recommendation_detail",
        raise_database_error,
    )

    response = client.get("/api/recommendations/101")

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "The recommendation could not be loaded because "
            "the database is unavailable."
        )
    }


@pytest.mark.parametrize(
    ("action", "target_status"),
    [
        ("accept", "Accepted"),
        ("reject", "Rejected"),
    ],
)
def test_accept_and_reject_recommendation(
    client: Any,
    monkeypatch: Any,
    action: str,
    target_status: str,
) -> None:
    """Accept and reject endpoints should update review status."""

    captured_parameters: dict[str, Any] = {}

    def mock_change_recommendation_status(
        *,
        recommendation_id: int,
        target_status: str,
    ) -> dict[str, Any]:
        captured_parameters.update(
            {
                "recommendation_id": recommendation_id,
                "target_status": target_status,
            }
        )

        return {
            "outcome": "success",
            "response": build_detail_response(
                recommendation_status=target_status,
            ),
        }

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "change_recommendation_status",
        mock_change_recommendation_status,
    )

    response = client.patch(
        f"/api/recommendations/101/{action}"
    )

    assert response.status_code == 200

    assert captured_parameters == {
        "recommendation_id": 101,
        "target_status": target_status,
    }

    response_data = response.json()

    assert (
        response_data["recommendation"]["status"]
        == target_status
    )


@pytest.mark.parametrize(
    "action",
    [
        "accept",
        "reject",
    ],
)
def test_review_action_returns_404_when_not_found(
    client: Any,
    monkeypatch: Any,
    action: str,
) -> None:
    """Reviewing an unknown recommendation should return 404."""

    def mock_change_recommendation_status(
        *,
        recommendation_id: int,
        target_status: str,
    ) -> dict[str, Any]:
        del recommendation_id
        del target_status

        return {
            "outcome": "not_found",
        }

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "change_recommendation_status",
        mock_change_recommendation_status,
    )

    response = client.patch(
        f"/api/recommendations/999/{action}"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": (
            "The requested recommendation was not found."
        )
    }


@pytest.mark.parametrize(
    ("action", "current_status"),
    [
        ("accept", "Rejected"),
        ("reject", "Accepted"),
        ("accept", "Converted to Task"),
    ],
)
def test_review_action_returns_409_for_invalid_status(
    client: Any,
    monkeypatch: Any,
    action: str,
    current_status: str,
) -> None:
    """A completed review state should not be changed again."""

    def mock_change_recommendation_status(
        *,
        recommendation_id: int,
        target_status: str,
    ) -> dict[str, Any]:
        del recommendation_id
        del target_status

        return {
            "outcome": "conflict",
            "current_status": current_status,
        }

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "change_recommendation_status",
        mock_change_recommendation_status,
    )

    response = client.patch(
        f"/api/recommendations/101/{action}"
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "This recommendation cannot be changed because "
            f"its current status is '{current_status}'."
        )
    }


@pytest.mark.parametrize(
    ("action", "expected_message"),
    [
        (
            "accept",
            (
                "The recommendation could not be accepted because "
                "the database is unavailable."
            ),
        ),
        (
            "reject",
            (
                "The recommendation could not be rejected because "
                "the database is unavailable."
            ),
        ),
    ],
)
def test_review_action_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
    action: str,
    expected_message: str,
) -> None:
    """Accept and reject database failures should return 503."""

    def raise_database_error(
        **_: Any,
    ) -> dict[str, Any]:
        raise SQLAlchemyError(
            "Simulated recommendation-review failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "change_recommendation_status",
        raise_database_error,
    )

    response = client.patch(
        f"/api/recommendations/101/{action}"
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": expected_message,
    }


def test_edit_recommendation_updates_selected_fields(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Editable recommendation fields should reach the service."""

    captured_parameters: dict[str, Any] = {}

    def mock_edit_recommendation(
        *,
        recommendation_id: int,
        update_data: dict[str, Any],
    ) -> dict[str, Any]:
        captured_parameters.update(
            {
                "recommendation_id": recommendation_id,
                "update_data": update_data,
            }
        )

        return {
            "outcome": "success",
            "response": build_detail_response(
                recommendation_status="Edited",
                recommendation_title=(
                    "Implement a focused sales recovery plan"
                ),
                recommendation_text=(
                    "Review category performance and implement "
                    "a focused store-level recovery plan."
                ),
                suggested_owner_role="Store Manager",
                suggested_deadline="2026-08-20",
                expected_impact=(
                    "Improve revenue and target achievement."
                ),
            ),
        }

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "edit_recommendation",
        mock_edit_recommendation,
    )

    request_payload = {
        "recommendation_title": (
            "  Implement a focused sales recovery plan  "
        ),
        "recommendation_text": (
            "  Review category performance and implement "
            "a focused store-level recovery plan.  "
        ),
        "suggested_owner_role": "  Store Manager  ",
        "suggested_deadline": "2026-08-20",
        "expected_impact": (
            "  Improve revenue and target achievement.  "
        ),
    }

    response = client.patch(
        "/api/recommendations/101/edit",
        json=request_payload,
    )

    assert response.status_code == 200

    assert captured_parameters == {
        "recommendation_id": 101,
        "update_data": {
            "recommendation_title": (
                "Implement a focused sales recovery plan"
            ),
            "recommendation_text": (
                "Review category performance and implement "
                "a focused store-level recovery plan."
            ),
            "suggested_owner_role": "Store Manager",
            "suggested_deadline": date(2026, 8, 20),
            "expected_impact": (
                "Improve revenue and target achievement."
            ),
        },
    }

    response_data = response.json()
    recommendation = response_data["recommendation"]

    assert recommendation["status"] == "Edited"
    assert (
        recommendation["suggested_owner_role"]
        == "Store Manager"
    )
    assert (
        recommendation["suggested_deadline"]
        == "2026-08-20"
    )


def test_edit_recommendation_rejects_empty_request(
    client: Any,
) -> None:
    """An edit request must contain at least one field."""

    response = client.patch(
        "/api/recommendations/101/edit",
        json={},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "At least one editable field must be provided."
        )
    }


def test_edit_recommendation_rejects_null_values(
    client: Any,
) -> None:
    """Explicit null fields should be rejected by the router."""

    response = client.patch(
        "/api/recommendations/101/edit",
        json={
            "expected_impact": None,
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "Editable fields cannot be null. Omit fields that "
            "should remain unchanged."
        )
    }


@pytest.mark.parametrize(
    ("request_payload", "invalid_field"),
    [
        (
            {
                "recommendation_title": "Plan",
            },
            "recommendation_title",
        ),
        (
            {
                "recommendation_text": "Too short",
            },
            "recommendation_text",
        ),
        (
            {
                "suggested_owner_role": "A",
            },
            "suggested_owner_role",
        ),
        (
            {
                "expected_impact": "Low",
            },
            "expected_impact",
        ),
        (
            {
                "suggested_deadline": "invalid-date",
            },
            "suggested_deadline",
        ),
    ],
)
def test_edit_recommendation_validates_request_fields(
    client: Any,
    request_payload: dict[str, Any],
    invalid_field: str,
) -> None:
    """Invalid edit-field values should return HTTP 422."""

    response = client.patch(
        "/api/recommendations/101/edit",
        json=request_payload,
    )

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        invalid_field in error["loc"]
        for error in error_details
    )


def test_edit_recommendation_returns_404_when_not_found(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Editing an unknown recommendation should return 404."""

    def mock_edit_recommendation(
        *,
        recommendation_id: int,
        update_data: dict[str, Any],
    ) -> dict[str, Any]:
        del recommendation_id
        del update_data

        return {
            "outcome": "not_found",
        }

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "edit_recommendation",
        mock_edit_recommendation,
    )

    response = client.patch(
        "/api/recommendations/999/edit",
        json={
            "recommendation_title": (
                "Review the updated management recommendation"
            ),
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": (
            "The requested recommendation was not found."
        )
    }


def test_edit_recommendation_returns_409_for_invalid_status(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Accepted recommendations should not be edited again."""

    def mock_edit_recommendation(
        *,
        recommendation_id: int,
        update_data: dict[str, Any],
    ) -> dict[str, Any]:
        del recommendation_id
        del update_data

        return {
            "outcome": "conflict",
            "current_status": "Accepted",
        }

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "edit_recommendation",
        mock_edit_recommendation,
    )

    response = client.patch(
        "/api/recommendations/101/edit",
        json={
            "recommendation_title": (
                "Review the updated management recommendation"
            ),
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "This recommendation cannot be changed because "
            "its current status is 'Accepted'."
        )
    }


def test_edit_recommendation_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    """An edit database failure should return HTTP 503."""

    def raise_database_error(
        **_: Any,
    ) -> dict[str, Any]:
        raise SQLAlchemyError(
            "Simulated recommendation-edit failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.recommendations."
        "edit_recommendation",
        raise_database_error,
    )

    response = client.patch(
        "/api/recommendations/101/edit",
        json={
            "recommendation_title": (
                "Review the updated management recommendation"
            ),
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "The recommendation could not be edited because "
            "the database is unavailable."
        )
    }