from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any

import backend.app.tools.business_read_tools as read_tools_module
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
from backend.app.tools.business_read_tools import (
    READ_ONLY_BUSINESS_TOOL_NAMES,
    register_read_only_business_tools,
)


NOW = datetime(2026, 8, 31, 12, 0, 0)


def build_issue_response() -> dict[str, Any]:
    return {
        "status": "success",
        "issue": {
            "issue_id": "ISSUE-HIGH-001",
            "title": "Restore product availability",
            "issue_type": "Product Availability Risk",
            "business_area": "Inventory",
            "priority_level": "High",
            "priority_score": 95.0,
            "priority_reason": "High business impact.",
            "status": "Open",
            "entity_type": "Product",
            "entity_id": "P017",
            "store_id": "S003",
            "product_id": "P017",
            "vendor_id": "V004",
            "period_label": "2026-06",
            "finding_count": 2,
            "high_finding_count": 2,
            "medium_finding_count": 0,
            "low_finding_count": 0,
            "root_cause_status": "Complete",
            "summary": "Availability risk detected.",
            "evidence_summary": "Low stock and delayed supply.",
            "created_at": NOW,
            "updated_at": NOW,
            "last_detected_at": NOW,
        },
        "evidence_count": 1,
        "evidence": [
            {
                "evidence_id": 7,
                "source_finding_id": "LOW-STOCK-S003-P017",
                "source_report": "inventory_analysis",
                "source_module": "inventory_analysis",
                "analysis_type": "Low Stock",
                "business_area": "Inventory",
                "severity": "High",
                "entity_type": "Product",
                "entity_id": "P017",
                "store_id": "S003",
                "product_id": "P017",
                "vendor_id": "V004",
                "summary": "Stock is below the reorder trigger.",
                "evidence": "Current stock is below threshold.",
                "detected_at": NOW,
                "created_at": NOW,
            }
        ],
        "root_cause": {
            "root_cause_analysis_id": 3,
            "root_cause_category": "Supply Availability",
            "root_cause_summary": "Delayed replenishment.",
            "root_cause_explanation": (
                "Delayed supply contributed to the low stock position."
            ),
            "confidence_score": 0.9,
            "evidence_count": 1,
            "analysis_status": "Complete",
            "review_status": "Pending Review",
            "analysis_version": 1,
            "generated_at": NOW,
            "reviewed_at": None,
            "updated_at": NOW,
        },
    }


def build_recommendation_response() -> dict[str, Any]:
    return {
        "status": "success",
        "recommendation": {
            "recommendation_id": 21,
            "issue_id": "ISSUE-HIGH-001",
            "recommendation_title": "Restore product availability",
            "recommendation_text": (
                "Expedite replenishment and verify supplier delivery."
            ),
            "suggested_owner_role": "Inventory Manager",
            "suggested_deadline": date(2026, 9, 2),
            "expected_impact": "Reduce product availability risk.",
            "confidence_score": 0.9,
            "status": "Pending Review",
            "issue_title": "Restore product availability",
            "issue_type": "Product Availability Risk",
            "business_area": "Inventory",
            "priority_level": "High",
            "priority_score": 95.0,
            "issue_status": "Open",
            "root_cause_category": "Supply Availability",
            "root_cause_summary": "Delayed replenishment.",
            "root_cause_explanation": (
                "Delayed supply contributed to the low stock position."
            ),
            "root_cause_confidence": 0.9,
            "root_cause_review_status": "Pending Review",
            "created_at": NOW,
            "updated_at": NOW,
        },
    }


def build_task_response() -> dict[str, Any]:
    return {
        "status": "success",
        "task": {
            "task_id": 31,
            "issue_id": "ISSUE-HIGH-001",
            "recommendation_id": 21,
            "title": "Expedite replenishment",
            "description": "Follow up with supplier.",
            "assigned_to": None,
            "assigned_role": "Inventory Manager",
            "due_date": date(2026, 9, 2),
            "priority_level": "High",
            "status": "To Do",
            "issue_title": "Restore product availability",
            "recommendation_title": "Restore product availability",
            "issue_type": "Product Availability Risk",
            "business_area": "Inventory",
            "issue_status": "Open",
            "recommendation_status": "Converted to Task",
            "created_at": NOW,
            "updated_at": NOW,
        },
    }


def build_brief_response() -> dict[str, Any]:
    return {
        "status": "success",
        "generated_at": NOW,
        "brief": {
            "brief_id": 11,
            "brief_date": date(2026, 8, 31),
            "brief_type": "Daily Executive Brief",
            "summary_text": "Current operating snapshot.",
            "brief_data": {"brief_version": 1},
            "status": "Draft",
            "created_at": NOW,
            "updated_at": NOW,
        },
    }


def build_executor() -> AgentToolExecutor:
    registry = ToolRegistry()
    register_read_only_business_tools(registry)
    return AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=False,
        timeout_seconds=1.0,
    )


def build_context(
    *,
    agent_name: str,
    allowed_tools: list[str],
) -> ToolExecutionContext:
    return ToolExecutionContext(
        run_id="RUN-READ-TOOLS-001",
        agent_name=agent_name,
        requested_by="pytest",
        allowed_tools=allowed_tools,
        allow_write_tools=False,
        approved_write_tools=[],
    )


def test_application_service_registers_all_six_read_tools() -> None:
    registered_tool_names = set(
        list_registered_agent_tools()
    )

    assert set(
        READ_ONLY_BUSINESS_TOOL_NAMES
    ).issubset(
        registered_tool_names
    )


