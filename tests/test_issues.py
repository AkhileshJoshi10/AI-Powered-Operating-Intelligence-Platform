from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError


SAMPLE_ISSUE = {
    "issue_id": "ISSUE-SALES-S003-2026-06",
    "title": "Significant sales decline at Store S003",
    "issue_type": "Store Sales Decline",
    "business_area": "Sales",
    "priority_level": "High",
    "priority_score": 91.50,
    "priority_reason": (
        "The issue has high financial and operational impact."
    ),
    "status": "Open",
    "entity_type": "Store",
    "entity_id": "S003",
    "store_id": "S003",
    "product_id": None,
    "vendor_id": None,
    "period_label": "2026-06",
    "finding_count": 3,
    "high_finding_count": 2,
    "medium_finding_count": 1,
    "low_finding_count": 0,
    "root_cause_status": "Generated",
    "summary": "Store S003 experienced a significant sales decline.",
    "evidence_summary": (
        "Sales declined and target achievement remained low."
    ),
    "created_at": "2026-08-03T09:00:00",
    "updated_at": "2026-08-03T09:30:00",
    "last_detected_at": "2026-08-03T09:30:00",
}


SAMPLE_EVIDENCE = {
    "evidence_id": 101,
    "source_finding_id": "SALES-DECLINE-S003-2026-06",
    "source_report": "sales_analysis_report",
    "source_module": "sales_analysis",
    "analysis_type": "Store Sales Decline",
    "business_area": "Sales",
    "severity": "High",
    "entity_type": "Store",
    "entity_id": "S003",
    "store_id": "S003",
    "product_id": None,
    "vendor_id": None,
    "summary": "Store S003 sales declined during June.",
    "evidence": "Month-over-month sales declined by 57.86%.",
    "detected_at": "2026-08-03T08:45:00",
    "created_at": "2026-08-03T09:00:00",
}


SAMPLE_ROOT_CAUSE = {
    "root_cause_analysis_id": 10,
    "root_cause_category": "Demand and Operational Performance",
    "root_cause_summary": (
        "Reduced demand and operational issues contributed "
        "to the sales decline."
    ),
    "root_cause_explanation": (
        "The available evidence shows reduced sales performance, "
        "low target achievement, and related operational findings."
    ),
    "confidence_score": 88.50,
    "evidence_count": 3,
    "analysis_status": "Generated",
    "review_status": "Pending Review",
    "analysis_version": 1,
    "generated_at": "2026-08-03T09:15:00",
    "reviewed_at": None,
    "updated_at": "2026-08-03T09:15:00",
}


