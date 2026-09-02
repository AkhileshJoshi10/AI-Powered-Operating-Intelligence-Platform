from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


AutomationCallbackStatus = Literal[
    "Succeeded",
    "Failed",
    "Skipped",
]


class AutomationLogItem(BaseModel):
    """One persisted automation execution record."""

    automation_log_id: int
    task_id: int | None = None
    issue_id: str | None = None
    workflow_name: str
    action_type: str
    execution_status: str
    idempotency_key: str
    n8n_execution_id: str | None = None
    attempt_count: int
    http_status_code: int | None = None
    message: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    request_metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    executed_at: datetime


class AutomationLogListResponse(BaseModel):
    """Paginated automation log response."""

    status: str = Field(default="success")
    total_items: int
    limit: int
    offset: int
    items: list[AutomationLogItem]


class AutomationLogDetailResponse(BaseModel):
    """Response containing one automation log."""

    status: str = Field(default="success")
    automation_log: AutomationLogItem


class IssueAutomationTriggerRequest(BaseModel):
    """Request to trigger an issue-level workflow."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    issue_id: str = Field(
        min_length=2,
        max_length=220,
    )


class TaskAutomationTriggerRequest(BaseModel):
    """Request to trigger a task-level workflow."""

    model_config = ConfigDict(
        extra="forbid",
    )

    task_id: int = Field(
        ge=1,
    )


class AutomationTriggerResponse(BaseModel):
    """Response returned after a controlled n8n trigger request."""

    status: str = Field(default="success")
    message: str
    duplicate: bool = False
    automation_log: AutomationLogItem


class AutomationCallbackRequest(BaseModel):
    """Protected result callback sent by n8n."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    idempotency_key: str = Field(
        min_length=8,
        max_length=200,
    )
    execution_status: AutomationCallbackStatus
    n8n_execution_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    message: str | None = Field(
        default=None,
        max_length=4000,
    )
    error_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )
    error_message: str | None = Field(
        default=None,
        max_length=4000,
    )


class AutomationCallbackResponse(BaseModel):
    """Response returned after an authenticated n8n callback."""

    status: str = Field(default="success")
    message: str
    duplicate: bool = False
    automation_log: AutomationLogItem
