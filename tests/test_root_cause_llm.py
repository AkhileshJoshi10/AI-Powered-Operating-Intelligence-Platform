from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any, Callable

import pandas as pd

import backend.app.agents.root_cause_agent as root_cause_module
from backend.app.agents import (
    AgentContext,
    AgentExecutionStatus,
)
from backend.app.agents.root_cause_agent import RootCauseAgent
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
        mutate: Callable[[dict[str, Any]], None],
    ) -> None:
        super().__init__(config)
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

        if isinstance(structured_output, dict):
            self._mutate(
                structured_output
            )
            metadata["mock_structured_output"] = structured_output

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
            "Simulated root-cause LLM timeout."
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


def configure_root_cause_pipeline(
    monkeypatch: Any,
) -> dict[str, Any]:
    """Configure deterministic RCA dependencies with controlled data."""

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

    selected_issues = pd.DataFrame(
        [
            {"issue_id": "ISSUE-HIGH-001"},
            {"issue_id": "ISSUE-HIGH-002"},
        ]
    )

    selected_evidence = pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-HIGH-001",
                "source_finding_id": "FINDING-001",
            },
            {
                "issue_id": "ISSUE-HIGH-001",
                "source_finding_id": "FINDING-002",
            },
            {
                "issue_id": "ISSUE-HIGH-002",
                "source_finding_id": "FINDING-003",
            },
        ]
    )

    analyses = pd.DataFrame(
        [
            {
                "analysis_id": "RCA-ISSUE-HIGH-001",
                "executive_rank": 1,
                "issue_id": "ISSUE-HIGH-001",
                "title": "Product availability risk",
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
                "root_cause_explanation": (
                    "Stock is materially below the reorder requirement."
                ),
                "contributing_factors": (
                    "Current stock is below reorder level. "
                    "Supplier delivery performance is delayed."
                ),
                "evidence_summary": (
                    "Stock and delivery evidence are linked."
                ),
                "investigation_focus": (
                    "Review replenishment and supplier delivery."
                ),
                "confidence_score": 82.0,
                "evidence_count": 2,
                "evidence_types": "Low Stock, Vendor Delay",
                "analysis_method": (
                    "Rule-Based Database and Evidence Analysis"
                ),
                "analysis_status": "Generated",
                "review_status": "Pending Review",
                "generated_at": pd.Timestamp(
                    "2026-08-05T09:00:00"
                ),
            },
            {
                "analysis_id": "RCA-ISSUE-HIGH-002",
                "executive_rank": 2,
                "issue_id": "ISSUE-HIGH-002",
                "title": "Vendor delivery risk",
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
                "root_cause_explanation": (
                    "Delivery delays and partial fulfilment require review."
                ),
                "contributing_factors": (
                    "Multiple deliveries were delayed. "
                    "Partial deliveries were recorded."
                ),
                "evidence_summary": (
                    "Vendor delivery records support the assessment."
                ),
                "investigation_focus": (
                    "Review SLA compliance and supplier capacity."
                ),
                "confidence_score": 74.0,
                "evidence_count": 1,
                "evidence_types": "Vendor Delay",
                "analysis_method": (
                    "Rule-Based Database and Evidence Analysis"
                ),
                "analysis_status": "Generated",
                "review_status": "Pending Review",
                "generated_at": pd.Timestamp(
                    "2026-08-05T09:00:00"
                ),
            },
        ]
    )

    database_records = [
        {"issue_id": "ISSUE-HIGH-001"},
        {"issue_id": "ISSUE-HIGH-002"},
    ]
    persistence_calls: list[dict[str, Any]] = []

    monkeypatch.setattr(
        root_cause_module,
        "build_priority_reference",
        lambda **_: (
            priority_reference.copy(),
            "Priority Agent output",
        ),
    )
    monkeypatch.setattr(
        root_cause_module,
        "load_selected_issues",
        lambda database_engine, reference: selected_issues.copy(),
    )
    monkeypatch.setattr(
        root_cause_module,
        "load_selected_evidence",
        lambda database_engine, issue_ids: selected_evidence.copy(),
    )
    monkeypatch.setattr(
        root_cause_module,
        "build_root_cause_outputs",
        lambda database_engine, issues, evidence: (
            analyses.copy(),
            list(database_records),
        ),
    )

    def fake_save(
        database_engine: Any,
        records: list[dict[str, Any]],
    ) -> None:
        persistence_calls.append(
            {
                "engine": database_engine,
                "record_count": len(records),
            }
        )

    monkeypatch.setattr(
        root_cause_module,
        "save_root_causes_to_database",
        fake_save,
    )

    return {
        "analyses": analyses,
        "selected_evidence": selected_evidence,
        "persistence_calls": persistence_calls,
    }


