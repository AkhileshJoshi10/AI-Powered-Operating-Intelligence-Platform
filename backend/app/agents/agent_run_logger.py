from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.engine import Engine

from backend.app.agents.agent_context import AgentContext
from backend.app.agents.agent_result import AgentResult
from backend.app.db.database import engine


MAX_SUMMARY_LENGTH = 4000


def truncate_text(
    value: str,
    *,
    maximum_length: int = MAX_SUMMARY_LENGTH,
) -> str:
    """Restrict stored log text to a controlled length."""

    if len(value) <= maximum_length:
        return value

    return (
        value[:maximum_length - 3]
        + "..."
    )


def serialize_summary(
    payload: dict[str, Any],
) -> str:
    """Convert a summary payload into compact JSON text."""

    serialized_value = json.dumps(
        payload,
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
        sort_keys=True,
    )

    return truncate_text(
        serialized_value
    )


def serialize_json_value(
    value: Any,
) -> str:
    """Serialize one value for a PostgreSQL JSONB parameter."""

    return json.dumps(
        value,
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
        sort_keys=True,
    )


def to_naive_utc(
    value: datetime,
) -> datetime:
    """
    Convert a datetime to naive UTC.

    The current agent_runs columns use PostgreSQL TIMESTAMP without
    time-zone information.
    """

    if value.tzinfo is None:
        return value

    return (
        value.astimezone(timezone.utc)
        .replace(tzinfo=None)
    )


def build_input_summary(
    context: AgentContext,
) -> str:
    """
    Build a compact and safe input summary.

    Full business data is not stored in the execution log. Only
    identifiers and available input categories are recorded.
    """

    payload = {
        "run_id": context.run_id,
        "run_type": context.run_type,
        "requested_by": context.requested_by,
        "issue_count": len(
            context.issue_ids
        ),
        "issue_ids": context.issue_ids[:20],
        "input_data_keys": sorted(
            str(key)
            for key in context.input_data
        ),
        "metadata_keys": sorted(
            str(key)
            for key in context.metadata
        ),
        "created_at": (
            context.created_at.isoformat()
        ),
    }

    return serialize_summary(
        payload
    )


def build_output_summary(
    result: AgentResult,
) -> str:
    """Build a compact summary of an agent result."""

    payload = {
        "run_id": result.run_id,
        "agent_version": (
            result.agent_version
        ),
        "summary": result.summary,
        "used_fallback": (
            result.used_fallback
        ),
        "error_type": result.error_type,
        "error_message": (
            result.error_message
        ),
        "model_provider": (
            result.model_provider
        ),
        "model_name": result.model_name,
        "prompt_name": result.prompt_name,
        "prompt_version": (
            result.prompt_version
        ),
        "input_tokens": result.input_tokens,
        "output_tokens": (
            result.output_tokens
        ),
        "total_tokens": result.total_tokens,
        "estimated_cost_usd": (
            result.estimated_cost_usd
        ),
        "llm_latency_ms": (
            result.llm_latency_ms
        ),
        "tool_call_count": len(
            result.tool_calls
        ),
        "llm_error_type": (
            result.llm_error_type
        ),
        "llm_error_message": (
            result.llm_error_message
        ),
        "output_data_keys": sorted(
            str(key)
            for key in result.output_data
        ),
        "duration_ms": result.duration_ms,
    }

    return serialize_summary(
        payload
    )


class AgentRunLogger(Protocol):
    """Interface supported by agent execution loggers."""

    def save_result(
        self,
        *,
        context: AgentContext,
        result: AgentResult,
    ) -> int:
        """Store an agent result and return its database ID."""

        ...


class PostgresAgentRunLogger:
    """Store deterministic, LLM, and tool execution records."""

    def __init__(
        self,
        database_engine: Engine = engine,
    ) -> None:
        """Initialize the logger with a SQLAlchemy engine."""

        self._engine = database_engine

    def save_result(
        self,
        *,
        context: AgentContext,
        result: AgentResult,
    ) -> int:
        """Insert one synchronized execution into agent_runs."""

        if context.run_id != result.run_id:
            raise ValueError(
                "The context and result run IDs do not match."
            )

        query = text(
            """
            INSERT INTO agent_runs (
                agent_name,
                agent_version,
                run_type,
                execution_status,
                input_summary,
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
            )
            VALUES (
                :agent_name,
                :agent_version,
                :run_type,
                :execution_status,
                :input_summary,
                :output_summary,
                :model_provider,
                :model_name,
                :prompt_name,
                :prompt_version,
                :input_tokens,
                :output_tokens,
                :total_tokens,
                :estimated_cost_usd,
                :llm_latency_ms,
                :used_fallback,
                CAST(:tool_calls AS JSONB),
                CAST(:run_metadata AS JSONB),
                :error_type,
                :error_message,
                :llm_error_type,
                :llm_error_message,
                :started_at,
                :completed_at
            )
            RETURNING agent_run_id;
            """
        )

        parameters = {
            "agent_name": result.agent_name,
            "agent_version": (
                result.agent_version
            ),
            "run_type": result.run_type,
            "execution_status": (
                result.execution_status.value
            ),
            "input_summary": (
                build_input_summary(
                    context
                )
            ),
            "output_summary": (
                build_output_summary(
                    result
                )
            ),
            "model_provider": (
                result.model_provider
            ),
            "model_name": result.model_name,
            "prompt_name": result.prompt_name,
            "prompt_version": (
                result.prompt_version
            ),
            "input_tokens": result.input_tokens,
            "output_tokens": (
                result.output_tokens
            ),
            "total_tokens": result.total_tokens,
            "estimated_cost_usd": (
                result.estimated_cost_usd
            ),
            "llm_latency_ms": (
                result.llm_latency_ms
            ),
            "used_fallback": (
                result.used_fallback
            ),
            "tool_calls": (
                serialize_json_value(
                    result.tool_calls
                )
            ),
            "run_metadata": (
                serialize_json_value(
                    result.run_metadata
                )
            ),
            "error_type": result.error_type,
            "error_message": (
                truncate_text(
                    result.error_message
                )
                if result.error_message
                else None
            ),
            "llm_error_type": (
                result.llm_error_type
            ),
            "llm_error_message": (
                truncate_text(
                    result.llm_error_message
                )
                if result.llm_error_message
                else None
            ),
            "started_at": to_naive_utc(
                result.started_at
            ),
            "completed_at": to_naive_utc(
                result.completed_at
            ),
        }

        with self._engine.begin() as connection:
            agent_run_id = connection.execute(
                query,
                parameters,
            ).scalar_one()

        return int(
            agent_run_id
        )