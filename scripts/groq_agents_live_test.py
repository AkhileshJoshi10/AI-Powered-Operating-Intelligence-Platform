from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal
from pathlib import Path
import runpy
from typing import Any

from dotenv import dotenv_values
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_ENV_FILE = PROJECT_ROOT / ".env"
TEST_CONFTEXT = PROJECT_ROOT / "tests" / "conftest.py"
EXPECTED_TEST_DATABASE = "ai_operating_intelligence_test"

AGENT_SEQUENCE = [
    "Monitoring Agent",
    "Priority Agent",
    "Root-Cause Agent",
    "Recommendation Agent",
    "Executive Brief Agent",
]

EXPECTED_PROMPTS = {
    "Monitoring Agent": "monitoring_summary",
    "Priority Agent": "priority_explanation",
    "Root-Cause Agent": "root_cause_explanation",
    "Recommendation Agent": "recommendation_enhancement",
    "Executive Brief Agent": "executive_brief_enhancement",
}


AGENT_ARGUMENTS = {
    "monitoring": "Monitoring Agent",
    "priority": "Priority Agent",
    "root-cause": "Root-Cause Agent",
    "recommendation": "Recommendation Agent",
    "executive-brief": "Executive Brief Agent",
}


def parse_arguments(
) -> argparse.Namespace:
    """Read the optional one-agent live validation selector."""

    parser = argparse.ArgumentParser(
        description=(
            "Run controlled live Groq validation against the "
            "dedicated test database."
        )
    )
    parser.add_argument(
        "--agent",
        choices=[
            "all",
            *AGENT_ARGUMENTS.keys(),
        ],
        default="all",
        help=(
            "Run one agent or the final five-agent sequence. "
            "Default: all."
        ),
    )

    return parser.parse_args()


def resolve_agent_sequence(
    selected_agent: str,
) -> list[str]:
    """Resolve a CLI selector to one or all agent names."""

    if selected_agent == "all":
        return list(
            AGENT_SEQUENCE
        )

    return [
        AGENT_ARGUMENTS[
            selected_agent
        ]
    ]


def load_live_groq_key() -> str:
    """Read the real Groq key without printing or copying it elsewhere."""

    if not DEVELOPMENT_ENV_FILE.exists():
        raise RuntimeError(
            "Missing .env file containing GROQ_API_KEY."
        )

    values = dotenv_values(
        DEVELOPMENT_ENV_FILE
    )
    api_key = str(
        values.get(
            "GROQ_API_KEY",
            "",
        )
        or ""
    ).strip()

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing from .env."
        )

    return api_key


def load_verified_test_state(
) -> dict[str, Any]:
    """Load the existing pytest database safety checks first."""

    if not TEST_CONFTEXT.exists():
        raise RuntimeError(
            "tests/conftest.py was not found."
        )

    state = runpy.run_path(
        str(TEST_CONFTEXT)
    )

    actual_database_name = str(
        state.get(
            "actual_database_name",
            "",
        )
    )

    if actual_database_name != EXPECTED_TEST_DATABASE:
        raise RuntimeError(
            "Unsafe database detected. Expected "
            f"{EXPECTED_TEST_DATABASE!r}, received "
            f"{actual_database_name!r}."
        )

    return state


def money_value(
    value: object,
) -> float:
    """Convert PostgreSQL numeric values safely for validation."""

    if isinstance(value, Decimal):
        return float(value)

    if value is None:
        return 0.0

    return float(value)