def test_all_business_tool_definitions_are_read_only() -> None:
    registry = ToolRegistry()
    register_read_only_business_tools(registry)

    for definition in registry.definitions():
        assert definition.access_mode == ToolAccessMode.READ_ONLY
        assert definition.requires_human_approval is False


def test_get_issue_returns_only_issue_section(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        read_tools_module,
        "get_issue_detail",
        lambda issue_id: build_issue_response(),
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_issue",
            arguments={"issue_id": "ISSUE-HIGH-001"},
            context=build_context(
                agent_name="Root-Cause Agent",
                allowed_tools=["get_issue"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output["found"] is True
    assert result.output["issue"]["issue_id"] == "ISSUE-HIGH-001"
    assert "evidence" not in result.output
    assert "root_cause" not in result.output


def test_get_issue_evidence_returns_validated_evidence(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        read_tools_module,
        "get_issue_detail",
        lambda issue_id: build_issue_response(),
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_issue_evidence",
            arguments={"issue_id": "ISSUE-HIGH-001"},
            context=build_context(
                agent_name="Root-Cause Agent",
                allowed_tools=["get_issue_evidence"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output["found"] is True
    assert result.output["evidence_count"] == 1
    assert result.output["evidence"][0]["evidence_id"] == 7


def test_get_root_cause_returns_persisted_root_cause(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        read_tools_module,
        "get_issue_detail",
        lambda issue_id: build_issue_response(),
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_root_cause",
            arguments={"issue_id": "ISSUE-HIGH-001"},
            context=build_context(
                agent_name="Recommendation Agent",
                allowed_tools=["get_root_cause"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert (
        result.output["root_cause"]["root_cause_category"]
        == "Supply Availability"
    )


def test_get_recommendation_returns_validated_record(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        read_tools_module,
        "get_recommendation_detail",
        lambda recommendation_id: build_recommendation_response(),
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_recommendation",
            arguments={"recommendation_id": 21},
            context=build_context(
                agent_name="Executive Brief Agent",
                allowed_tools=["get_recommendation"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output["recommendation"]["recommendation_id"] == 21


def test_get_task_returns_validated_record(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        read_tools_module,
        "get_task_detail",
        lambda task_id: build_task_response(),
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_task",
            arguments={"task_id": 31},
            context=build_context(
                agent_name="Executive Brief Agent",
                allowed_tools=["get_task"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output["task"]["task_id"] == 31


def test_get_executive_brief_reads_latest_stored_record_only(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []

    def fake_latest() -> dict[str, Any]:
        calls.append("latest")
        return build_brief_response()

    monkeypatch.setattr(
        read_tools_module,
        "get_latest_executive_brief",
        fake_latest,
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_executive_brief",
            arguments={},
            context=build_context(
                agent_name="Executive Brief Agent",
                allowed_tools=["get_executive_brief"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output["brief"]["brief_id"] == 11
    assert calls == ["latest"]


def test_missing_records_return_found_false(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        read_tools_module,
        "get_issue_detail",
        lambda issue_id: None,
    )
    monkeypatch.setattr(
        read_tools_module,
        "get_recommendation_detail",
        lambda recommendation_id: None,
    )
    monkeypatch.setattr(
        read_tools_module,
        "get_task_detail",
        lambda task_id: None,
    )
    monkeypatch.setattr(
        read_tools_module,
        "get_latest_executive_brief",
        lambda: None,
    )

    executor = build_executor()

    cases = [
        (
            "get_issue",
            {"issue_id": "MISSING"},
            "Root-Cause Agent",
        ),
        (
            "get_recommendation",
            {"recommendation_id": 999},
            "Recommendation Agent",
        ),
        (
            "get_task",
            {"task_id": 999},
            "Executive Brief Agent",
        ),
        (
            "get_executive_brief",
            {},
            "Executive Brief Agent",
        ),
    ]

    for tool_name, arguments, agent_name in cases:
        result = asyncio.run(
            executor.execute(
                tool_name=tool_name,
                arguments=arguments,
                context=build_context(
                    agent_name=agent_name,
                    allowed_tools=[tool_name],
                ),
            )
        )
        assert result.status == ToolExecutionStatus.SUCCESS
        assert result.output["found"] is False


def test_agent_allowlist_blocks_unapproved_read_tool(monkeypatch: Any) -> None:
    calls: list[str] = []

    def fake_issue_detail(issue_id: str) -> dict[str, Any]:
        calls.append(issue_id)
        return build_issue_response()

    monkeypatch.setattr(
        read_tools_module,
        "get_issue_detail",
        fake_issue_detail,
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_issue_evidence",
            arguments={"issue_id": "ISSUE-HIGH-001"},
            context=build_context(
                agent_name="Monitoring Agent",
                allowed_tools=["get_issue_evidence"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED
    assert calls == []


def test_invalid_arguments_fail_before_service_call(monkeypatch: Any) -> None:
    calls: list[str] = []

    def fake_task_detail(task_id: int) -> dict[str, Any]:
        calls.append(str(task_id))
        return build_task_response()

    monkeypatch.setattr(
        read_tools_module,
        "get_task_detail",
        fake_task_detail,
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name="get_task",
            arguments={"task_id": 0, "unexpected": "value"},
            context=build_context(
                agent_name="Executive Brief Agent",
                allowed_tools=["get_task"],
            ),
        )
    )

    assert result.status == ToolExecutionStatus.FAILED
    assert result.call_record.error_type == "ToolInputValidationError"
    assert calls == []
