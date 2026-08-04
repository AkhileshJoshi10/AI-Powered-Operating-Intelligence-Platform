from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import backend.app.routers.chief_of_staff as router_module
import backend.app.services.chief_of_staff_service as service_module
from backend.app.agents import AgentExecutionStatus
from backend.app.schemas.chief_of_staff import ChiefOfStaffRunRequest


AGENT_SEQUENCE = [
    "Monitoring Agent",
    "Priority Agent",
    "Root-Cause Agent",
    "Recommendation Agent",
    "Executive Brief Agent",
]


class FakeWorkflowResult:
    """Controlled agent result used by workflow-service tests."""

    def __init__(
        self,
        *,
        run_id: str,
        agent_name: str,
        execution_status: AgentExecutionStatus,
        log_persisted: bool = True,
        logging_error: str | None = None,
        agent_run_id: int | None = None,
    ) -> None:
        self.run_id = run_id
        self.agent_name = agent_name
        self.run_type = service_module.CHIEF_OF_STAFF_RUN_TYPE
        self.execution_status = execution_status
        self.summary = f"{agent_name} controlled result."
        self.output_data = {"agent_name": agent_name}
        self.used_fallback = False
        self.error_type = (
            "RuntimeError"
            if execution_status == AgentExecutionStatus.FAILED
            else None
        )
        self.error_message = (
            "Controlled agent failure."
            if execution_status == AgentExecutionStatus.FAILED
            else None
        )
        self.started_at = datetime(
            2026,
            8,
            5,
            1,
            0,
            tzinfo=timezone.utc,
        )
        self.completed_at = datetime(
            2026,
            8,
            5,
            1,
            0,
            1,
            tzinfo=timezone.utc,
        )
        self.duration_ms = 1000.0
        self.agent_run_id = agent_run_id
        self.log_persisted = log_persisted
        self.logging_error = logging_error

    def model_dump(
        self,
        *,
        mode: str,
    ) -> dict[str, Any]:
        """Return response-schema-compatible data."""

        assert mode == "json"

        return {
            "run_id": self.run_id,
            "agent_name": self.agent_name,
            "run_type": self.run_type,
            "execution_status": self.execution_status.value,
            "summary": self.summary,
            "output_data": self.output_data,
            "used_fallback": self.used_fallback,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_ms": self.duration_ms,
            "agent_run_id": self.agent_run_id,
            "log_persisted": self.log_persisted,
            "logging_error": self.logging_error,
        }


class FakeWorkflowOrchestrator:
    """Capture workflow-service sequence arguments."""

    def __init__(
        self,
        results: list[FakeWorkflowResult],
    ) -> None:
        self.results = results
        self.agent_names: list[str] | None = None
        self.context: Any = None
        self.stop_on_failure: bool | None = None

    async def run_sequence(
        self,
        *,
        agent_names: list[str],
        context: Any,
        stop_on_failure: bool,
    ) -> list[FakeWorkflowResult]:
        self.agent_names = list(agent_names)
        self.context = context
        self.stop_on_failure = stop_on_failure

        return self.results


def build_fake_results(
    *,
    run_id: str,
    failed_agent_name: str | None = None,
    result_count: int = 5,
    logging_failure_agent: str | None = None,
) -> list[FakeWorkflowResult]:
    """Build controlled workflow results in canonical order."""

    results = []

    for index, agent_name in enumerate(
        AGENT_SEQUENCE[:result_count],
        start=1,
    ):
        execution_status = (
            AgentExecutionStatus.FAILED
            if agent_name == failed_agent_name
            else AgentExecutionStatus.SUCCESS
        )

        has_logging_failure = (
            agent_name == logging_failure_agent
        )

        results.append(
            FakeWorkflowResult(
                run_id=run_id,
                agent_name=agent_name,
                execution_status=execution_status,
                log_persisted=not has_logging_failure,
                logging_error=(
                    "Controlled logging failure."
                    if has_logging_failure
                    else None
                ),
                agent_run_id=(
                    None
                    if has_logging_failure
                    else index
                ),
            )
        )

    return results


