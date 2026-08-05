from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from sqlalchemy import text

from backend.app.agents import (
    AgentContext,
    AgentExecutionStatus,
    AgentOrchestrator,
    BaseAgent,
    PostgresAgentRunLogger,
)
from backend.app.db.database import engine
from backend.app.llm import LLMTimeoutError


class LLMMetadataAgent(BaseAgent):
    """Agent used to test successful LLM metadata extraction."""

    name = "LLM Metadata Test Agent"
    description = "Returns controlled business and LLM metadata."
    version = "2.3.1"

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        del context

        return {
            "summary": "LLM-supported agent completed.",
            "business_result": {
                "status": "Complete",
                "issue_count": 2,
            },
            "_execution_metadata": {
                "model_provider": "mock",
                "model_name": "mock-deterministic-v1",
                "prompt_name": "executive_brief_enhancement",
                "prompt_version": "v1",
                "input_tokens": 152,
                "output_tokens": 19,
                "total_tokens": 171,
                "estimated_cost_usd": 0.0,
                "llm_latency_ms": 4.25,
                "tool_calls": [
                    {
                        "tool_name": "read_issue",
                        "status": "Success",
                        "issue_id": "TEST-ISSUE-001",
                    }
                ],
                "run_metadata": {
                    "structured_output": True,
                    "request_id": "test-request-001",
                },
            },
        }


class DeterministicMetadataAgent(BaseAgent):
    """Agent used to verify deterministic metadata defaults."""

    name = "Deterministic Metadata Test Agent"
    description = "Returns no LLM-specific execution metadata."

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        del context

        return {
            "summary": "Deterministic agent completed.",
            "business_result": {
                "status": "Complete",
            },
        }


class InvalidTokenMetadataAgent(BaseAgent):
    """Agent used to test incomplete token metadata rejection."""

    name = "Invalid Token Metadata Agent"
    description = "Returns incomplete token usage metadata."

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        del context

        return {
            "summary": "Invalid token metadata.",
            "_execution_metadata": {
                "input_tokens": 10,
            },
        }


class LLMFallbackMetadataAgent(BaseAgent):
    """Agent used to test LLM failure and deterministic fallback."""

    name = "LLM Fallback Metadata Agent"
    description = "Falls back after a controlled LLM timeout."
    version = "1.4.0"

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        del context

        raise LLMTimeoutError(
            "Simulated LLM timeout."
        )

    async def fallback(
        self,
        context: AgentContext,
        error: Exception,
    ) -> dict[str, Any] | None:
        del context
        del error

        return {
            "summary": "Deterministic fallback completed.",
            "business_result": {
                "status": "Fallback",
            },
            "_execution_metadata": {
                "model_provider": "mock",
                "model_name": "mock-deterministic-v1",
                "prompt_name": "fallback_test_prompt",
                "prompt_version": "v1",
                "tool_calls": [],
                "run_metadata": {
                    "fallback_reason": "llm_timeout",
                    "structured_output": True,
                },
            },
        }


def confirm_test_database() -> None:
    """Prevent integration tests from using the development database."""

    with engine.connect() as connection:
        database_name = connection.execute(
            text(
                "SELECT current_database();"
            )
        ).scalar_one()

    assert (
        database_name
        == "ai_operating_intelligence_test"
    )


def delete_agent_run(
    agent_run_id: int | None,
) -> None:
    """Delete one integration-test execution record."""

    if agent_run_id is None:
        return

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


