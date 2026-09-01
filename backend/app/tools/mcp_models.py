from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


MCP_PROTOCOL_TARGET = "2026-07-28"


class MCPToolAnnotations(BaseModel):
    """
    Conservative MCP tool-behaviour hints.

    These are only client hints. Application authorization continues to
    come exclusively from AgentToolExecutor.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    read_only_hint: bool = Field(
        serialization_alias="readOnlyHint",
    )
    destructive_hint: bool = Field(
        serialization_alias="destructiveHint",
    )
    idempotent_hint: bool = Field(
        serialization_alias="idempotentHint",
    )
    open_world_hint: bool = Field(
        serialization_alias="openWorldHint",
    )


class MCPToolDescriptor(BaseModel):
    """Protocol-shaped MCP tool descriptor."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    name: str
    description: str

    input_schema: dict[str, Any] = Field(
        serialization_alias="inputSchema",
    )
    output_schema: dict[str, Any] = Field(
        serialization_alias="outputSchema",
    )

    annotations: MCPToolAnnotations


class MCPListToolsResult(BaseModel):
    """
    Modern tools/list result.

    ttlMs=0 and cacheScope=private are intentionally conservative because
    the list depends on the current authorization/execution context.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    tools: list[MCPToolDescriptor]

    result_type: Literal["complete"] = Field(
        default="complete",
        serialization_alias="resultType",
    )
    ttl_ms: int = Field(
        default=0,
        ge=0,
        serialization_alias="ttlMs",
    )
    cache_scope: Literal[
        "private",
    ] = Field(
        default="private",
        serialization_alias="cacheScope",
    )

    next_cursor: str | None = Field(
        default=None,
        serialization_alias="nextCursor",
    )


class MCPTextContent(BaseModel):
    """MCP text content block."""

    model_config = ConfigDict(
        extra="forbid",
    )

    type: Literal["text"] = "text"
    text: str = Field(
        min_length=1,
        max_length=4000,
    )


class MCPCallToolResult(BaseModel):
    """Protocol-shaped MCP tools/call result."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    content: list[MCPTextContent]

    result_type: Literal["complete"] = Field(
        default="complete",
        serialization_alias="resultType",
    )

    structured_content: Any | None = Field(
        default=None,
        serialization_alias="structuredContent",
    )

    is_error: bool = Field(
        default=False,
        serialization_alias="isError",
    )

    meta: dict[str, Any] = Field(
        default_factory=dict,
        serialization_alias="_meta",
    )
