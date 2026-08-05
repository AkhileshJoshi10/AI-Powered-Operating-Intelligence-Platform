from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from backend.app.agents.agent_context import AgentContext
from backend.app.agents.agent_result import (
    AgentExecutionMetadata,
    AgentExecutionStatus,
    AgentResult,
)
from backend.app.llm.llm_exceptions import LLMError


EXECUTION_METADATA_KEY = "_execution_metadata"


def current_utc_time() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(
        timezone.utc
    )


def calculate_duration_ms(
    timer_started_at: float,
) -> float:
    """Return elapsed execution time in milliseconds."""

    return round(
        (
            perf_counter()
            - timer_started_at
        )
        * 1000,
        2,
    )


def normalize_error_message(
    error: Exception,
) -> str:
    """Normalize an exception message for structured output."""

    message = " ".join(
        str(error).split()
    )

    return message or type(error).__name__


def build_llm_error_metadata(
    error: Exception,
) -> dict[str, str | None]:
    """Capture LLM-specific error details without changing failures."""

    if not isinstance(
        error,
        LLMError,
    ):
        return {
            "llm_error_type": None,
            "llm_error_message": None,
        }

    return {
        "llm_error_type": type(
            error
        ).__name__,
        "llm_error_message": (
            normalize_error_message(
                error
            )[:4000]
        ),
    }


