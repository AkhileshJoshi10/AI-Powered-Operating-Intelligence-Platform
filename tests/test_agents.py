from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from backend.app.agents import (
    AgentContext,
    AgentExecutionStatus,
    AgentOrchestrator,
    BaseAgent,
    PostgresAgentRunLogger,
)
from backend.app.db.database import engine


class SuccessfulAgent(BaseAgent):
    """Agent used to test successful execution."""

    name = "Successful Agent"
    description = "Returns a successful deterministic result."

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        return {
            "summary": "Successful agent completed.",
            "run_id_received": context.run_id,
            "issue_count": len(context.issue_ids),
        }


class FailingAgent(BaseAgent):
    """Agent used to test primary execution failure."""

    name = "Failing Agent"
    description = "Raises a controlled execution error."

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        del context

        raise ValueError(
            "Simulated primary agent failure."
        )


class FallbackAgent(BaseAgent):
    """Agent used to test deterministic fallback execution."""

    name = "Fallback Agent"
    description = "Uses fallback logic after primary failure."

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        del context

        raise RuntimeError(
            "Simulated LLM execution failure."
        )

    async def fallback(
        self,
        context: AgentContext,
        error: Exception,
    ) -> dict[str, Any] | None:
        return {
            "summary": "Deterministic fallback completed.",
            "run_id_received": context.run_id,
            "primary_error": str(error),
        }


class BrokenFallbackAgent(BaseAgent):
    """Agent used to test failure in primary and fallback logic."""

    name = "Broken Fallback Agent"
    description = "Fails during both primary and fallback execution."

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        del context

        raise RuntimeError(
            "Simulated primary failure."
        )

    async def fallback(
        self,
        context: AgentContext,
        error: Exception,
    ) -> dict[str, Any] | None:
        del context
        del error

        raise TypeError(
            "Simulated fallback failure."
        )


class InvalidOutputAgent(BaseAgent):
    """Agent used to test invalid output handling."""

    name = "Invalid Output Agent"
    description = "Returns a value that is not a dictionary."

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        del context

        return ["invalid-output"]  # type: ignore[return-value]


class FirstSequenceAgent(BaseAgent):
    """First agent in the sequence test."""

    name = "First Sequence Agent"
    description = "Produces output for a later agent."

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        return {
            "summary": "First sequence result.",
            "shared_value": "available-to-next-agent",
            "run_id_received": context.run_id,
        }


class SecondSequenceAgent(BaseAgent):
    """Second agent in the sequence test."""

    name = "Second Sequence Agent"
    description = "Reads the previous agent result."

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        previous_results = context.metadata.get(
            "previous_agent_results",
            {},
        )

        first_result = previous_results.get(
            "First Sequence Agent",
            {},
        )

        return {
            "summary": "Second sequence result.",
            "previous_summary": first_result.get(
                "summary"
            ),
            "previous_shared_value": (
                first_result.get(
                    "output_data",
                    {},
                ).get(
                    "shared_value"
                )
            ),
        }


class FailingRunLogger:
    """Logger used to simulate persistence failure."""

    def save_result(
        self,
        *,
        context: AgentContext,
        result: Any,
    ) -> int:
        del context
        del result

        raise RuntimeError(
            "Simulated agent-run logging failure."
        )


def test_agent_context_normalizes_values_and_deduplicates_issue_ids(
) -> None:
    """Agent context should normalize its controlled text fields."""

    context = AgentContext(
        run_id="  test-run-001  ",
        run_type="  scheduled   monitoring  ",
        requested_by="  Operations   Manager  ",
        issue_ids=[
            " ISSUE-001 ",
            "ISSUE-002",
            "ISSUE-001",
            "",
        ],
        input_data={
            "source": "pytest",
        },
    )

    assert context.run_id == "test-run-001"
    assert context.run_type == "scheduled monitoring"
    assert context.requested_by == "Operations Manager"
    assert context.issue_ids == [
        "ISSUE-001",
        "ISSUE-002",
    ]
    assert context.input_data == {
        "source": "pytest",
    }
    assert context.created_at.tzinfo is not None


def test_agent_context_rejects_unknown_fields(
) -> None:
    """Unknown fields should not silently enter agent context."""

    with pytest.raises(
        ValidationError
    ):
        AgentContext(
            run_type="manual",
            unsupported_field=True,
        )


def test_base_agent_returns_success_result(
) -> None:
    """Successful execution should return a structured result."""

    context = AgentContext(
        run_type="unit-test",
        issue_ids=[
            "ISSUE-001",
            "ISSUE-002",
        ],
    )

    result = asyncio.run(
        SuccessfulAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )
    assert result.agent_name == "Successful Agent"
    assert result.run_id == context.run_id
    assert result.run_type == "unit-test"
    assert result.summary == "Successful agent completed."
    assert result.output_data["issue_count"] == 2
    assert result.used_fallback is False
    assert result.error_type is None
    assert result.error_message is None
    assert result.duration_ms >= 0
    assert result.agent_run_id is None
    assert result.log_persisted is False
    assert result.logging_error is None


def test_base_agent_returns_failure_result_without_fallback(
) -> None:
    """An unhandled primary failure should become a failed result."""

    context = AgentContext(
        run_type="unit-test",
    )

    result = asyncio.run(
        FailingAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.FAILED
    )
    assert result.used_fallback is False
    assert result.error_type == "ValueError"
    assert (
        result.error_message
        == "Simulated primary agent failure."
    )
    assert result.output_data == {}
    assert (
        result.summary
        == "Failing Agent failed during execution."
    )


def test_base_agent_uses_successful_fallback(
) -> None:
    """Fallback output should preserve the primary error details."""

    context = AgentContext(
        run_type="fallback-test",
    )

    result = asyncio.run(
        FallbackAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )
    assert result.used_fallback is True
    assert result.error_type == "RuntimeError"
    assert (
        result.error_message
        == "Simulated LLM execution failure."
    )
    assert (
        result.summary
        == "Deterministic fallback completed."
    )
    assert (
        result.output_data["run_id_received"]
        == context.run_id
    )


def test_base_agent_reports_fallback_failure(
) -> None:
    """Failure in both execution paths should return Failed."""

    context = AgentContext(
        run_type="fallback-failure-test",
    )

    result = asyncio.run(
        BrokenFallbackAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.FAILED
    )
    assert result.used_fallback is False
    assert result.error_type == "TypeError"
    assert "Primary error:" in (
        result.error_message
        or ""
    )
    assert "Fallback error:" in (
        result.error_message
        or ""
    )
    assert (
        result.summary
        == (
            "Broken Fallback Agent failed, "
            "and its fallback also failed."
        )
    )


def test_base_agent_rejects_non_dictionary_output(
) -> None:
    """Agent execution output must follow the dictionary contract."""

    context = AgentContext(
        run_type="invalid-output-test",
    )

    result = asyncio.run(
        InvalidOutputAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.FAILED
    )
    assert result.error_type == "TypeError"
    assert (
        result.error_message
        == "Agent run output must be a dictionary."
    )


