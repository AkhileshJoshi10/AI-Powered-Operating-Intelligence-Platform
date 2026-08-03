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