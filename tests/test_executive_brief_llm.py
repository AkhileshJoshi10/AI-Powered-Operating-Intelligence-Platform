from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import date, datetime
from typing import Any, Callable

import backend.app.agents.executive_brief_agent as brief_module
from backend.app.agents import (
    AgentContext,
    AgentExecutionStatus,
)
from backend.app.agents.executive_brief_agent import (
    ExecutiveBriefAgent,
)
from backend.app.llm import (
    LLMProviderConfig,
    LLMRequest,
    LLMResponse,
    LLMTimeoutError,
    MockLLMProvider,
)


class MutatingMockProvider(MockLLMProvider):
    """Mock provider that mutates controlled structured output."""

    def __init__(
        self,
        config: LLMProviderConfig,
        mutate: Callable[[dict[str, Any]], None],
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
            "Simulated Executive Brief LLM timeout."
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
        timeout_seconds=1.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        max_input_tokens=10000,
        max_output_tokens=3000,
        max_estimated_cost_usd=0.0,
        temperature=0.0,
        mask_sensitive_data=True,
        allowed_tools=[],
    )


def build_service_response(
    *,
    action: str = "created",
) -> dict[str, Any]:
    """Build one valid deterministic Executive Brief response."""

    return {
        "status": "success",
        "generated_at": datetime(
            2026,
            8,
            5,
            18,
            0,
            0,
        ),
        "action": action,
        "message": (
            "Daily Executive Brief "
            f"{action} successfully."
        ),
        "brief": {
            "brief_id": 11,
            "brief_date": date(
                2026,
                8,
                5,
            ),
            "brief_type": "Daily Executive Brief",
            "summary_text": (
                "The current operating snapshot contains 12 open "
                "business issues, including 4 high-priority issues. "
                "3 recommendations are awaiting management review. "
                "There are 5 active tasks, including 1 blocked and "
                "2 overdue tasks."
            ),
            "brief_data": {
                "brief_version": 1,
                "generated_at": "2026-08-05T18:00:00",
                "kpi_snapshot": {
                    "total_kpis": 2,
                    "kpis": [
                        {
                            "kpi_key": "total_sales",
                            "kpi_name": "Total Sales",
                            "value": 125000.0,
                            "display_value": "₹125,000.00",
                        },
                        {
                            "kpi_key": "operating_profit",
                            "kpi_name": "Operating Profit",
                            "value": 18000.0,
                            "display_value": "₹18,000.00",
                        },
                    ],
                    "latest_store_target_achievement": [],
                },
                "issue_snapshot": {
                    "open_issue_count": 12,
                    "high_priority_open_issue_count": 4,
                    "in_progress_issue_count": 1,
                    "top_open_issues": [
                        {
                            "issue_id": "ISSUE-HIGH-001",
                            "title": "Restore product availability",
                            "priority_level": "High",
                            "priority_score": 95.0,
                        }
                    ],
                },
                "recommendation_snapshot": {
                    "total_recommendations": 5,
                    "recommendations_needing_review": 3,
                    "status_counts": {
                        "Pending Review": 3,
                    },
                    "top_recommendations": [
                        {
                            "recommendation_id": 21,
                            "issue_id": "ISSUE-HIGH-001",
                            "recommendation_title": (
                                "Restore product availability"
                            ),
                        }
                    ],
                },
                "task_snapshot": {
                    "total_tasks": 8,
                    "active_task_count": 5,
                    "blocked_task_count": 1,
                    "overdue_task_count": 2,
                    "status_counts": {
                        "Blocked": 1,
                    },
                    "overdue_tasks": [
                        {
                            "task_id": 31,
                            "task_title": (
                                "Expedite replenishment"
                            ),
                            "status": "Blocked",
                            "due_date": "2026-08-04",
                        }
                    ],
                    "priority_tasks": [
                        {
                            "task_id": 31,
                            "task_title": (
                                "Expedite replenishment"
                            ),
                            "status": "Blocked",
                            "due_date": "2026-08-04",
                        }
                    ],
                },
                "management_attention": [
                    "Review 4 high-priority open business issues.",
                    (
                        "Complete management review for "
                        "3 recommendations."
                    ),
                    "Resolve blockers affecting 1 tasks.",
                    "Address 2 overdue tasks.",
                ],
            },
            "status": "Draft",
            "created_at": datetime(
                2026,
                8,
                5,
                18,
                0,
                0,
            ),
            "updated_at": datetime(
                2026,
                8,
                5,
                18,
                0,
                0,
            ),
        },
    }


def configure_brief_service(
    monkeypatch: Any,
    *,
    action: str = "created",
) -> list[str]:
    """Configure the deterministic service and capture its calls."""

    calls: list[str] = []

    def fake_generate(
    ) -> dict[str, Any]:
        calls.append(
            action
        )

        return build_service_response(
            action=action
        )

    monkeypatch.setattr(
        brief_module,
        "generate_daily_executive_brief",
        fake_generate,
    )

    return calls


