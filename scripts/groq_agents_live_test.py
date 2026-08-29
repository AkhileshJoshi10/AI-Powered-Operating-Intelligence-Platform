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
    parser.add_argument(
        "--require-rag",
        action="store_true",
        help=(
            "Require supported Day 34 agents to retrieve real "
            "PostgreSQL knowledge and return at least one allowed "
            "DOC-* knowledge citation. Supported single-agent modes: "
            "root-cause and recommendation."
        ),
    )

    arguments = parser.parse_args()

    if (
        arguments.require_rag
        and arguments.agent
        not in {
            "root-cause",
            "recommendation",
            "executive-brief",
            "all",
        }
    ):
        parser.error(
            "--require-rag can be used only with "
            "--agent root-cause, --agent recommendation, "
            "--agent executive-brief, or --agent all."
        )

    return arguments


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


def normalized_string_list(
    value: object,
) -> list[str]:
    """Return normalized unique strings from one list value."""

    if not isinstance(
        value,
        list,
    ):
        return []

    values: list[str] = []

    for item in value:
        normalized = " ".join(
            str(
                item
            ).split()
        )

        if (
            normalized
            and normalized not in values
        ):
            values.append(
                normalized
            )

    return values


def collect_nested_reference_ids(
    items: object,
    field_name: str,
) -> list[str]:
    """Collect one controlled reference field from nested dictionaries."""

    if not isinstance(
        items,
        list,
    ):
        return []

    values: list[str] = []

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        for value in normalized_string_list(
            item.get(
                field_name
            )
        ):
            if value not in values:
                values.append(
                    value
                )

    return values


def validate_root_cause_rag_output(
    *,
    enhancement: dict[str, Any],
    run_metadata: dict[str, Any] | None = None,
) -> list[str]:
    """Validate live Root-Cause RAG retrieval and citation separation."""

    failures: list[str] = []

    knowledge_retrieval = enhancement.get(
        "knowledge_retrieval",
        {},
    )

    if (
        not isinstance(
            knowledge_retrieval,
            dict,
        )
        or not knowledge_retrieval
    ):
        metadata = (
            run_metadata
            if isinstance(
                run_metadata,
                dict,
            )
            else {}
        )
        knowledge_retrieval = metadata.get(
            "knowledge_retrieval",
            {},
        )

    if not isinstance(
        knowledge_retrieval,
        dict,
    ):
        return [
            "Root-Cause Agent did not return knowledge retrieval metadata."
        ]

    retrieval_status = str(
        knowledge_retrieval.get(
            "status",
            "",
        )
    )

    try:
        included_count = int(
            knowledge_retrieval.get(
                "included_result_count",
                0,
            )
            or 0
        )
    except (TypeError, ValueError):
        included_count = 0

    retrieved_citations = (
        normalized_string_list(
            knowledge_retrieval.get(
                "citations"
            )
        )
    )

    top_level_knowledge_citations = (
        normalized_string_list(
            enhancement.get(
                "knowledge_citation_ids"
            )
        )
    )

    explanations = enhancement.get(
        "root_cause_explanations",
        [],
    )

    nested_knowledge_citations = (
        collect_nested_reference_ids(
            explanations,
            "knowledge_citation_ids",
        )
    )

    business_evidence_ids = (
        normalized_string_list(
            enhancement.get(
                "evidence_ids"
            )
        )
    )
    business_evidence_ids.extend(
        reference_id
        for reference_id in (
            collect_nested_reference_ids(
                explanations,
                "evidence_ids",
            )
        )
        if reference_id not in business_evidence_ids
    )

    returned_knowledge_citations = list(
        top_level_knowledge_citations
    )

    for citation_id in nested_knowledge_citations:
        if (
            citation_id
            not in returned_knowledge_citations
        ):
            returned_knowledge_citations.append(
                citation_id
            )

    if retrieval_status != "success":
        failures.append(
            "Root-Cause RAG retrieval status was not success."
        )

    if included_count < 1:
        failures.append(
            "Root-Cause RAG did not include any PostgreSQL "
            "knowledge chunks."
        )

    if not retrieved_citations:
        failures.append(
            "Root-Cause RAG did not expose any retrieved DOC-* citations."
        )

    invalid_retrieved = [
        citation_id
        for citation_id in retrieved_citations
        if not citation_id.startswith(
            "DOC-"
        )
    ]

    if invalid_retrieved:
        failures.append(
            "Root-Cause retrieval returned non-DOC knowledge "
            "citations: "
            + ", ".join(
                invalid_retrieved
            )
        )

    if not returned_knowledge_citations:
        failures.append(
            "Root-Cause Groq enhancement did not cite any "
            "retrieved knowledge."
        )

    unsupported_knowledge_citations = sorted(
        set(
            returned_knowledge_citations
        ).difference(
            retrieved_citations
        )
    )

    if unsupported_knowledge_citations:
        failures.append(
            "Root-Cause Groq enhancement returned knowledge "
            "citations that were not retrieved: "
            + ", ".join(
                unsupported_knowledge_citations
            )
        )

    invalid_returned_knowledge = [
        citation_id
        for citation_id in returned_knowledge_citations
        if not citation_id.startswith(
            "DOC-"
        )
    ]

    if invalid_returned_knowledge:
        failures.append(
            "Root-Cause knowledge_citation_ids contains "
            "non-DOC identifiers: "
            + ", ".join(
                invalid_returned_knowledge
            )
        )

    doc_ids_in_business_evidence = [
        evidence_id
        for evidence_id in business_evidence_ids
        if evidence_id.startswith(
            "DOC-"
        )
    ]

    if doc_ids_in_business_evidence:
        failures.append(
            "Root-Cause evidence_ids incorrectly contains "
            "knowledge DOC-* citations: "
            + ", ".join(
                doc_ids_in_business_evidence
            )
        )

    missing_top_level_knowledge = sorted(
        set(
            nested_knowledge_citations
        ).difference(
            top_level_knowledge_citations
        )
    )

    if missing_top_level_knowledge:
        failures.append(
            "Nested Root-Cause knowledge citations were missing "
            "from top-level knowledge_citation_ids: "
            + ", ".join(
                missing_top_level_knowledge
            )
        )

    return failures


