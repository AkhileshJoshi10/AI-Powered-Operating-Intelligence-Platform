from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any

import backend.app.tools.analytics_read_tools as analytics_tools_module
from backend.app.services.agent_tool_service import (
    list_registered_agent_tools,
)
from backend.app.tools import (
    AgentToolExecutor,
    ToolAccessMode,
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolRegistry,
)
from backend.app.tools.analytics_read_tools import (
    READ_ONLY_ANALYTICS_TOOL_NAMES,
    register_read_only_analytics_tools,
)
from backend.app.tools.business_read_tools import (
    READ_ONLY_BUSINESS_TOOL_NAMES,
)


NOW = datetime(2026, 8, 31, 12, 0, 0)


def build_context(
    *,
    agent_name: str,
    allowed_tools: list[str],
) -> ToolExecutionContext:
    return ToolExecutionContext(
        run_id="RUN-ANALYTICS-TOOLS-001",
        agent_name=agent_name,
        requested_by="pytest",
        allowed_tools=allowed_tools,
        allow_write_tools=False,
        approved_write_tools=[],
    )


def build_executor() -> AgentToolExecutor:
    registry = ToolRegistry()
    register_read_only_analytics_tools(registry)

    return AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=False,
        timeout_seconds=1.0,
    )


def build_kpi_response() -> dict[str, Any]:
    return {
        "status": "success",
        "total_kpis": 1,
        "kpis": [
            {
                "kpi_key": "total_sales",
                "kpi_name": "Total Sales",
                "value": 125000.0,
                "display_value": "₹125,000.00",
                "unit": "Currency",
                "reference_period": "2026-06",
                "description": "Validated sales total.",
                "calculated_at": "2026-08-31T12:00:00",
            }
        ],
        "latest_store_target_achievement": [],
    }


def build_response(
    finding: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "success",
        "generated_at": NOW,
        "total_findings": 1,
        "matching_findings": 1,
        "limit": 10,
        "offset": 0,
        "summary": [
            {
                "analysis_type": finding["analysis_type"],
                "severity": finding["severity"],
                "finding_count": 1,
            }
        ],
        "findings": [finding],
    }


SALES_FINDING = {
    "finding_id": "SALES-001",
    "analysis_type": "Store Sales Decline",
    "business_area": "Sales",
    "severity": "High",
    "entity_type": "Store",
    "entity_id": "S003",
    "entity_name": "SmartMart Store 3",
    "store_id": "S003",
    "store_name": "SmartMart Store 3",
    "product_id": None,
    "product_name": None,
    "region": "North",
    "category": None,
    "month": "2026-06",
    "previous_month": "2026-05",
    "current_sales": 50000.0,
    "previous_sales": 80000.0,
    "sales_change_percent": -37.5,
    "benchmark_value": -15.0,
    "benchmark_label": "Decline threshold",
    "target_achievement_percent": 60.0,
    "summary": "Sales declined.",
    "evidence": "Current sales are below the prior month.",
    "status": "Open",
    "detected_at": NOW,
}

INVENTORY_FINDING = {
    "finding_id": "INV-001",
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
    "inventory_date": date(2026, 6, 30),
    "expiry_date": None,
    "days_to_expiry": None,
    "current_stock": 4.0,
    "reorder_level": 10.0,
    "stock_ratio": 0.4,
    "stock_status": "Low Stock",
    "reorder_required": "Yes",
    "related_complaints": 0,
    "high_severity_complaints": 0,
    "summary": "Low stock detected.",
    "evidence": "Stock is below the reorder trigger.",
    "status": "Open",
    "detected_at": NOW,
}

COMPLAINT_FINDING = {
    "finding_id": "COMP-001",
    "analysis_type": "High Severity Complaint",
    "business_area": "Customer Service",
    "severity": "High",
    "entity_type": "Complaint",
    "entity_id": "COMP00001",
    "entity_name": "Complaint COMP00001",
    "store_id": "S003",
    "store_name": "SmartMart Store 3",
    "product_id": "P011",
    "product_name": "Product 11",
    "region": "North",
    "complaint_id": "COMP00001",
    "complaint_type": "Product Quality",
    "complaint_severity": "High",
    "complaint_status": "Open",
    "complaint_date": date(2026, 6, 20),
    "complaint_age_days": 10,
    "total_complaints": None,
    "high_severity_complaints": None,
    "unresolved_complaints": None,
    "monthly_growth_percent": None,
    "benchmark_value": None,
    "benchmark_label": None,
    "summary": "High-severity complaint is open.",
    "evidence": "Complaint remains unresolved.",
    "status": "Open",
    "detected_at": NOW,
}