def test_orchestrator_rejects_duplicate_agent_names(
) -> None:
    """Agent names must be unique within one orchestrator."""

    orchestrator = AgentOrchestrator(
        agents=[
            SuccessfulAgent(),
        ]
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        orchestrator.register_agent(
            SuccessfulAgent()
        )


def test_orchestrator_rejects_unknown_agent(
) -> None:
    """Requesting an unregistered agent should raise KeyError."""

    orchestrator = AgentOrchestrator()

    with pytest.raises(
        KeyError,
        match="not registered",
    ):
        orchestrator.get_agent(
            "Unknown Agent"
        )


def test_orchestrator_sequence_shares_previous_results(
) -> None:
    """Later agents should receive earlier structured results."""

    context = AgentContext(
        run_type="sequence-test",
    )

    orchestrator = AgentOrchestrator(
        agents=[
            FirstSequenceAgent(),
            SecondSequenceAgent(),
        ]
    )

    results = asyncio.run(
        orchestrator.run_sequence(
            agent_names=[
                "First Sequence Agent",
                "Second Sequence Agent",
            ],
            context=context,
        )
    )

    assert len(results) == 2

    assert (
        results[0].execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert (
        results[1].execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert (
        results[1].output_data[
            "previous_summary"
        ]
        == "First sequence result."
    )

    assert (
        results[1].output_data[
            "previous_shared_value"
        ]
        == "available-to-next-agent"
    )


def test_orchestrator_sequence_stops_after_failure(
) -> None:
    """The sequence should stop when stop_on_failure is enabled."""

    context = AgentContext(
        run_type="stop-on-failure-test",
    )

    orchestrator = AgentOrchestrator(
        agents=[
            FailingAgent(),
            SecondSequenceAgent(),
        ]
    )

    results = asyncio.run(
        orchestrator.run_sequence(
            agent_names=[
                "Failing Agent",
                "Second Sequence Agent",
            ],
            context=context,
            stop_on_failure=True,
        )
    )

    assert len(results) == 1
    assert (
        results[0].execution_status
        == AgentExecutionStatus.FAILED
    )


def test_orchestrator_preserves_result_when_logging_fails(
) -> None:
    """A logging error should not replace a successful result."""

    context = AgentContext(
        run_type="logging-failure-test",
    )

    orchestrator = AgentOrchestrator(
        agents=[
            SuccessfulAgent(),
        ],
        run_logger=FailingRunLogger(),
    )

    result = asyncio.run(
        orchestrator.run_agent(
            "Successful Agent",
            context,
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )
    assert result.agent_run_id is None
    assert result.log_persisted is False
    assert (
        result.logging_error
        == "Simulated agent-run logging failure."
    )


def test_postgres_logger_rejects_mismatched_run_ids(
) -> None:
    """The logger should reject unrelated context and result data."""

    first_context = AgentContext(
        run_type="mismatch-test",
    )

    second_context = AgentContext(
        run_type="mismatch-test",
    )

    result = asyncio.run(
        SuccessfulAgent().execute(
            first_context
        )
    )

    logger = PostgresAgentRunLogger(
        engine
    )

    with pytest.raises(
        ValueError,
        match="run IDs do not match",
    ):
        logger.save_result(
            context=second_context,
            result=result,
        )


@pytest.mark.integration
def test_postgres_logger_persists_and_deletes_agent_run(
) -> None:
    """A real agent execution should be logged in the test database."""

    agent_run_id: int | None = None

    with engine.connect() as connection:
        actual_database = connection.execute(
            text(
                "SELECT current_database();"
            )
        ).scalar_one()

    assert (
        actual_database
        == "ai_operating_intelligence_test"
    )

    context = AgentContext(
        run_type="pytest-agent-integration",
        requested_by="pytest",
        issue_ids=[
            "TEST-ISSUE-001",
        ],
        input_data={
            "test_mode": True,
        },
    )

    orchestrator = AgentOrchestrator(
        agents=[
            SuccessfulAgent(),
        ],
        run_logger=PostgresAgentRunLogger(
            engine
        ),
    )

    try:
        result = asyncio.run(
            orchestrator.run_agent(
                "Successful Agent",
                context,
            )
        )

        agent_run_id = result.agent_run_id

        assert (
            result.execution_status
            == AgentExecutionStatus.SUCCESS
        )
        assert result.log_persisted is True
        assert agent_run_id is not None
        assert result.logging_error is None

        with engine.connect() as connection:
            stored_record = connection.execute(
                text(
                    """
                    SELECT
                        agent_run_id,
                        agent_name,
                        run_type,
                        execution_status,
                        input_summary,
                        output_summary,
                        started_at,
                        completed_at
                    FROM agent_runs
                    WHERE agent_run_id = :agent_run_id;
                    """
                ),
                {
                    "agent_run_id": agent_run_id,
                },
            ).mappings().one()

        assert (
            stored_record["agent_name"]
            == "Successful Agent"
        )
        assert (
            stored_record["run_type"]
            == "pytest-agent-integration"
        )
        assert (
            stored_record["execution_status"]
            == "Success"
        )
        assert stored_record["started_at"] is not None
        assert stored_record["completed_at"] is not None

        input_summary = json.loads(
            stored_record["input_summary"]
        )

        output_summary = json.loads(
            stored_record["output_summary"]
        )

        assert (
            input_summary["run_id"]
            == context.run_id
        )
        assert input_summary["issue_count"] == 1
        assert (
            input_summary["issue_ids"]
            == ["TEST-ISSUE-001"]
        )
        assert (
            input_summary["input_data_keys"]
            == ["test_mode"]
        )

        assert (
            output_summary["run_id"]
            == context.run_id
        )
        assert (
            output_summary["summary"]
            == "Successful agent completed."
        )
        assert (
            output_summary["used_fallback"]
            is False
        )

    finally:
        if agent_run_id is not None:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        DELETE FROM agent_runs
                        WHERE agent_run_id = :agent_run_id;
                        """
                    ),
                    {
                        "agent_run_id": agent_run_id,
                    },
                )

# -------------------------------------------------------------------------
# Monitoring Agent tests
# -------------------------------------------------------------------------

import backend.app.agents.monitoring_agent as monitoring_module
from backend.app.agents import MonitoringAgent


def build_mock_monitoring_finding(
    *,
    finding_id: str,
    analysis_type: str,
    business_area: str,
    severity: str,
    entity_id: str,
) -> dict[str, Any]:
    """Build one analytics finding for Monitoring Agent tests."""

    return {
        "finding_id": finding_id,
        "analysis_type": analysis_type,
        "business_area": business_area,
        "severity": severity,
        "entity_type": "Test Entity",
        "entity_id": entity_id,
        "summary": f"Summary for {finding_id}.",
        "evidence": f"Evidence for {finding_id}.",
    }


def build_mock_monitoring_response(
    *,
    total_findings: int,
    high_count: int,
    medium_count: int,
    low_count: int,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build one valid analytics-service response."""

    summary: list[dict[str, Any]] = []

    for severity, finding_count in [
        ("High", high_count),
        ("Medium", medium_count),
        ("Low", low_count),
    ]:
        if finding_count > 0:
            summary.append(
                {
                    "analysis_type": "Test Analysis",
                    "severity": severity,
                    "finding_count": finding_count,
                }
            )

    return {
        "status": "success",
        "generated_at": "2026-08-04T04:30:00",
        "total_findings": total_findings,
        "matching_findings": total_findings,
        "limit": 10,
        "offset": 0,
        "summary": summary,
        "findings": findings,
    }


def configure_successful_monitoring_services(
    monkeypatch: Any,
) -> None:
    """Configure all Monitoring Agent services to succeed."""

    monkeypatch.setattr(
        monitoring_module,
        "get_kpi_response",
        lambda: {
            "status": "success",
            "total_kpis": 2,
            "kpis": [
                {
                    "kpi_key": "total_sales",
                    "kpi_name": "Total Sales",
                    "value": 100000.00,
                    "display_value": "₹100,000.00",
                    "unit": "Currency",
                    "reference_period": "2026-06",
                    "description": "Total sales value.",
                    "calculated_at": "2026-08-04T04:30:00",
                },
                {
                    "kpi_key": "low_stock_count",
                    "kpi_name": "Low-Stock Count",
                    "value": 5,
                    "display_value": "5",
                    "unit": "Count",
                    "reference_period": "2026-06",
                    "description": "Low-stock products.",
                    "calculated_at": "2026-08-04T04:30:00",
                },
            ],
            "latest_store_target_achievement": [],
        },
    )

    sales_response = build_mock_monitoring_response(
        total_findings=2,
        high_count=1,
        medium_count=1,
        low_count=0,
        findings=[
            build_mock_monitoring_finding(
                finding_id="SALES-HIGH-001",
                analysis_type="Store Sales Decline",
                business_area="Sales",
                severity="High",
                entity_id="S001",
            ),
            build_mock_monitoring_finding(
                finding_id="SALES-MEDIUM-001",
                analysis_type="Low Target Achievement",
                business_area="Sales",
                severity="Medium",
                entity_id="S002",
            ),
        ],
    )

    inventory_response = build_mock_monitoring_response(
        total_findings=3,
        high_count=1,
        medium_count=1,
        low_count=1,
        findings=[
            build_mock_monitoring_finding(
                finding_id="INVENTORY-HIGH-001",
                analysis_type="Low Stock",
                business_area="Operations",
                severity="High",
                entity_id="S001-P001",
            ),
            build_mock_monitoring_finding(
                finding_id="INVENTORY-LOW-001",
                analysis_type="Reorder Soon",
                business_area="Operations",
                severity="Low",
                entity_id="S002-P002",
            ),
        ],
    )

    complaint_response = build_mock_monitoring_response(
        total_findings=4,
        high_count=2,
        medium_count=2,
        low_count=0,
        findings=[
            build_mock_monitoring_finding(
                finding_id="COMPLAINT-HIGH-001",
                analysis_type="Open High-Severity Complaint",
                business_area="Customer Service",
                severity="High",
                entity_id="C001",
            ),
        ],
    )

    vendor_response = build_mock_monitoring_response(
        total_findings=2,
        high_count=1,
        medium_count=1,
        low_count=0,
        findings=[
            build_mock_monitoring_finding(
                finding_id="VENDOR-HIGH-001",
                analysis_type="Repeated Vendor Delays",
                business_area="Procurement",
                severity="High",
                entity_id="V001",
            ),
        ],
    )

    finance_response = build_mock_monitoring_response(
        total_findings=1,
        high_count=1,
        medium_count=0,
        low_count=0,
        findings=[
            build_mock_monitoring_finding(
                finding_id="FINANCE-HIGH-001",
                analysis_type="High Financial Risk",
                business_area="Finance",
                severity="High",
                entity_id="S001",
            ),
        ],
    )

    monkeypatch.setattr(
        monitoring_module,
        "get_sales_analytics",
        lambda **_: sales_response,
    )

    monkeypatch.setattr(
        monitoring_module,
        "get_inventory_analytics",
        lambda **_: inventory_response,
    )

    monkeypatch.setattr(
        monitoring_module,
        "get_complaint_analytics",
        lambda **_: complaint_response,
    )

    monkeypatch.setattr(
        monitoring_module,
        "get_vendor_analytics",
        lambda **_: vendor_response,
    )

    monkeypatch.setattr(
        monitoring_module,
        "get_finance_analytics",
        lambda **_: finance_response,
    )


def test_monitoring_agent_returns_complete_snapshot(
    monkeypatch: Any,
) -> None:
    """All successful services should produce a complete snapshot."""

    configure_successful_monitoring_services(
        monkeypatch
    )

    context = AgentContext(
        run_type="monitoring-unit-test",
        input_data={
            "finding_limit": 5,
        },
    )

    result = asyncio.run(
        MonitoringAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )
    assert result.used_fallback is False

    output_data = result.output_data

    assert (
        output_data["monitoring_status"]
        == "Complete"
    )

    assert output_data["successful_sources"] == [
        "kpis",
        "sales",
        "inventory",
        "complaints",
        "vendors",
        "finance",
    ]

    assert output_data["failed_sources"] == []

    assert (
        output_data["kpi_snapshot"]["total_kpis"]
        == 2
    )

    assert output_data["finding_totals"] == {
        "total": 12,
        "by_source": {
            "sales": 2,
            "inventory": 3,
            "complaints": 4,
            "vendors": 2,
            "finance": 1,
        },
        "by_severity": {
            "High": 6,
            "Medium": 5,
            "Low": 1,
        },
    }

    assert len(
        output_data["top_findings"]
    ) == 5

    assert all(
        finding["severity"] == "High"
        for finding in output_data[
            "top_findings"
        ]
    )

    assert (
        "Monitoring completed with 2 KPIs "
        "and 12 business findings"
        in result.summary
    )


def test_monitoring_agent_returns_partial_snapshot(
    monkeypatch: Any,
) -> None:
    """One source failure should not prevent other sources running."""

    configure_successful_monitoring_services(
        monkeypatch
    )

    def raise_inventory_failure(
        **_: Any,
    ) -> dict[str, Any]:
        raise RuntimeError(
            "Simulated inventory monitoring failure."
        )

    monkeypatch.setattr(
        monitoring_module,
        "get_inventory_analytics",
        raise_inventory_failure,
    )

    context = AgentContext(
        run_type="partial-monitoring-test",
    )

    result = asyncio.run(
        MonitoringAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    output_data = result.output_data

    assert (
        output_data["monitoring_status"]
        == "Partial"
    )

    assert "inventory" not in (
        output_data["successful_sources"]
    )

    assert len(
        output_data["failed_sources"]
    ) == 1

    failure = output_data[
        "failed_sources"
    ][0]

    assert failure["source"] == "inventory"
    assert failure["error_type"] == "RuntimeError"
    assert (
        failure["error_message"]
        == "Simulated inventory monitoring failure."
    )

    assert (
        output_data["finding_totals"]["total"]
        == 9
    )

    assert (
        "Partial monitoring was returned"
        in result.summary
    )


def test_monitoring_agent_fails_when_every_source_fails(
    monkeypatch: Any,
) -> None:
    """The agent should fail when no monitoring source succeeds."""

    def raise_monitoring_failure(
        *_: Any,
        **__: Any,
    ) -> dict[str, Any]:
        raise RuntimeError(
            "Simulated monitoring source failure."
        )

    monkeypatch.setattr(
        monitoring_module,
        "get_kpi_response",
        raise_monitoring_failure,
    )

    monkeypatch.setattr(
        monitoring_module,
        "get_sales_analytics",
        raise_monitoring_failure,
    )

    monkeypatch.setattr(
        monitoring_module,
        "get_inventory_analytics",
        raise_monitoring_failure,
    )

    monkeypatch.setattr(
        monitoring_module,
        "get_complaint_analytics",
        raise_monitoring_failure,
    )

    monkeypatch.setattr(
        monitoring_module,
        "get_vendor_analytics",
        raise_monitoring_failure,
    )

    monkeypatch.setattr(
        monitoring_module,
        "get_finance_analytics",
        raise_monitoring_failure,
    )

    context = AgentContext(
        run_type="failed-monitoring-test",
    )

    result = asyncio.run(
        MonitoringAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.FAILED
    )

    assert result.error_type == "RuntimeError"

    assert (
        result.error_message
        == (
            "All monitoring sources failed: "
            "kpis, sales, inventory, complaints, "
            "vendors, finance."
        )
    )


@pytest.mark.parametrize(
    "invalid_limit",
    [
        pytest.param(
            0,
            id="below-minimum",
        ),
        pytest.param(
            101,
            id="above-maximum",
        ),
        pytest.param(
            True,
            id="boolean-value",
        ),
        pytest.param(
            "invalid",
            id="non-integer-text",
        ),
    ],
)
def test_monitoring_agent_rejects_invalid_finding_limit(
    invalid_limit: object,
) -> None:
    """The finding limit must be an integer between 1 and 100."""

    context = AgentContext(
        run_type="invalid-limit-test",
        input_data={
            "finding_limit": invalid_limit,
        },
    )

    result = asyncio.run(
        MonitoringAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.FAILED
    )

    assert result.error_type == "ValueError"


@pytest.mark.integration
def test_monitoring_agent_with_seeded_test_database(
) -> None:
    """The real services should produce the known seeded snapshot."""

    with engine.connect() as connection:
        actual_database = connection.execute(
            text(
                "SELECT current_database();"
            )
        ).scalar_one()

    assert (
        actual_database
        == "ai_operating_intelligence_test"
    )

    context = AgentContext(
        run_type="monitoring-integration-test",
        requested_by="pytest",
        input_data={
            "finding_limit": 10,
        },
    )

    result = asyncio.run(
        MonitoringAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    output_data = result.output_data

    assert (
        output_data["monitoring_status"]
        == "Complete"
    )

    assert (
        output_data["kpi_snapshot"]["total_kpis"]
        == 12
    )

    assert output_data["finding_totals"] == {
        "total": 495,
        "by_source": {
            "sales": 5,
            "inventory": 122,
            "complaints": 345,
            "vendors": 19,
            "finance": 4,
        },
        "by_severity": {
            "High": 294,
            "Medium": 139,
            "Low": 62,
        },
    }

    assert output_data["successful_sources"] == [
        "kpis",
        "sales",
        "inventory",
        "complaints",
        "vendors",
        "finance",
    ]

    assert output_data["failed_sources"] == []

    assert len(
        output_data["top_findings"]
    ) == 10

    # -------------------------------------------------------------------------
# Priority Agent tests
# -------------------------------------------------------------------------

import pandas as pd

import backend.app.agents.priority_agent as priority_module
from backend.app.agents import PriorityAgent


def build_mock_priority_pipeline_data(
) -> dict[str, Any]:
    """Build controlled Priority Agent pipeline data."""

    detailed_findings = pd.DataFrame(
        [
            {"finding_id": "FINDING-001"},
            {"finding_id": "FINDING-002"},
            {"finding_id": "FINDING-003"},
            {"finding_id": "FINDING-004"},
            {"finding_id": "FINDING-005"},
        ]
    )

    source_finding_counts = {
        "sales": 2,
        "inventory": 1,
        "complaints": 1,
        "vendors": 1,
        "finance": 0,
    }

    issues = pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-HIGH-001",
                "priority_level": "High",
            },
            {
                "issue_id": "ISSUE-MEDIUM-001",
                "priority_level": "Medium",
            },
            {
                "issue_id": "ISSUE-LOW-001",
                "priority_level": "Low",
            },
        ]
    )

    evidence = pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-HIGH-001",
                "source_finding_id": "FINDING-001",
            },
            {
                "issue_id": "ISSUE-HIGH-001",
                "source_finding_id": "FINDING-002",
            },
            {
                "issue_id": "ISSUE-MEDIUM-001",
                "source_finding_id": "FINDING-003",
            },
            {
                "issue_id": "ISSUE-LOW-001",
                "source_finding_id": "FINDING-004",
            },
            {
                "issue_id": "ISSUE-LOW-001",
                "source_finding_id": "FINDING-005",
            },
        ]
    )

    manager_priorities = pd.DataFrame(
        [
            {
                "manager_rank": 1,
                "issue_id": "ISSUE-HIGH-001",
                "title": "High-priority test issue",
                "priority_level": "High",
                "priority_score": 95.0,
            },
            {
                "manager_rank": 2,
                "issue_id": "ISSUE-MEDIUM-001",
                "title": "Medium-priority test issue",
                "priority_level": "Medium",
                "priority_score": 60.0,
            },
        ]
    )

    active_issue_summary = pd.DataFrame(
        [
            {
                "priority_level": "High",
                "issue_count": 1,
            },
            {
                "priority_level": "Medium",
                "issue_count": 1,
            },
            {
                "priority_level": "Low",
                "issue_count": 1,
            },
        ]
    )

    active_issues = pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-HIGH-001",
            },
            {
                "issue_id": "ISSUE-MEDIUM-001",
            },
            {
                "issue_id": "ISSUE-LOW-001",
            },
        ]
    )

    executive_priorities = pd.DataFrame(
        [
            {
                "executive_rank": 1,
                "issue_id": "ISSUE-HIGH-001",
                "title": "High-priority test issue",
                "priority_level": "High",
                "priority_score": 95.0,
                "executive_score": 130.0,
            },
        ]
    )

    return {
        "detailed_findings": detailed_findings,
        "source_finding_counts": source_finding_counts,
        "issues": issues,
        "evidence": evidence,
        "manager_priorities": manager_priorities,
        "active_issue_summary": active_issue_summary,
        "active_issues": active_issues,
        "executive_priorities": executive_priorities,
        "persistence_calls": [],
    }


