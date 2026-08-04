from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChiefOfStaffRunRequest(BaseModel):
    """Input settings for one complete Chief of Staff workflow."""

    requested_by: str = Field(
        default="API User",
        min_length=1,
        max_length=150,
    )

    issue_ids: list[str] = Field(
        default_factory=list,
        max_length=50,
    )

    finding_limit: int = Field(
        default=10,
        ge=1,
        le=100,
    )

    manager_limit: int = Field(
        default=15,
        ge=1,
        le=100,
    )

    executive_limit: int = Field(
        default=10,
        ge=1,
        le=50,
    )

    analysis_limit: int = Field(
        default=10,
        ge=1,
        le=50,
    )

    recommendation_limit: int = Field(
        default=10,
        ge=1,
        le=50,
    )

    stop_on_failure: bool = True


class ChiefOfStaffAgentResult(BaseModel):
    """One agent result returned by the workflow."""

    run_id: str
    agent_name: str
    run_type: str

    execution_status: Literal[
        "Success",
        "Failed",
        "Skipped",
    ]

    summary: str
    output_data: dict[str, Any]

    used_fallback: bool

    error_type: str | None = None
    error_message: str | None = None

    started_at: datetime
    completed_at: datetime
    duration_ms: float

    agent_run_id: int | None = None
    log_persisted: bool
    logging_error: str | None = None


class ChiefOfStaffWorkflowSummary(BaseModel):
    """Compact status summary for one workflow execution."""

    total_agents: int
    completed_agents: int
    successful_agents: int
    failed_agents: int
    skipped_agents: int

    stopped_early: bool
    failed_agent_name: str | None = None

    persisted_agent_logs: int
    logging_failures: int


class ChiefOfStaffRunResponse(BaseModel):
    """Response returned after running the Chief of Staff workflow."""

    status: Literal["success"] = "success"

    workflow_status: Literal[
        "Complete",
        "Partial",
        "Failed",
    ]

    run_id: str
    run_type: str
    requested_by: str

    started_at: datetime
    completed_at: datetime
    duration_ms: float

    agent_sequence: list[str]
    workflow_summary: ChiefOfStaffWorkflowSummary

    results: list[ChiefOfStaffAgentResult]