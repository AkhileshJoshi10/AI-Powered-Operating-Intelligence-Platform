from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any

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
from backend.app.db.database import engine
from backend.app.schemas.chief_of_staff import (
    ChiefOfStaffRunRequest,
)


CHIEF_OF_STAFF_RUN_TYPE = (
    "chief-of-staff-workflow"
)


CHIEF_OF_STAFF_AGENT_SEQUENCE = [
    "Monitoring Agent",
    "Priority Agent",
    "Root-Cause Agent",
    "Recommendation Agent",
    "Executive Brief Agent",
]


def current_utc_time() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(
        timezone.utc
    )


def build_chief_of_staff_orchestrator(
) -> AgentOrchestrator:
    """Register the deterministic Chief of Staff agents."""

    return AgentOrchestrator(
        agents=[
            MonitoringAgent(),
            PriorityAgent(),
            RootCauseAgent(),
            RecommendationAgent(),
            ExecutiveBriefAgent(),
        ],
        run_logger=PostgresAgentRunLogger(
            engine
        ),
    )


def determine_workflow_status(
    *,
    completed_agent_count: int,
    failed_agent_count: int,
) -> str:
    """Determine the overall workflow completion status."""

    expected_agent_count = len(
        CHIEF_OF_STAFF_AGENT_SEQUENCE
    )

    if (
        failed_agent_count == 0
        and completed_agent_count
        == expected_agent_count
    ):
        return "Complete"

    if (
        completed_agent_count
        < expected_agent_count
    ):
        return "Failed"

    return "Partial"


async def run_chief_of_staff_workflow(
    request: ChiefOfStaffRunRequest,
) -> dict[str, Any]:
    """Run the complete deterministic Chief of Staff workflow."""

    started_at = current_utc_time()
    performance_start = perf_counter()

    context = AgentContext(
        run_type=CHIEF_OF_STAFF_RUN_TYPE,
        requested_by=request.requested_by,
        issue_ids=request.issue_ids,
        input_data={
            "finding_limit": (
                request.finding_limit
            ),
            "manager_limit": (
                request.manager_limit
            ),
            "executive_limit": (
                request.executive_limit
            ),
            "analysis_limit": (
                request.analysis_limit
            ),
            "recommendation_limit": (
                request.recommendation_limit
            ),
        },
        metadata={
            "workflow_name": (
                "AI Chief of Staff"
            ),
            "trigger_source": "FastAPI",
        },
    )

    orchestrator = (
        build_chief_of_staff_orchestrator()
    )

    results = await orchestrator.run_sequence(
        agent_names=(
            CHIEF_OF_STAFF_AGENT_SEQUENCE
        ),
        context=context,
        stop_on_failure=request.stop_on_failure,
    )

    completed_at = current_utc_time()

    duration_ms = round(
        (
            perf_counter()
            - performance_start
        )
        * 1000,
        2,
    )

    successful_results = [
        result
        for result in results
        if (
            result.execution_status
            == AgentExecutionStatus.SUCCESS
        )
    ]

    failed_results = [
        result
        for result in results
        if (
            result.execution_status
            == AgentExecutionStatus.FAILED
        )
    ]

    skipped_results = [
        result
        for result in results
        if (
            result.execution_status
            == AgentExecutionStatus.SKIPPED
        )
    ]

    persisted_agent_logs = sum(
        1
        for result in results
        if result.log_persisted
    )

    logging_failures = sum(
        1
        for result in results
        if result.logging_error is not None
    )

    failed_agent_name = (
        failed_results[0].agent_name
        if failed_results
        else None
    )

    workflow_status = (
        determine_workflow_status(
            completed_agent_count=len(
                results
            ),
            failed_agent_count=len(
                failed_results
            ),
        )
    )

    return {
        "status": "success",
        "workflow_status": (
            workflow_status
        ),
        "run_id": context.run_id,
        "run_type": context.run_type,
        "requested_by": (
            context.requested_by
        ),
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "agent_sequence": (
            CHIEF_OF_STAFF_AGENT_SEQUENCE
        ),
        "workflow_summary": {
            "total_agents": len(
                CHIEF_OF_STAFF_AGENT_SEQUENCE
            ),
            "completed_agents": len(
                results
            ),
            "successful_agents": len(
                successful_results
            ),
            "failed_agents": len(
                failed_results
            ),
            "skipped_agents": len(
                skipped_results
            ),
            "stopped_early": (
                len(results)
                < len(
                    CHIEF_OF_STAFF_AGENT_SEQUENCE
                )
            ),
            "failed_agent_name": (
                failed_agent_name
            ),
            "persisted_agent_logs": (
                persisted_agent_logs
            ),
            "logging_failures": (
                logging_failures
            ),
        },
        "results": [
            result.model_dump(
                mode="json"
            )
            for result in results
        ],
    }