from __future__ import annotations

import json
from string import Template
from typing import Any

from pydantic import BaseModel, Field

from backend.app.llm.llm_exceptions import (
    LLMConfigurationError,
)
from backend.app.llm.llm_models import (
    LLMMessage,
)


class PromptTemplate(BaseModel):
    """Versioned prompt definition for one controlled agent task."""

    name: str = Field(
        min_length=1,
        max_length=150,
    )
    version: str = Field(
        min_length=1,
        max_length=50,
    )
    description: str = Field(
        min_length=1,
        max_length=500,
    )
    system_template: str = Field(
        min_length=1,
        max_length=20000,
    )
    user_template: str = Field(
        min_length=1,
        max_length=50000,
    )
    required_variables: list[str] = Field(
        default_factory=list,
        max_length=100,
    )
    response_schema_name: str | None = Field(
        default=None,
        max_length=150,
    )
    allowed_tools: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    def render(
        self,
        variables: dict[str, Any],
    ) -> list[LLMMessage]:
        """Render the prompt after checking all required inputs."""

        missing_variables = [
            variable_name
            for variable_name in self.required_variables
            if variable_name not in variables
        ]

        if missing_variables:
            raise LLMConfigurationError(
                "Missing prompt variables: "
                + ", ".join(
                    missing_variables
                )
            )

        serialized_variables = {
            key: (
                value
                if isinstance(value, str)
                else json.dumps(
                    value,
                    ensure_ascii=False,
                    default=str,
                    sort_keys=True,
                )
            )
            for key, value in variables.items()
        }

        try:
            system_content = Template(
                self.system_template
            ).substitute(
                serialized_variables
            )
            user_content = Template(
                self.user_template
            ).substitute(
                serialized_variables
            )
        except KeyError as error:
            raise LLMConfigurationError(
                "Prompt rendering failed because "
                f"variable {error!s} was not supplied."
            ) from error

        return [
            LLMMessage(
                role="system",
                content=system_content,
            ),
            LLMMessage(
                role="user",
                content=user_content,
            ),
        ]


class PromptRegistry:
    """Store prompt templates by stable name and version."""

    def __init__(
        self,
    ) -> None:
        self._prompts: dict[
            tuple[str, str],
            PromptTemplate,
        ] = {}

    def register(
        self,
        prompt: PromptTemplate,
    ) -> None:
        key = (
            prompt.name.casefold(),
            prompt.version.casefold(),
        )

        if key in self._prompts:
            raise LLMConfigurationError(
                f"Prompt '{prompt.name}' version "
                f"'{prompt.version}' is already registered."
            )

        self._prompts[key] = prompt

    def get(
        self,
        prompt_name: str,
        prompt_version: str,
    ) -> PromptTemplate:
        key = (
            prompt_name.strip().casefold(),
            prompt_version.strip().casefold(),
        )

        if key not in self._prompts:
            raise LLMConfigurationError(
                f"Prompt '{prompt_name}' version "
                f"'{prompt_version}' is not registered."
            )

        return self._prompts[key]

    def list_prompts(
        self,
    ) -> list[dict[str, str]]:
        return [
            {
                "name": prompt.name,
                "version": prompt.version,
                "description": prompt.description,
            }
            for prompt in self._prompts.values()
        ]


COMMON_SYSTEM_TEMPLATE = """
You are a controlled AI component inside the SmartMart AI Chief of Staff.
Use only the validated context supplied by the application.
Do not invent business facts, evidence, causes, actions, people, dates,
amounts, or metrics. Preserve all exact factual values. When evidence is
missing, state that clearly. Return one JSON object only.
""".strip()


def build_default_prompt_registry(
) -> PromptRegistry:
    """Create versioned prompts for the five Chief of Staff agents."""

    registry = PromptRegistry()

    prompt_definitions = [
        (
            "monitoring_summary",
            "Summarize current business health and meaningful changes.",
            (
                "Summarize the validated monitoring context. "
                "Identify areas requiring attention and include "
                "evidence identifiers and missing-evidence warnings."
            ),
            "MonitoringSummaryV1",
        ),
        (
            "priority_explanation",
            "Explain deterministic issue priorities for managers.",
            (
                "Explain the existing deterministic priority values. "
                "Do not alter scores or rankings. Explain review order "
                "using only supplied evidence."
            ),
            "PriorityExplanationV1",
        ),
        (
            "root_cause_explanation",
            "Explain deterministic root-cause analysis safely.",
            (
                "Convert the deterministic root-cause result into a "
                "manager-friendly explanation. Reject unsupported "
                "causal claims and identify missing evidence."
            ),
            "RootCauseExplanationV1",
        ),
        (
            "recommendation_enhancement",
            "Improve deterministic recommendation clarity.",
            (
                "Improve action sequencing and clarity without "
                "automatically approving, executing, or converting "
                "the recommendation into a task."
            ),
            "RecommendationEnhancementV1",
        ),
        (
            "executive_brief_enhancement",
            "Create a concise evidence-grounded executive narrative.",
            (
                "Enhance the deterministic Executive Brief language. "
                "Preserve exact values, highlight meaningful changes, "
                "and cite internal evidence identifiers."
            ),
            "ExecutiveBriefEnhancementV1",
        ),
    ]

    for (
        prompt_name,
        description,
        task_instruction,
        response_schema_name,
    ) in prompt_definitions:
        registry.register(
            PromptTemplate(
                name=prompt_name,
                version="v1",
                description=description,
                system_template=(
                    COMMON_SYSTEM_TEMPLATE
                ),
                user_template=(
                    task_instruction
                    + "\n\nValidated context:\n"
                    + "$validated_context_json"
                ),
                required_variables=[
                    "validated_context_json",
                ],
                response_schema_name=(
                    response_schema_name
                ),
                allowed_tools=[],
            )
        )

    return registry


default_prompt_registry = (
    build_default_prompt_registry()
)
