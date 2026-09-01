from __future__ import annotations

from typing import Any

from backend.app.services.agent_tool_service import (
    build_default_tool_executor,
    default_tool_registry,
)
from backend.app.tools.mcp_models import (
    MCPCallToolResult,
    MCPListToolsResult,
    MCPTextContent,
    MCPToolAnnotations,
    MCPToolDescriptor,
)
from backend.app.tools.tool_exceptions import (
    ToolNotFoundError,
)
from backend.app.tools.tool_executor import (
    AgentToolExecutor,
)
from backend.app.tools.tool_models import (
    ToolAccessMode,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionStatus,
)
from backend.app.tools.tool_registry import (
    ToolRegistry,
)


class MCPToolUnavailableError(RuntimeError):
    """
    Protocol-level failure for a tool that cannot be discovered/called.

    Unknown and unauthorized tools intentionally use the same external
    error so the MCP surface does not become a permission oracle.
    """


def build_mcp_annotations(
    definition: ToolDefinition,
) -> MCPToolAnnotations:
    """
    Build conservative MCP annotations from the internal access mode.

    These are behavioural hints only and never replace executor gates.
    """

    is_read_only = (
        definition.access_mode
        == ToolAccessMode.READ_ONLY
    )

    return MCPToolAnnotations(
        read_only_hint=is_read_only,
        destructive_hint=(
            not is_read_only
        ),
        idempotent_hint=is_read_only,
        open_world_hint=False,
    )


def build_mcp_tool_descriptor(
    definition: ToolDefinition,
) -> MCPToolDescriptor:
    """Convert one internal tool definition to an MCP descriptor."""

    return MCPToolDescriptor(
        name=definition.name,
        description=definition.description,
        input_schema=definition.input_json_schema(),
        output_schema=definition.output_json_schema(),
        annotations=build_mcp_annotations(
            definition
        ),
    )


def build_safe_mcp_meta(
    *,
    tool_name: str,
    execution_status: ToolExecutionStatus,
    tool_call_id: str,
    access_mode: ToolAccessMode | None,
) -> dict[str, Any]:
    """Build audit-safe protocol metadata without arguments or output."""

    return {
        "toolName": tool_name,
        "toolCallId": tool_call_id,
        "executionStatus": execution_status.value,
        "accessMode": (
            access_mode.value
            if access_mode is not None
            else None
        ),
    }


class ControlledMCPToolService:
    """
    MCP-compatible adapter over the existing controlled tool system.

    It owns no business handler and performs no direct database access.
    ToolRegistry and AgentToolExecutor remain the source of truth.
    """

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        executor: AgentToolExecutor,
    ) -> None:
        self.registry = registry
        self.executor = executor

    def list_tools(
        self,
        *,
        context: ToolExecutionContext,
    ) -> MCPListToolsResult:
        """
        Return only tools executable in this exact authorization context.

        Write tools therefore remain absent until every write gate,
        including explicit human approval, has already been granted.
        """

        visible_tools: list[
            MCPToolDescriptor
        ] = []

        for definition in self.registry.definitions():
            permission_reason = (
                self.executor.permission_reason(
                    definition=definition,
                    context=context,
                )
            )

            if permission_reason is not None:
                continue

            visible_tools.append(
                build_mcp_tool_descriptor(
                    definition
                )
            )

        return MCPListToolsResult(
            tools=visible_tools,
            result_type="complete",
            ttl_ms=0,
            cache_scope="private",
        )

    async def call_tool(
        self,
        *,
        name: str,
        arguments: dict[str, Any] | None,
        context: ToolExecutionContext,
    ) -> MCPCallToolResult:
        """
        Execute one MCP tools/call request through AgentToolExecutor.

        The execution context is server-side data. It never comes from
        model-supplied tool arguments.
        """

        try:
            definition = self.registry.get(
                name
            )

        except ToolNotFoundError as error:
            raise MCPToolUnavailableError(
                "The requested MCP tool is unavailable."
            ) from error

        # Hide authorization details and prevent guessed tool names from
        # becoming a capability-discovery side channel.
        if (
            self.executor.permission_reason(
                definition=definition,
                context=context,
            )
            is not None
        ):
            raise MCPToolUnavailableError(
                "The requested MCP tool is unavailable."
            )

        execution_result = (
            await self.executor.execute(
                tool_name=definition.name,
                arguments=arguments or {},
                context=context,
            )
        )

        call_record = execution_result.call_record

        safe_meta = build_safe_mcp_meta(
            tool_name=definition.name,
            execution_status=(
                execution_result.status
            ),
            tool_call_id=(
                call_record.tool_call_id
            ),
            access_mode=(
                call_record.access_mode
            ),
        )

        if (
            execution_result.status
            == ToolExecutionStatus.SUCCESS
        ):
            return MCPCallToolResult(
                content=[
                    MCPTextContent(
                        text=(
                            f"Controlled tool '{definition.name}' "
                            "completed successfully."
                        )
                    )
                ],
                result_type="complete",
                structured_content=(
                    execution_result.output
                ),
                is_error=False,
                meta=safe_meta,
            )

        # Tool-level validation/execution failures are returned as an MCP
        # tool error so a conforming client/model can reason about failure
        # without receiving raw exception data or sensitive arguments.
        error_type = (
            call_record.error_type
            or "ControlledToolError"
        )

        return MCPCallToolResult(
            content=[
                MCPTextContent(
                    text=(
                        f"Controlled tool '{definition.name}' "
                        f"failed with {error_type}."
                    )
                )
            ],
            result_type="complete",
            structured_content=None,
            is_error=True,
            meta=safe_meta,
        )


def build_default_mcp_tool_service(
) -> ControlledMCPToolService:
    """Build the application MCP adapter from the existing registry."""

    return ControlledMCPToolService(
        registry=default_tool_registry,
        executor=build_default_tool_executor(),
    )