def configure_successful_priority_pipeline(
    monkeypatch: Any,
) -> dict[str, Any]:
    """Configure all Priority Agent dependencies to succeed."""

    pipeline_data = build_mock_priority_pipeline_data()

    monkeypatch.setattr(
        priority_module,
        "build_detailed_findings",
        lambda: (
            pipeline_data[
                "detailed_findings"
            ].copy(),
            pipeline_data[
                "source_finding_counts"
            ].copy(),
        ),
    )

    monkeypatch.setattr(
        priority_module,
        "build_priority_outputs",
        lambda detailed_findings: (
            pipeline_data["issues"].copy(),
            pipeline_data["evidence"].copy(),
        ),
    )

    def fake_save_to_database(
        database_engine: Any,
        issues_dataframe: pd.DataFrame,
        evidence_dataframe: pd.DataFrame,
    ) -> None:
        pipeline_data[
            "persistence_calls"
        ].append(
            {
                "engine": database_engine,
                "issue_count": len(
                    issues_dataframe
                ),
                "evidence_count": len(
                    evidence_dataframe
                ),
            }
        )

    monkeypatch.setattr(
        priority_module,
        "save_to_database",
        fake_save_to_database,
    )

    monkeypatch.setattr(
        priority_module,
        "load_manager_priorities",
        lambda database_engine, limit: (
            pipeline_data[
                "manager_priorities"
            ]
            .head(limit)
            .copy()
        ),
    )

    monkeypatch.setattr(
        priority_module,
        "load_active_issue_summary",
        lambda database_engine: (
            pipeline_data[
                "active_issue_summary"
            ].copy()
        ),
    )

    monkeypatch.setattr(
        priority_module,
        "load_active_issues",
        lambda database_engine: (
            pipeline_data[
                "active_issues"
            ].copy()
        ),
    )

    monkeypatch.setattr(
        priority_module,
        "select_executive_priorities",
        lambda *,
        active_issues,
        limit: (
            pipeline_data[
                "executive_priorities"
            ]
            .head(limit)
            .copy()
        ),
    )

    return pipeline_data