@pytest.mark.parametrize(
    (
        "completed_agent_count",
        "failed_agent_count",
        "expected_status",
    ),
    [
        pytest.param(5, 0, "Complete", id="complete"),
        pytest.param(5, 1, "Partial", id="partial"),
        pytest.param(3, 1, "Failed", id="stopped-early"),
        pytest.param(4, 0, "Failed", id="incomplete"),
    ],
)
def test_determine_workflow_status(
    completed_agent_count: int,
    failed_agent_count: int,
    expected_status: str,
) -> None:
    """Workflow status should reflect completion and failures."""

    assert (
        service_module.determine_workflow_status(
            completed_agent_count=completed_agent_count,
            failed_agent_count=failed_agent_count,
        )
        == expected_status
    )


def test_workflow_service_returns_complete_result(
    monkeypatch: Any,
) -> None:
    """Five successful agents should produce a Complete workflow."""

    fake_orchestrator = FakeWorkflowOrchestrator(
        build_fake_results(
            run_id="workflow-run-complete",
        )
    )

    monkeypatch.setattr(
        service_module,
        "build_chief_of_staff_orchestrator",
        lambda: fake_orchestrator,
    )

    request = ChiefOfStaffRunRequest(
        requested_by="Operations Manager",
        issue_ids=["ISSUE-HIGH-001"],
        finding_limit=12,
        manager_limit=20,
        executive_limit=8,
        analysis_limit=8,
        recommendation_limit=8,
        stop_on_failure=True,
    )

    response_data = asyncio.run(
        service_module.run_chief_of_staff_workflow(
            request
        )
    )

    assert response_data["workflow_status"] == "Complete"
    assert response_data["run_type"] == "chief-of-staff-workflow"
    assert response_data["requested_by"] == "Operations Manager"
    assert response_data["agent_sequence"] == AGENT_SEQUENCE

    assert response_data["workflow_summary"] == {
        "total_agents": 5,
        "completed_agents": 5,
        "successful_agents": 5,
        "failed_agents": 0,
        "skipped_agents": 0,
        "stopped_early": False,
        "failed_agent_name": None,
        "persisted_agent_logs": 5,
        "logging_failures": 0,
    }

    assert len(response_data["results"]) == 5
    assert fake_orchestrator.agent_names == AGENT_SEQUENCE
    assert fake_orchestrator.stop_on_failure is True

    context = fake_orchestrator.context

    assert context.issue_ids == ["ISSUE-HIGH-001"]
    assert context.input_data == {
        "finding_limit": 12,
        "manager_limit": 20,
        "executive_limit": 8,
        "analysis_limit": 8,
        "recommendation_limit": 8,
    }
    assert context.metadata == {
        "workflow_name": "AI Chief of Staff",
        "trigger_source": "FastAPI",
    }


def test_workflow_service_reports_stopped_early_failure(
    monkeypatch: Any,
) -> None:
    """A stopped sequence should identify its failed agent."""

    fake_orchestrator = FakeWorkflowOrchestrator(
        build_fake_results(
            run_id="workflow-run-failed",
            failed_agent_name="Root-Cause Agent",
            result_count=3,
        )
    )

    monkeypatch.setattr(
        service_module,
        "build_chief_of_staff_orchestrator",
        lambda: fake_orchestrator,
    )

    response_data = asyncio.run(
        service_module.run_chief_of_staff_workflow(
            ChiefOfStaffRunRequest(
                stop_on_failure=True
            )
        )
    )

    assert response_data["workflow_status"] == "Failed"
    assert response_data["workflow_summary"] == {
        "total_agents": 5,
        "completed_agents": 3,
        "successful_agents": 2,
        "failed_agents": 1,
        "skipped_agents": 0,
        "stopped_early": True,
        "failed_agent_name": "Root-Cause Agent",
        "persisted_agent_logs": 3,
        "logging_failures": 0,
    }