def validate_recommendation_rag_output(
    *,
    enhancement: dict[str, Any],
    run_metadata: dict[str, Any] | None = None,
) -> list[str]:
    """Validate live Recommendation RAG retrieval and citations."""

    failures: list[str] = []

    knowledge_retrieval = enhancement.get(
        "knowledge_retrieval",
        {},
    )

    if (
        not isinstance(
            knowledge_retrieval,
            dict,
        )
        or not knowledge_retrieval
    ):
        metadata = (
            run_metadata
            if isinstance(
                run_metadata,
                dict,
            )
            else {}
        )
        knowledge_retrieval = metadata.get(
            "knowledge_retrieval",
            {},
        )

    if not isinstance(
        knowledge_retrieval,
        dict,
    ):
        return [
            (
                "Recommendation Agent did not return "
                "knowledge retrieval metadata."
            )
        ]

    retrieval_status = str(
        knowledge_retrieval.get(
            "status",
            "",
        )
    )

    try:
        included_count = int(
            knowledge_retrieval.get(
                "included_result_count",
                0,
            )
            or 0
        )
    except (TypeError, ValueError):
        included_count = 0

    retrieved_citations = (
        normalized_string_list(
            knowledge_retrieval.get(
                "citations"
            )
        )
    )

    top_level_knowledge_citations = (
        normalized_string_list(
            enhancement.get(
                "knowledge_citation_ids"
            )
        )
    )

    recommendation_items = enhancement.get(
        "recommendation_enhancements",
        [],
    )

    nested_knowledge_citations = (
        collect_nested_reference_ids(
            recommendation_items,
            "knowledge_citation_ids",
        )
    )

    returned_knowledge_citations = list(
        top_level_knowledge_citations
    )

    for citation_id in nested_knowledge_citations:
        if (
            citation_id
            not in returned_knowledge_citations
        ):
            returned_knowledge_citations.append(
                citation_id
            )

    if retrieval_status != "success":
        failures.append(
            "Recommendation RAG retrieval status was not success."
        )

    if included_count < 1:
        failures.append(
            "Recommendation RAG did not include any PostgreSQL "
            "knowledge chunks."
        )

    if not retrieved_citations:
        failures.append(
            "Recommendation RAG did not expose any retrieved "
            "DOC-* citations."
        )

    invalid_retrieved = [
        citation_id
        for citation_id in retrieved_citations
        if not citation_id.startswith(
            "DOC-"
        )
    ]

    if invalid_retrieved:
        failures.append(
            "Recommendation retrieval returned non-DOC knowledge "
            "citations: "
            + ", ".join(
                invalid_retrieved
            )
        )

    if not returned_knowledge_citations:
        failures.append(
            "Recommendation Groq enhancement did not cite any "
            "retrieved knowledge."
        )

    unsupported_knowledge_citations = sorted(
        set(
            returned_knowledge_citations
        ).difference(
            retrieved_citations
        )
    )

    if unsupported_knowledge_citations:
        failures.append(
            "Recommendation Groq enhancement returned knowledge "
            "citations that were not retrieved: "
            + ", ".join(
                unsupported_knowledge_citations
            )
        )

    invalid_returned_knowledge = [
        citation_id
        for citation_id in returned_knowledge_citations
        if not citation_id.startswith(
            "DOC-"
        )
    ]

    if invalid_returned_knowledge:
        failures.append(
            "Recommendation knowledge_citation_ids contains "
            "non-DOC identifiers: "
            + ", ".join(
                invalid_returned_knowledge
            )
        )

    missing_top_level_knowledge = sorted(
        set(
            nested_knowledge_citations
        ).difference(
            top_level_knowledge_citations
        )
    )

    if missing_top_level_knowledge:
        failures.append(
            "Nested Recommendation knowledge citations were missing "
            "from top-level knowledge_citation_ids: "
            + ", ".join(
                missing_top_level_knowledge
            )
        )

    if enhancement.get(
        "human_review_required"
    ) is not True:
        failures.append(
            "Recommendation RAG removed the human-review requirement."
        )

    if enhancement.get(
        "recommendations_approved"
    ) is not False:
        failures.append(
            "Recommendation RAG incorrectly approved recommendations."
        )

    if enhancement.get(
        "tasks_created"
    ) is not False:
        failures.append(
            "Recommendation RAG incorrectly created tasks."
        )

    return failures


