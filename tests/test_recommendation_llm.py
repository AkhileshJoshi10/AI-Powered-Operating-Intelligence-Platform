from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any, Callable

import pandas as pd

import backend.app.agents.recommendation_agent as recommendation_module
from backend.app.agents import (
    AgentContext,
    AgentExecutionStatus,
)
from backend.app.agents.recommendation_agent import RecommendationAgent
from backend.app.llm import (
    LLMProviderConfig,
    LLMRequest,
    LLMResponse,
    LLMTimeoutError,
    MockLLMProvider,
)


class MutatingMockProvider(MockLLMProvider):
    """Mock provider that changes controlled structured output."""

    def __init__(
        self,
        config: LLMProviderConfig,
        mutate: Callable[
            [dict[str, Any]],
            None,
        ],
    ) -> None:
        super().__init__(
            config
        )
        self._mutate = mutate

    async def _generate_once(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        metadata = dict(
            request.metadata
        )
        structured_output = deepcopy(
            metadata.get(
                "mock_structured_output",
                {},
            )
        )

        if isinstance(
            structured_output,
            dict,
        ):
            self._mutate(
                structured_output
            )
            metadata[
                "mock_structured_output"
            ] = structured_output

        return await super()._generate_once(
            request.model_copy(
                update={
                    "metadata": metadata,
                }
            )
        )


class TimeoutMockProvider(MockLLMProvider):
    """Mock provider used to verify deterministic fallback."""

    async def _generate_once(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        del request

        raise LLMTimeoutError(
            "Simulated recommendation LLM timeout."
        )


def build_provider_config(
    *,
    enabled: bool = True,
) -> LLMProviderConfig:
    """Build a controlled provider configuration for tests."""

    return LLMProviderConfig(
        enabled=enabled,
        provider_name="mock",
        model_name="mock-deterministic-v1",
        max_retries=0,
        retry_backoff_seconds=0,
        max_estimated_cost_usd=0.0,
    )


def configure_recommendation_pipeline(
    monkeypatch: Any,
) -> dict[str, Any]:
    """Configure deterministic recommendation dependencies."""

    priority_reference = pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-HIGH-001",
                "executive_rank": 1,
                "executive_score": 130.0,
            },
            {
                "issue_id": "ISSUE-HIGH-002",
                "executive_rank": 2,
                "executive_score": 115.0,
            },
        ]
    )

    recommendation_context = pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-HIGH-001",
            },
            {
                "issue_id": "ISSUE-HIGH-002",
            },
        ]
    )

    recommendations = pd.DataFrame(
        [
            {
                "executive_rank": 1,
                "issue_id": "ISSUE-HIGH-001",
                "issue_title": "Product availability risk",
                "issue_type": "Product Availability Risk",
                "business_area": "Inventory",
                "priority_level": "High",
                "priority_score": 95.0,
                "executive_score": 130.0,
                "root_cause_category": (
                    "Inventory Replenishment and Supply Risk"
                ),
                "root_cause_summary": (
                    "Likely inventory replenishment failure."
                ),
                "root_cause_confidence_score": 82.0,
                "recommendation_title": (
                    "Restore product availability"
                ),
                "recommendation_text": (
                    "Reason for action: Likely inventory "
                    "replenishment failure. Recommended action steps: "
                    "1. Confirm current stock and pending orders. "
                    "2. Expedite the vendor order. "
                    "3. Review the reorder level. "
                    "4. Track stock daily."
                ),
                "suggested_owner_role": "Inventory Manager",
                "suggested_deadline": "2026-08-08",
                "expected_impact": (
                    "Reduce stockout exposure and protect sales."
                ),
                "confidence_score": 82.0,
                "status": "Pending Review",
                "generated_at": pd.Timestamp(
                    "2026-08-05T10:00:00"
                ),
            },
            {
                "executive_rank": 2,
                "issue_id": "ISSUE-HIGH-002",
                "issue_title": "Vendor delivery risk",
                "issue_type": "Vendor Performance Risk",
                "business_area": "Procurement",
                "priority_level": "High",
                "priority_score": 85.0,
                "executive_score": 115.0,
                "root_cause_category": (
                    "Vendor Reliability and Fulfilment Risk"
                ),
                "root_cause_summary": (
                    "Likely supplier reliability issue."
                ),
                "root_cause_confidence_score": 74.0,
                "recommendation_title": (
                    "Correct vendor delivery performance"
                ),
                "recommendation_text": (
                    "Reason for action: Likely supplier reliability "
                    "issue. Recommended action steps: "
                    "1. Review delayed and partial deliveries. "
                    "2. Request a corrective delivery plan. "
                    "3. Identify affected products and stores. "
                    "4. Prepare a backup supplier."
                ),
                "suggested_owner_role": "Procurement Manager",
                "suggested_deadline": "2026-08-10",
                "expected_impact": (
                    "Improve delivery reliability and reduce shortages."
                ),
                "confidence_score": 74.0,
                "status": "Pending Review",
                "generated_at": pd.Timestamp(
                    "2026-08-05T10:00:00"
                ),
            },
        ]
    )

    database_records = [
        {
            "issue_id": "ISSUE-HIGH-001",
        },
        {
            "issue_id": "ISSUE-HIGH-002",
        },
    ]
    persistence_calls: list[
        dict[str, Any]
    ] = []

    monkeypatch.setattr(
        recommendation_module,
        "build_recommendation_reference",
        lambda **_: (
            priority_reference.copy(),
            "Root-Cause Agent output",
        ),
    )
    monkeypatch.setattr(
        recommendation_module,
        "load_recommendation_context",
        lambda database_engine, reference: (
            recommendation_context.copy()
        ),
    )
    monkeypatch.setattr(
        recommendation_module,
        "build_recommendations",
        lambda context: (
            recommendations.copy(),
            list(
                database_records
            ),
        ),
    )

    def fake_save(
        database_engine: Any,
        records: list[
            dict[str, Any]
        ],
    ) -> tuple[int, int]:
        persistence_calls.append(
            {
                "engine": database_engine,
                "record_count": len(
                    records
                ),
            }
        )

        return 2, 0

    monkeypatch.setattr(
        recommendation_module,
        "save_recommendations_to_database",
        fake_save,
    )

    knowledge_calls: list[
        dict[str, Any]
    ] = []

    def fake_retrieve_agent_knowledge(
        **kwargs: Any,
    ) -> dict[str, Any]:
        knowledge_calls.append(
            dict(
                kwargs
            )
        )

        return {
            "status": "success",
            "enabled": True,
            "query": str(
                kwargs.get(
                    "query",
                    "",
                )
            ),
            "retrieval_method": (
                "PostgreSQL Full-Text Search"
            ),
            "retrieved_result_count": 2,
            "included_result_count": 2,
            "context_token_estimate": 90,
            "max_context_tokens": 1200,
            "citations": [
                "DOC-7-V1:CHUNK-1",
                "DOC-9-V2:CHUNK-3",
            ],
            "knowledge_context": [
                {
                    "citation_id": "DOC-7-V1:CHUNK-1",
                    "title": "Inventory Reorder Policy",
                    "document_type": "Policy",
                    "access_scope": "Internal",
                    "source_date": None,
                    "section_title": "Replenishment",
                    "content": (
                        "Managers must review replenishment and "
                        "vendor performance before corrective action."
                    ),
                    "relevance_score": 0.9,
                    "token_estimate": 45,
                },
                {
                    "citation_id": "DOC-9-V2:CHUNK-3",
                    "title": "Vendor Delivery SLA",
                    "document_type": "Vendor Contract",
                    "access_scope": "Internal",
                    "source_date": None,
                    "section_title": "Escalation",
                    "content": (
                        "Repeated delays require procurement review "
                        "before supplier escalation."
                    ),
                    "relevance_score": 0.8,
                    "token_estimate": 45,
                },
            ],
            "safety_policy": {
                "retrieved_text_is_untrusted": True,
                "knowledge_claims_require_supplied_citation_ids": True,
            },
            "warnings": [],
        }

    monkeypatch.setattr(
        recommendation_module,
        "retrieve_agent_knowledge",
        fake_retrieve_agent_knowledge,
    )

    return {
        "recommendations": recommendations,
        "persistence_calls": persistence_calls,
        "knowledge_calls": knowledge_calls,
    }