def test_root_cause_agent_remains_deterministic_when_llm_disabled(
    monkeypatch: Any,
) -> None:
    """A disabled provider should preserve the deterministic result."""

    configure_root_cause_pipeline(
        monkeypatch
    )

    provider = MockLLMProvider(
        build_provider_config(
            enabled=False
        )
    )
    context = AgentContext(
        run_type="root-cause-llm-disabled-test",
        input_data={
            "analysis_limit": 2,
        },
    )

    result = asyncio.run(
        RootCauseAgent(
            llm_provider=provider
        ).execute(context)
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.agent_version == "1.1.0"
    assert result.used_fallback is False
    assert "llm_enhancement" not in result.output_data
    assert result.output_data["analysis"]["generated_count"] == 2
    assert result.output_data["review_protection"] == {
        "human_review_required": True,
        "llm_enhancement_persisted_to_root_cause_table": False,
        "accepted_or_edited_records_preserved": True,
    }


def test_root_cause_agent_adds_grounded_llm_explanation(
    monkeypatch: Any,
) -> None:
    """The mock provider should enhance without changing RCA facts."""

    configure_root_cause_pipeline(
        monkeypatch
    )

    provider = MockLLMProvider(
        build_provider_config()
    )
    context = AgentContext(
        run_type="root-cause-llm-success-test",
        input_data={
            "analysis_limit": 2,
        },
    )

    result = asyncio.run(
        RootCauseAgent(
            llm_provider=provider
        ).execute(context)
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.used_fallback is False
    assert result.model_provider == "mock"
    assert result.model_name == "mock-deterministic-v1"
    assert result.prompt_name == "root_cause_explanation"
    assert result.prompt_version == "v1"
    assert result.total_tokens is not None

    enhancement = result.output_data["llm_enhancement"]

    assert enhancement["status"] == "Complete"
    assert enhancement["schema_name"] == "RootCauseExplanationV1"
    assert enhancement["persisted_to_root_cause_table"] is False
    assert enhancement["human_review_required"] is True

    explanations = enhancement["root_cause_explanations"]

    assert [item["issue_id"] for item in explanations] == [
        "ISSUE-HIGH-001",
        "ISSUE-HIGH-002",
    ]
    assert explanations[0][
        "deterministic_root_cause_category"
    ] == "Inventory Replenishment and Supply Risk"
    assert explanations[0]["confidence_score"] == 82.0
    assert explanations[0]["evidence_ids"] == [
        "FINDING-001",
        "FINDING-002",
    ]
    assert explanations[0]["human_review_required"] is True


def test_root_cause_agent_falls_back_after_llm_timeout(
    monkeypatch: Any,
) -> None:
    """LLM timeout should retain the deterministic RCA output."""

    configure_root_cause_pipeline(
        monkeypatch
    )

    provider = TimeoutMockProvider(
        build_provider_config()
    )
    context = AgentContext(
        run_type="root-cause-llm-timeout-test",
        input_data={
            "analysis_limit": 2,
        },
    )

    result = asyncio.run(
        RootCauseAgent(
            llm_provider=provider
        ).execute(context)
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.used_fallback is True
    assert result.error_type == "LLMTimeoutError"
    assert result.llm_error_type == "LLMTimeoutError"
    assert result.output_data["analysis"]["generated_count"] == 2
    assert result.output_data["llm_enhancement"]["status"] == "Fallback"
    assert result.run_metadata["llm_enhancement_status"] == "Fallback"


def test_root_cause_agent_rejects_invented_issue_reference(
    monkeypatch: Any,
) -> None:
    """An invented issue ID should trigger deterministic fallback."""

    configure_root_cause_pipeline(
        monkeypatch
    )

    def mutate(output: dict[str, Any]) -> None:
        output["root_cause_explanations"][0][
            "issue_id"
        ] = "ISSUE-INVENTED-999"

    provider = MutatingMockProvider(
        build_provider_config(),
        mutate,
    )
    context = AgentContext(
        run_type="root-cause-invented-issue-test",
        input_data={
            "analysis_limit": 2,
        },
    )

    result = asyncio.run(
        RootCauseAgent(
            llm_provider=provider
        ).execute(context)
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.used_fallback is True
    assert result.llm_error_type == "LLMProviderResponseError"
    assert "unsupported controlled identifiers" in (
        result.llm_error_message or ""
    )
    assert result.output_data["analysis"]["generated_count"] == 2


def test_root_cause_agent_rejects_changed_category_and_factor(
    monkeypatch: Any,
) -> None:
    """Changed RCA facts must not replace deterministic output."""

    configure_root_cause_pipeline(
        monkeypatch
    )

    def mutate(output: dict[str, Any]) -> None:
        first = output["root_cause_explanations"][0]
        first["deterministic_root_cause_category"] = (
            "Invented Commercial Cause"
        )
        first["likely_contributing_factors"] = [
            "An unsupported competitor action caused the issue."
        ]

    provider = MutatingMockProvider(
        build_provider_config(),
        mutate,
    )
    context = AgentContext(
        run_type="root-cause-changed-facts-test",
        input_data={
            "analysis_limit": 2,
        },
    )

    result = asyncio.run(
        RootCauseAgent(
            llm_provider=provider
        ).execute(context)
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.used_fallback is True
    assert result.llm_error_type == "LLMProviderResponseError"
    assert "changed the deterministic root-cause category" in (
        result.llm_error_message or ""
    )
    assert result.output_data["analyses"][0][
        "root_cause_category"
    ] == "Inventory Replenishment and Supply Risk"