class BaseAgent(ABC):
    """
    Common interface for all AI Chief of Staff agents.

    Individual agents inherit from this class and implement their
    deterministic, LLM-supported, or tool-supported run method.
    """

    name: str = ""
    description: str = ""
    version: str = "1.0.0"

    def __init__(self) -> None:
        """Validate the agent definition."""

        cleaned_name = " ".join(
            self.name.split()
        )

        if not cleaned_name:
            raise ValueError(
                "Every agent must define a non-empty name."
            )

        cleaned_version = " ".join(
            self.version.split()
        )

        if not cleaned_version:
            raise ValueError(
                "Every agent must define a non-empty version."
            )

        self.name = cleaned_name
        self.version = cleaned_version
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

        LLM-supported agents may include a reserved
        ``_execution_metadata`` dictionary in their return value.
        BaseAgent removes that dictionary from business output and
        stores it in AgentResult for execution logging.
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

    def extract_execution_metadata(
        self,
        output_data: dict[str, Any],
    ) -> tuple[
        dict[str, Any],
        AgentExecutionMetadata,
    ]:
        """
        Separate optional execution metadata from business output.

        The input dictionary is copied so an agent's original return
        object is never mutated.
        """

        cleaned_output = dict(
            output_data
        )

        raw_metadata = cleaned_output.pop(
            EXECUTION_METADATA_KEY,
            {},
        )

        if raw_metadata is None:
            raw_metadata = {}

        if isinstance(
            raw_metadata,
            AgentExecutionMetadata,
        ):
            metadata = raw_metadata

        elif isinstance(
            raw_metadata,
            dict,
        ):
            metadata = AgentExecutionMetadata(
                **raw_metadata
            )

        else:
            raise TypeError(
                "_execution_metadata must be a dictionary "
                "or AgentExecutionMetadata."
            )

        return (
            cleaned_output,
            metadata,
        )

    def build_result(
        self,
        *,
        context: AgentContext,
        execution_status: AgentExecutionStatus,
        summary: str,
        output_data: dict[str, Any],
        used_fallback: bool,
        error_type: str | None,
        error_message: str | None,
        started_at: datetime,
        completed_at: datetime,
        duration_ms: float,
        execution_metadata: (
            AgentExecutionMetadata | None
        ) = None,
        llm_error: Exception | None = None,
    ) -> AgentResult:
        """Build one synchronized AgentResult."""

        metadata = (
            execution_metadata
            or AgentExecutionMetadata()
        )

        llm_error_metadata = (
            build_llm_error_metadata(
                llm_error
            )
            if llm_error is not None
            else {
                "llm_error_type": (
                    metadata.llm_error_type
                ),
                "llm_error_message": (
                    metadata.llm_error_message
                ),
            }
        )

        return AgentResult(
            run_id=context.run_id,
            agent_name=self.name,
            agent_version=self.version,
            run_type=context.run_type,
            execution_status=execution_status,
            summary=summary,
            output_data=output_data,
            used_fallback=used_fallback,
            error_type=error_type,
            error_message=error_message,
            model_provider=(
                metadata.model_provider
            ),
            model_name=metadata.model_name,
            prompt_name=metadata.prompt_name,
            prompt_version=(
                metadata.prompt_version
            ),
            input_tokens=metadata.input_tokens,
            output_tokens=(
                metadata.output_tokens
            ),
            total_tokens=metadata.total_tokens,
            estimated_cost_usd=(
                metadata.estimated_cost_usd
            ),
            llm_latency_ms=(
                metadata.llm_latency_ms
            ),
            tool_calls=metadata.tool_calls,
            run_metadata=(
                metadata.run_metadata
            ),
            llm_error_type=(
                llm_error_metadata[
                    "llm_error_type"
                ]
            ),
            llm_error_message=(
                llm_error_metadata[
                    "llm_error_message"
                ]
            ),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
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
            raw_output_data = await self.run(
                context
            )

            if not isinstance(
                raw_output_data,
                dict,
            ):
                raise TypeError(
                    "Agent run output must be a dictionary."
                )

            (
                output_data,
                execution_metadata,
            ) = self.extract_execution_metadata(
                raw_output_data
            )

            completed_at = current_utc_time()

            return self.build_result(
                context=context,
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
                duration_ms=calculate_duration_ms(
                    timer_started_at
                ),
                execution_metadata=(
                    execution_metadata
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

                return self.build_result(
                    context=context,
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
                        f"{normalize_error_message(primary_error)}. "
                        "Fallback error: "
                        f"{normalize_error_message(fallback_error)}."
                    ),
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=calculate_duration_ms(
                        timer_started_at
                    ),
                    llm_error=(
                        primary_error
                        if isinstance(
                            primary_error,
                            LLMError,
                        )
                        else fallback_error
                    ),
                )

            if fallback_output is not None:
                if not isinstance(
                    fallback_output,
                    dict,
                ):
                    completed_at = current_utc_time()

                    return self.build_result(
                        context=context,
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
                        duration_ms=(
                            calculate_duration_ms(
                                timer_started_at
                            )
                        ),
                        llm_error=primary_error,
                    )

                try:
                    (
                        cleaned_fallback_output,
                        fallback_metadata,
                    ) = self.extract_execution_metadata(
                        fallback_output
                    )

                except Exception as metadata_error:
                    completed_at = current_utc_time()

                    return self.build_result(
                        context=context,
                        execution_status=(
                            AgentExecutionStatus.FAILED
                        ),
                        summary=(
                            f"{self.name} returned invalid "
                            "fallback execution metadata."
                        ),
                        output_data={},
                        used_fallback=False,
                        error_type=type(
                            metadata_error
                        ).__name__,
                        error_message=(
                            normalize_error_message(
                                metadata_error
                            )
                        ),
                        started_at=started_at,
                        completed_at=completed_at,
                        duration_ms=(
                            calculate_duration_ms(
                                timer_started_at
                            )
                        ),
                        llm_error=primary_error,
                    )

                completed_at = current_utc_time()

                return self.build_result(
                    context=context,
                    execution_status=(
                        AgentExecutionStatus.SUCCESS
                    ),
                    summary=self.build_summary(
                        cleaned_fallback_output
                    ),
                    output_data=(
                        cleaned_fallback_output
                    ),
                    used_fallback=True,
                    error_type=type(
                        primary_error
                    ).__name__,
                    error_message=(
                        normalize_error_message(
                            primary_error
                        )
                    ),
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=calculate_duration_ms(
                        timer_started_at
                    ),
                    execution_metadata=(
                        fallback_metadata
                    ),
                    llm_error=primary_error,
                )

            completed_at = current_utc_time()

            return self.build_result(
                context=context,
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
                error_message=(
                    normalize_error_message(
                        primary_error
                    )
                ),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=calculate_duration_ms(
                    timer_started_at
                ),
                llm_error=primary_error,
            )