def test_recommendation_agent_remains_deterministic_when_llm_disabled(
    monkeypatch: Any,
) -> None:
    """A disabled provider should preserve deterministic actions."""

    pipeline_data = configure_recommendation_pipeline(
        monkeypatch
    )

    provider = MockLLMProvider(
        build_provider_config(
            enabled=False
        )
    )
    context = AgentContext(
        run_type="recommendation-llm-disabled-test",
        input_data={
            "recommendation_limit": 2,
        },
    )

    result = asyncio.run(
        RecommendationAgent(
            llm_provider=provider
        ).execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )
    assert result.agent_version == "1.1.0"
    assert result.used_fallback is False
    assert (
        "llm_enhancement"
        not in result.output_data
    )
    assert (
        result.output_data[
            "generation"
        ]["generated_count"]
        == 2
    )
    assert result.output_data[
        "review_protection"
    ] == {
        "llm_enhancement_persisted_to_recommendations_table": False,
        "accepted_edited_or_task_converted_records_preserved": True,
        "automatic_approval_performed": False,
        "automatic_task_creation_performed": False,
    }
    assert pipeline_data[
        "knowledge_calls"
    ] == []


def test_recommendation_agent_adds_grounded_llm_enhancement(
    monkeypatch: Any,
) -> None:
    """Mock enhancement should preserve recommendation facts."""

    pipeline_data = configure_recommendation_pipeline(
        monkeypatch
    )

    provider = MockLLMProvider(
        build_provider_config()
    )
    context = AgentContext(
        run_type="recommendation-llm-success-test",
        input_data={
            "recommendation_limit": 2,
        },
    )

    result = asyncio.run(
        RecommendationAgent(
            llm_provider=provider
        ).execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )
    assert result.used_fallback is False
    assert result.model_provider == "mock"
    assert (
        result.model_name
        == "mock-deterministic-v1"
    )
    assert (
        result.prompt_name
        == "recommendation_enhancement"
    )
    assert result.prompt_version == "v1"
    assert result.total_tokens is not None

    enhancement = result.output_data[
        "llm_enhancement"
    ]

    assert enhancement["status"] == "Complete"
    assert (
        enhancement["schema_name"]
        == "RecommendationEnhancementV1"
    )
    assert (
        enhancement[
            "persisted_to_recommendations_table"
        ]
        is False
    )
    assert enhancement[
        "recommendations_approved"
    ] is False
    assert enhancement["tasks_created"] is False
    assert enhancement[
        "human_review_required"
    ] is True

    items = enhancement[
        "recommendation_enhancements"
    ]

    assert [
        item["issue_id"]
        for item in items
    ] == [
        "ISSUE-HIGH-001",
        "ISSUE-HIGH-002",
    ]
    assert (
        items[0][
            "deterministic_owner_role"
        ]
        == "Inventory Manager"
    )
    assert (
        items[0][
            "deterministic_deadline"
        ]
        == "2026-08-08"
    )
    assert (
        items[0][
            "deterministic_confidence_score"
        ]
        == 82.0
    )
    assert [
        action["step_id"]
        for action in items[0][
            "sequenced_actions"
        ]
    ] == [
        "ISSUE-HIGH-001:ACTION-01",
        "ISSUE-HIGH-001:ACTION-02",
        "ISSUE-HIGH-001:ACTION-03",
        "ISSUE-HIGH-001:ACTION-04",
    ]
    assert items[0][
        "knowledge_citation_ids"
    ] == []
    assert enhancement[
        "knowledge_citation_ids"
    ] == []
    assert enhancement[
        "knowledge_retrieval"
    ]["status"] == "success"
    assert enhancement[
        "knowledge_retrieval"
    ]["citations"] == [
        "DOC-7-V1:CHUNK-1",
        "DOC-9-V2:CHUNK-3",
    ]
    assert result.run_metadata[
        "knowledge_retrieval"
    ]["citations"] == [
        "DOC-7-V1:CHUNK-1",
        "DOC-9-V2:CHUNK-3",
    ]
    assert len(
        pipeline_data[
            "knowledge_calls"
        ]
    ) == 1
    assert pipeline_data[
        "knowledge_calls"
    ][0][
        "allowed_access_scopes"
    ] == (
        "Internal",
    )


