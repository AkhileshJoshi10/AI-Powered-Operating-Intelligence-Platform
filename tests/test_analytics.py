from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError


GENERATED_AT = "2026-08-03T11:00:00"


SAMPLE_SALES_FINDING = {
    "finding_id": "SALES-DECLINE-S003-2026-06",
    "analysis_type": "Store Sales Decline",
    "business_area": "Sales",
    "severity": "High",
    "entity_type": "Store",
    "entity_id": "S003",
    "entity_name": "SmartMart Store 3",
    "store_id": "S003",
    "store_name": "SmartMart Store 3",
    "month": "2026-06",
    "previous_month": "2026-05",
    "current_sales": 421400.00,
    "previous_sales": 1000000.00,
    "sales_change_percent": -57.86,
    "target_achievement_percent": 57.86,
    "summary": "Store S003 recorded a significant sales decline.",
    "evidence": "Sales declined by 57.86% compared with May.",
    "status": "Open",
    "detected_at": GENERATED_AT,
}


SAMPLE_INVENTORY_FINDING = {
    "finding_id": "INVENTORY-LOW-STOCK-S003-P017",
    "analysis_type": "Low Stock",
    "business_area": "Inventory",
    "severity": "High",
    "entity_type": "Store Product",
    "entity_id": "S003-P017",
    "store_id": "S003",
    "store_name": "SmartMart Store 3",
    "product_id": "P017",
    "product_name": "Product 17",
    "vendor_id": "V004",
    "vendor_name": "Vendor 4",
    "inventory_date": "2026-06-30",
    "current_stock": 5.00,
    "reorder_level": 100.00,
    "stock_ratio": 0.05,
    "stock_status": "Low",
    "reorder_required": "Yes",
    "related_complaints": 4,
    "high_severity_complaints": 2,
    "summary": "Product P017 has critically low stock.",
    "evidence": "Current stock is 5% of the reorder level.",
    "status": "Open",
    "detected_at": GENERATED_AT,
}


SAMPLE_COMPLAINT_FINDING = {
    "finding_id": "COMPLAINT-HIGH-SEVERITY-C0001",
    "analysis_type": "High Severity Complaint",
    "business_area": "Complaints",
    "severity": "High",
    "entity_type": "Complaint",
    "entity_id": "C0001",
    "entity_name": "Complaint C0001",
    "store_id": "S003",
    "product_id": "P011",
    "region": "North",
    "complaint_id": "C0001",
    "complaint_type": "Product Quality",
    "complaint_severity": "High",
    "complaint_status": "Open",
    "complaint_date": "2026-06-20",
    "complaint_age_days": 44,
    "summary": "A high-severity complaint remains open.",
    "evidence": "Complaint C0001 is unresolved after 44 days.",
    "status": "Open",
    "detected_at": GENERATED_AT,
}


SAMPLE_VENDOR_FINDING = {
    "finding_id": "VENDOR-DELAY-V004",
    "analysis_type": "Vendor Delivery Delay",
    "business_area": "Procurement",
    "severity": "High",
    "entity_type": "Vendor",
    "entity_id": "V004",
    "entity_name": "Vendor 4",
    "vendor_id": "V004",
    "vendor_name": "Vendor 4",
    "delivery_count": 10,
    "delayed_deliveries": 7,
    "average_delay_days": 6.50,
    "on_time_delivery_rate": 30.00,
    "summary": "Vendor V004 has frequent delivery delays.",
    "evidence": "Seven of ten deliveries were delayed.",
    "status": "Open",
    "detected_at": GENERATED_AT,
}


SAMPLE_FINANCE_FINDING = {
    "finding_id": "FINANCE-RISK-S003-2026-06",
    "analysis_type": "Financial Risk",
    "business_area": "Finance",
    "severity": "High",
    "entity_type": "Store Month",
    "entity_id": "S003-2026-06",
    "entity_name": "SmartMart Store 3 - 2026-06",
    "store_id": "S003",
    "store_name": "SmartMart Store 3",
    "month": "2026-06",
    "total_revenue": 578600.00,
    "operating_profit": -42000.00,
    "target_achievement_percent": 57.86,
    "risk_status": "High Risk",
    "summary": "Store S003 has high financial risk in June.",
    "evidence": "Operating profit was negative.",
    "status": "Open",
    "detected_at": GENERATED_AT,
}