def test_list_issues_returns_paginated_response(
    client: Any,
    monkeypatch: Any,
) -> None:
    """The issue-list endpoint should return valid paginated data."""

    def mock_get_issue_list(
        *,
        priority: str | None,
        business_area: str | None,
        issue_status: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        assert priority is None
        assert business_area is None
        assert issue_status is None
        assert limit == 20
        assert offset == 0

        return {
            "status": "success",
            "total_items": 1,
            "limit": 20,
            "offset": 0,
            "items": [SAMPLE_ISSUE],
        }

    monkeypatch.setattr(
        "backend.app.routers.issues.get_issue_list",
        mock_get_issue_list,
    )

    response = client.get("/api/issues")

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "success"
    assert response_data["total_items"] == 1
    assert response_data["limit"] == 20
    assert response_data["offset"] == 0
    assert len(response_data["items"]) == 1

    issue = response_data["items"][0]

    assert issue["issue_id"] == "ISSUE-SALES-S003-2026-06"
    assert issue["priority_level"] == "High"
    assert issue["priority_score"] == 91.50
    assert issue["business_area"] == "Sales"
    assert issue["store_id"] == "S003"


def test_list_issues_forwards_filters_and_pagination(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Query filters should be passed correctly to the service."""

    captured_parameters: dict[str, Any] = {}

    def mock_get_issue_list(
        *,
        priority: str | None,
        business_area: str | None,
        issue_status: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        captured_parameters.update(
            {
                "priority": priority,
                "business_area": business_area,
                "issue_status": issue_status,
                "limit": limit,
                "offset": offset,
            }
        )

        return {
            "status": "success",
            "total_items": 1,
            "limit": limit,
            "offset": offset,
            "items": [SAMPLE_ISSUE],
        }

    monkeypatch.setattr(
        "backend.app.routers.issues.get_issue_list",
        mock_get_issue_list,
    )

    response = client.get(
        "/api/issues",
        params={
            "priority": "High",
            "business_area": "Sales",
            "status": "Open",
            "limit": 10,
            "offset": 5,
        },
    )

    assert response.status_code == 200

    assert captured_parameters == {
        "priority": "High",
        "business_area": "Sales",
        "issue_status": "Open",
        "limit": 10,
        "offset": 5,
    }

    response_data = response.json()

    assert response_data["limit"] == 10
    assert response_data["offset"] == 5


def test_list_issues_accepts_empty_result(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A valid search with no matches should return an empty list."""

    def mock_get_issue_list(
        *,
        priority: str | None,
        business_area: str | None,
        issue_status: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        return {
            "status": "success",
            "total_items": 0,
            "limit": limit,
            "offset": offset,
            "items": [],
        }

    monkeypatch.setattr(
        "backend.app.routers.issues.get_issue_list",
        mock_get_issue_list,
    )

    response = client.get(
        "/api/issues",
        params={
            "priority": "Low",
            "business_area": "Unknown Area",
        },
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
            {"priority": "Critical"},
            "priority",
        ),
        (
            {"status": "Pending"},
            "status",
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
        (
            {"business_area": ""},
            "business_area",
        ),
    ],
)
def test_list_issues_rejects_invalid_query_parameters(
    client: Any,
    query_parameters: dict[str, Any],
    invalid_field: str,
) -> None:
    """Invalid filters and pagination values should return 422."""

    response = client.get(
        "/api/issues",
        params=query_parameters,
    )

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        invalid_field in error["loc"]
        for error in error_details
    )


def test_list_issues_returns_503_when_database_fails(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A list-query database failure should return a controlled 503."""

    def raise_database_error(
        **_: Any,
    ) -> dict[str, Any]:
        raise SQLAlchemyError(
            "Simulated issue-list database failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.issues.get_issue_list",
        raise_database_error,
    )

    response = client.get("/api/issues")

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "Business issues could not be loaded because "
            "the database is unavailable."
        )
    }


def test_get_issue_detail_returns_evidence_and_root_cause(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Issue details should include evidence and root-cause data."""

    def mock_get_issue_detail(
        issue_id: str,
    ) -> dict[str, Any]:
        assert issue_id == "ISSUE-SALES-S003-2026-06"

        return {
            "status": "success",
            "issue": SAMPLE_ISSUE,
            "evidence_count": 1,
            "evidence": [SAMPLE_EVIDENCE],
            "root_cause": SAMPLE_ROOT_CAUSE,
        }

    monkeypatch.setattr(
        "backend.app.routers.issues.get_issue_detail",
        mock_get_issue_detail,
    )

    response = client.get(
        "/api/issues/ISSUE-SALES-S003-2026-06"
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "success"
    assert response_data["issue"]["store_id"] == "S003"
    assert response_data["evidence_count"] == 1
    assert len(response_data["evidence"]) == 1

    evidence = response_data["evidence"][0]

    assert evidence["severity"] == "High"
    assert evidence["source_module"] == "sales_analysis"

    root_cause = response_data["root_cause"]

    assert root_cause is not None
    assert (
        root_cause["root_cause_category"]
        == "Demand and Operational Performance"
    )
    assert root_cause["confidence_score"] == 88.50
    assert root_cause["review_status"] == "Pending Review"


def test_get_issue_detail_allows_missing_root_cause(
    client: Any,
    monkeypatch: Any,
) -> None:
    """An issue may be returned before root-cause analysis exists."""

    def mock_get_issue_detail(
        issue_id: str,
    ) -> dict[str, Any]:
        return {
            "status": "success",
            "issue": {
                **SAMPLE_ISSUE,
                "issue_id": issue_id,
                "root_cause_status": "Pending",
            },
            "evidence_count": 1,
            "evidence": [SAMPLE_EVIDENCE],
            "root_cause": None,
        }

    monkeypatch.setattr(
        "backend.app.routers.issues.get_issue_detail",
        mock_get_issue_detail,
    )

    response = client.get(
        "/api/issues/ISSUE-WITHOUT-RCA"
    )

    assert response.status_code == 200
    assert response.json()["root_cause"] is None


def test_get_issue_detail_returns_404_for_unknown_issue(
    client: Any,
    monkeypatch: Any,
) -> None:
    """An unknown issue identifier should return 404."""

    def mock_get_issue_detail(
        issue_id: str,
    ) -> None:
        assert issue_id == "UNKNOWN-ISSUE"

        return None

    monkeypatch.setattr(
        "backend.app.routers.issues.get_issue_detail",
        mock_get_issue_detail,
    )

    response = client.get(
        "/api/issues/UNKNOWN-ISSUE"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "The requested issue was not found."
    }


def test_get_issue_detail_returns_503_when_database_fails(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A detail-query database failure should return a controlled 503."""

    def raise_database_error(
        issue_id: str,
    ) -> dict[str, Any]:
        del issue_id

        raise SQLAlchemyError(
            "Simulated issue-detail database failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.issues.get_issue_detail",
        raise_database_error,
    )

    response = client.get(
        "/api/issues/ISSUE-SALES-S003-2026-06"
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "The issue could not be loaded because "
            "the database is unavailable."
        )
    }