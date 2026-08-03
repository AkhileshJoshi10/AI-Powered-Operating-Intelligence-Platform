from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentExecutionStatus(str, Enum):
    """Supported states for an agent execution."""

    SUCCESS = "Success"
    FAILED = "Failed"
    SKIPPED = "Skipped"


class AgentResult(BaseModel):
    """
    Structured result returned by every agent.

    The same structure supports deterministic agents, LLM-supported
    agents, fallback execution, and execution logging.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    run_id: str = Field(
        min_length=1,
    )

    agent_name: str = Field(
        min_length=1,
        max_length=150,
    )

    run_type: str = Field(
        min_length=1,
        max_length=100,
    )

    execution_status: AgentExecutionStatus

    summary: str = ""

    output_data: dict[str, Any] = Field(
        default_factory=dict,
    )

    used_fallback: bool = False

    error_type: str | None = None

    error_message: str | None = None

    started_at: datetime

    completed_at: datetime

    duration_ms: float = Field(
        ge=0,
    )

    agent_run_id: int | None = Field(
        default=None,
        ge=1,
    )

    log_persisted: bool = False

    logging_error: str | None = None