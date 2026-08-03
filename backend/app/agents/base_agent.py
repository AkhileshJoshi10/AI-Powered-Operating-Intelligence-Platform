from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from backend.app.agents.agent_context import AgentContext
from backend.app.agents.agent_result import (
    AgentExecutionStatus,
    AgentResult,
)


def current_utc_time() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(timezone.utc)


class BaseAgent(ABC):
    """
    Common interface for all AI Chief of Staff agents.

    Individual agents will inherit from this class and implement
    their own run method.
    """

    name: str = ""
    description: str = ""

    def __init__(self) -> None:
        """Validate the agent definition."""

        cleaned_name = " ".join(
            self.name.split()
        )

        if not cleaned_name:
            raise ValueError(
                "Every agent must define a non-empty name."
            )

        self.name = cleaned_name
        self.description = " ".join(
            self.description.split()
        )

    @abstractmethod
    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        """
        Execute the main agent logic.

        This method may later call deterministic services, an LLM
        provider, tools, or a combination of these components.
        """

        raise NotImplementedError

    async def fallback(
        self,
        context: AgentContext,
        error: Exception,
    ) -> dict[str, Any] | None:
        """
        Run deterministic fallback logic after primary execution fails.

        Agents without fallback behavior return None.
        """

        del context
        del error

        return None

    def build_summary(
        self,
        output_data: dict[str, Any],
    ) -> str:
        """
        Build a compact summary from an agent output.

        Individual agents may override this method.
        """

        explicit_summary = output_data.get(
            "summary"
        )

        if explicit_summary is not None:
            cleaned_summary = " ".join(
                str(explicit_summary).split()
            )

            if cleaned_summary:
                return cleaned_summary

        return (
            f"{self.name} completed successfully."
        )

    async def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:
        """
        Execute the agent with timing, failure handling, and fallback.

        This method always returns a structured AgentResult instead
        of exposing an unhandled agent exception to the orchestrator.
        """

        started_at = current_utc_time()
        timer_started_at = perf_counter()

        try:
            output_data = await self.run(
                context
            )

            if not isinstance(
                output_data,
                dict,
            ):
                raise TypeError(
                    "Agent run output must be a dictionary."
                )

            completed_at = current_utc_time()

            return AgentResult(
                run_id=context.run_id,
                agent_name=self.name,
                run_type=context.run_type,
                execution_status=(
                    AgentExecutionStatus.SUCCESS
                ),
                summary=self.build_summary(
                    output_data
                ),
                output_data=output_data,
                used_fallback=False,
                error_type=None,
                error_message=None,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=round(
                    (
                        perf_counter()
                        - timer_started_at
                    )
                    * 1000,
                    2,
                ),
            )

        except Exception as primary_error:
            try:
                fallback_output = await self.fallback(
                    context,
                    primary_error,
                )

            except Exception as fallback_error:
                completed_at = current_utc_time()

                return AgentResult(
                    run_id=context.run_id,
                    agent_name=self.name,
                    run_type=context.run_type,
                    execution_status=(
                        AgentExecutionStatus.FAILED
                    ),
                    summary=(
                        f"{self.name} failed, and its "
                        "fallback also failed."
                    ),
                    output_data={},
                    used_fallback=False,
                    error_type=type(
                        fallback_error
                    ).__name__,
                    error_message=(
                        "Primary error: "
                        f"{primary_error}. "
                        "Fallback error: "
                        f"{fallback_error}."
                    ),
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=round(
                        (
                            perf_counter()
                            - timer_started_at
                        )
                        * 1000,
                        2,
                    ),
                )

            if fallback_output is not None:
                if not isinstance(
                    fallback_output,
                    dict,
                ):
                    completed_at = current_utc_time()

                    return AgentResult(
                        run_id=context.run_id,
                        agent_name=self.name,
                        run_type=context.run_type,
                        execution_status=(
                            AgentExecutionStatus.FAILED
                        ),
                        summary=(
                            f"{self.name} returned an "
                            "invalid fallback result."
                        ),
                        output_data={},
                        used_fallback=False,
                        error_type="TypeError",
                        error_message=(
                            "Agent fallback output must "
                            "be a dictionary."
                        ),
                        started_at=started_at,
                        completed_at=completed_at,
                        duration_ms=round(
                            (
                                perf_counter()
                                - timer_started_at
                            )
                            * 1000,
                            2,
                        ),
                    )

                completed_at = current_utc_time()

                return AgentResult(
                    run_id=context.run_id,
                    agent_name=self.name,
                    run_type=context.run_type,
                    execution_status=(
                        AgentExecutionStatus.SUCCESS
                    ),
                    summary=self.build_summary(
                        fallback_output
                    ),
                    output_data=fallback_output,
                    used_fallback=True,
                    error_type=type(
                        primary_error
                    ).__name__,
                    error_message=str(
                        primary_error
                    ),
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=round(
                        (
                            perf_counter()
                            - timer_started_at
                        )
                        * 1000,
                        2,
                    ),
                )

            completed_at = current_utc_time()

            return AgentResult(
                run_id=context.run_id,
                agent_name=self.name,
                run_type=context.run_type,
                execution_status=(
                    AgentExecutionStatus.FAILED
                ),
                summary=(
                    f"{self.name} failed during execution."
                ),
                output_data={},
                used_fallback=False,
                error_type=type(
                    primary_error
                ).__name__,
                error_message=str(
                    primary_error
                ),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=round(
                    (
                        perf_counter()
                        - timer_started_at
                    )
                    * 1000,
                    2,
                ),
            )