def test_workflow_service_returns_partial_when_execution_continues(
    monkeypatch: Any,
) -> None:
    """A full sequence containing a failure should be Partial."""

    fake_orchestrator = FakeWorkflowOrchestrator(
        build_fake_results(
            run_id="workflow-run-partial",
            failed_agent_name="Priority Agent",
        )
    )

    monkeypatch.setattr(
        service_module,
        "build_chief_of_staff_orchestrator",
        lambda: fake_orchestrator,
    )

    response_data = asyncio.run(
        service_module.run_chief_of_staff_workflow(
            ChiefOfStaffRunRequest(
                stop_on_failure=False
            )
        )
    )

    assert response_data["workflow_status"] == "Partial"
    assert response_data["workflow_summary"]["completed_agents"] == 5
    assert response_data["workflow_summary"]["failed_agents"] == 1
    assert response_data["workflow_summary"]["stopped_early"] is False
    assert fake_orchestrator.stop_on_failure is False


def test_workflow_service_reports_logging_failure_without_failing_run(
    monkeypatch: Any,
) -> None:
    """Agent-log failure should not replace successful execution."""

    fake_orchestrator = FakeWorkflowOrchestrator(
        build_fake_results(
            run_id="workflow-run-logging-failure",
            logging_failure_agent="Recommendation Agent",
        )
    )

    monkeypatch.setattr(
        service_module,
        "build_chief_of_staff_orchestrator",
        lambda: fake_orchestrator,
    )

    response_data = asyncio.run(
        service_module.run_chief_of_staff_workflow(
            ChiefOfStaffRunRequest()
        )
    )

    assert response_data["workflow_status"] == "Complete"
    assert (
        response_data["workflow_summary"]["persisted_agent_logs"]
        == 4
    )
    assert (
        response_data["workflow_summary"]["logging_failures"]
        == 1
    )


def build_api_workflow_response(
    *,
    request: ChiefOfStaffRunRequest,
) -> dict[str, Any]:
    """Build one valid router response."""

    run_id = "api-workflow-run-001"

    results = [
        FakeWorkflowResult(
            run_id=run_id,
            agent_name=agent_name,
            execution_status=AgentExecutionStatus.SUCCESS,
            agent_run_id=index,
        ).model_dump(mode="json")
        for index, agent_name in enumerate(
            AGENT_SEQUENCE,
            start=1,
        )
    ]

    return {
        "status": "success",
        "workflow_status": "Complete",
        "run_id": run_id,
        "run_type": "chief-of-staff-workflow",
        "requested_by": request.requested_by,
        "started_at": "2026-08-05T01:00:00+00:00",
        "completed_at": "2026-08-05T01:00:05+00:00",
        "duration_ms": 5000.0,
        "agent_sequence": AGENT_SEQUENCE,
        "workflow_summary": {
            "total_agents": 5,
            "completed_agents": 5,
            "successful_agents": 5,
            "failed_agents": 0,
            "skipped_agents": 0,
            "stopped_early": False,
            "failed_agent_name": None,
            "persisted_agent_logs": 5,
            "logging_failures": 0,
        },
        "results": results,
    }