def test_recommendation_agent_falls_back_after_llm_timeout(
    monkeypatch: Any,
) -> None:
    """LLM timeout should retain deterministic recommendations."""

    configure_recommendation_pipeline(
        monkeypatch
    )

    provider = TimeoutMockProvider(
        build_provider_config()
    )
    context = AgentContext(
        run_type="recommendation-llm-timeout-test",
        input_data={
            "recommendation_limit": 2,
        },
    )

    result = asyncio.run(
        RecommendationAgent(
            llm_provider=provider
        ).execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )
    assert result.used_fallback is True
    assert (
        result.error_type
        == "LLMTimeoutError"
    )
    assert (
        result.llm_error_type
        == "LLMTimeoutError"
    )
    assert (
        result.output_data[
            "generation"
        ]["generated_count"]
        == 2
    )
    assert (
        result.output_data[
            "llm_enhancement"
        ]["status"]
        == "Fallback"
    )
    assert (
        result.run_metadata[
            "llm_enhancement_status"
        ]
        == "Fallback"
    )


def test_recommendation_agent_rejects_invented_issue_reference(
    monkeypatch: Any,
) -> None:
    """An invented issue ID should trigger deterministic fallback."""

    configure_recommendation_pipeline(
        monkeypatch
    )

    def mutate(
        output: dict[str, Any],
    ) -> None:
        output[
            "recommendation_enhancements"
        ][0]["issue_id"] = (
            "ISSUE-INVENTED-999"
        )

    provider = MutatingMockProvider(
        build_provider_config(),
        mutate,
    )
    context = AgentContext(
        run_type="recommendation-invented-issue-test",
        input_data={
            "recommendation_limit": 2,
        },
    )

    result = asyncio.run(
        RecommendationAgent(
            llm_provider=provider
        ).execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )
    assert result.used_fallback is True
    assert (
        result.llm_error_type
        == "LLMProviderResponseError"
    )
    assert (
        "unsupported controlled identifiers"
        in (
            result.llm_error_message
            or ""
        )
    )
    assert (
        result.output_data[
            "recommendations"
        ][0]["issue_id"]
        == "ISSUE-HIGH-001"
    )