def build_analytics_response(
    finding: dict[str, Any],
    *,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Build a valid analytics service response."""

    return {
        "status": "success",
        "generated_at": GENERATED_AT,
        "total_findings": 1,
        "matching_findings": 1,
        "limit": limit,
        "offset": offset,
        "summary": [
            {
                "analysis_type": finding["analysis_type"],
                "severity": finding["severity"],
                "finding_count": 1,
            }
        ],
        "findings": [finding],
    }


ANALYTICS_CASES = [
    {
        "name": "sales",
        "endpoint": "/api/analytics/sales",
        "service_target": (
            "backend.app.routers.analytics.get_sales_analytics"
        ),
        "query_parameters": {
            "severity": "High",
            "analysis_type": "Store Sales Decline",
            "limit": 10,
            "offset": 2,
        },
        "expected_service_parameters": {
            "severity": "High",
            "analysis_type": "Store Sales Decline",
            "limit": 10,
            "offset": 2,
        },
        "finding": SAMPLE_SALES_FINDING,
        "database_error": (
            "Sales analytics could not be loaded because "
            "the database operation failed."
        ),
        "processing_error": (
            "Sales analytics could not be processed."
        ),
    },
    {
        "name": "inventory",
        "endpoint": "/api/analytics/inventory",
        "service_target": (
            "backend.app.routers.analytics.get_inventory_analytics"
        ),
        "query_parameters": {
            "severity": "High",
            "analysis_type": "Low Stock",
            "store_id": "S003",
            "product_id": "P017",
            "vendor_id": "V004",
            "limit": 10,
            "offset": 2,
        },
        "expected_service_parameters": {
            "severity": "High",
            "analysis_type": "Low Stock",
            "store_id": "S003",
            "product_id": "P017",
            "vendor_id": "V004",
            "limit": 10,
            "offset": 2,
        },
        "finding": SAMPLE_INVENTORY_FINDING,
        "database_error": (
            "Inventory analytics could not be loaded because "
            "the database operation failed."
        ),
        "processing_error": (
            "Inventory analytics could not be processed."
        ),
    },
    {
        "name": "complaints",
        "endpoint": "/api/analytics/complaints",
        "service_target": (
            "backend.app.routers.analytics.get_complaint_analytics"
        ),
        "query_parameters": {
            "severity": "High",
            "analysis_type": "High Severity Complaint",
            "store_id": "S003",
            "product_id": "P011",
            "region": "North",
            "complaint_type": "Product Quality",
            "complaint_status": "Open",
            "limit": 10,
            "offset": 2,
        },
        "expected_service_parameters": {
            "severity": "High",
            "analysis_type": "High Severity Complaint",
            "store_id": "S003",
            "product_id": "P011",
            "region": "North",
            "complaint_type": "Product Quality",
            "complaint_status": "Open",
            "limit": 10,
            "offset": 2,
        },
        "finding": SAMPLE_COMPLAINT_FINDING,
        "database_error": (
            "Complaint analytics could not be loaded because "
            "the database operation failed."
        ),
        "processing_error": (
            "Complaint analytics could not be processed."
        ),
    },
    {
        "name": "vendors",
        "endpoint": "/api/analytics/vendors",
        "service_target": (
            "backend.app.routers.analytics.get_vendor_analytics"
        ),
        "query_parameters": {
            "severity": "High",
            "analysis_type": "Vendor Delivery Delay",
            "vendor_id": "V004",
            "limit": 10,
            "offset": 2,
        },
        "expected_service_parameters": {
            "severity": "High",
            "analysis_type": "Vendor Delivery Delay",
            "vendor_id": "V004",
            "limit": 10,
            "offset": 2,
        },
        "finding": SAMPLE_VENDOR_FINDING,
        "database_error": (
            "Vendor analytics could not be loaded because "
            "the database operation failed."
        ),
        "processing_error": (
            "Vendor analytics could not be processed."
        ),
    },
    {
        "name": "finance",
        "endpoint": "/api/analytics/finance",
        "service_target": (
            "backend.app.routers.analytics.get_finance_analytics"
        ),
        "query_parameters": {
            "severity": "High",
            "analysis_type": "Financial Risk",
            "store_id": "S003",
            "month": "2026-06",
            "risk_status": "High Risk",
            "limit": 10,
            "offset": 2,
        },
        "expected_service_parameters": {
            "severity": "High",
            "analysis_type": "Financial Risk",
            "store_id": "S003",
            "month": "2026-06",
            "risk_status": "High Risk",
            "limit": 10,
            "offset": 2,
        },
        "finding": SAMPLE_FINANCE_FINDING,
        "database_error": (
            "Finance analytics could not be loaded because "
            "the database operation failed."
        ),
        "processing_error": (
            "Finance analytics could not be processed."
        ),
    },
]


ANALYTICS_PARAMETERS = [
    pytest.param(case, id=case["name"])
    for case in ANALYTICS_CASES
]


@pytest.mark.parametrize("case", ANALYTICS_PARAMETERS)
def test_analytics_endpoint_returns_findings_and_forwards_filters(
    client: Any,
    monkeypatch: Any,
    case: dict[str, Any],
) -> None:
    """Each endpoint should return findings and forward filters."""

    captured_parameters: dict[str, Any] = {}

    def mock_analytics_service(
        **service_parameters: Any,
    ) -> dict[str, Any]:
        captured_parameters.update(service_parameters)

        return build_analytics_response(
            case["finding"],
            limit=service_parameters["limit"],
            offset=service_parameters["offset"],
        )

    monkeypatch.setattr(
        case["service_target"],
        mock_analytics_service,
    )

    response = client.get(
        case["endpoint"],
        params=case["query_parameters"],
    )

    assert response.status_code == 200
    assert captured_parameters == case[
        "expected_service_parameters"
    ]

    response_data = response.json()

    assert response_data["status"] == "success"
    assert response_data["generated_at"] == GENERATED_AT
    assert response_data["total_findings"] == 1
    assert response_data["matching_findings"] == 1
    assert response_data["limit"] == 10
    assert response_data["offset"] == 2
    assert len(response_data["summary"]) == 1
    assert len(response_data["findings"]) == 1
    assert (
        response_data["findings"][0]["finding_id"]
        == case["finding"]["finding_id"]
    )
    assert (
        response_data["findings"][0]["business_area"]
        == case["finding"]["business_area"]
    )


@pytest.mark.parametrize("case", ANALYTICS_PARAMETERS)
def test_analytics_endpoint_accepts_empty_result(
    client: Any,
    monkeypatch: Any,
    case: dict[str, Any],
) -> None:
    """A valid analytics run may return no findings."""

    def mock_empty_analytics_service(
        **service_parameters: Any,
    ) -> dict[str, Any]:
        return {
            "status": "success",
            "generated_at": GENERATED_AT,
            "total_findings": 0,
            "matching_findings": 0,
            "limit": service_parameters["limit"],
            "offset": service_parameters["offset"],
            "summary": [],
            "findings": [],
        }

    monkeypatch.setattr(
        case["service_target"],
        mock_empty_analytics_service,
    )

    response = client.get(case["endpoint"])

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "generated_at": GENERATED_AT,
        "total_findings": 0,
        "matching_findings": 0,
        "limit": 50,
        "offset": 0,
        "summary": [],
        "findings": [],
    }


INVALID_QUERY_CASES = [
    pytest.param(
        "/api/analytics/sales",
        {"severity": "Critical"},
        "severity",
        id="sales-invalid-severity",
    ),
    pytest.param(
        "/api/analytics/sales",
        {"analysis_type": "A"},
        "analysis_type",
        id="sales-short-analysis-type",
    ),
    pytest.param(
        "/api/analytics/sales",
        {"limit": 0},
        "limit",
        id="sales-limit-below-minimum",
    ),
    pytest.param(
        "/api/analytics/sales",
        {"limit": 101},
        "limit",
        id="sales-limit-above-maximum",
    ),
    pytest.param(
        "/api/analytics/sales",
        {"offset": -1},
        "offset",
        id="sales-negative-offset",
    ),
    pytest.param(
        "/api/analytics/inventory",
        {"store_id": "S"},
        "store_id",
        id="inventory-short-store-id",
    ),
    pytest.param(
        "/api/analytics/inventory",
        {"product_id": "P"},
        "product_id",
        id="inventory-short-product-id",
    ),
    pytest.param(
        "/api/analytics/inventory",
        {"vendor_id": "V"},
        "vendor_id",
        id="inventory-short-vendor-id",
    ),
    pytest.param(
        "/api/analytics/inventory",
        {"severity": "Critical"},
        "severity",
        id="inventory-invalid-severity",
    ),
    pytest.param(
        "/api/analytics/complaints",
        {"region": "N"},
        "region",
        id="complaints-short-region",
    ),
    pytest.param(
        "/api/analytics/complaints",
        {"complaint_type": "Q"},
        "complaint_type",
        id="complaints-short-type",
    ),
    pytest.param(
        "/api/analytics/complaints",
        {"complaint_status": "O"},
        "complaint_status",
        id="complaints-short-status",
    ),
    pytest.param(
        "/api/analytics/vendors",
        {"vendor_id": "V"},
        "vendor_id",
        id="vendors-short-vendor-id",
    ),
    pytest.param(
        "/api/analytics/finance",
        {"store_id": "S"},
        "store_id",
        id="finance-short-store-id",
    ),
    pytest.param(
        "/api/analytics/finance",
        {"month": "2026-13"},
        "month",
        id="finance-invalid-month-number",
    ),
    pytest.param(
        "/api/analytics/finance",
        {"month": "06-2026"},
        "month",
        id="finance-invalid-month-format",
    ),
    pytest.param(
        "/api/analytics/finance",
        {"risk_status": "No"},
        "risk_status",
        id="finance-short-risk-status",
    ),
]


@pytest.mark.parametrize(
    ("endpoint", "query_parameters", "invalid_field"),
    INVALID_QUERY_CASES,
)
def test_analytics_endpoint_rejects_invalid_query_parameters(
    client: Any,
    endpoint: str,
    query_parameters: dict[str, Any],
    invalid_field: str,
) -> None:
    """Invalid filters and pagination should return HTTP 422."""

    response = client.get(
        endpoint,
        params=query_parameters,
    )

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        invalid_field in error["loc"]
        for error in error_details
    )


@pytest.mark.parametrize("case", ANALYTICS_PARAMETERS)
def test_analytics_endpoint_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
    case: dict[str, Any],
) -> None:
    """Database failures should return controlled HTTP 503 responses."""

    def raise_database_error(
        **_: Any,
    ) -> dict[str, Any]:
        raise SQLAlchemyError(
            "Simulated analytics database failure."
        )

    monkeypatch.setattr(
        case["service_target"],
        raise_database_error,
    )

    response = client.get(case["endpoint"])

    assert response.status_code == 503
    assert response.json() == {
        "detail": case["database_error"],
    }


@pytest.mark.parametrize("case", ANALYTICS_PARAMETERS)
def test_analytics_endpoint_returns_500_on_processing_failure(
    client: Any,
    monkeypatch: Any,
    case: dict[str, Any],
) -> None:
    """Processing failures should return controlled HTTP 500 responses."""

    def raise_processing_error(
        **_: Any,
    ) -> dict[str, Any]:
        raise ValueError(
            "Simulated analytics processing failure."
        )

    monkeypatch.setattr(
        case["service_target"],
        raise_processing_error,
    )

    response = client.get(case["endpoint"])

    assert response.status_code == 500
    assert response.json() == {
        "detail": case["processing_error"],
    }


@pytest.mark.parametrize(
    "exception_type",
    [
        pytest.param(KeyError, id="key-error"),
        pytest.param(TypeError, id="type-error"),
    ],
)
def test_sales_analytics_catches_other_processing_errors(
    client: Any,
    monkeypatch: Any,
    exception_type: type[Exception],
) -> None:
    """Sales analytics should also catch KeyError and TypeError."""

    def raise_processing_error(
        **_: Any,
    ) -> dict[str, Any]:
        raise exception_type(
            "Simulated sales processing failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.analytics.get_sales_analytics",
        raise_processing_error,
    )

    response = client.get("/api/analytics/sales")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Sales analytics could not be processed.",
    }

# ---------------------------------------------------------------------------
# Seeded PostgreSQL integration tests
# ---------------------------------------------------------------------------

EXPECTED_TEST_DATABASE = "ai_operating_intelligence_test"


SEEDED_KPI_DISPLAY_VALUES = {
    "Total Sales": "₹39,064,024.80",
    "Total Revenue": "₹39,064,024.80",
    "Sales Growth": "-6.81%",
    "Store Target Achievement": "90.22%",
    "Average Order Value": "₹879.13",
    "Total Operating Profit": "₹5,228,532.44",
    "Low-Stock Count": "37",
    "Overstock Count": "28",
    "High-Severity Complaint Count": "312",
    "Open Complaint Count": "323",
    "Vendor Delay Count": "39",
    "Vendor On-Time Delivery Rate": "54.12%",
}


SEEDED_ANALYTICS_BASELINES = [
    pytest.param(
        "/api/analytics/sales",
        5,
        id="seeded-sales-baseline",
    ),
    pytest.param(
        "/api/analytics/inventory",
        122,
        id="seeded-inventory-baseline",
    ),
    pytest.param(
        "/api/analytics/complaints",
        345,
        id="seeded-complaints-baseline",
    ),
    pytest.param(
        "/api/analytics/vendors",
        19,
        id="seeded-vendors-baseline",
    ),
    pytest.param(
        "/api/analytics/finance",
        4,
        id="seeded-finance-baseline",
    ),
]


SEEDED_CRITICAL_SCENARIOS = [
    pytest.param(
        "/api/analytics/sales",
        {
            "severity": "High",
            "analysis_type": "Low Target Achievement",
            "limit": 100,
        },
        "LOW-TARGET-S003-2026-06",
        {
            "analysis_type": "Low Target Achievement",
            "severity": "High",
            "store_id": "S003",
            "month": "2026-06",
        },
        id="seeded-low-target-achievement",
    ),
    pytest.param(
        "/api/analytics/inventory",
        {
            "severity": "High",
            "analysis_type": "Low Stock",
            "store_id": "S003",
            "product_id": "P017",
            "limit": 100,
        },
        "LOW-STOCK-S003-P017-2026-06-30",
        {
            "analysis_type": "Low Stock",
            "severity": "High",
            "store_id": "S003",
            "product_id": "P017",
            "vendor_id": "V007",
        },
        id="seeded-critical-low-stock",
    ),
    pytest.param(
        "/api/analytics/complaints",
        {
            "severity": "High",
            "analysis_type": "High Complaint Product",
            "product_id": "P017",
            "limit": 100,
        },
        "HIGH-COMPLAINT-PRODUCT-P017",
        {
            "analysis_type": "High Complaint Product",
            "severity": "High",
            "product_id": "P017",
        },
        id="seeded-high-complaint-product",
    ),
    pytest.param(
        "/api/analytics/vendors",
        {
            "severity": "High",
            "analysis_type": "Low On-Time Delivery Rate",
            "vendor_id": "V009",
            "limit": 100,
        },
        "LOW-ON-TIME-RATE-V009",
        {
            "analysis_type": "Low On-Time Delivery Rate",
            "severity": "High",
            "vendor_id": "V009",
        },
        id="seeded-low-vendor-on-time-rate",
    ),
    pytest.param(
        "/api/analytics/finance",
        {
            "severity": "High",
            "analysis_type": "High Financial Risk",
            "store_id": "S003",
            "month": "2026-06",
            "risk_status": "High Risk",
            "limit": 100,
        },
        "HIGH-FINANCIAL-RISK-S003-2026-06",
        {
            "analysis_type": "High Financial Risk",
            "severity": "High",
            "store_id": "S003",
            "month": "2026-06",
            "risk_status": "High Risk",
        },
        id="seeded-high-financial-risk",
    ),
]


def get_finding_by_id(
    response_data: dict[str, Any],
    finding_id: str,
) -> dict[str, Any]:
    """Return one expected finding from an analytics response."""

    for finding in response_data["findings"]:
        if finding["finding_id"] == finding_id:
            return finding

    pytest.fail(
        f"Expected finding '{finding_id}' was not returned."
    )


@pytest.mark.integration
def test_seeded_analytics_uses_isolated_test_database() -> None:
    """Integration analytics must run only against the test database."""

    from sqlalchemy import text

    from backend.app.db.database import engine

    with engine.connect() as connection:
        actual_database = connection.execute(
            text("SELECT current_database();")
        ).scalar_one()

    assert actual_database == EXPECTED_TEST_DATABASE
    assert str(actual_database).endswith("_test")


@pytest.mark.integration
def test_seeded_kpis_match_expected_business_baseline(
    client: Any,
) -> None:
    """Real KPI calculations should match the seeded business baseline."""

    response = client.get("/api/kpis")

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["total_kpis"] == 12
    assert (
        len(
            response_data[
                "latest_store_target_achievement"
            ]
        )
        == 10
    )

    actual_display_values = {
        kpi["kpi_name"]: kpi["display_value"]
        for kpi in response_data["kpis"]
    }

    assert actual_display_values == SEEDED_KPI_DISPLAY_VALUES


@pytest.mark.integration
@pytest.mark.parametrize(
    ("endpoint", "expected_total_findings"),
    SEEDED_ANALYTICS_BASELINES,
)
def test_seeded_analytics_totals_match_expected_baseline(
    client: Any,
    endpoint: str,
    expected_total_findings: int,
) -> None:
    """Real analytics should reproduce the frozen seeded baseline."""

    response = client.get(
        endpoint,
        params={
            "limit": 100,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "success"
    assert (
        response_data["total_findings"]
        == expected_total_findings
    )
    assert (
        response_data["matching_findings"]
        == expected_total_findings
    )
    assert response_data["limit"] == 100
    assert response_data["offset"] == 0
    assert len(response_data["findings"]) == min(
        expected_total_findings,
        100,
    )

    summary_total = sum(
        summary_item["finding_count"]
        for summary_item in response_data["summary"]
    )

    assert summary_total == expected_total_findings


@pytest.mark.integration
@pytest.mark.parametrize(
    (
        "endpoint",
        "query_parameters",
        "expected_finding_id",
        "expected_fields",
    ),
    SEEDED_CRITICAL_SCENARIOS,
)
def test_seeded_critical_business_scenarios_are_detected(
    client: Any,
    endpoint: str,
    query_parameters: dict[str, Any],
    expected_finding_id: str,
    expected_fields: dict[str, Any],
) -> None:
    """Seeded high-priority business scenarios must be detected."""

    response = client.get(
        endpoint,
        params=query_parameters,
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["matching_findings"] >= 1

    finding = get_finding_by_id(
        response_data,
        expected_finding_id,
    )

    for field_name, expected_value in expected_fields.items():
        assert finding[field_name] == expected_value

    assert finding["summary"]
    assert finding["evidence"]
    assert finding["status"] == "Open"


@pytest.mark.integration
def test_seeded_inventory_api_serializes_missing_expiry_as_null(
    client: Any,
) -> None:
    """Non-expiring inventory findings must return JSON null, not NaT."""

    response = client.get(
        "/api/analytics/inventory",
        params={
            "product_id": "P024",
            "limit": 100,
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["matching_findings"] >= 1
    assert response_data["findings"]

    assert all(
        finding["expiry_date"] is None
        for finding in response_data["findings"]
    )