async def main() -> None:
    """Run one or all real agents with Groq against only the test DB."""

    arguments = parse_arguments()
    selected_sequence = resolve_agent_sequence(
        arguments.agent
    )

    live_api_key = load_live_groq_key()
    test_state = load_verified_test_state()

    # Import application modules only after tests/conftest.py has loaded
    # and verified the dedicated _test database environment.
    from backend.app.agents import (
        AgentContext,
        AgentExecutionStatus,
        AgentOrchestrator,
        ExecutiveBriefAgent,
        MonitoringAgent,
        PostgresAgentRunLogger,
        PriorityAgent,
        RecommendationAgent,
        RootCauseAgent,
    )
    from backend.app.llm import (
        GroqProvider,
        LLMProviderConfig,
    )

    test_engine = test_state[
        "engine"
    ]

    provider_config = LLMProviderConfig(
        enabled=True,
        provider_name="groq",
        model_name="openai/gpt-oss-20b",
        timeout_seconds=45.0,
        max_retries=2,
        retry_backoff_seconds=1.0,
        max_input_tokens=16000,
        max_output_tokens=2000,
        max_estimated_cost_usd=0.02,
        temperature=0.0,
        mask_sensitive_data=True,
        allowed_tools=[],
    )

    provider = GroqProvider(
        provider_config,
        api_key=live_api_key,
    )

    orchestrator = AgentOrchestrator(
        agents=[
            MonitoringAgent(
                llm_provider=provider
            ),
            PriorityAgent(
                llm_provider=provider
            ),
            RootCauseAgent(
                llm_provider=provider
            ),
            RecommendationAgent(
                llm_provider=provider
            ),
            ExecutiveBriefAgent(
                llm_provider=provider
            ),
        ],
        run_logger=PostgresAgentRunLogger(
            test_engine
        ),
    )

    context = AgentContext(
        run_type=(
            "day36-live-groq-five-agent-test"
            if arguments.agent == "all"
            else (
                "day36-live-groq-"
                + arguments.agent
                + "-test"
            )
        ),
        requested_by="manual-day36",
        input_data={
            "finding_limit": 3,
            "manager_limit": 2,
            "executive_limit": 2,
            "analysis_limit": 2,
            "recommendation_limit": 2,
        },
    )

    print(
        "Database:",
        EXPECTED_TEST_DATABASE,
    )
    print(
        "Provider:",
        provider.provider_name,
    )
    print(
        "Model:",
        provider_config.model_name,
    )
    print(
        "Running live validation:",
        ", ".join(
            selected_sequence
        ),
    )
    print(
        "Rate-limit retries will honor Groq retry-after headers."
    )

    results = await orchestrator.run_sequence(
        agent_names=selected_sequence,
        context=context,
        stop_on_failure=True,
    )

    failures: list[str] = []
    total_tokens = 0
    total_estimated_cost = 0.0

    if len(results) != len(selected_sequence):
        failures.append(
            "The selected live sequence stopped before all "
            "requested agents ran."
        )

    for result in results:
        enhancement = result.output_data.get(
            "llm_enhancement",
            {},
        )
        enhancement_status = (
            enhancement.get(
                "status"
            )
            if isinstance(
                enhancement,
                dict,
            )
            else None
        )

        print()
        print(
            f"[{result.agent_name}]"
        )
        print(
            "  Execution:",
            result.execution_status.value,
        )
        print(
            "  Enhancement:",
            enhancement_status,
        )
        print(
            "  Fallback:",
            result.used_fallback,
        )
        print(
            "  Provider:",
            result.model_provider,
        )
        print(
            "  Model:",
            result.model_name,
        )
        print(
            "  Prompt:",
            result.prompt_name,
            result.prompt_version,
        )
        print(
            "  Tokens:",
            result.total_tokens,
        )
        print(
            "  Estimated list-price USD:",
            result.estimated_cost_usd,
        )
        print(
            "  LLM latency ms:",
            result.llm_latency_ms,
        )
        print(
            "  Logged:",
            result.log_persisted,
            "ID:",
            result.agent_run_id,
        )

        if result.error_message:
            print(
                "  Error:",
                result.error_message,
            )

        if (
            result.execution_status
            != AgentExecutionStatus.SUCCESS
        ):
            failures.append(
                f"{result.agent_name} did not complete successfully."
            )

        if result.used_fallback:
            failures.append(
                f"{result.agent_name} used deterministic fallback."
            )

        if enhancement_status != "Complete":
            failures.append(
                f"{result.agent_name} did not return a Complete "
                "LLM enhancement."
            )

        if result.model_provider != "groq":
            failures.append(
                f"{result.agent_name} did not record Groq provider metadata."
            )

        if result.model_name != provider_config.model_name:
            failures.append(
                f"{result.agent_name} recorded an unexpected model."
            )

        if result.prompt_name != EXPECTED_PROMPTS.get(
            result.agent_name
        ):
            failures.append(
                f"{result.agent_name} recorded an unexpected prompt."
            )

        if (
            result.input_tokens is None
            or result.output_tokens is None
            or result.total_tokens is None
        ):
            failures.append(
                f"{result.agent_name} did not record token usage."
            )
        else:
            if result.total_tokens != (
                result.input_tokens
                + result.output_tokens
            ):
                failures.append(
                    f"{result.agent_name} token totals are inconsistent."
                )

            total_tokens += result.total_tokens

        if result.estimated_cost_usd is not None:
            total_estimated_cost += (
                result.estimated_cost_usd
            )

        if (
            not result.log_persisted
            or result.agent_run_id is None
        ):
            failures.append(
                f"{result.agent_name} was not persisted to agent_runs."
            )
            continue

        with test_engine.connect() as connection:
            stored = connection.execute(
                text(
                    """
                    SELECT
                        agent_name,
                        model_provider,
                        model_name,
                        prompt_name,
                        prompt_version,
                        input_tokens,
                        output_tokens,
                        total_tokens,
                        estimated_cost_usd,
                        llm_latency_ms,
                        used_fallback,
                        llm_error_type
                    FROM agent_runs
                    WHERE agent_run_id = :agent_run_id;
                    """
                ),
                {
                    "agent_run_id": result.agent_run_id,
                },
            ).mappings().one()

        if stored["agent_name"] != result.agent_name:
            failures.append(
                f"agent_runs name mismatch for {result.agent_name}."
            )

        if stored["model_provider"] != "groq":
            failures.append(
                f"agent_runs provider mismatch for {result.agent_name}."
            )

        if stored["model_name"] != provider_config.model_name:
            failures.append(
                f"agent_runs model mismatch for {result.agent_name}."
            )

        if stored["prompt_name"] != result.prompt_name:
            failures.append(
                f"agent_runs prompt mismatch for {result.agent_name}."
            )

        if stored["total_tokens"] != result.total_tokens:
            failures.append(
                f"agent_runs token mismatch for {result.agent_name}."
            )

        if bool(stored["used_fallback"]):
            failures.append(
                f"agent_runs shows fallback for {result.agent_name}."
            )

        if stored["llm_error_type"] is not None:
            failures.append(
                f"agent_runs contains an LLM error for {result.agent_name}."
            )

        if money_value(
            stored["estimated_cost_usd"]
        ) < 0:
            failures.append(
                f"agent_runs contains an invalid cost for {result.agent_name}."
            )

    print()
    print(
        "Total tokens:",
        total_tokens,
    )
    print(
        "Total estimated list-price USD:",
        round(
            total_estimated_cost,
            8,
        ),
    )

    if failures:
        print()
        print(
            "DAY 36 LIVE VALIDATION FAILED"
        )

        for failure in failures:
            print(
                " -",
                failure,
            )

        raise RuntimeError(
            "Day 36 live Groq five-agent validation failed."
        )

    print()
    if arguments.agent == "all":
        print(
            "DAY 36 LIVE FIVE-AGENT VALIDATION PASSED"
        )
    else:
        print(
            "DAY 36 LIVE AGENT VALIDATION PASSED:",
            selected_sequence[0],
        )


if __name__ == "__main__":
    asyncio.run(
        main()
    )
