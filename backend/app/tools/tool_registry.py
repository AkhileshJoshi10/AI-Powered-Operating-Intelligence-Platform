from __future__ import annotations

import re

from backend.app.tools.tool_exceptions import (
    ToolNotFoundError,
    ToolRegistrationError,
)
from backend.app.tools.tool_models import (
    ToolAccessMode,
    ToolDefinition,
)


TOOL_NAME_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{2,63}$"
)


def normalize_tool_name(
    value: object,
) -> str:
    """Normalize and validate one stable tool identifier."""

    normalized = "_".join(
        str(value).strip().casefold().split()
    )

    if not TOOL_NAME_PATTERN.fullmatch(
        normalized
    ):
        raise ToolRegistrationError(
            "Tool names must use lowercase letters, numbers, "
            "and underscores, start with a letter, and contain "
            "between 3 and 64 characters."
        )

    return normalized


class ToolRegistry:
    """In-memory registry containing only explicitly approved tools."""

    def __init__(
        self,
    ) -> None:
        self._tools: dict[
            str,
            ToolDefinition,
        ] = {}

    def register(
        self,
        definition: ToolDefinition,
    ) -> None:
        """Register one tool definition and reject unsafe definitions."""

        normalized_name = normalize_tool_name(
            definition.name
        )

        if normalized_name != definition.name:
            raise ToolRegistrationError(
                "ToolDefinition.name must already be normalized "
                f"as '{normalized_name}'."
            )

        if normalized_name in self._tools:
            raise ToolRegistrationError(
                f"Tool '{normalized_name}' is already registered."
            )

        cleaned_description = " ".join(
            definition.description.split()
        )

        if not cleaned_description:
            raise ToolRegistrationError(
                "Every tool must define a non-empty description."
            )

        if (
            definition.access_mode
            == ToolAccessMode.WRITE
            and not definition.requires_human_approval
        ):
            raise ToolRegistrationError(
                "Write tools must require human approval."
            )

        self._tools[
            normalized_name
        ] = definition

    def get(
        self,
        tool_name: str,
    ) -> ToolDefinition:
        """Return one registered tool or fail closed."""

        try:
            normalized_name = normalize_tool_name(
                tool_name
            )

        except ToolRegistrationError as error:
            raise ToolNotFoundError(
                "The requested tool name is invalid."
            ) from error

        definition = self._tools.get(
            normalized_name
        )

        if definition is None:
            raise ToolNotFoundError(
                f"Tool '{normalized_name}' is not registered."
            )

        return definition

    def names(
        self,
    ) -> list[str]:
        """Return registered tool names in stable order."""

        return sorted(
            self._tools
        )

    def definitions(
        self,
    ) -> list[ToolDefinition]:
        """Return registered definitions in stable name order."""

        return [
            self._tools[
                name
            ]
            for name in self.names()
        ]

    def clear(
        self,
    ) -> None:
        """Remove all definitions. Intended mainly for isolated tests."""

        self._tools.clear()
