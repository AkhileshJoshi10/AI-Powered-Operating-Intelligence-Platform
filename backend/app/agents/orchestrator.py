from __future__ import annotations

from collections.abc import Iterable

from backend.app.agents.agent_context import AgentContext
from backend.app.agents.agent_result import (
    AgentExecutionStatus,
    AgentResult,
)
from backend.app.agents.agent_run_logger import (
    AgentRunLogger,
)
from backend.app.agents.base_agent import BaseAgent


class AgentOrchestrator:
    """
    Register and coordinate AI Chief of Staff agents.

    The orchestrator does not depend on an LLM provider. A database
    logger can be supplied when persistent run tracking is required.
    """

    def __init__(
        self,
        agents: Iterable[BaseAgent] | None = None,
        *,
        run_logger: AgentRunLogger | None = None,
    ) -> None:
        """Initialize the agent registry and optional run logger."""

        self._agents: dict[str, BaseAgent] = {}
        self._run_logger = run_logger

        if agents is not None:
            for agent in agents:
                self.register_agent(
                    agent
                )

    def register_agent(
        self,
        agent: BaseAgent,
    ) -> None:
        """Register one agent by its unique name."""

        normalized_name = (
            agent.name.casefold()
        )

        if normalized_name in self._agents:
            raise ValueError(
                f"An agent named '{agent.name}' "
                "is already registered."
            )

        self._agents[
            normalized_name
        ] = agent

    def get_agent(
        self,
        agent_name: str,
    ) -> BaseAgent:
        """Return a registered agent."""

        normalized_name = (
            agent_name.strip().casefold()
        )

        if normalized_name not in self._agents:
            raise KeyError(
                f"Agent '{agent_name}' is not registered."
            )

        return self._agents[
            normalized_name
        ]

    def list_agents(
        self,
    ) -> list[dict[str, str]]:
        """Return registered agent names and descriptions."""

        return [
            {
                "name": agent.name,
                "description": agent.description,
            }
            for agent in self._agents.values()
        ]

    def persist_result(
        self,
        *,
        context: AgentContext,
        result: AgentResult,
    ) -> AgentResult:
        """
        Persist an agent result when a logger has been configured.

        Logging failures are returned as operational metadata and do
        not replace or hide the actual agent execution result.
        """

        if self._run_logger is None:
            return result

        try:
            agent_run_id = self._run_logger.save_result(
                context=context,
                result=result,
            )

        except Exception as error:
            logging_error = " ".join(
                str(error).split()
            )

            if not logging_error:
                logging_error = type(
                    error
                ).__name__

            return result.model_copy(
                update={
                    "agent_run_id": None,
                    "log_persisted": False,
                    "logging_error": (
                        logging_error[:1000]
                    ),
                }
            )

        return result.model_copy(
            update={
                "agent_run_id": agent_run_id,
                "log_persisted": True,
                "logging_error": None,
            }
        )

    async def run_agent(
        self,
        agent_name: str,
        context: AgentContext,
    ) -> AgentResult:
        """Execute and optionally persist one registered agent."""

        agent = self.get_agent(
            agent_name
        )

        result = await agent.execute(
            context
        )

        return self.persist_result(
            context=context,
            result=result,
        )

    async def run_sequence(
        self,
        *,
        agent_names: list[str],
        context: AgentContext,
        stop_on_failure: bool = True,
    ) -> list[AgentResult]:
        """
        Execute agents sequentially.

        Each completed result is made available to later agents through
        context.metadata["previous_agent_results"].
        """

        results: list[AgentResult] = []

        working_context = context.model_copy(
            deep=True
        )

        previous_agent_results = (
            working_context.metadata.setdefault(
                "previous_agent_results",
                {},
            )
        )

        for agent_name in agent_names:
            result = await self.run_agent(
                agent_name,
                working_context,
            )

            results.append(
                result
            )

            previous_agent_results[
                result.agent_name
            ] = result.model_dump(
                mode="json"
            )

            if (
                stop_on_failure
                and result.execution_status
                == AgentExecutionStatus.FAILED
            ):
                break

        return results