def test_chief_of_staff_api_returns_complete_workflow(
    client: Any,
    monkeypatch: Any,
) -> None:
    """The API should return the validated workflow response."""

    captured_request: dict[str, Any] = {}

    async def mock_run_workflow(
        request: ChiefOfStaffRunRequest,
    ) -> dict[str, Any]:
        captured_request["request"] = request
        return build_api_workflow_response(
            request=request
        )

    monkeypatch.setattr(
        router_module,
        "run_chief_of_staff_workflow",
        mock_run_workflow,
    )

    response = client.post(
        "/api/chief-of-staff/run",
        json={
            "requested_by": "Test Manager",
            "finding_limit": 15,
            "manager_limit": 20,
            "executive_limit": 8,
            "analysis_limit": 8,
            "recommendation_limit": 8,
            "stop_on_failure": True,
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["workflow_status"] == "Complete"
    assert response_data["requested_by"] == "Test Manager"
    assert response_data["agent_sequence"] == AGENT_SEQUENCE
    assert (
        response_data["workflow_summary"]["persisted_agent_logs"]
        == 5
    )
    assert len(response_data["results"]) == 5
    assert {
        result["run_id"]
        for result in response_data["results"]
    } == {response_data["run_id"]}

    captured = captured_request["request"]
    assert captured.finding_limit == 15
    assert captured.manager_limit == 20
    assert captured.executive_limit == 8
    assert captured.analysis_limit == 8
    assert captured.recommendation_limit == 8


def test_chief_of_staff_api_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A workflow database failure should return HTTP 503."""

    async def raise_database_failure(
        request: ChiefOfStaffRunRequest,
    ) -> dict[str, Any]:
        del request
        raise SQLAlchemyError(
            "Controlled workflow database failure."
        )

    monkeypatch.setattr(
        router_module,
        "run_chief_of_staff_workflow",
        raise_database_failure,
    )

    response = client.post(
        "/api/chief-of-staff/run",
        json={},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "The Chief of Staff workflow could not run "
            "because a database operation failed."
        )
    }


@pytest.mark.parametrize(
    "exception_type",
    [
        pytest.param(KeyError, id="key-error"),
        pytest.param(TypeError, id="type-error"),
        pytest.param(ValueError, id="value-error"),
    ],
)
def test_chief_of_staff_api_returns_500_on_processing_failure(
    client: Any,
    monkeypatch: Any,
    exception_type: type[Exception],
) -> None:
    """Invalid internal workflow results should return HTTP 500."""

    async def raise_processing_failure(
        request: ChiefOfStaffRunRequest,
    ) -> dict[str, Any]:
        del request
        raise exception_type(
            "Controlled workflow processing failure."
        )

    monkeypatch.setattr(
        router_module,
        "run_chief_of_staff_workflow",
        raise_processing_failure,
    )

    response = client.post(
        "/api/chief-of-staff/run",
        json={},
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": (
            "The Chief of Staff workflow could not be "
            "processed because its internal result was invalid."
        )
    }


@pytest.mark.parametrize(
    "request_body",
    [
        pytest.param(
            {"requested_by": ""},
            id="empty-requested-by",
        ),
        pytest.param(
            {"finding_limit": 0},
            id="invalid-finding-limit",
        ),
        pytest.param(
            {"manager_limit": 101},
            id="invalid-manager-limit",
        ),
        pytest.param(
            {"executive_limit": 51},
            id="invalid-executive-limit",
        ),
        pytest.param(
            {"analysis_limit": 0},
            id="invalid-analysis-limit",
        ),
        pytest.param(
            {"recommendation_limit": 51},
            id="invalid-recommendation-limit",
        ),
        pytest.param(
            {
                "issue_ids": [
                    f"ISSUE-{index:03d}"
                    for index in range(51)
                ],
            },
            id="too-many-issue-ids",
        ),
    ],
)
def test_chief_of_staff_api_rejects_invalid_request(
    client: Any,
    request_body: dict[str, Any],
) -> None:
    """Pydantic request validation should return HTTP 422."""

    response = client.post(
        "/api/chief-of-staff/run",
        json=request_body,
    )

    assert response.status_code == 422


@pytest.mark.integration
def test_chief_of_staff_api_runs_seeded_workflow(
    client: Any,
    test_engine: Any,
) -> None:
    """The real endpoint should run and log all five agents."""

    with test_engine.connect() as connection:
        actual_database = connection.execute(
            text(
                "SELECT current_database();"
            )
        ).scalar_one()

        reviewed_before = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM recommendations
                WHERE status IN (
                    'Accepted',
                    'Edited',
                    'Converted to Task'
                );
                """
            )
        ).scalar_one()

        task_count_before = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM tasks;
                """
            )
        ).scalar_one()

    assert (
        actual_database
        == "ai_operating_intelligence_test"
    )

    response = client.post(
        "/api/chief-of-staff/run",
        json={
            "requested_by": "pytest",
            "finding_limit": 10,
            "manager_limit": 15,
            "executive_limit": 10,
            "analysis_limit": 10,
            "recommendation_limit": 10,
            "stop_on_failure": True,
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert (
        response_data["workflow_status"]
        == "Complete"
    )
    assert (
        response_data["run_type"]
        == "chief-of-staff-workflow"
    )
    assert (
        response_data["agent_sequence"]
        == AGENT_SEQUENCE
    )

    assert response_data[
        "workflow_summary"
    ] == {
        "total_agents": 5,
        "completed_agents": 5,
        "successful_agents": 5,
        "failed_agents": 0,
        "skipped_agents": 0,
        "stopped_early": False,
        "failed_agent_name": None,
        "persisted_agent_logs": 5,
        "logging_failures": 0,
    }

    results = response_data["results"]

    assert [
        result["agent_name"]
        for result in results
    ] == AGENT_SEQUENCE

    assert all(
        result["execution_status"] == "Success"
        for result in results
    )
    assert all(
        result["run_id"] == response_data["run_id"]
        for result in results
    )
    assert all(
        result["log_persisted"] is True
        for result in results
    )

    agent_run_ids = [
        int(result["agent_run_id"])
        for result in results
    ]

    try:
        with test_engine.connect() as connection:
            stored_agent_runs = connection.execute(
                text(
                    """
                    SELECT
                        agent_run_id,
                        agent_name,
                        run_type,
                        execution_status
                    FROM agent_runs
                    WHERE agent_run_id = ANY(:agent_run_ids)
                    ORDER BY agent_run_id;
                    """
                ),
                {
                    "agent_run_ids": agent_run_ids,
                },
            ).mappings().all()

            reviewed_after = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM recommendations
                    WHERE status IN (
                        'Accepted',
                        'Edited',
                        'Converted to Task'
                    );
                    """
                )
            ).scalar_one()

            task_count_after = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM tasks;
                    """
                )
            ).scalar_one()

            daily_brief_count = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM executive_briefs
                    WHERE
                        brief_date = :brief_date
                        AND brief_type = :brief_type;
                    """
                ),
                {
                    "brief_date": date.today(),
                    "brief_type": "Daily Executive Brief",
                },
            ).scalar_one()

        assert len(stored_agent_runs) == 5

        assert {
            row["agent_name"]
            for row in stored_agent_runs
        } == set(AGENT_SEQUENCE)

        assert all(
            row["run_type"] == "chief-of-staff-workflow"
            for row in stored_agent_runs
        )
        assert all(
            row["execution_status"] == "Success"
            for row in stored_agent_runs
        )

        assert reviewed_after == reviewed_before
        assert task_count_after == task_count_before
        assert daily_brief_count == 1

        recommendation_result = next(
            result
            for result in results
            if result["agent_name"]
            == "Recommendation Agent"
        )

        assert (
            recommendation_result[
                "output_data"
            ]["human_review"]["required"]
            is True
        )
        assert (
            recommendation_result[
                "output_data"
            ]["human_review"]["allowed_actions"]
            == [
                "Accept",
                "Edit",
                "Reject",
            ]
        )

    finally:
        with test_engine.begin() as connection:
            connection.execute(
                text(
                    """
                    DELETE FROM agent_runs
                    WHERE agent_run_id = ANY(:agent_run_ids);
                    """
                ),
                {
                    "agent_run_ids": agent_run_ids,
                },
            )