def test_priority_agent_returns_complete_result(
    monkeypatch: Any,
) -> None:
    """The Priority Agent should return structured priority output."""

    pipeline_data = (
        configure_successful_priority_pipeline(
            monkeypatch
        )
    )

    context = AgentContext(
        run_type="priority-unit-test",
        input_data={
            "manager_limit": 2,
            "executive_limit": 1,
        },
    )

    result = asyncio.run(
        PriorityAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert result.used_fallback is False

    output_data = result.output_data

    assert (
        output_data["priority_status"]
        == "Complete"
    )

    assert (
        output_data["database_persisted"]
        is True
    )

    assert output_data["detailed_findings"] == {
        "total": 5,
        "by_source": {
            "sales": 2,
            "inventory": 1,
            "complaints": 1,
            "vendors": 1,
            "finance": 0,
        },
    }

    assert output_data["issues"] == {
        "total_created": 3,
        "by_priority": {
            "High": 1,
            "Medium": 1,
            "Low": 1,
        },
        "active_by_priority": {
            "High": 1,
            "Medium": 1,
            "Low": 1,
        },
    }

    assert output_data["evidence_records"] == {
        "total": 5,
    }

    assert (
        output_data[
            "manager_priorities"
        ]["requested_limit"]
        == 2
    )

    assert (
        output_data[
            "manager_priorities"
        ]["returned_count"]
        == 2
    )

    assert (
        len(
            output_data[
                "manager_priorities"
            ]["items"]
        )
        == 2
    )

    assert (
        output_data[
            "executive_priorities"
        ]["requested_limit"]
        == 1
    )

    assert (
        output_data[
            "executive_priorities"
        ]["returned_count"]
        == 1
    )

    assert (
        len(
            output_data[
                "executive_priorities"
            ]["items"]
        )
        == 1
    )

    assert output_data[
        "monitoring_comparison"
    ] == {
        "available": False,
        "monitoring_finding_total": None,
        "priority_input_finding_total": 5,
        "totals_match": None,
    }

    assert (
        "Priority analysis consolidated "
        "5 findings into 3 business issues"
        in result.summary
    )

    persistence_calls = pipeline_data[
        "persistence_calls"
    ]

    assert len(
        persistence_calls
    ) == 1

    assert (
        persistence_calls[0]["engine"]
        is priority_module.engine
    )

    assert (
        persistence_calls[0]["issue_count"]
        == 3
    )

    assert (
        persistence_calls[0]["evidence_count"]
        == 5
    )


@pytest.mark.parametrize(
    (
        "input_data",
        "expected_error",
    ),
    [
        pytest.param(
            {
                "manager_limit": 0,
            },
            "manager_limit must be at least 1.",
            id="manager-below-minimum",
        ),
        pytest.param(
            {
                "manager_limit": 101,
            },
            (
                "manager_limit cannot be greater "
                "than 100."
            ),
            id="manager-above-maximum",
        ),
        pytest.param(
            {
                "manager_limit": True,
            },
            "manager_limit must be an integer.",
            id="manager-boolean",
        ),
        pytest.param(
            {
                "manager_limit": "invalid",
            },
            "manager_limit must be an integer.",
            id="manager-invalid-text",
        ),
        pytest.param(
            {
                "executive_limit": 0,
            },
            "executive_limit must be at least 1.",
            id="executive-below-minimum",
        ),
        pytest.param(
            {
                "executive_limit": 51,
            },
            (
                "executive_limit cannot be greater "
                "than 50."
            ),
            id="executive-above-maximum",
        ),
        pytest.param(
            {
                "executive_limit": True,
            },
            "executive_limit must be an integer.",
            id="executive-boolean",
        ),
        pytest.param(
            {
                "executive_limit": "invalid",
            },
            "executive_limit must be an integer.",
            id="executive-invalid-text",
        ),
    ],
)
def test_priority_agent_rejects_invalid_limits(
    input_data: dict[str, object],
    expected_error: str,
) -> None:
    """Priority list limits must remain within allowed ranges."""

    context = AgentContext(
        run_type="invalid-priority-limit-test",
        input_data=input_data,
    )

    result = asyncio.run(
        PriorityAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.FAILED
    )

    assert result.error_type == "ValueError"

    assert (
        result.error_message
        == expected_error
    )


def test_priority_agent_fails_when_no_issues_are_created(
    monkeypatch: Any,
) -> None:
    """An empty issue output should cause a controlled failure."""

    detailed_findings = pd.DataFrame(
        [
            {
                "finding_id": "FINDING-001",
            },
        ]
    )

    monkeypatch.setattr(
        priority_module,
        "build_detailed_findings",
        lambda: (
            detailed_findings,
            {
                "sales": 1,
                "inventory": 0,
                "complaints": 0,
                "vendors": 0,
                "finance": 0,
            },
        ),
    )

    monkeypatch.setattr(
        priority_module,
        "build_priority_outputs",
        lambda findings: (
            pd.DataFrame(),
            pd.DataFrame(),
        ),
    )

    context = AgentContext(
        run_type="empty-priority-test",
    )

    result = asyncio.run(
        PriorityAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.FAILED
    )

    assert result.error_type == "RuntimeError"

    assert (
        result.error_message
        == (
            "The priority engine did not "
            "create any issues."
        )
    )


class SequenceMonitoringAgent(
    BaseAgent
):
    """Monitoring stub used for the agent-sequence test."""

    name = "Monitoring Agent"

    description = (
        "Returns a controlled monitoring total "
        "for sequence testing."
    )

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        del context

        return {
            "summary": (
                "Controlled monitoring completed."
            ),
            "finding_totals": {
                "total": 5,
            },
        }


def test_monitoring_and_priority_sequence_shares_totals(
    monkeypatch: Any,
) -> None:
    """Priority Agent should receive the prior monitoring total."""

    configure_successful_priority_pipeline(
        monkeypatch
    )

    context = AgentContext(
        run_type="monitoring-priority-sequence-test",
        input_data={
            "manager_limit": 2,
            "executive_limit": 1,
        },
    )

    orchestrator = AgentOrchestrator(
        agents=[
            SequenceMonitoringAgent(),
            PriorityAgent(),
        ]
    )

    results = asyncio.run(
        orchestrator.run_sequence(
            agent_names=[
                "Monitoring Agent",
                "Priority Agent",
            ],
            context=context,
        )
    )

    assert len(results) == 2

    monitoring_result = results[0]
    priority_result = results[1]

    assert (
        monitoring_result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert (
        priority_result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert priority_result.output_data[
        "monitoring_comparison"
    ] == {
        "available": True,
        "monitoring_finding_total": 5,
        "priority_input_finding_total": 5,
        "totals_match": True,
    }


@pytest.mark.integration
def test_priority_agent_with_seeded_test_database(
) -> None:
    """The real priority pipeline should match seeded data."""

    with engine.connect() as connection:
        actual_database = connection.execute(
            text(
                "SELECT current_database();"
            )
        ).scalar_one()

    assert (
        actual_database
        == "ai_operating_intelligence_test"
    )

    context = AgentContext(
        run_type="priority-integration-test",
        requested_by="pytest",
        input_data={
            "manager_limit": 15,
            "executive_limit": 10,
        },
    )

    result = asyncio.run(
        PriorityAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    output_data = result.output_data

    assert (
        output_data["priority_status"]
        == "Complete"
    )

    assert (
        output_data["database_persisted"]
        is True
    )

    assert output_data[
        "detailed_findings"
    ] == {
        "total": 495,
        "by_source": {
            "sales": 5,
            "inventory": 122,
            "complaints": 345,
            "vendors": 19,
            "finance": 4,
        },
    }

    assert (
        output_data["issues"][
            "total_created"
        ]
        == 129
    )

    assert (
        sum(
            output_data["issues"][
                "by_priority"
            ].values()
        )
        == 129
    )

    assert (
        output_data["evidence_records"][
            "total"
        ]
        == 495
    )

    assert (
        output_data[
            "manager_priorities"
        ]["requested_limit"]
        == 15
    )

    assert (
        output_data[
            "manager_priorities"
        ]["returned_count"]
        == 15
    )

    assert (
        len(
            output_data[
                "manager_priorities"
            ]["items"]
        )
        == 15
    )

    assert (
        output_data[
            "executive_priorities"
        ]["requested_limit"]
        == 10
    )

    assert (
        output_data[
            "executive_priorities"
        ]["returned_count"]
        == 10
    )

    assert (
        len(
            output_data[
                "executive_priorities"
            ]["items"]
        )
        == 10
    )


@pytest.mark.integration
def test_priority_agent_result_is_logged(
    monkeypatch: Any,
) -> None:
    """A Priority Agent execution should be stored in agent_runs."""

    configure_successful_priority_pipeline(
        monkeypatch
    )

    agent_run_id: int | None = None

    with engine.connect() as connection:
        actual_database = connection.execute(
            text(
                "SELECT current_database();"
            )
        ).scalar_one()

    assert (
        actual_database
        == "ai_operating_intelligence_test"
    )

    context = AgentContext(
        run_type="priority-logging-integration-test",
        requested_by="pytest",
        input_data={
            "manager_limit": 2,
            "executive_limit": 1,
        },
    )

    orchestrator = AgentOrchestrator(
        agents=[
            PriorityAgent(),
        ],
        run_logger=PostgresAgentRunLogger(
            engine
        ),
    )

    try:
        result = asyncio.run(
            orchestrator.run_agent(
                "Priority Agent",
                context,
            )
        )

        agent_run_id = result.agent_run_id

        assert (
            result.execution_status
            == AgentExecutionStatus.SUCCESS
        )

        assert result.log_persisted is True
        assert result.logging_error is None
        assert agent_run_id is not None

        with engine.connect() as connection:
            stored_record = connection.execute(
                text(
                    """
                    SELECT
                        agent_name,
                        run_type,
                        execution_status,
                        input_summary,
                        output_summary
                    FROM agent_runs
                    WHERE agent_run_id = :agent_run_id;
                    """
                ),
                {
                    "agent_run_id": agent_run_id,
                },
            ).mappings().one()

        assert (
            stored_record["agent_name"]
            == "Priority Agent"
        )

        assert (
            stored_record["run_type"]
            == (
                "priority-logging-"
                "integration-test"
            )
        )

        assert (
            stored_record["execution_status"]
            == "Success"
        )

        input_summary = json.loads(
            stored_record[
                "input_summary"
            ]
        )

        output_summary = json.loads(
            stored_record[
                "output_summary"
            ]
        )

        assert (
            input_summary[
                "input_data_keys"
            ]
            == [
                "executive_limit",
                "manager_limit",
            ]
        )

        assert (
            "Priority analysis consolidated"
            in output_summary["summary"]
        )

    finally:
        if agent_run_id is not None:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        DELETE FROM agent_runs
                        WHERE agent_run_id = :agent_run_id;
                        """
                    ),
                    {
                        "agent_run_id": agent_run_id,
                    },
                )


# -------------------------------------------------------------------------
# Root-Cause Agent tests
# -------------------------------------------------------------------------

import backend.app.agents.root_cause_agent as root_cause_module
from backend.app.agents import RootCauseAgent


def build_mock_root_cause_pipeline_data(
) -> dict[str, Any]:
    """Build controlled Root-Cause Agent pipeline data."""

    priority_reference = pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-HIGH-001",
                "executive_rank": 1,
                "executive_score": 130.0,
            },
            {
                "issue_id": "ISSUE-HIGH-002",
                "executive_rank": 2,
                "executive_score": 115.0,
            },
        ]
    )

    selected_issues = pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-HIGH-001",
            },
            {
                "issue_id": "ISSUE-HIGH-002",
            },
        ]
    )

    selected_evidence = pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-HIGH-001",
                "source_finding_id": "FINDING-001",
            },
            {
                "issue_id": "ISSUE-HIGH-001",
                "source_finding_id": "FINDING-002",
            },
            {
                "issue_id": "ISSUE-HIGH-002",
                "source_finding_id": "FINDING-003",
            },
        ]
    )

    analyses = pd.DataFrame(
        [
            {
                "analysis_id": "RCA-ISSUE-HIGH-001",
                "executive_rank": 1,
                "issue_id": "ISSUE-HIGH-001",
                "root_cause_category": (
                    "Inventory Replenishment and Supply Risk"
                ),
                "confidence_score": 82.0,
                "evidence_count": 2,
                "generated_at": pd.Timestamp(
                    "2026-08-04T09:00:00"
                ),
            },
            {
                "analysis_id": "RCA-ISSUE-HIGH-002",
                "executive_rank": 2,
                "issue_id": "ISSUE-HIGH-002",
                "root_cause_category": (
                    "Vendor Reliability and Fulfilment Risk"
                ),
                "confidence_score": 74.0,
                "evidence_count": 1,
                "generated_at": pd.Timestamp(
                    "2026-08-04T09:00:00"
                ),
            },
        ]
    )

    database_records = [
        {
            "issue_id": "ISSUE-HIGH-001",
        },
        {
            "issue_id": "ISSUE-HIGH-002",
        },
    ]

    return {
        "priority_reference": priority_reference,
        "selected_issues": selected_issues,
        "selected_evidence": selected_evidence,
        "analyses": analyses,
        "database_records": database_records,
        "persistence_calls": [],
    }


def configure_successful_root_cause_pipeline(
    monkeypatch: Any,
    *,
    patch_priority_reference: bool = True,
) -> dict[str, Any]:
    """Configure Root-Cause Agent dependencies to succeed."""

    pipeline_data = (
        build_mock_root_cause_pipeline_data()
    )

    if patch_priority_reference:
        monkeypatch.setattr(
            root_cause_module,
            "build_priority_reference",
            lambda **_: (
                pipeline_data[
                    "priority_reference"
                ].copy(),
                "Priority Agent output",
            ),
        )

    monkeypatch.setattr(
        root_cause_module,
        "load_selected_issues",
        lambda database_engine, priority_reference: (
            pipeline_data[
                "selected_issues"
            ].copy()
        ),
    )

    monkeypatch.setattr(
        root_cause_module,
        "load_selected_evidence",
        lambda database_engine, issue_ids: (
            pipeline_data[
                "selected_evidence"
            ].copy()
        ),
    )

    def fake_build_root_cause_outputs(
        database_engine: Any,
        selected_issues: pd.DataFrame,
        selected_evidence: pd.DataFrame,
    ) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
        del database_engine
        del selected_issues
        del selected_evidence

        return (
            pipeline_data[
                "analyses"
            ].copy(),
            list(
                pipeline_data[
                    "database_records"
                ]
            ),
        )

    monkeypatch.setattr(
        root_cause_module,
        "build_root_cause_outputs",
        fake_build_root_cause_outputs,
    )

    def fake_save_root_causes_to_database(
        database_engine: Any,
        database_records: list[dict[str, Any]],
    ) -> None:
        pipeline_data[
            "persistence_calls"
        ].append(
            {
                "engine": database_engine,
                "record_count": len(
                    database_records
                ),
            }
        )

    monkeypatch.setattr(
        root_cause_module,
        "save_root_causes_to_database",
        fake_save_root_causes_to_database,
    )

    return pipeline_data


def test_root_cause_agent_returns_complete_result(
    monkeypatch: Any,
) -> None:
    """The agent should return structured root-cause output."""

    pipeline_data = (
        configure_successful_root_cause_pipeline(
            monkeypatch
        )
    )

    context = AgentContext(
        run_type="root-cause-unit-test",
        input_data={
            "analysis_limit": 2,
        },
    )

    result = asyncio.run(
        RootCauseAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert result.used_fallback is False

    output_data = result.output_data

    assert (
        output_data["root_cause_status"]
        == "Complete"
    )

    assert output_data["selection"] == {
        "source": "Priority Agent output",
        "requested_limit": 2,
        "selected_issue_count": 2,
        "issue_ids": [
            "ISSUE-HIGH-001",
            "ISSUE-HIGH-002",
        ],
    }

    assert output_data["analysis"] == {
        "generated_count": 2,
        "analysis_method": (
            "Rule-Based Database and "
            "Evidence Analysis"
        ),
        "technical_review_required_count": 0,
        "zero_evidence_count": 0,
        "confidence": {
            "average": 78.0,
            "minimum": 74.0,
            "maximum": 82.0,
        },
    }

    assert output_data["evidence"] == {
        "selected_evidence_records": 3,
        "evidence_records_used": 3,
    }

    assert output_data["database"] == {
        "persisted": True,
        "table": "root_cause_analyses",
        "review_status": "Pending Review",
    }

    assert len(
        output_data["analyses"]
    ) == 2

    assert (
        output_data["analyses"][0][
            "generated_at"
        ]
        == "2026-08-04T09:00:00"
    )

    assert (
        "2 evidence-based assessments"
        in result.summary
    )

    persistence_calls = pipeline_data[
        "persistence_calls"
    ]

    assert len(
        persistence_calls
    ) == 1

    assert (
        persistence_calls[0]["engine"]
        is root_cause_module.engine
    )

    assert (
        persistence_calls[0][
            "record_count"
        ]
        == 2
    )


def test_root_cause_agent_returns_partial_status_for_technical_review(
    monkeypatch: Any,
) -> None:
    """Technical-review analyses should produce Partial status."""

    pipeline_data = (
        configure_successful_root_cause_pipeline(
            monkeypatch
        )
    )

    pipeline_data["analyses"].loc[
        1,
        "root_cause_category",
    ] = "Technical Review Required"

    context = AgentContext(
        run_type="partial-root-cause-test",
        input_data={
            "analysis_limit": 2,
        },
    )

    result = asyncio.run(
        RootCauseAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert (
        result.output_data[
            "root_cause_status"
        ]
        == "Partial"
    )

    assert (
        result.output_data["analysis"][
            "technical_review_required_count"
        ]
        == 1
    )

    assert (
        "1 assessments require technical review"
        in result.summary
    )


@pytest.mark.parametrize(
    (
        "invalid_limit",
        "expected_error",
    ),
    [
        pytest.param(
            0,
            "analysis_limit must be at least 1.",
            id="below-minimum",
        ),
        pytest.param(
            51,
            (
                "analysis_limit cannot be greater "
                "than 50."
            ),
            id="above-maximum",
        ),
        pytest.param(
            True,
            "analysis_limit must be an integer.",
            id="boolean-value",
        ),
        pytest.param(
            "invalid",
            "analysis_limit must be an integer.",
            id="non-integer-text",
        ),
    ],
)
def test_root_cause_agent_rejects_invalid_analysis_limit(
    invalid_limit: object,
    expected_error: str,
) -> None:
    """Analysis limit must remain between 1 and 50."""

    context = AgentContext(
        run_type="invalid-root-cause-limit-test",
        input_data={
            "analysis_limit": invalid_limit,
        },
    )

    result = asyncio.run(
        RootCauseAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.FAILED
    )

    assert result.error_type == "ValueError"

    assert (
        result.error_message
        == expected_error
    )


def test_root_cause_agent_preserves_requested_issue_order(
    monkeypatch: Any,
) -> None:
    """Explicit issue IDs should be selected in caller order."""

    active_issues = pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-HIGH-001",
                "priority_score": 95.0,
                "critical_evidence_score": 25.0,
            },
            {
                "issue_id": "ISSUE-HIGH-002",
                "priority_score": 85.0,
                "critical_evidence_score": 20.0,
            },
        ]
    )

    monkeypatch.setattr(
        root_cause_module,
        "load_active_issues",
        lambda database_engine: (
            active_issues.copy()
        ),
    )

    context = AgentContext(
        run_type="requested-root-cause-test",
        issue_ids=[
            "ISSUE-HIGH-002",
            "ISSUE-HIGH-001",
        ],
        input_data={
            "analysis_limit": 2,
        },
    )

    priority_reference, selection_source = (
        root_cause_module.build_priority_reference(
            context=context,
            analysis_limit=2,
        )
    )

    assert (
        selection_source
        == "Requested issue IDs"
    )

    assert (
        priority_reference[
            "issue_id"
        ].tolist()
        == [
            "ISSUE-HIGH-002",
            "ISSUE-HIGH-001",
        ]
    )

    assert (
        priority_reference[
            "executive_rank"
        ].tolist()
        == [
            1,
            2,
        ]
    )

    assert (
        priority_reference[
            "executive_score"
        ].tolist()
        == [
            105.0,
            120.0,
        ]
    )


def test_root_cause_agent_rejects_unknown_requested_issue(
    monkeypatch: Any,
) -> None:
    """Unknown issue IDs should not be analyzed."""

    active_issues = pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-HIGH-001",
            },
        ]
    )

    monkeypatch.setattr(
        root_cause_module,
        "load_active_issues",
        lambda database_engine: (
            active_issues.copy()
        ),
    )

    context = AgentContext(
        run_type="unknown-root-cause-issue-test",
        issue_ids=[
            "ISSUE-UNKNOWN-001",
        ],
        input_data={
            "analysis_limit": 1,
        },
    )

    result = asyncio.run(
        RootCauseAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.FAILED
    )

    assert result.error_type == "ValueError"

    assert (
        result.error_message
        == (
            "Requested issues were not found in "
            "the active issue register: "
            "ISSUE-UNKNOWN-001"
        )
    )


def test_root_cause_agent_rejects_more_issue_ids_than_limit(
) -> None:
    """Explicit issue count cannot exceed analysis limit."""

    context = AgentContext(
        run_type="root-cause-request-limit-test",
        issue_ids=[
            "ISSUE-HIGH-001",
            "ISSUE-HIGH-002",
        ],
        input_data={
            "analysis_limit": 1,
        },
    )

    result = asyncio.run(
        RootCauseAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.FAILED
    )

    assert result.error_type == "ValueError"

    assert (
        result.error_message
        == (
            "2 issue IDs were requested, but "
            "analysis_limit is 1."
        )
    )


def test_root_cause_agent_fails_when_selected_issues_are_empty(
    monkeypatch: Any,
) -> None:
    """The agent should fail when selected issues cannot be loaded."""

    monkeypatch.setattr(
        root_cause_module,
        "build_priority_reference",
        lambda **_: (
            pd.DataFrame(
                [
                    {
                        "issue_id": "ISSUE-HIGH-001",
                        "executive_rank": 1,
                        "executive_score": 120.0,
                    },
                ]
            ),
            "Current executive ranking",
        ),
    )

    monkeypatch.setattr(
        root_cause_module,
        "load_selected_issues",
        lambda database_engine, priority_reference: (
            pd.DataFrame()
        ),
    )

    context = AgentContext(
        run_type="empty-selected-issues-test",
    )

    result = asyncio.run(
        RootCauseAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.FAILED
    )

    assert result.error_type == "RuntimeError"

    assert (
        result.error_message
        == (
            "No active issues matched the selected "
            "root-cause analysis reference."
        )
    )


def test_root_cause_agent_fails_when_no_analyses_are_generated(
    monkeypatch: Any,
) -> None:
    """An empty analysis result should cause controlled failure."""

    monkeypatch.setattr(
        root_cause_module,
        "build_priority_reference",
        lambda **_: (
            pd.DataFrame(
                [
                    {
                        "issue_id": "ISSUE-HIGH-001",
                        "executive_rank": 1,
                        "executive_score": 120.0,
                    },
                ]
            ),
            "Current executive ranking",
        ),
    )

    monkeypatch.setattr(
        root_cause_module,
        "load_selected_issues",
        lambda database_engine, priority_reference: (
            pd.DataFrame(
                [
                    {
                        "issue_id": "ISSUE-HIGH-001",
                    },
                ]
            )
        ),
    )

    monkeypatch.setattr(
        root_cause_module,
        "load_selected_evidence",
        lambda database_engine, issue_ids: (
            pd.DataFrame()
        ),
    )

    def return_empty_root_cause_output(
        database_engine: Any,
        selected_issues: pd.DataFrame,
        selected_evidence: pd.DataFrame,
    ) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
        del database_engine
        del selected_issues
        del selected_evidence

        return pd.DataFrame(), []

    monkeypatch.setattr(
        root_cause_module,
        "build_root_cause_outputs",
        return_empty_root_cause_output,
    )

    context = AgentContext(
        run_type="empty-root-cause-output-test",
    )

    result = asyncio.run(
        RootCauseAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.FAILED
    )

    assert result.error_type == "RuntimeError"

    assert (
        result.error_message
        == (
            "No root-cause analyses were generated."
        )
    )


class SequencePriorityAgent(
    BaseAgent
):
    """Priority stub used for Root-Cause Agent sequence testing."""

    name = "Priority Agent"

    description = (
        "Returns controlled executive priorities "
        "for sequence testing."
    )

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        del context

        return {
            "summary": (
                "Controlled priority analysis completed."
            ),
            "executive_priorities": {
                "items": [
                    {
                        "issue_id": "ISSUE-HIGH-001",
                        "executive_rank": 1,
                        "executive_score": 130.0,
                    },
                    {
                        "issue_id": "ISSUE-HIGH-002",
                        "executive_rank": 2,
                        "executive_score": 115.0,
                    },
                ],
            },
        }


def test_priority_and_root_cause_sequence_shares_priorities(
    monkeypatch: Any,
) -> None:
    """Root-Cause Agent should use prior executive selections."""

    configure_successful_root_cause_pipeline(
        monkeypatch,
        patch_priority_reference=False,
    )

    context = AgentContext(
        run_type="priority-root-cause-sequence-test",
        input_data={
            "analysis_limit": 2,
        },
    )

    orchestrator = AgentOrchestrator(
        agents=[
            SequencePriorityAgent(),
            RootCauseAgent(),
        ]
    )

    results = asyncio.run(
        orchestrator.run_sequence(
            agent_names=[
                "Priority Agent",
                "Root-Cause Agent",
            ],
            context=context,
        )
    )

    assert len(results) == 2

    assert (
        results[0].execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert (
        results[1].execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert results[1].output_data[
        "selection"
    ] == {
        "source": "Priority Agent output",
        "requested_limit": 2,
        "selected_issue_count": 2,
        "issue_ids": [
            "ISSUE-HIGH-001",
            "ISSUE-HIGH-002",
        ],
    }


@pytest.mark.integration
def test_root_cause_agent_with_seeded_test_database(
) -> None:
    """The real sequence should analyze seeded executive issues."""

    with engine.connect() as connection:
        actual_database = connection.execute(
            text(
                "SELECT current_database();"
            )
        ).scalar_one()

    assert (
        actual_database
        == "ai_operating_intelligence_test"
    )

    context = AgentContext(
        run_type="root-cause-integration-test",
        requested_by="pytest",
        input_data={
            "manager_limit": 15,
            "executive_limit": 10,
            "analysis_limit": 10,
        },
    )

    orchestrator = AgentOrchestrator(
        agents=[
            PriorityAgent(),
            RootCauseAgent(),
        ]
    )

    results = asyncio.run(
        orchestrator.run_sequence(
            agent_names=[
                "Priority Agent",
                "Root-Cause Agent",
            ],
            context=context,
        )
    )

    assert len(results) == 2

    priority_result = results[0]
    root_cause_result = results[1]

    assert (
        priority_result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert (
        root_cause_result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    output_data = (
        root_cause_result.output_data
    )

    assert (
        output_data["root_cause_status"]
        == "Complete"
    )

    assert (
        output_data["selection"]["source"]
        == "Priority Agent output"
    )

    assert (
        output_data["selection"][
            "selected_issue_count"
        ]
        == 10
    )

    assert (
        output_data["analysis"][
            "generated_count"
        ]
        == 10
    )

    assert (
        output_data["analysis"][
            "technical_review_required_count"
        ]
        == 0
    )

    assert (
        output_data["analysis"][
            "zero_evidence_count"
        ]
        == 0
    )

    confidence = output_data[
        "analysis"
    ]["confidence"]

    assert (
        0.0
        < confidence["minimum"]
        <= confidence["average"]
        <= confidence["maximum"]
        <= 100.0
    )

    assert (
        output_data["evidence"][
            "evidence_records_used"
        ]
        > 0
    )

    assert (
        output_data["database"]["persisted"]
        is True
    )

    selected_issue_ids = output_data[
        "selection"
    ]["issue_ids"]

    assert (
        "ISSUE-PRODUCT-AVAILABILITY-RISK-S003-P017"
        in selected_issue_ids
    )

    with engine.connect() as connection:
        stored_rows = connection.execute(
            text(
                """
                SELECT
                    issue_id,
                    confidence_score,
                    evidence_count,
                    analysis_status,
                    review_status
                FROM root_cause_analyses;
                """
            )
        ).mappings().all()

    stored_by_issue_id = {
        row["issue_id"]: row
        for row in stored_rows
    }

    for issue_id in selected_issue_ids:
        assert issue_id in stored_by_issue_id

        stored_record = stored_by_issue_id[
            issue_id
        ]

        assert (
            stored_record[
                "confidence_score"
            ]
            is not None
        )

        assert (
            stored_record[
                "evidence_count"
            ]
            > 0
        )

        assert (
            stored_record[
                "analysis_status"
            ]
            == "Generated"
        )

        assert (
            stored_record[
                "review_status"
            ]
            == "Pending Review"
        )


@pytest.mark.integration
def test_root_cause_agent_result_is_logged(
    monkeypatch: Any,
) -> None:
    """A Root-Cause Agent execution should be stored in agent_runs."""

    configure_successful_root_cause_pipeline(
        monkeypatch
    )

    agent_run_id: int | None = None

    with engine.connect() as connection:
        actual_database = connection.execute(
            text(
                "SELECT current_database();"
            )
        ).scalar_one()

    assert (
        actual_database
        == "ai_operating_intelligence_test"
    )

    context = AgentContext(
        run_type="root-cause-logging-integration-test",
        requested_by="pytest",
        input_data={
            "analysis_limit": 2,
        },
    )

    orchestrator = AgentOrchestrator(
        agents=[
            RootCauseAgent(),
        ],
        run_logger=PostgresAgentRunLogger(
            engine
        ),
    )

    try:
        result = asyncio.run(
            orchestrator.run_agent(
                "Root-Cause Agent",
                context,
            )
        )

        agent_run_id = result.agent_run_id

        assert (
            result.execution_status
            == AgentExecutionStatus.SUCCESS
        )

        assert result.log_persisted is True
        assert result.logging_error is None
        assert agent_run_id is not None

        with engine.connect() as connection:
            stored_record = connection.execute(
                text(
                    """
                    SELECT
                        agent_name,
                        run_type,
                        execution_status,
                        input_summary,
                        output_summary
                    FROM agent_runs
                    WHERE agent_run_id = :agent_run_id;
                    """
                ),
                {
                    "agent_run_id": agent_run_id,
                },
            ).mappings().one()

        assert (
            stored_record["agent_name"]
            == "Root-Cause Agent"
        )

        assert (
            stored_record["run_type"]
            == (
                "root-cause-logging-"
                "integration-test"
            )
        )

        assert (
            stored_record[
                "execution_status"
            ]
            == "Success"
        )

        input_summary = json.loads(
            stored_record[
                "input_summary"
            ]
        )

        output_summary = json.loads(
            stored_record[
                "output_summary"
            ]
        )

        assert (
            input_summary[
                "input_data_keys"
            ]
            == [
                "analysis_limit",
            ]
        )

        assert (
            "Root-cause analysis generated"
            in output_summary["summary"]
        )

    finally:
        if agent_run_id is not None:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        DELETE FROM agent_runs
                        WHERE agent_run_id = :agent_run_id;
                        """
                    ),
                    {
                        "agent_run_id": agent_run_id,
                    },
                )