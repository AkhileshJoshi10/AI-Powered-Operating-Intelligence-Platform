from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TaskStatus = Literal[
    "Unassigned",
    "To Do",
    "In Progress",
    "Blocked",
    "Completed",
]


TaskPriority = Literal[
    "High",
    "Medium",
    "Low",
]


class TaskItem(BaseModel):
    """Task information used in task lists and conversion responses."""

    task_id: int
    issue_id: str | None = None
    recommendation_id: int | None = None

    title: str
    description: str | None = None

    assigned_to: str | None = None
    assigned_role: str | None = None

    due_date: date | None = None
    priority_level: TaskPriority | None = None
    status: TaskStatus

    issue_title: str | None = None
    recommendation_title: str | None = None

    created_at: datetime
    updated_at: datetime


class TaskDetail(TaskItem):
    """Complete task information with linked business context."""

    issue_type: str | None = None
    business_area: str | None = None
    issue_status: str | None = None
    recommendation_status: str | None = None


class TaskStatusUpdateRequest(BaseModel):
    """New Kanban status requested for a task."""

    status: TaskStatus


class TaskAssignmentRequest(BaseModel):
    """Employee assignment information for a task."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    assigned_to: str = Field(
        min_length=2,
        max_length=150,
    )

    assigned_role: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )


class TaskConversionResponse(BaseModel):
    """Response returned after converting a recommendation into a task."""

    status: str = Field(default="success")
    message: str
    recommendation_status: str
    task: TaskItem


class TaskListResponse(BaseModel):
    """Paginated response returned by GET /api/tasks."""

    status: str = Field(default="success")
    total_items: int
    limit: int
    offset: int
    items: list[TaskItem]


class TaskDetailResponse(BaseModel):
    """Response returned by GET /api/tasks/{task_id}."""

    status: str = Field(default="success")
    task: TaskDetail


class TaskStatusUpdateResponse(BaseModel):
    """Response returned after changing a task's Kanban status."""

    status: str = Field(default="success")
    message: str
    task: TaskDetail


class TaskAssignmentResponse(BaseModel):
    """Response returned after assigning a task."""

    status: str = Field(default="success")
    message: str
    task: TaskDetail