def test_executive_brief_agent_remains_deterministic_when_llm_disabled(
    monkeypatch: Any,
) -> None:
    """A disabled provider should preserve the persisted brief."""

    calls = configure_brief_service(
        monkeypatch
    )

    result = asyncio.run(
        ExecutiveBriefAgent(
            llm_provider=MockLLMProvider(
                build_provider_config(
                    enabled=False
                )
            )
        ).execute(
            AgentContext(
                run_type="executive-brief-llm-disabled-test"
            )
        )
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.agent_version == "1.1.0"
    assert result.used_fallback is False
    assert "llm_enhancement" not in result.output_data
    assert result.output_data["snapshot"] == {
        "total_kpis": 2,
        "open_issue_count": 12,
        "high_priority_open_issue_count": 4,
        "recommendations_needing_review": 3,
        "active_task_count": 5,
        "blocked_task_count": 1,
        "overdue_task_count": 2,
    }
    assert result.output_data["database"]["brief_id"] == 11
    assert calls == ["created"]


def test_executive_brief_agent_adds_grounded_llm_enhancement(
    monkeypatch: Any,
) -> None:
    """Mock enhancement should preserve deterministic brief facts."""

    calls = configure_brief_service(
        monkeypatch
    )

    result = asyncio.run(
        ExecutiveBriefAgent(
            llm_provider=MockLLMProvider(
                build_provider_config()
            )
        ).execute(
            AgentContext(
                run_type="executive-brief-llm-success-test"
            )
        )
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.used_fallback is False
    assert result.model_provider == "mock"
    assert result.model_name == "mock-deterministic-v1"
    assert result.prompt_name == "executive_brief_enhancement"
    assert result.prompt_version == "v1"
    assert result.total_tokens is not None
    assert calls == ["created"]

    output_data = result.output_data

    assert output_data["snapshot"]["open_issue_count"] == 12
    assert output_data["database"]["brief_id"] == 11
    assert output_data["generation"]["action"] == "created"

    enhancement = output_data["llm_enhancement"]

    assert enhancement["status"] == "Complete"
    assert enhancement["schema_name"] == "ExecutiveBriefEnhancementV1"
    assert enhancement["persisted_to_executive_briefs"] is False
    assert enhancement["database_record_authoritative"] is True
    assert enhancement["deterministic_snapshot"] == output_data["snapshot"]
    assert enhancement["deterministic_brief_action"] == "created"
    assert enhancement["deterministic_brief_date"] == "2026-08-05"
    assert enhancement["deterministic_record_status"] == "Draft"
    assert enhancement["comparison_available"] is False
    assert enhancement["human_review_required"] is True
    assert enhancement["database_update_performed"] is False
    assert enhancement["workflow_action_performed"] is False
    assert len(enhancement["management_attention"]) == 4


def test_executive_brief_agent_falls_back_after_llm_timeout(
    monkeypatch: Any,
) -> None:
    """LLM timeout should retain the persisted deterministic brief."""

    calls = configure_brief_service(
        monkeypatch,
        action="updated",
    )

    result = asyncio.run(
        ExecutiveBriefAgent(
            llm_provider=TimeoutMockProvider(
                build_provider_config()
            )
        ).execute(
            AgentContext(
                run_type="executive-brief-llm-timeout-test"
            )
        )
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.used_fallback is True
    assert result.error_type == "LLMTimeoutError"
    assert result.llm_error_type == "LLMTimeoutError"
    assert result.output_data["database"]["brief_id"] == 11
    assert result.output_data["generation"]["action"] == "updated"
    assert result.output_data["llm_enhancement"]["status"] == "Fallback"
    assert result.run_metadata["llm_enhancement_status"] == "Fallback"
    assert calls == ["updated"]


def test_executive_brief_agent_rejects_changed_snapshot_count(
    monkeypatch: Any,
) -> None:
    """The LLM cannot alter deterministic Executive Brief counts."""

    configure_brief_service(
        monkeypatch
    )

    def mutate(
        output: dict[str, Any],
    ) -> None:
        output["deterministic_snapshot"][
            "open_issue_count"
        ] = 999

    result = asyncio.run(
        ExecutiveBriefAgent(
            llm_provider=MutatingMockProvider(
                build_provider_config(),
                mutate,
            )
        ).execute(
            AgentContext(
                run_type="executive-brief-count-change-test"
            )
        )
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.used_fallback is True
    assert result.llm_error_type == "LLMProviderResponseError"
    assert "snapshot counts" in (
        result.llm_error_message or ""
    )
    assert result.output_data["snapshot"]["open_issue_count"] == 12


def test_executive_brief_agent_rejects_invented_evidence_reference(
    monkeypatch: Any,
) -> None:
    """The LLM cannot cite an internal reference absent from the brief."""

    configure_brief_service(
        monkeypatch
    )

    def mutate(
        output: dict[str, Any],
    ) -> None:
        output["evidence_ids"].append(
            "BRIEF-INVENTED:999"
        )

    result = asyncio.run(
        ExecutiveBriefAgent(
            llm_provider=MutatingMockProvider(
                build_provider_config(),
                mutate,
            )
        ).execute(
            AgentContext(
                run_type="executive-brief-invented-reference-test"
            )
        )
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.used_fallback is True
    assert result.llm_error_type == "LLMProviderResponseError"
    assert "unsupported evidence identifiers" in (
        result.llm_error_message or ""
    )
    assert result.output_data["database"]["brief_id"] == 11


def test_executive_brief_agent_rejects_change_or_workflow_claims(
    monkeypatch: Any,
) -> None:
    """The LLM cannot claim comparison data or perform workflow actions."""

    configure_brief_service(
        monkeypatch
    )

    def mutate(
        output: dict[str, Any],
    ) -> None:
        output["comparison_available"] = True
        output["workflow_action_performed"] = True

    result = asyncio.run(
        ExecutiveBriefAgent(
            llm_provider=MutatingMockProvider(
                build_provider_config(),
                mutate,
            )
        ).execute(
            AgentContext(
                run_type="executive-brief-control-flag-test"
            )
        )
    )

    assert result.execution_status == AgentExecutionStatus.SUCCESS
    assert result.used_fallback is True
    assert result.llm_error_type == "LLMProviderResponseError"
    assert result.output_data["snapshot"]["open_issue_count"] == 12
    assert result.output_data["database"]["record_status"] == "Draft"