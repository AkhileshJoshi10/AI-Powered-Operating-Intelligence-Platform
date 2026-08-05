from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import pytest

import backend.app.agents.priority_agent as priority_module
from backend.app.agents import (
    AgentContext,
    AgentExecutionStatus,
)
from backend.app.agents.priority_agent import (
    PriorityAgent,
)
from backend.app.llm import (
    LLMProviderConfig,
    LLMRequest,
    LLMTimeoutError,
    MockLLMProvider,
)


def build_mock_config(
    *,
    enabled: bool = True,
) -> LLMProviderConfig:
    """Build controlled mock-provider configuration."""

    return LLMProviderConfig(
        enabled=enabled,
        provider_name="mock",
        model_name="mock-deterministic-v1",
        timeout_seconds=1.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        max_input_tokens=4000,
        max_output_tokens=1000,
        max_estimated_cost_usd=0.02,
        temperature=0.0,
        mask_sensitive_data=True,
        allowed_tools=[],
    )


def build_deterministic_output(
) -> dict[str, Any]:
    """Build one controlled deterministic priority result."""

    manager_items = [
        {
            "manager_rank": 1,
            "issue_id": "ISSUE-HIGH-001",
            "title": "Restore product availability",
            "business_area": "Operations",
            "priority_level": "High",
            "priority_score": 95.0,
            "priority_reason": (
                "High-severity availability evidence."
            ),
            "finding_count": 2,
            "evidence_summary": (
                "Two validated inventory findings."
            ),
        },
        {
            "manager_rank": 2,
            "issue_id": "ISSUE-MEDIUM-001",
            "title": "Improve store target achievement",
            "business_area": "Sales",
            "priority_level": "Medium",
            "priority_score": 60.0,
            "priority_reason": (
                "Target achievement remains below threshold."
            ),
            "finding_count": 1,
            "evidence_summary": (
                "One validated sales finding."
            ),
        },
    ]

    executive_items = [
        {
            **manager_items[0],
            "executive_rank": 1,
            "executive_score": 130.0,
            "critical_evidence_score": 25.0,
        },
        {
            **manager_items[1],
            "executive_rank": 2,
            "executive_score": 85.0,
            "critical_evidence_score": 15.0,
        },
    ]

    return {
        "summary": (
            "Priority analysis consolidated 5 findings into "
            "3 business issues: 1 High, 1 Medium, and 1 Low. "
            "2 executive priorities were selected."
        ),
        "priority_status": "Complete",
        "generated_at": datetime(
            2026,
            8,
            5,
            11,
            0,
            tzinfo=timezone.utc,
        ),
        "database_persisted": True,
        "detailed_findings": {
            "total": 5,
            "by_source": {
                "sales": 2,
                "inventory": 2,
                "complaints": 1,
                "vendors": 0,
                "finance": 0,
            },
        },
        "issues": {
            "total_created": 3,
            "by_priority": {
                "High": 1,
                "Medium": 1,
                "Low": 1,
            },
            "active_by_priority": {
                "High": 1,
                "Medium": 1,
                "Low": 1,
            },
        },
        "evidence_records": {
            "total": 5,
        },
        "manager_priorities": {
            "requested_limit": 2,
            "returned_count": 2,
            "items": manager_items,
        },
        "executive_priorities": {
            "requested_limit": 2,
            "returned_count": 2,
            "items": executive_items,
        },
        "monitoring_comparison": {
            "available": True,
            "monitoring_finding_total": 5,
            "priority_input_finding_total": 5,
            "totals_match": True,
        },
        "evidence_references": {
            "source_field": "source_finding_id",
            "selected_issue_count": 2,
            "total_available": 5,
            "included_count": 3,
            "by_issue": {
                "ISSUE-HIGH-001": [
                    "FINDING-001",
                    "FINDING-002",
                ],
                "ISSUE-MEDIUM-001": [
                    "FINDING-003",
                ],
            },
        },
    }


class FailingPriorityProvider(
    MockLLMProvider
):
    """Raise one controlled provider timeout."""

    async def _generate_once(
        self,
        request: LLMRequest,
    ) -> Any:
        del request

        raise LLMTimeoutError(
            "Simulated Priority Agent timeout."
        )