def test_recommendation_agent_rejects_changed_owner_and_action(
    monkeypatch: Any,
) -> None:
    """Changed deterministic recommendation facts must be rejected."""

    configure_recommendation_pipeline(
        monkeypatch
    )

    def mutate(
        output: dict[str, Any],
    ) -> None:
        first = output[
            "recommendation_enhancements"
        ][0]
        first[
            "deterministic_owner_role"
        ] = "Chief Executive Officer"
        first["sequenced_actions"][0][
            "action_text"
        ] = (
            "Approve an unvalidated emergency purchase."
        )

    provider = MutatingMockProvider(
        build_provider_config(),
        mutate,
    )
    context = AgentContext(
        run_type="recommendation-changed-facts-test",
        input_data={
            "recommendation_limit": 2,
        },
    )

    result = asyncio.run(
        RecommendationAgent(
            llm_provider=provider
        ).execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )
    assert result.used_fallback is True
    assert (
        result.llm_error_type
        == "LLMProviderResponseError"
    )
    assert (
        "changed the deterministic suggested owner"
        in (
            result.llm_error_message
            or ""
        )
    )
    assert (
        result.output_data[
            "recommendations"
        ][0][
            "suggested_owner_role"
        ]
        == "Inventory Manager"
    )


def test_recommendation_agent_rejects_automatic_approval_or_task_creation(
    monkeypatch: Any,
) -> None:
    """The LLM cannot approve recommendations or create tasks."""

    configure_recommendation_pipeline(
        monkeypatch
    )

    def mutate(
        output: dict[str, Any],
    ) -> None:
        output[
            "recommendations_approved"
        ] = True
        output[
            "tasks_created"
        ] = True

    provider = MutatingMockProvider(
        build_provider_config(),
        mutate,
    )
    context = AgentContext(
        run_type="recommendation-auto-action-test",
        input_data={
            "recommendation_limit": 2,
        },
    )

    result = asyncio.run(
        RecommendationAgent(
            llm_provider=provider
        ).execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )
    assert result.used_fallback is True
    assert (
        result.llm_error_type
        == "LLMProviderResponseError"
    )
    assert (
        "did not match RecommendationEnhancementV1"
        in (
            result.llm_error_message
            or ""
        )
    )
    assert (
        result.output_data[
            "review_protection"
        ][
            "automatic_approval_performed"
        ]
        is False
    )
    assert (
        result.output_data[
            "review_protection"
        ][
            "automatic_task_creation_performed"
        ]
        is False
    )

