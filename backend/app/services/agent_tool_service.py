from __future__ import annotations

from typing import Any

from backend.app.core.config import settings
from backend.app.tools import (
    AgentToolExecutor,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolRegistry,
)
from backend.app.tools.analytics_read_tools import (
    register_read_only_analytics_tools,
)
from backend.app.tools.business_read_tools import (
    register_read_only_business_tools,
)
from backend.app.tools.read_only_sql_tool import (
    build_read_only_sql_tool_definition,
)
from backend.app.tools.task_write_tool import (
    build_task_conversion_tool_definition,
)


default_tool_registry = ToolRegistry()

register_read_only_business_tools(
    default_tool_registry
)

register_read_only_analytics_tools(
    default_tool_registry
)

default_tool_registry.register(
    build_read_only_sql_tool_definition(
        enabled=settings.agent_read_only_sql_enabled,
        statement_timeout_ms=(
            settings.agent_read_only_sql_statement_timeout_ms
        ),
        maximum_rows=settings.agent_read_only_sql_max_rows,
    )
)

default_tool_registry.register(
    build_task_conversion_tool_definition(
        enabled=settings.agent_task_conversion_tool_enabled,
    )
)


def register_agent_tool(
    definition: ToolDefinition,
) -> None:
    """Register one additional application-approved agent tool."""

    default_tool_registry.register(
        definition
    )


def list_registered_agent_tools(
) -> list[str]:
    """Return registered application tool names."""

    return default_tool_registry.names()


def build_default_tool_executor(
) -> AgentToolExecutor:
    """Build the controlled executor from application settings."""

    return AgentToolExecutor(
        default_tool_registry,
        tools_enabled=(
            settings.agent_tools_enabled
        ),
        write_tools_enabled=(
            settings.agent_write_tools_enabled
        ),
        timeout_seconds=(
            settings.agent_tool_timeout_seconds
        ),
    )


async def execute_agent_tool(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    context: ToolExecutionContext,
) -> ToolExecutionResult:
    """Execute one registered tool through the controlled layer."""

    executor = build_default_tool_executor()

    return await executor.execute(
        tool_name=tool_name,
        arguments=arguments,
        context=context,
    )
