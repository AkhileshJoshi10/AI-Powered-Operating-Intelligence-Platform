from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import pytest

import backend.app.agents.monitoring_agent as monitoring_module
from backend.app.agents import (
    AgentContext,
    AgentExecutionStatus,
)
from backend.app.agents.llm_enhancement import (
    MonitoringSummaryV1,
    run_structured_enhancement,
)
from backend.app.agents.monitoring_agent import (
    MonitoringAgent,
)
from backend.app.llm import (
    LLMProviderConfig,
    LLMProviderResponseError,
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
    """Build a controlled deterministic monitoring snapshot."""

    return {
        "summary": (
            "Monitoring completed with 2 KPIs and "
            "3 business findings: 2 High, "
            "1 Medium, and 0 Low."
        ),
        "monitoring_status": "Complete",
        "snapshot_generated_at": datetime(
            2026,
            8,
            5,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        "finding_limit_per_source": 10,
        "successful_sources": [
            "kpis",
            "sales",
            "inventory",
        ],
        "failed_sources": [],
        "kpi_snapshot": {
            "status": "success",
            "total_kpis": 2,
            "kpis": [
                {
                    "kpi_key": "total_sales",
                    "kpi_name": "Total Sales",
                    "value": 100000.0,
                    "display_value": "₹100,000.00",
                    "unit": "Currency",
                    "reference_period": "2026-06",
                    "description": (
                        "Validated total sales."
                    ),
                },
                {
                    "kpi_key": "low_stock_count",
                    "kpi_name": "Low-Stock Count",
                    "value": 5,
                    "display_value": "5",
                    "unit": "Count",
                    "reference_period": "2026-06",
                    "description": (
                        "Validated low-stock count."
                    ),
                },
            ],
            "latest_store_target_achievement": [],
        },
        "analytics_snapshot": {},
        "finding_totals": {
            "total": 3,
            "by_source": {
                "sales": 1,
                "inventory": 2,
            },
            "by_severity": {
                "High": 2,
                "Medium": 1,
                "Low": 0,
            },
        },
        "top_findings": [
            {
                "source": "sales",
                "finding_id": "SALES-HIGH-001",
                "analysis_type": (
                    "Store Sales Decline"
                ),
                "business_area": "Sales",
                "severity": "High",
                "entity_type": "Store",
                "entity_id": "S003",
                "summary": (
                    "Store S003 sales declined."
                ),
                "evidence": (
                    "Validated sales decline evidence."
                ),
            },
            {
                "source": "inventory",
                "finding_id": (
                    "INVENTORY-HIGH-001"
                ),
                "analysis_type": "Low Stock",
                "business_area": "Operations",
                "severity": "High",
                "entity_type": "Inventory",
                "entity_id": "S003-P017",
                "summary": (
                    "Product P017 has low stock."
                ),
                "evidence": (
                    "Validated inventory evidence."
                ),
            },
            {
                "source": "inventory",
                "finding_id": (
                    "INVENTORY-MEDIUM-001"
                ),
                "analysis_type": "Reorder Soon",
                "business_area": "Operations",
                "severity": "Medium",
                "entity_type": "Inventory",
                "entity_id": "S003-P018",
                "summary": (
                    "Product P018 should be reordered."
                ),
                "evidence": (
                    "Validated reorder evidence."
                ),
            },
        ],
    }


class FailingMonitoringProvider(
    MockLLMProvider
):
    """Raise one controlled provider timeout."""

    async def _generate_once(
        self,
        request: LLMRequest,
    ) -> Any:
        del request

        raise LLMTimeoutError(
            "Simulated Monitoring Agent timeout."
        )


def test_monitoring_agent_preserves_deterministic_mode(
    monkeypatch: Any,
) -> None:
    """Disabled LLM execution should not change deterministic output."""

    deterministic_output = (
        build_deterministic_output()
    )

    monkeypatch.setattr(
        monitoring_module,
        "build_deterministic_monitoring_output",
        lambda context: dict(
            deterministic_output
        ),
    )

    agent = MonitoringAgent(
        llm_provider=MockLLMProvider(
            build_mock_config(
                enabled=False
            )
        )
    )

    result = asyncio.run(
        agent.execute(
            AgentContext(
                run_type=(
                    "monitoring-llm-disabled-test"
                )
            )
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert result.used_fallback is False
    assert result.agent_version == "1.1.0"
    assert (
        result.summary
        == deterministic_output["summary"]
    )
    assert (
        "llm_enhancement"
        not in result.output_data
    )
    assert result.model_provider is None
    assert result.prompt_name is None
    assert result.input_tokens is None


def test_monitoring_agent_adds_grounded_llm_enhancement(
    monkeypatch: Any,
) -> None:
    """Enabled mock execution should add validated enhancement data."""

    deterministic_output = (
        build_deterministic_output()
    )

    monkeypatch.setattr(
        monitoring_module,
        "build_deterministic_monitoring_output",
        lambda context: dict(
            deterministic_output
        ),
    )

    agent = MonitoringAgent(
        llm_provider=MockLLMProvider(
            build_mock_config()
        )
    )

    result = asyncio.run(
        agent.execute(
            AgentContext(
                run_type=(
                    "monitoring-llm-success-test"
                )
            )
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
        == "monitoring_summary"
    )
    assert result.prompt_version == "v1"
    assert result.input_tokens is not None
    assert result.output_tokens is not None
    assert (
        result.total_tokens
        == (
            result.input_tokens
            + result.output_tokens
        )
    )
    assert result.estimated_cost_usd == 0.0
    assert result.llm_latency_ms is not None

    output_data = result.output_data

    assert (
        output_data["finding_totals"]
        == deterministic_output[
            "finding_totals"
        ]
    )

    assert (
        output_data["kpi_snapshot"]
        == deterministic_output[
            "kpi_snapshot"
        ]
    )

    enhancement = output_data[
        "llm_enhancement"
    ]

    assert (
        enhancement["status"]
        == "Complete"
    )
    assert (
        enhancement["schema_name"]
        == "MonitoringSummaryV1"
    )
    assert (
        enhancement[
            "business_health_status"
        ]
        == "At Risk"
    )
    assert (
        enhancement[
            "confidence_score"
        ]
        == 95.0
    )
    assert set(
        enhancement[
            "evidence_ids"
        ]
    ) == {
        "SALES-HIGH-001",
        "INVENTORY-HIGH-001",
        "INVENTORY-MEDIUM-001",
    }

    assert (
        "_execution_metadata"
        not in output_data
    )


def test_monitoring_agent_uses_deterministic_fallback(
    monkeypatch: Any,
) -> None:
    """An LLM failure should retain the deterministic snapshot."""

    deterministic_output = (
        build_deterministic_output()
    )

    monkeypatch.setattr(
        monitoring_module,
        "build_deterministic_monitoring_output",
        lambda context: dict(
            deterministic_output
        ),
    )

    agent = MonitoringAgent(
        llm_provider=(
            FailingMonitoringProvider(
                build_mock_config()
            )
        )
    )

    result = asyncio.run(
        agent.execute(
            AgentContext(
                run_type=(
                    "monitoring-llm-fallback-test"
                )
            )
        )
    )

    assert (
        result.execution_status
        == AgentExecutionStatus.SUCCESS
    )

    assert result.used_fallback is True
    assert result.error_type == "LLMTimeoutError"
    assert (
        result.error_message
        == (
            "Simulated Monitoring Agent timeout."
        )
    )
    assert (
        result.llm_error_type
        == "LLMTimeoutError"
    )
    assert (
        result.llm_error_message
        == (
            "Simulated Monitoring Agent timeout."
        )
    )

    assert (
        result.summary
        == deterministic_output["summary"]
    )

    assert (
        result.output_data[
            "finding_totals"
        ]
        == deterministic_output[
            "finding_totals"
        ]
    )

    assert (
        result.output_data[
            "llm_enhancement"
        ]["status"]
        == "Fallback"
    )

    assert result.model_provider == "mock"
    assert (
        result.prompt_name
        == "monitoring_summary"
    )
    assert result.prompt_version == "v1"
    assert result.input_tokens is None


def test_shared_enhancement_rejects_unsupported_evidence(
) -> None:
    """LLM output cannot cite identifiers absent from its context."""

    provider = MockLLMProvider(
        build_mock_config()
    )

    with pytest.raises(
        LLMProviderResponseError,
        match=(
            "unsupported evidence identifiers"
        ),
    ):
        asyncio.run(
            run_structured_enhancement(
                provider=provider,
                agent_name="Monitoring Agent",
                agent_version="1.1.0",
                prompt_name=(
                    "monitoring_summary"
                ),
                prompt_version="v1",
                validated_context={
                    "top_findings": [
                        {
                            "finding_id": (
                                "VALID-EVIDENCE-001"
                            ),
                        }
                    ]
                },
                response_model=(
                    MonitoringSummaryV1
                ),
                allowed_evidence_ids=[
                    "VALID-EVIDENCE-001",
                ],
                mock_structured_output={
                    "summary": (
                        "Controlled monitoring summary."
                    ),
                    "business_health_status": (
                        "At Risk"
                    ),
                    "attention_areas": [
                        {
                            "business_area": (
                                "Sales"
                            ),
                            "urgency": "High",
                            "reason": (
                                "Controlled reason."
                            ),
                            "evidence_ids": [
                                "INVENTED-EVIDENCE-999",
                            ],
                        }
                    ],
                    "evidence_ids": [
                        "INVENTED-EVIDENCE-999",
                    ],
                    "confidence_score": 80.0,
                    "missing_evidence_warnings": [],
                },
            )
        )