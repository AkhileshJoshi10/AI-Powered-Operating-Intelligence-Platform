from __future__ import annotations


class AgentToolError(Exception):
    """Base exception for controlled agent-tool failures."""


class ToolRegistrationError(AgentToolError):
    """Raised when a tool definition cannot be registered."""


class ToolNotFoundError(AgentToolError):
    """Raised when a requested tool is not registered."""


class ToolPermissionError(AgentToolError):
    """Raised when tool execution is not permitted."""


class ToolInputValidationError(AgentToolError):
    """Raised when tool arguments fail their declared schema."""


class ToolOutputValidationError(AgentToolError):
    """Raised when tool output fails its declared schema."""


class ToolExecutionError(AgentToolError):
    """Raised when a tool handler fails during execution."""


class ToolTimeoutError(AgentToolError):
    """Raised when a tool exceeds its execution timeout."""
