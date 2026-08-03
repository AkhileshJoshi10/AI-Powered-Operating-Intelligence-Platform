from __future__ import annotations

from typing import Any

from sqlalchemy.exc import SQLAlchemyError


SAMPLE_KPI_RESPONSE = {
    "status": "success",
    "total_kpis": 2,
    "kpis": [
        {
            "kpi_key": "total_sales",
            "kpi_name": "Total Sales",
            "value": 39064024.80,
            "display_value": "₹39,064,024.80",
            "unit": "INR",
            "reference_period": "Full Dataset",
            "description": "Total sales generated across all stores.",
            "calculated_at": "2026-08-03T05:00:00",
        },
        {
            "kpi_key": "sales_growth",
            "kpi_name": "Sales Growth",
            "value": -6.81,
            "display_value": "-6.81%",
            "unit": "Percent",
            "reference_period": "Latest Month",
            "description": "Month-over-month sales growth.",
            "calculated_at": "2026-08-03T05:00:00",
        },
    ],
    "latest_store_target_achievement": [
        {
            "store_id": "S003",
            "store_name": "SmartMart Store 3",
            "month": "2026-06",
            "monthly_sales_target": 1000000.00,
            "total_revenue": 578600.00,
            "operating_profit": 42000.00,
            "target_achievement_percent": 57.86,
            "risk_status": "High Risk",
        }
    ],
}


def test_get_kpis_returns_expected_response(
    client: Any,
    monkeypatch: Any,
) -> None:
    """The KPI endpoint should return the service response."""

    def mock_get_kpi_response() -> dict[str, Any]:
        return SAMPLE_KPI_RESPONSE

    monkeypatch.setattr(
        "backend.app.routers.kpis.get_kpi_response",
        mock_get_kpi_response,
    )

    response = client.get("/api/kpis")

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "success"
    assert response_data["total_kpis"] == 2
    assert len(response_data["kpis"]) == 2
    assert len(
        response_data["latest_store_target_achievement"]
    ) == 1

    first_kpi = response_data["kpis"][0]

    assert first_kpi["kpi_key"] == "total_sales"
    assert first_kpi["kpi_name"] == "Total Sales"
    assert first_kpi["value"] == 39064024.80
    assert first_kpi["unit"] == "INR"

    store_record = response_data[
        "latest_store_target_achievement"
    ][0]

    assert store_record["store_id"] == "S003"
    assert store_record["target_achievement_percent"] == 57.86
    assert store_record["risk_status"] == "High Risk"


def test_get_kpis_accepts_empty_kpi_result(
    client: Any,
    monkeypatch: Any,
) -> None:
    """The endpoint should return a valid empty KPI response."""

    def mock_empty_kpi_response() -> dict[str, Any]:
        return {
            "status": "success",
            "total_kpis": 0,
            "kpis": [],
            "latest_store_target_achievement": [],
        }

    monkeypatch.setattr(
        "backend.app.routers.kpis.get_kpi_response",
        mock_empty_kpi_response,
    )

    response = client.get("/api/kpis")

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "total_kpis": 0,
        "kpis": [],
        "latest_store_target_achievement": [],
    }


def test_get_kpis_returns_503_when_database_fails(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A KPI database failure should return a controlled 503."""

    def raise_database_error() -> dict[str, Any]:
        raise SQLAlchemyError(
            "Simulated KPI database failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.kpis.get_kpi_response",
        raise_database_error,
    )

    response = client.get("/api/kpis")

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "Business KPIs could not be loaded because the "
            "database is unavailable."
        )
    }