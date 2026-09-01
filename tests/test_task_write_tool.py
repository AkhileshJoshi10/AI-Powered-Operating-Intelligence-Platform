from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any

import backend.app.tools.task_write_tool as task_tool_module
from backend.app.services.agent_tool_service import (
    default_tool_registry,
    list_registered_agent_tools,
)
from backend.app.tools import (
    AgentToolExecutor,
    ToolAccessMode,
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolRegistry,
)
from backend.app.tools.task_write_tool import (
    CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME,
    build_task_conversion_tool_definition,
)


NOW = datetime(
    2026,
    8,
    31,
    12,
    0,
    0,
)


def build_task_data() -> dict[str, Any]:
    return {
        "task_id": 31,
        "issue_id": "ISSUE-HIGH-001",
        "recommendation_id": 21,
        "title": "Restore product availability",
        "description": (
            "Expedite replenishment and verify supplier delivery."
        ),
        "assigned_to": None,
        "assigned_role": "Inventory Manager",
        "due_date": date(2026, 9, 2),
        "priority_level": "High",
        "status": "To Do",
        "issue_title": None,
        "recommendation_title": None,
        "created_at": NOW,
        "updated_at": NOW,
    }


def build_context(
    *,
    allow_write_tools: bool,
    approved: bool,
    agent_name: str = "Recommendation Agent",
) -> ToolExecutionContext:
    return ToolExecutionContext(
        run_id="RUN-TASK-WRITE-001",
        agent_name=agent_name,
        requested_by="Manager Review User",
        allowed_tools=[
            CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME
        ],
        allow_write_tools=allow_write_tools,
        approved_write_tools=(
            [
                CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME
            ]
            if approved
            else []
        ),
    )


def build_executor(
    *,
    enabled: bool = True,
    write_tools_enabled: bool = True,
) -> AgentToolExecutor:
    registry = ToolRegistry()

    registry.register(
        build_task_conversion_tool_definition(
            enabled=enabled
        )
    )

    return AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=write_tools_enabled,
        timeout_seconds=1.0,
    )


def test_task_conversion_tool_is_registered_but_disabled_by_default() -> None:
    assert (
        CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME
        in list_registered_agent_tools()
    )

    definition = default_tool_registry.get(
        CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME
    )

    assert definition.enabled is False
    assert definition.access_mode == ToolAccessMode.WRITE
    assert definition.requires_human_approval is True
    assert definition.allowed_agents == (
        "Recommendation Agent",
    )


def test_specific_capability_gate_denies_before_service(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        task_tool_module,
        "convert_recommendation_to_task",
        lambda *args, **kwargs: calls.append("called"),
    )

    result = asyncio.run(
        build_executor(
            enabled=False,
            write_tools_enabled=True,
        ).execute(
            tool_name=(
                CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME
            ),
            arguments={"recommendation_id": 21},
            context=build_context(
                allow_write_tools=True,
                approved=True,
            ),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED
    assert calls == []


def test_global_write_gate_denies_before_service(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        task_tool_module,
        "convert_recommendation_to_task",
        lambda *args, **kwargs: calls.append("called"),
    )

    result = asyncio.run(
        build_executor(
            enabled=True,
            write_tools_enabled=False,
        ).execute(
            tool_name=(
                CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME
            ),
            arguments={"recommendation_id": 21},
            context=build_context(
                allow_write_tools=True,
                approved=True,
            ),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED
    assert calls == []


def test_run_write_permission_is_required(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        task_tool_module,
        "convert_recommendation_to_task",
        lambda *args, **kwargs: calls.append("called"),
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name=(
                CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME
            ),
            arguments={"recommendation_id": 21},
            context=build_context(
                allow_write_tools=False,
                approved=True,
            ),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED
    assert calls == []


def test_explicit_human_approval_is_required(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        task_tool_module,
        "convert_recommendation_to_task",
        lambda *args, **kwargs: calls.append("called"),
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name=(
                CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME
            ),
            arguments={"recommendation_id": 21},
            context=build_context(
                allow_write_tools=True,
                approved=False,
            ),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED
    assert calls == []


def test_unapproved_agent_cannot_use_task_write_tool(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        task_tool_module,
        "convert_recommendation_to_task",
        lambda *args, **kwargs: calls.append("called"),
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name=(
                CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME
            ),
            arguments={"recommendation_id": 21},
            context=build_context(
                allow_write_tools=True,
                approved=True,
                agent_name="Executive Brief Agent",
            ),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED
    assert calls == []


def test_model_cannot_supply_task_fields(
    monkeypatch: Any,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        task_tool_module,
        "convert_recommendation_to_task",
        lambda *args, **kwargs: calls.append("called"),
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name=(
                CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME
            ),
            arguments={
                "recommendation_id": 21,
                "title": "Invented task title",
                "status": "Completed",
            },
            context=build_context(
                allow_write_tools=True,
                approved=True,
            ),
        )
    )

    assert result.status == ToolExecutionStatus.FAILED
    assert (
        result.call_record.error_type
        == "ToolInputValidationError"
    )
    assert calls == []


def test_not_accepted_recommendation_cannot_create_task(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        task_tool_module,
        "convert_recommendation_to_task",
        lambda recommendation_id: {
            "outcome": "invalid_status",
            "current_status": "Pending Review",
        },
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name=(
                CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME
            ),
            arguments={"recommendation_id": 21},
            context=build_context(
                allow_write_tools=True,
                approved=True,
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output["outcome"] == "not_accepted"
    assert result.output["task"] is None
    assert result.output["current_status"] == "Pending Review"


def test_accepted_recommendation_uses_persisted_task_data(
    monkeypatch: Any,
) -> None:
    calls: list[int] = []

    def fake_convert(
        recommendation_id: int,
    ) -> dict[str, Any]:
        calls.append(
            recommendation_id
        )

        return {
            "outcome": "success",
            "response": {
                "status": "success",
                "message": (
                    "Recommendation converted into "
                    "a task successfully."
                ),
                "recommendation_status": "Converted to Task",
                "task": build_task_data(),
            },
        }

    monkeypatch.setattr(
        task_tool_module,
        "convert_recommendation_to_task",
        fake_convert,
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name=(
                CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME
            ),
            arguments={"recommendation_id": 21},
            context=build_context(
                allow_write_tools=True,
                approved=True,
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output["outcome"] == "converted"
    assert result.output["task_id"] == 31
    assert (
        result.output["task"]["title"]
        == "Restore product availability"
    )
    assert calls == [21]


def test_already_converted_is_idempotent_business_outcome(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        task_tool_module,
        "convert_recommendation_to_task",
        lambda recommendation_id: {
            "outcome": "already_converted",
            "task_id": 31,
            "current_status": "Converted to Task",
        },
    )

    result = asyncio.run(
        build_executor().execute(
            tool_name=(
                CREATE_TASK_FROM_APPROVED_RECOMMENDATION_TOOL_NAME
            ),
            arguments={"recommendation_id": 21},
            context=build_context(
                allow_write_tools=True,
                approved=True,
            ),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output["outcome"] == "already_converted"
    assert result.output["task_id"] == 31
    assert result.output["task"] is None