def test_recommendation_agent_rejects_invented_knowledge_citation(
    monkeypatch: Any,
) -> None:
    """Knowledge citations must come only from safe retrieval."""

    configure_recommendation_pipeline(
        monkeypatch
    )

    def mutate(
        output: dict[str, Any],
    ) -> None:
        output[
            "knowledge_citation_ids"
        ] = [
            "DOC-999-V1:CHUNK-99"
        ]

    provider = MutatingMockProvider(
        build_provider_config(),
        mutate,
    )
    context = AgentContext(
        run_type=(
            "recommendation-invented-knowledge-citation-test"
        ),
        input_data={
            "recommendation_limit": 2,
        },
    )

    result = asyncio.run(
        RecommendationAgent(
            llm_provider=provider
        ).execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )
    assert result.used_fallback is True
    assert (
        result.llm_error_type
        == "LLMProviderResponseError"
    )
    assert (
        "unsupported controlled identifiers"
        in (
            result.llm_error_message
            or ""
        )
    )
    assert (
        "knowledge_citation_ids"
        in (
            result.llm_error_message
            or ""
        )
    )


def test_recommendation_agent_continues_when_knowledge_retrieval_fails(
    monkeypatch: Any,
) -> None:
    """Optional RAG failure must not replace deterministic actions."""

    configure_recommendation_pipeline(
        monkeypatch
    )

    def fail_retrieval(
        **_: Any,
    ) -> dict[str, Any]:
        raise RuntimeError(
            "Simulated knowledge database failure."
        )

    monkeypatch.setattr(
        recommendation_module,
        "retrieve_agent_knowledge",
        fail_retrieval,
    )

    provider = MockLLMProvider(
        build_provider_config()
    )
    context = AgentContext(
        run_type=(
            "recommendation-knowledge-unavailable-test"
        ),
        input_data={
            "recommendation_limit": 2,
        },
    )

    result = asyncio.run(
        RecommendationAgent(
            llm_provider=provider
        ).execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )
    assert result.used_fallback is False

    enhancement = result.output_data[
        "llm_enhancement"
    ]

    assert enhancement[
        "knowledge_citation_ids"
    ] == []
    assert enhancement[
        "knowledge_retrieval"
    ]["status"] == "unavailable"
    assert enhancement[
        "knowledge_retrieval"
    ]["error_type"] == "RuntimeError"
    assert any(
        "deterministic recommendation remains authoritative"
        in warning
        for warning in enhancement[
            "knowledge_retrieval"
        ]["warnings"]
    )


def test_recommendation_agent_uses_knowledge_citation_when_required(
    monkeypatch: Any,
) -> None:
    """Controlled RAG mode should carry retrieved citations."""

    configure_recommendation_pipeline(
        monkeypatch
    )

    provider = MockLLMProvider(
        build_provider_config()
    )
    context = AgentContext(
        run_type=(
            "recommendation-required-knowledge-citation-success-test"
        ),
        input_data={
            "recommendation_limit": 2,
            "require_knowledge_citation": True,
        },
    )

    result = asyncio.run(
        RecommendationAgent(
            llm_provider=provider
        ).execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )
    assert result.used_fallback is False

    enhancement = result.output_data[
        "llm_enhancement"
    ]

    assert enhancement[
        "knowledge_citation_ids"
    ] == [
        "DOC-7-V1:CHUNK-1",
        "DOC-9-V2:CHUNK-3",
    ]

    for item in enhancement[
        "recommendation_enhancements"
    ]:
        assert item[
            "knowledge_citation_ids"
        ] == [
            "DOC-7-V1:CHUNK-1",
            "DOC-9-V2:CHUNK-3",
        ]


def test_recommendation_agent_requires_knowledge_citation_when_requested(
    monkeypatch: Any,
) -> None:
    """Controlled RAG mode must actually cite retrieved knowledge."""

    configure_recommendation_pipeline(
        monkeypatch
    )

    def mutate(
        output: dict[str, Any],
    ) -> None:
        output[
            "knowledge_citation_ids"
        ] = []

        for item in output.get(
            "recommendation_enhancements",
            [],
        ):
            if isinstance(
                item,
                dict,
            ):
                item[
                    "knowledge_citation_ids"
                ] = []

    provider = MutatingMockProvider(
        build_provider_config(),
        mutate,
    )
    context = AgentContext(
        run_type=(
            "recommendation-required-knowledge-citation-test"
        ),
        input_data={
            "recommendation_limit": 2,
            "require_knowledge_citation": True,
        },
    )

    result = asyncio.run(
        RecommendationAgent(
            llm_provider=provider
        ).execute(
            context
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )
    assert result.used_fallback is True
    assert (
        result.llm_error_type
        == "LLMProviderResponseError"
    )
    assert (
        "required at least one retrieved knowledge citation"
        in (
            result.llm_error_message
            or ""
        )
    )