VENDOR_FINDING = {
    "finding_id": "VENDOR-001",
    "analysis_type": "Vendor Delivery Delay",
    "business_area": "Procurement",
    "severity": "High",
    "entity_type": "Vendor",
    "entity_id": "V004",
    "entity_name": "Vendor 4",
    "vendor_id": "V004",
    "vendor_name": "Vendor 4",
    "delivery_count": 10,
    "delayed_deliveries": 6,
    "partial_deliveries": 1,
    "average_delay_days": 3.5,
    "maximum_delay_days": 8.0,
    "average_quality_rating": 3.2,
    "on_time_delivery_rate": 40.0,
    "summary": "Vendor delays detected.",
    "evidence": "Six of ten deliveries were delayed.",
    "status": "Open",
    "detected_at": NOW,
}

FINANCE_FINDING = {
    "finding_id": "FINANCE-001",
    "analysis_type": "Financial Risk",
    "business_area": "Finance",
    "severity": "High",
    "entity_type": "Store Month",
    "entity_id": "S003-2026-06",
    "entity_name": "SmartMart Store 3 - 2026-06",
    "store_id": "S003",
    "store_name": "SmartMart Store 3",
    "month": "2026-06",
    "total_revenue": 50000.0,
    "operating_profit": -5000.0,
    "operating_profit_margin_percent": -10.0,
    "target_achievement_percent": 60.0,
    "risk_status": "High Risk",
    "summary": "Financial risk detected.",
    "evidence": "Operating profit is negative.",
    "status": "Open",
    "detected_at": NOW,
}


def test_application_registry_contains_business_and_analytics_tools() -> None:
    expected = set(
        READ_ONLY_BUSINESS_TOOL_NAMES
    ) | set(
        READ_ONLY_ANALYTICS_TOOL_NAMES
    )

    assert expected.issubset(
        set(
            list_registered_agent_tools()
        )
    )


def test_every_analytics_tool_is_read_only() -> None:
    registry = ToolRegistry()
    register_read_only_analytics_tools(registry)

    for definition in registry.definitions():
        assert definition.access_mode == ToolAccessMode.READ_ONLY
        assert definition.requires_human_approval is False