def test_priority_agent_preserves_deterministic_mode(
    monkeypatch: Any,
) -> None:
    """Disabled LLM execution must not change deterministic output."""

    deterministic_output = build_deterministic_output()

    monkeypatch.setattr(
        priority_module,
        "build_deterministic_priority_output",
        lambda context: dict(deterministic_output),
    )

    agent = PriorityAgent(
        llm_provider=MockLLMProvider(
            build_mock_config(enabled=False)
        )
    )

    result = asyncio.run(
        agent.execute(
            AgentContext(
                run_type="priority-llm-disabled-test"
            )
        )
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.used_fallback is False
    assert result.agent_version == "1.1.0"
    assert result.summary == deterministic_output["summary"]
    assert "llm_enhancement" not in result.output_data
    assert result.model_provider is None
    assert result.prompt_name is None


def test_priority_agent_adds_grounded_explanations(
    monkeypatch: Any,
) -> None:
    """Enabled mock execution should explain unchanged priorities."""

    deterministic_output = build_deterministic_output()

    monkeypatch.setattr(
        priority_module,
        "build_deterministic_priority_output",
        lambda context: dict(deterministic_output),
    )

    result = asyncio.run(
        PriorityAgent(
            llm_provider=MockLLMProvider(
                build_mock_config()
            )
        ).execute(
            AgentContext(
                run_type="priority-llm-success-test"
            )
        )
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.used_fallback is False
    assert result.model_provider == "mock"
    assert result.model_name == "mock-deterministic-v1"
    assert result.prompt_name == "priority_explanation"
    assert result.prompt_version == "v1"
    assert result.input_tokens is not None
    assert result.output_tokens is not None
    assert result.total_tokens == (
        result.input_tokens + result.output_tokens
    )
    assert result.estimated_cost_usd == 0.0
    assert result.llm_latency_ms is not None

    output_data = result.output_data

    assert output_data["manager_priorities"] == (
        deterministic_output["manager_priorities"]
    )
    assert output_data["executive_priorities"] == (
        deterministic_output["executive_priorities"]
    )
    assert output_data["issues"] == deterministic_output["issues"]

    enhancement = output_data["llm_enhancement"]

    assert enhancement["status"] == "Complete"
    assert enhancement["schema_name"] == "PriorityExplanationV1"
    assert enhancement["review_first_issue_id"] == "ISSUE-HIGH-001"
    assert [
        item["issue_id"]
        for item in enhancement["priority_explanations"]
    ] == [
        "ISSUE-HIGH-001",
        "ISSUE-MEDIUM-001",
    ]

    first = enhancement["priority_explanations"][0]
    assert first["deterministic_priority_level"] == "High"
    assert first["deterministic_priority_score"] == 95.0
    assert first["manager_rank"] == 1
    assert first["executive_rank"] == 1
    assert set(first["evidence_ids"]) == {
        "FINDING-001",
        "FINDING-002",
    }
    assert "_execution_metadata" not in output_data


def test_priority_agent_uses_deterministic_fallback(
    monkeypatch: Any,
) -> None:
    """Provider failure should retain deterministic scores and ranks."""

    deterministic_output = build_deterministic_output()

    monkeypatch.setattr(
        priority_module,
        "build_deterministic_priority_output",
        lambda context: dict(deterministic_output),
    )

    result = asyncio.run(
        PriorityAgent(
            llm_provider=FailingPriorityProvider(
                build_mock_config()
            )
        ).execute(
            AgentContext(
                run_type="priority-llm-fallback-test"
            )
        )
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.used_fallback is True
    assert result.error_type == "LLMTimeoutError"
    assert result.llm_error_type == "LLMTimeoutError"
    assert result.summary == deterministic_output["summary"]
    assert result.output_data["manager_priorities"] == (
        deterministic_output["manager_priorities"]
    )
    assert result.output_data["llm_enhancement"]["status"] == "Fallback"
    assert result.model_provider == "mock"
    assert result.prompt_name == "priority_explanation"


def test_priority_agent_rejects_changed_deterministic_score(
    monkeypatch: Any,
) -> None:
    """An altered priority score should trigger deterministic fallback."""

    deterministic_output = build_deterministic_output()

    monkeypatch.setattr(
        priority_module,
        "build_deterministic_priority_output",
        lambda context: dict(deterministic_output),
    )

    invalid_output = priority_module.build_mock_priority_output(
        deterministic_output
    )
    invalid_output["priority_explanations"][0][
        "deterministic_priority_score"
    ] = 99.0

    monkeypatch.setattr(
        priority_module,
        "build_mock_priority_output",
        lambda output: invalid_output,
    )

    result = asyncio.run(
        PriorityAgent(
            llm_provider=MockLLMProvider(
                build_mock_config()
            )
        ).execute(
            AgentContext(
                run_type="priority-score-guardrail-test"
            )
        )
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.used_fallback is True
    assert result.error_type == "LLMProviderResponseError"
    assert result.llm_error_type == "LLMProviderResponseError"
    assert "changed the deterministic priority score" in (
        result.error_message or ""
    )
    assert result.output_data["executive_priorities"] == (
        deterministic_output["executive_priorities"]
    )


def test_priority_agent_rejects_invented_issue_reference(
    monkeypatch: Any,
) -> None:
    """An invented issue ID should trigger deterministic fallback."""

    deterministic_output = build_deterministic_output()

    monkeypatch.setattr(
        priority_module,
        "build_deterministic_priority_output",
        lambda context: dict(deterministic_output),
    )

    invalid_output = priority_module.build_mock_priority_output(
        deterministic_output
    )
    invalid_output["review_first_issue_id"] = "ISSUE-INVENTED-999"
    invalid_output["priority_explanations"][0][
        "issue_id"
    ] = "ISSUE-INVENTED-999"

    monkeypatch.setattr(
        priority_module,
        "build_mock_priority_output",
        lambda output: invalid_output,
    )

    result = asyncio.run(
        PriorityAgent(
            llm_provider=MockLLMProvider(
                build_mock_config()
            )
        ).execute(
            AgentContext(
                run_type="priority-reference-guardrail-test"
            )
        )
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.used_fallback is True
    assert result.error_type == "LLMProviderResponseError"
    assert "unsupported controlled identifiers" in (
        result.error_message or ""
    )
    assert result.output_data["manager_priorities"] == (
        deterministic_output["manager_priorities"]
    )