def validate_executive_brief_rag_output(
    *,
    enhancement: dict[str, Any],
    run_metadata: dict[str, Any] | None = None,
) -> list[str]:
    """Validate live Executive Brief RAG retrieval and controls."""

    failures: list[str] = []
    enhancement_complete = (
        enhancement.get(
            "status"
        )
        == "Complete"
    )

    knowledge_retrieval = enhancement.get(
        "knowledge_retrieval",
        {},
    )

    if (
        not isinstance(
            knowledge_retrieval,
            dict,
        )
        or not knowledge_retrieval
    ):
        metadata = (
            run_metadata
            if isinstance(
                run_metadata,
                dict,
            )
            else {}
        )
        knowledge_retrieval = metadata.get(
            "knowledge_retrieval",
            {},
        )

    if not isinstance(
        knowledge_retrieval,
        dict,
    ):
        return [
            (
                "Executive Brief Agent did not return "
                "knowledge retrieval metadata."
            )
        ]

    retrieval_status = str(
        knowledge_retrieval.get(
            "status",
            "",
        )
    )

    try:
        included_count = int(
            knowledge_retrieval.get(
                "included_result_count",
                0,
            )
            or 0
        )
    except (TypeError, ValueError):
        included_count = 0

    retrieved_citations = (
        normalized_string_list(
            knowledge_retrieval.get(
                "citations"
            )
        )
    )

    top_level_knowledge_citations = (
        normalized_string_list(
            enhancement.get(
                "knowledge_citation_ids"
            )
        )
    )

    attention_items = enhancement.get(
        "management_attention",
        [],
    )

    nested_knowledge_citations = (
        collect_nested_reference_ids(
            attention_items,
            "knowledge_citation_ids",
        )
    )

    returned_knowledge_citations = list(
        top_level_knowledge_citations
    )

    for citation_id in nested_knowledge_citations:
        if (
            citation_id
            not in returned_knowledge_citations
        ):
            returned_knowledge_citations.append(
                citation_id
            )

    evidence_ids = normalized_string_list(
        enhancement.get(
            "evidence_ids"
        )
    )

    evidence_ids.extend(
        reference_id
        for reference_id in (
            collect_nested_reference_ids(
                attention_items,
                "evidence_ids",
            )
        )
        if reference_id not in evidence_ids
    )

    if retrieval_status != "success":
        failures.append(
            "Executive Brief RAG retrieval status was not success."
        )

    if included_count < 1:
        failures.append(
            "Executive Brief RAG did not include any PostgreSQL "
            "knowledge chunks."
        )

    if not retrieved_citations:
        failures.append(
            "Executive Brief RAG did not expose any retrieved "
            "DOC-* citations."
        )

    invalid_retrieved = [
        citation_id
        for citation_id in retrieved_citations
        if not citation_id.startswith(
            "DOC-"
        )
    ]

    if invalid_retrieved:
        failures.append(
            "Executive Brief retrieval returned non-DOC knowledge "
            "citations: "
            + ", ".join(
                invalid_retrieved
            )
        )

    # A provider/request failure has no completed LLM output to inspect.
    # The caller separately records fallback and provider errors.
    if not enhancement_complete:
        return failures

    if not returned_knowledge_citations:
        failures.append(
            "Executive Brief Groq enhancement did not cite any "
            "retrieved knowledge."
        )

    unsupported_knowledge_citations = sorted(
        set(
            returned_knowledge_citations
        ).difference(
            retrieved_citations
        )
    )

    if unsupported_knowledge_citations:
        failures.append(
            "Executive Brief Groq enhancement returned knowledge "
            "citations that were not retrieved: "
            + ", ".join(
                unsupported_knowledge_citations
            )
        )

    invalid_returned_knowledge = [
        citation_id
        for citation_id in returned_knowledge_citations
        if not citation_id.startswith(
            "DOC-"
        )
    ]

    if invalid_returned_knowledge:
        failures.append(
            "Executive Brief knowledge_citation_ids contains "
            "non-DOC identifiers: "
            + ", ".join(
                invalid_returned_knowledge
            )
        )

    doc_ids_in_business_evidence = [
        evidence_id
        for evidence_id in evidence_ids
        if evidence_id.startswith(
            "DOC-"
        )
    ]

    if doc_ids_in_business_evidence:
        failures.append(
            "Executive Brief evidence_ids incorrectly contains "
            "knowledge DOC-* citations: "
            + ", ".join(
                doc_ids_in_business_evidence
            )
        )

    missing_top_level_knowledge = sorted(
        set(
            nested_knowledge_citations
        ).difference(
            top_level_knowledge_citations
        )
    )

    if missing_top_level_knowledge:
        failures.append(
            "Nested Executive Brief knowledge citations were "
            "missing from top-level knowledge_citation_ids: "
            + ", ".join(
                missing_top_level_knowledge
            )
        )

    if enhancement.get(
        "human_review_required"
    ) is not True:
        failures.append(
            "Executive Brief RAG removed the human-review requirement."
        )

    if enhancement.get(
        "database_update_performed"
    ) is not False:
        failures.append(
            "Executive Brief RAG incorrectly performed a database update."
        )

    if enhancement.get(
        "workflow_action_performed"
    ) is not False:
        failures.append(
            "Executive Brief RAG incorrectly performed a workflow action."
        )

    if enhancement.get(
        "comparison_available"
    ) is not False:
        failures.append(
            "Executive Brief RAG incorrectly claimed comparison data."
        )

    return failures


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
        max_output_tokens=(
            1400
            if (
                arguments.require_rag
                and arguments.agent == "executive-brief"
            )
            else 2000
        ),
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
            (
                "day34-live-root-cause-rag-test"
                if arguments.agent == "root-cause"
                else (
                    "day34-live-recommendation-rag-test"
                    if arguments.agent == "recommendation"
                    else (
                        "day34-live-executive-brief-rag-test"
                        if arguments.agent == "executive-brief"
                        else "day34-live-multi-agent-rag-test"
                    )
                )
            )
            if arguments.require_rag
            else (
                "day36-live-groq-five-agent-test"
                if arguments.agent == "all"
                else (
                    "day36-live-groq-"
                    + arguments.agent
                    + "-test"
                )
            )
        ),
        requested_by=(
            "manual-day34-rag"
            if arguments.require_rag
            else "manual-day36"
        ),
        input_data={
            "finding_limit": 3,
            "manager_limit": 2,
            "executive_limit": 2,
            "analysis_limit": 2,
            "recommendation_limit": 2,
            "require_knowledge_citation": (
                arguments.require_rag
            ),
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
            arguments.require_rag
            and result.agent_name
            in {
                "Root-Cause Agent",
                "Recommendation Agent",
                "Executive Brief Agent",
            }
            and isinstance(
                enhancement,
                dict,
            )
        ):
            knowledge_retrieval = enhancement.get(
                "knowledge_retrieval",
                {},
            )

            if (
                not isinstance(
                    knowledge_retrieval,
                    dict,
                )
                or not knowledge_retrieval
            ):
                run_metadata = (
                    result.run_metadata
                    if isinstance(
                        result.run_metadata,
                        dict,
                    )
                    else {}
                )
                knowledge_retrieval = run_metadata.get(
                    "knowledge_retrieval",
                    {},
                )

            if isinstance(
                knowledge_retrieval,
                dict,
            ):
                print(
                    "  RAG retrieval:",
                    knowledge_retrieval.get(
                        "status"
                    ),
                )
                print(
                    "  RAG included chunks:",
                    knowledge_retrieval.get(
                        "included_result_count"
                    ),
                )
                print(
                    "  Retrieved knowledge citations:",
                    knowledge_retrieval.get(
                        "citations"
                    ),
                )
                print(
                    "  Returned knowledge citations:",
                    enhancement.get(
                        "knowledge_citation_ids"
                    ),
                )

            rag_run_metadata = (
                result.run_metadata
                if isinstance(
                    result.run_metadata,
                    dict,
                )
                else {}
            )

            if (
                result.agent_name
                == "Root-Cause Agent"
            ):
                failures.extend(
                    validate_root_cause_rag_output(
                        enhancement=enhancement,
                        run_metadata=rag_run_metadata,
                    )
                )

            if (
                result.agent_name
                == "Recommendation Agent"
            ):
                failures.extend(
                    validate_recommendation_rag_output(
                        enhancement=enhancement,
                        run_metadata=rag_run_metadata,
                    )
                )

            if (
                result.agent_name
                == "Executive Brief Agent"
            ):
                failures.extend(
                    validate_executive_brief_rag_output(
                        enhancement=enhancement,
                        run_metadata=rag_run_metadata,
                    )
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

        if arguments.require_rag:
            if arguments.agent == "root-cause":
                failure_heading = (
                    "DAY 34 ROOT-CAUSE LIVE RAG VALIDATION FAILED"
                )
            elif arguments.agent == "recommendation":
                failure_heading = (
                    "DAY 34 RECOMMENDATION LIVE RAG VALIDATION FAILED"
                )
            elif arguments.agent == "executive-brief":
                failure_heading = (
                    "DAY 34 EXECUTIVE BRIEF LIVE RAG VALIDATION FAILED"
                )
            else:
                failure_heading = (
                    "DAY 34 MULTI-AGENT LIVE RAG VALIDATION FAILED"
                )
        else:
            failure_heading = (
                "DAY 36 LIVE VALIDATION FAILED"
            )

        print(
            failure_heading
        )

        for failure in failures:
            print(
                " -",
                failure,
            )

        if arguments.require_rag:
            if arguments.agent == "root-cause":
                failure_message = (
                    "Day 34 Root-Cause live RAG validation failed."
                )
            elif arguments.agent == "recommendation":
                failure_message = (
                    "Day 34 Recommendation live RAG validation failed."
                )
            elif arguments.agent == "executive-brief":
                failure_message = (
                    "Day 34 Executive Brief live RAG validation failed."
                )
            else:
                failure_message = (
                    "Day 34 multi-agent live RAG validation failed."
                )
        else:
            failure_message = (
                "Day 36 live Groq five-agent validation failed."
            )

        raise RuntimeError(
            failure_message
        )

    print()
    if arguments.require_rag:
        if arguments.agent == "root-cause":
            print(
                "DAY 34 ROOT-CAUSE LIVE RAG VALIDATION PASSED"
            )
        elif arguments.agent == "recommendation":
            print(
                "DAY 34 RECOMMENDATION LIVE RAG VALIDATION PASSED"
            )
        elif arguments.agent == "executive-brief":
            print(
                "DAY 34 EXECUTIVE BRIEF LIVE RAG VALIDATION PASSED"
            )
        else:
            print(
                "DAY 34 MULTI-AGENT LIVE RAG VALIDATION PASSED"
            )
    elif arguments.agent == "all":
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