def test_kpi_tool_returns_validated_snapshot(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        analytics_tools_module,
        "get_kpi_response",
        build_kpi_response,
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_kpi_snapshot",
            arguments={},
            context=build_context(
                agent_name="Monitoring Agent",
                allowed_tools=["get_kpi_snapshot"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output["total_kpis"] == 1
    assert result.output["kpis"][0]["kpi_key"] == "total_sales"


def test_sales_tool_forwards_only_validated_filters(monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []

    def fake_service(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return build_response(SALES_FINDING)

    monkeypatch.setattr(
        analytics_tools_module,
        "get_sales_analytics",
        fake_service,
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_sales_analytics",
            arguments={
                "severity": "High",
                "analysis_type": "Store Sales Decline",
                "limit": 10,
                "offset": 0,
            },
            context=build_context(
                agent_name="Root-Cause Agent",
                allowed_tools=["get_sales_analytics"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert calls == [
        {
            "severity": "High",
            "analysis_type": "Store Sales Decline",
            "limit": 10,
            "offset": 0,
        }
    ]


def test_inventory_tool_forwards_entity_filters(monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []

    def fake_service(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return build_response(INVENTORY_FINDING)

    monkeypatch.setattr(
        analytics_tools_module,
        "get_inventory_analytics",
        fake_service,
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_inventory_analytics",
            arguments={
                "severity": "High",
                "analysis_type": "Low Stock",
                "store_id": "S003",
                "product_id": "P017",
                "vendor_id": "V004",
                "limit": 10,
                "offset": 0,
            },
            context=build_context(
                agent_name="Root-Cause Agent",
                allowed_tools=["get_inventory_analytics"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert calls[0]["store_id"] == "S003"
    assert calls[0]["product_id"] == "P017"
    assert calls[0]["vendor_id"] == "V004"


def test_complaint_tool_forwards_bounded_filters(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        analytics_tools_module,
        "get_complaint_analytics",
        lambda **kwargs: build_response(COMPLAINT_FINDING),
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_complaint_analytics",
            arguments={
                "store_id": "S003",
                "product_id": "P011",
                "region": "North",
                "complaint_type": "Product Quality",
                "complaint_status": "Open",
            },
            context=build_context(
                agent_name="Monitoring Agent",
                allowed_tools=["get_complaint_analytics"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output["findings"][0]["complaint_id"] == "COMP00001"


def test_vendor_tool_returns_validated_findings(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        analytics_tools_module,
        "get_vendor_analytics",
        lambda **kwargs: build_response(VENDOR_FINDING),
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_vendor_analytics",
            arguments={
                "vendor_id": "V004",
            },
            context=build_context(
                agent_name="Monitoring Agent",
                allowed_tools=["get_vendor_analytics"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output["findings"][0]["vendor_id"] == "V004"


def test_finance_tool_validates_month_filter(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        analytics_tools_module,
        "get_finance_analytics",
        lambda **kwargs: build_response(FINANCE_FINDING),
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_finance_analytics",
            arguments={
                "store_id": "S003",
                "month": "2026-06",
                "risk_status": "High Risk",
            },
            context=build_context(
                agent_name="Root-Cause Agent",
                allowed_tools=["get_finance_analytics"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output["findings"][0]["month"] == "2026-06"


def test_invalid_month_is_rejected_before_service(monkeypatch: Any) -> None:
    calls: list[str] = []

    def fake_service(**kwargs: Any) -> dict[str, Any]:
        calls.append("called")
        return build_response(FINANCE_FINDING)

    monkeypatch.setattr(
        analytics_tools_module,
        "get_finance_analytics",
        fake_service,
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_finance_analytics",
            arguments={
                "month": "June-2026",
            },
            context=build_context(
                agent_name="Root-Cause Agent",
                allowed_tools=["get_finance_analytics"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.FAILED
    assert result.call_record.error_type == "ToolInputValidationError"
    assert calls == []


def test_result_limit_cannot_exceed_twenty(monkeypatch: Any) -> None:
    calls: list[str] = []

    def fake_service(**kwargs: Any) -> dict[str, Any]:
        calls.append("called")
        return build_response(SALES_FINDING)

    monkeypatch.setattr(
        analytics_tools_module,
        "get_sales_analytics",
        fake_service,
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_sales_analytics",
            arguments={
                "limit": 100,
            },
            context=build_context(
                agent_name="Monitoring Agent",
                allowed_tools=["get_sales_analytics"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.FAILED
    assert result.call_record.error_type == "ToolInputValidationError"
    assert calls == []


def test_arbitrary_sql_or_query_argument_is_rejected(monkeypatch: Any) -> None:
    calls: list[str] = []

    def fake_service(**kwargs: Any) -> dict[str, Any]:
        calls.append("called")
        return build_response(SALES_FINDING)

    monkeypatch.setattr(
        analytics_tools_module,
        "get_sales_analytics",
        fake_service,
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_sales_analytics",
            arguments={
                "query": "SELECT * FROM sales",
                "sql": "DROP TABLE sales",
            },
            context=build_context(
                agent_name="Monitoring Agent",
                allowed_tools=["get_sales_analytics"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.FAILED
    assert result.call_record.error_type == "ToolInputValidationError"
    assert calls == []


def test_recommendation_agent_cannot_run_raw_analytics(monkeypatch: Any) -> None:
    calls: list[str] = []

    def fake_service(**kwargs: Any) -> dict[str, Any]:
        calls.append("called")
        return build_response(INVENTORY_FINDING)

    monkeypatch.setattr(
        analytics_tools_module,
        "get_inventory_analytics",
        fake_service,
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_inventory_analytics",
            arguments={},
            context=build_context(
                agent_name="Recommendation Agent",
                allowed_tools=["get_inventory_analytics"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED
    assert calls == []


def test_malformed_service_output_is_rejected(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        analytics_tools_module,
        "get_sales_analytics",
        lambda **kwargs: {
            "status": "success",
            "findings": [],
        },
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_sales_analytics",
            arguments={},
            context=build_context(
                agent_name="Monitoring Agent",
                allowed_tools=["get_sales_analytics"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.FAILED
    assert result.call_record.error_type == "ToolExecutionError"