def test_base_agent_extracts_llm_metadata_from_business_output(
) -> None:
    """Execution metadata should move into AgentResult."""

    context = AgentContext(
        run_type="llm-metadata-unit-test",
        requested_by="pytest",
    )

    result = asyncio.run(
        LLMMetadataAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert result.agent_name == "LLM Metadata Test Agent"
    assert result.agent_version == "2.3.1"

    assert (
        "_execution_metadata"
        not in result.output_data
    )

    assert result.output_data == {
        "summary": "LLM-supported agent completed.",
        "business_result": {
            "status": "Complete",
            "issue_count": 2,
        },
    }

    assert result.model_provider == "mock"

    assert (
        result.model_name
        == "mock-deterministic-v1"
    )

    assert (
        result.prompt_name
        == "executive_brief_enhancement"
    )

    assert result.prompt_version == "v1"
    assert result.input_tokens == 152
    assert result.output_tokens == 19
    assert result.total_tokens == 171
    assert result.estimated_cost_usd == 0.0
    assert result.llm_latency_ms == 4.25

    assert result.tool_calls == [
        {
            "tool_name": "read_issue",
            "status": "Success",
            "issue_id": "TEST-ISSUE-001",
        }
    ]

    assert result.run_metadata == {
        "structured_output": True,
        "request_id": "test-request-001",
    }

    assert result.used_fallback is False
    assert result.error_type is None
    assert result.error_message is None
    assert result.llm_error_type is None
    assert result.llm_error_message is None


def test_deterministic_agent_uses_empty_llm_metadata_defaults(
) -> None:
    """Deterministic executions should remain valid."""

    context = AgentContext(
        run_type="deterministic-metadata-unit-test",
        requested_by="pytest",
    )

    result = asyncio.run(
        DeterministicMetadataAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert result.agent_version == "1.0.0"
    assert result.model_provider is None
    assert result.model_name is None
    assert result.prompt_name is None
    assert result.prompt_version is None
    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.total_tokens is None
    assert result.estimated_cost_usd is None
    assert result.llm_latency_ms is None
    assert result.used_fallback is False
    assert result.tool_calls == []
    assert result.run_metadata == {}
    assert result.llm_error_type is None
    assert result.llm_error_message is None


def test_invalid_token_metadata_returns_controlled_failure(
) -> None:
    """Incomplete token usage should fail schema validation."""

    context = AgentContext(
        run_type="invalid-token-metadata-test",
        requested_by="pytest",
    )

    result = asyncio.run(
        InvalidTokenMetadataAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.FAILED
    )

    assert result.error_type == "ValidationError"

    assert (
        "must be supplied together"
        in (
            result.error_message
            or ""
        )
    )

    assert result.output_data == {}


def test_llm_failure_uses_fallback_and_preserves_error_metadata(
) -> None:
    """LLM failure details should survive fallback execution."""

    context = AgentContext(
        run_type="llm-fallback-metadata-unit-test",
        requested_by="pytest",
    )

    result = asyncio.run(
        LLMFallbackMetadataAgent().execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert result.agent_version == "1.4.0"
    assert result.used_fallback is True
    assert result.error_type == "LLMTimeoutError"

    assert (
        result.error_message
        == "Simulated LLM timeout."
    )

    assert result.llm_error_type == "LLMTimeoutError"

    assert (
        result.llm_error_message
        == "Simulated LLM timeout."
    )

    assert result.model_provider == "mock"

    assert (
        result.model_name
        == "mock-deterministic-v1"
    )

    assert result.prompt_name == "fallback_test_prompt"
    assert result.prompt_version == "v1"

    assert result.run_metadata == {
        "fallback_reason": "llm_timeout",
        "structured_output": True,
    }

    assert (
        "_execution_metadata"
        not in result.output_data
    )


@pytest.mark.integration
def test_postgres_logger_persists_complete_llm_metadata(
) -> None:
    """Every new LLM metadata field should be stored."""

    confirm_test_database()

    context = AgentContext(
        run_type="llm-metadata-integration-test",
        requested_by="pytest",
        issue_ids=[
            "TEST-ISSUE-001",
        ],
    )

    orchestrator = AgentOrchestrator(
        agents=[
            LLMMetadataAgent(),
        ],
        run_logger=PostgresAgentRunLogger(
            engine
        ),
    )

    agent_run_id: int | None = None

    try:
        result = asyncio.run(
            orchestrator.run_agent(
                "LLM Metadata Test Agent",
                context,
            )
        )

        agent_run_id = result.agent_run_id

        assert result.log_persisted is True
        assert result.logging_error is None
        assert agent_run_id is not None

        with engine.connect() as connection:
            stored_record = connection.execute(
                text(
                    """
                    SELECT
                        agent_name,
                        agent_version,
                        run_type,
                        execution_status,
                        output_summary,
                        model_provider,
                        model_name,
                        prompt_name,
                        prompt_version,
                        input_tokens,
                        output_tokens,
                        total_tokens,
                        estimated_cost_usd,
                        llm_latency_ms,
                        used_fallback,
                        tool_calls,
                        run_metadata,
                        error_type,
                        error_message,
                        llm_error_type,
                        llm_error_message,
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
            == "LLM Metadata Test Agent"
        )

        assert stored_record["agent_version"] == "2.3.1"

        assert (
            stored_record["run_type"]
            == "llm-metadata-integration-test"
        )

        assert (
            stored_record["execution_status"]
            == "Success"
        )

        assert stored_record["model_provider"] == "mock"

        assert (
            stored_record["model_name"]
            == "mock-deterministic-v1"
        )

        assert (
            stored_record["prompt_name"]
            == "executive_brief_enhancement"
        )

        assert stored_record["prompt_version"] == "v1"
        assert stored_record["input_tokens"] == 152
        assert stored_record["output_tokens"] == 19
        assert stored_record["total_tokens"] == 171

        assert (
            float(
                stored_record[
                    "estimated_cost_usd"
                ]
            )
            == 0.0
        )

        assert (
            float(
                stored_record[
                    "llm_latency_ms"
                ]
            )
            == 4.25
        )

        assert stored_record["used_fallback"] is False

        assert stored_record["tool_calls"] == [
            {
                "tool_name": "read_issue",
                "status": "Success",
                "issue_id": "TEST-ISSUE-001",
            }
        ]

        assert stored_record["run_metadata"] == {
            "structured_output": True,
            "request_id": "test-request-001",
        }

        assert stored_record["error_type"] is None
        assert stored_record["error_message"] is None
        assert stored_record["llm_error_type"] is None
        assert stored_record["llm_error_message"] is None
        assert stored_record["started_at"] is not None
        assert stored_record["completed_at"] is not None

        output_summary = json.loads(
            stored_record["output_summary"]
        )

        assert output_summary["agent_version"] == "2.3.1"
        assert output_summary["model_provider"] == "mock"

        assert (
            output_summary["prompt_version"]
            == "v1"
        )

        assert output_summary["total_tokens"] == 171
        assert output_summary["tool_call_count"] == 1

        assert (
            "_execution_metadata"
            not in output_summary["output_data_keys"]
        )

    finally:
        delete_agent_run(
            agent_run_id
        )


@pytest.mark.integration
def test_postgres_logger_persists_deterministic_defaults(
) -> None:
    """Deterministic runs should store safe defaults and NULLs."""

    confirm_test_database()

    context = AgentContext(
        run_type="deterministic-metadata-integration-test",
        requested_by="pytest",
    )

    orchestrator = AgentOrchestrator(
        agents=[
            DeterministicMetadataAgent(),
        ],
        run_logger=PostgresAgentRunLogger(
            engine
        ),
    )

    agent_run_id: int | None = None

    try:
        result = asyncio.run(
            orchestrator.run_agent(
                "Deterministic Metadata Test Agent",
                context,
            )
        )

        agent_run_id = result.agent_run_id

        assert result.log_persisted is True
        assert agent_run_id is not None

        with engine.connect() as connection:
            stored_record = connection.execute(
                text(
                    """
                    SELECT
                        agent_version,
                        model_provider,
                        model_name,
                        prompt_name,
                        prompt_version,
                        input_tokens,
                        output_tokens,
                        total_tokens,
                        estimated_cost_usd,
                        llm_latency_ms,
                        used_fallback,
                        tool_calls,
                        run_metadata,
                        error_type,
                        error_message,
                        llm_error_type,
                        llm_error_message
                    FROM agent_runs
                    WHERE agent_run_id = :agent_run_id;
                    """
                ),
                {
                    "agent_run_id": agent_run_id,
                },
            ).mappings().one()

        assert stored_record["agent_version"] == "1.0.0"
        assert stored_record["model_provider"] is None
        assert stored_record["model_name"] is None
        assert stored_record["prompt_name"] is None
        assert stored_record["prompt_version"] is None
        assert stored_record["input_tokens"] is None
        assert stored_record["output_tokens"] is None
        assert stored_record["total_tokens"] is None
        assert stored_record["estimated_cost_usd"] is None
        assert stored_record["llm_latency_ms"] is None
        assert stored_record["used_fallback"] is False
        assert stored_record["tool_calls"] == []
        assert stored_record["run_metadata"] == {}
        assert stored_record["error_type"] is None
        assert stored_record["error_message"] is None
        assert stored_record["llm_error_type"] is None
        assert stored_record["llm_error_message"] is None

    finally:
        delete_agent_run(
            agent_run_id
        )


@pytest.mark.integration
def test_postgres_logger_persists_fallback_and_llm_error(
) -> None:
    """Fallback and LLM failure details should be stored together."""

    confirm_test_database()

    context = AgentContext(
        run_type="llm-fallback-metadata-integration-test",
        requested_by="pytest",
    )

    orchestrator = AgentOrchestrator(
        agents=[
            LLMFallbackMetadataAgent(),
        ],
        run_logger=PostgresAgentRunLogger(
            engine
        ),
    )

    agent_run_id: int | None = None

    try:
        result = asyncio.run(
            orchestrator.run_agent(
                "LLM Fallback Metadata Agent",
                context,
            )
        )

        agent_run_id = result.agent_run_id

        assert result.log_persisted is True
        assert agent_run_id is not None

        with engine.connect() as connection:
            stored_record = connection.execute(
                text(
                    """
                    SELECT
                        agent_version,
                        execution_status,
                        model_provider,
                        model_name,
                        prompt_name,
                        prompt_version,
                        used_fallback,
                        tool_calls,
                        run_metadata,
                        error_type,
                        error_message,
                        llm_error_type,
                        llm_error_message
                    FROM agent_runs
                    WHERE agent_run_id = :agent_run_id;
                    """
                ),
                {
                    "agent_run_id": agent_run_id,
                },
            ).mappings().one()

        assert stored_record["agent_version"] == "1.4.0"
        assert stored_record["execution_status"] == "Success"
        assert stored_record["model_provider"] == "mock"

        assert (
            stored_record["model_name"]
            == "mock-deterministic-v1"
        )

        assert (
            stored_record["prompt_name"]
            == "fallback_test_prompt"
        )

        assert stored_record["prompt_version"] == "v1"
        assert stored_record["used_fallback"] is True
        assert stored_record["tool_calls"] == []

        assert stored_record["run_metadata"] == {
            "fallback_reason": "llm_timeout",
            "structured_output": True,
        }

        assert (
            stored_record["error_type"]
            == "LLMTimeoutError"
        )

        assert (
            stored_record["error_message"]
            == "Simulated LLM timeout."
        )

        assert (
            stored_record["llm_error_type"]
            == "LLMTimeoutError"
        )

        assert (
            stored_record["llm_error_message"]
            == "Simulated LLM timeout."
        )

    finally:
        delete_agent_run(
            agent_run_id
        )