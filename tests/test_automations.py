from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.services.automation_service import (
    record_n8n_callback,
)
from backend.app.services.n8n_client import (
    N8NClient,
    N8NClientConfigurationError,
    N8NClientError,
)


SAMPLE_AUTOMATION_LOG = {
    "automation_log_id": 301,
    "task_id": 201,
    "issue_id": "ISSUE-SALES-S003-2026-06",
    "workflow_name": "Task Reminder",
    "action_type": "task_reminder",
    "execution_status": "Triggered",
    "idempotency_key": (
        "automation-0123456789abcdef0123456789abcdef"
    ),
    "n8n_execution_id": "n8n-901",
    "attempt_count": 1,
    "http_status_code": 200,
    "message": "Workflow request accepted by n8n.",
    "error_type": None,
    "error_message": None,
    "request_metadata": {
        "source": "FastAPI",
        "payload_version": "v1",
    },
    "executed_at": "2026-09-02T10:00:00",
}


def test_automation_log_migration_columns_exist(
    test_engine: Any,
) -> None:
    """The test database must receive the automation foundation migration."""

    expected_columns = {
        "automation_log_id",
        "task_id",
        "issue_id",
        "workflow_name",
        "action_type",
        "execution_status",
        "idempotency_key",
        "n8n_execution_id",
        "attempt_count",
        "http_status_code",
        "message",
        "error_type",
        "error_message",
        "request_metadata",
        "executed_at",
    }

    with test_engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'automation_logs';
                """
            )
        ).scalars().all()

    assert expected_columns.issubset(
        set(rows)
    )



def test_record_n8n_callback_is_idempotent_in_test_database(
    test_engine: Any,
) -> None:
    """A terminal callback cannot be duplicated or overwritten."""

    idempotency_key = (
        "automation-pytest-callback-idempotency-0001"
    )

    with test_engine.begin() as connection:
        connection.execute(
            text(
                """
                DELETE FROM automation_logs
                WHERE idempotency_key = :idempotency_key;
                """
            ),
            {
                "idempotency_key": idempotency_key,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO automation_logs (
                    workflow_name,
                    action_type,
                    execution_status,
                    idempotency_key,
                    request_metadata
                )
                VALUES (
                    'Pytest Callback',
                    'pytest_callback',
                    'Triggered',
                    :idempotency_key,
                    '{}'::JSONB
                );
                """
            ),
            {
                "idempotency_key": idempotency_key,
            },
        )

    try:
        first = record_n8n_callback(
            idempotency_key=idempotency_key,
            execution_status="Succeeded",
            n8n_execution_id="n8n-pytest-1",
            message="Completed.",
            error_type=None,
            error_message=None,
        )

        assert first[
            "outcome"
        ] == "success"
        assert first[
            "response"
        ][
            "automation_log"
        ][
            "execution_status"
        ] == "Succeeded"

        duplicate = record_n8n_callback(
            idempotency_key=idempotency_key,
            execution_status="Succeeded",
            n8n_execution_id="n8n-pytest-1",
            message="Completed again.",
            error_type=None,
            error_message=None,
        )

        assert duplicate[
            "outcome"
        ] == "duplicate"
        assert duplicate[
            "response"
        ][
            "duplicate"
        ] is True

        conflict = record_n8n_callback(
            idempotency_key=idempotency_key,
            execution_status="Failed",
            n8n_execution_id="n8n-pytest-2",
            message="Late conflicting callback.",
            error_type="LateFailure",
            error_message="Must not overwrite success.",
        )

        assert conflict == {
            "outcome": "conflict",
            "current_status": "Succeeded",
        }

    finally:
        with test_engine.begin() as connection:
            connection.execute(
                text(
                    """
                    DELETE FROM automation_logs
                    WHERE idempotency_key = :idempotency_key;
                    """
                ),
                {
                    "idempotency_key": idempotency_key,
                },
            )

def test_list_automation_logs_returns_paginated_response(
    client: Any,
    monkeypatch: Any,
) -> None:
    captured: dict[str, Any] = {}

    def mock_get_automation_log_list(
        **kwargs: Any,
    ) -> dict[str, Any]:
        captured.update(
            kwargs
        )

        return {
            "status": "success",
            "total_items": 1,
            "limit": kwargs[
                "limit"
            ],
            "offset": kwargs[
                "offset"
            ],
            "items": [
                SAMPLE_AUTOMATION_LOG
            ],
        }

    monkeypatch.setattr(
        "backend.app.routers.automations."
        "get_automation_log_list",
        mock_get_automation_log_list,
    )

    response = client.get(
        "/api/automation-logs",
        params={
            "status": "Triggered",
            "action_type": "task_reminder",
            "workflow_name": "Task Reminder",
            "task_id": 201,
            "issue_id": "ISSUE-SALES-S003-2026-06",
            "limit": 10,
            "offset": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()[
        "items"
    ][0][
        "automation_log_id"
    ] == 301
    assert captured == {
        "execution_status": "Triggered",
        "action_type": "task_reminder",
        "workflow_name": "Task Reminder",
        "task_id": 201,
        "issue_id": "ISSUE-SALES-S003-2026-06",
        "limit": 10,
        "offset": 5,
    }


@pytest.mark.parametrize(
    "params",
    [
        {"task_id": 0},
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"issue_id": "A"},
    ],
)
def test_list_automation_logs_rejects_invalid_filters(
    client: Any,
    params: dict[str, Any],
) -> None:
    response = client.get(
        "/api/automation-logs",
        params=params,
    )

    assert response.status_code == 422


def test_list_automation_logs_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    def fail(
        **_: Any,
    ) -> dict[str, Any]:
        raise SQLAlchemyError(
            "Simulated automation log failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.automations."
        "get_automation_log_list",
        fail,
    )

    response = client.get(
        "/api/automation-logs"
    )

    assert response.status_code == 503


def test_get_automation_log_returns_detail(
    client: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "backend.app.routers.automations."
        "get_automation_log_detail",
        lambda automation_log_id: {
            "status": "success",
            "automation_log": {
                **SAMPLE_AUTOMATION_LOG,
                "automation_log_id": automation_log_id,
            },
        },
    )

    response = client.get(
        "/api/automation-logs/301"
    )

    assert response.status_code == 200
    assert response.json()[
        "automation_log"
    ][
        "automation_log_id"
    ] == 301


def test_get_automation_log_returns_404_when_missing(
    client: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "backend.app.routers.automations."
        "get_automation_log_detail",
        lambda automation_log_id: None,
    )

    response = client.get(
        "/api/automation-logs/999"
    )

    assert response.status_code == 404


def test_callback_rejects_when_secret_not_configured(
    client: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "backend.app.routers.automations.settings",
        SimpleNamespace(
            n8n_callback_secret="",
        ),
    )

    response = client.post(
        "/api/automations/log",
        json={
            "idempotency_key": (
                "automation-0123456789abcdef"
            ),
            "execution_status": "Succeeded",
        },
    )

    assert response.status_code == 503


def test_callback_rejects_invalid_secret(
    client: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "backend.app.routers.automations.settings",
        SimpleNamespace(
            n8n_callback_secret="correct-secret",
        ),
    )

    response = client.post(
        "/api/automations/log",
        headers={
            "X-N8N-Callback-Secret": "wrong-secret",
        },
        json={
            "idempotency_key": (
                "automation-0123456789abcdef"
            ),
            "execution_status": "Succeeded",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid n8n callback credentials."
    }


def test_callback_records_authenticated_result(
    client: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "backend.app.routers.automations.settings",
        SimpleNamespace(
            n8n_callback_secret="correct-secret",
        ),
    )

    captured: dict[str, Any] = {}

    def mock_record_n8n_callback(
        **kwargs: Any,
    ) -> dict[str, Any]:
        captured.update(
            kwargs
        )

        return {
            "outcome": "success",
            "response": {
                "status": "success",
                "message": (
                    "The automation execution result was recorded."
                ),
                "duplicate": False,
                "automation_log": {
                    **SAMPLE_AUTOMATION_LOG,
                    "execution_status": "Succeeded",
                },
            },
        }

    monkeypatch.setattr(
        "backend.app.routers.automations."
        "record_n8n_callback",
        mock_record_n8n_callback,
    )

    response = client.post(
        "/api/automations/log",
        headers={
            "X-N8N-Callback-Secret": "correct-secret",
        },
        json={
            "idempotency_key": (
                "automation-0123456789abcdef"
            ),
            "execution_status": "Succeeded",
            "n8n_execution_id": "n8n-901",
            "message": "Workflow completed.",
        },
    )

    assert response.status_code == 200
    assert response.json()[
        "automation_log"
    ][
        "execution_status"
    ] == "Succeeded"
    assert captured[
        "idempotency_key"
    ] == "automation-0123456789abcdef"


def test_callback_rejects_unknown_idempotency_key(
    client: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "backend.app.routers.automations.settings",
        SimpleNamespace(
            n8n_callback_secret="correct-secret",
        ),
    )
    monkeypatch.setattr(
        "backend.app.routers.automations."
        "record_n8n_callback",
        lambda **kwargs: {
            "outcome": "not_found",
        },
    )

    response = client.post(
        "/api/automations/log",
        headers={
            "X-N8N-Callback-Secret": "correct-secret",
        },
        json={
            "idempotency_key": (
                "automation-0123456789abcdef"
            ),
            "execution_status": "Succeeded",
        },
    )

    assert response.status_code == 404


def test_callback_rejects_conflicting_terminal_update(
    client: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "backend.app.routers.automations.settings",
        SimpleNamespace(
            n8n_callback_secret="correct-secret",
        ),
    )
    monkeypatch.setattr(
        "backend.app.routers.automations."
        "record_n8n_callback",
        lambda **kwargs: {
            "outcome": "conflict",
            "current_status": "Succeeded",
        },
    )

    response = client.post(
        "/api/automations/log",
        headers={
            "X-N8N-Callback-Secret": "correct-secret",
        },
        json={
            "idempotency_key": (
                "automation-0123456789abcdef"
            ),
            "execution_status": "Failed",
            "error_type": "LateFailure",
        },
    )

    assert response.status_code == 409


def test_callback_forbids_extra_fields(
    client: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "backend.app.routers.automations.settings",
        SimpleNamespace(
            n8n_callback_secret="correct-secret",
        ),
    )

    response = client.post(
        "/api/automations/log",
        headers={
            "X-N8N-Callback-Secret": "correct-secret",
        },
        json={
            "idempotency_key": (
                "automation-0123456789abcdef"
            ),
            "execution_status": "Succeeded",
            "admin_override": True,
        },
    )

    assert response.status_code == 422


def test_trigger_rejects_invalid_secret(
    client: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "backend.app.routers.automations.settings",
        SimpleNamespace(
            automation_api_secret="correct-trigger-secret",
        ),
    )

    response = client.post(
        "/api/automations/task-reminder",
        headers={
            "X-Automation-API-Secret": "wrong-secret",
        },
        json={
            "task_id": 201,
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid automation trigger credentials."
    }


def test_high_priority_alert_returns_accepted_response(
    client: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "backend.app.routers.automations.settings",
        SimpleNamespace(
            automation_api_secret="trigger-secret",
        ),
    )
    monkeypatch.setattr(
        "backend.app.routers.automations."
        "trigger_high_priority_alert",
        lambda issue_id: {
            "outcome": "success",
            "response": {
                "status": "success",
                "message": (
                    "The workflow request was accepted by n8n."
                ),
                "duplicate": False,
                "automation_log": {
                    **SAMPLE_AUTOMATION_LOG,
                    "task_id": None,
                    "action_type": "high_priority_alert",
                },
            },
        },
    )

    response = client.post(
        "/api/automations/high-priority-alert",
        headers={
            "X-Automation-API-Secret": "trigger-secret",
        },
        json={
            "issue_id": "ISSUE-SALES-S003-2026-06",
        },
    )

    assert response.status_code == 202
    assert response.json()[
        "duplicate"
    ] is False


def test_task_reminder_returns_duplicate_without_retriggering(
    client: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "backend.app.routers.automations.settings",
        SimpleNamespace(
            automation_api_secret="trigger-secret",
        ),
    )
    monkeypatch.setattr(
        "backend.app.routers.automations."
        "trigger_task_reminder",
        lambda task_id: {
            "outcome": "duplicate",
            "response": {
                "status": "success",
                "message": "Duplicate suppressed.",
                "duplicate": True,
                "automation_log": SAMPLE_AUTOMATION_LOG,
            },
        },
    )

    response = client.post(
        "/api/automations/task-reminder",
        headers={
            "X-Automation-API-Secret": "trigger-secret",
        },
        json={
            "task_id": 201,
        },
    )

    assert response.status_code == 202
    assert response.json()[
        "duplicate"
    ] is True


@pytest.mark.parametrize(
    ("endpoint", "outcome", "expected_status"),
    [
        (
            "/api/automations/task-reminder",
            {"outcome": "not_found"},
            404,
        ),
        (
            "/api/automations/task-reminder",
            {
                "outcome": "invalid_state",
                "reason": "Completed tasks cannot receive reminders.",
            },
            409,
        ),
        (
            "/api/automations/task-reminder",
            {"outcome": "disabled"},
            503,
        ),
        (
            "/api/automations/task-reminder",
            {"outcome": "not_configured"},
            503,
        ),
        (
            "/api/automations/task-reminder",
            {
                "outcome": "delivery_failed",
                "automation_log": SAMPLE_AUTOMATION_LOG,
            },
            502,
        ),
    ],
)
def test_task_reminder_maps_controlled_outcomes(
    client: Any,
    monkeypatch: Any,
    endpoint: str,
    outcome: dict[str, Any],
    expected_status: int,
) -> None:
    monkeypatch.setattr(
        "backend.app.routers.automations.settings",
        SimpleNamespace(
            automation_api_secret="trigger-secret",
        ),
    )
    monkeypatch.setattr(
        "backend.app.routers.automations."
        "trigger_task_reminder",
        lambda task_id: outcome,
    )

    response = client.post(
        endpoint,
        headers={
            "X-Automation-API-Secret": "trigger-secret",
        },
        json={
            "task_id": 201,
        },
    )

    assert response.status_code == expected_status


def test_overdue_escalation_validates_positive_task_id(
    client: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "backend.app.routers.automations.settings",
        SimpleNamespace(
            automation_api_secret="trigger-secret",
        ),
    )

    response = client.post(
        "/api/automations/overdue-escalation",
        headers={
            "X-Automation-API-Secret": "trigger-secret",
        },
        json={
            "task_id": 0,
        },
    )

    assert response.status_code == 422


def test_n8n_client_rejects_embedded_credentials(
) -> None:
    with pytest.raises(
        N8NClientConfigurationError
    ):
        N8NClient(
            base_url=(
                "http://user:password@localhost:5678/webhook"
            ),
            auth_token="secret",
            timeout_seconds=10,
            max_retries=0,
            retry_backoff_seconds=0,
        )


def test_n8n_client_rejects_absolute_or_traversal_webhook_paths(
) -> None:
    client = N8NClient(
        base_url="http://localhost:5678/webhook",
        auth_token="secret",
        timeout_seconds=10,
        max_retries=0,
        retry_backoff_seconds=0,
    )

    for unsafe_path in (
        "https://example.com/steal",
        "../admin",
        "task-reminder?token=secret",
        "task-reminder\\..\\admin",
    ):
        with pytest.raises(
            N8NClientConfigurationError
        ):
            client._build_url(
                unsafe_path
            )



class _FakeWebhookResponse:
    status = 200

    def __enter__(self) -> "_FakeWebhookResponse":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc: Any,
        traceback: Any,
    ) -> bool:
        del exc_type
        del exc
        del traceback
        return False

    def read(
        self,
        maximum_bytes: int,
    ) -> bytes:
        assert maximum_bytes == 65536
        return b'{"executionId":"n8n-retry-1"}'


class _RetryOnceOpener:
    def __init__(self) -> None:
        self.calls = 0

    def open(
        self,
        request: Any,
        timeout: float,
    ) -> _FakeWebhookResponse:
        del request
        assert timeout == 10
        self.calls += 1

        if self.calls == 1:
            from urllib.error import URLError

            raise URLError(
                "temporary failure"
            )

        return _FakeWebhookResponse()


class _AlwaysFailOpener:
    def __init__(self) -> None:
        self.calls = 0

    def open(
        self,
        request: Any,
        timeout: float,
    ) -> Any:
        del request
        del timeout
        self.calls += 1

        from urllib.error import URLError

        raise URLError(
            "still unavailable"
        )


def test_n8n_client_retries_transient_connection_failure(
) -> None:
    client = N8NClient(
        base_url="http://localhost:5678/webhook",
        auth_token="secret",
        timeout_seconds=10,
        max_retries=2,
        retry_backoff_seconds=0,
    )
    opener = _RetryOnceOpener()
    client._opener = opener

    result = client.post_webhook(
        webhook_path="task-reminder",
        payload={
            "safe": True,
        },
        idempotency_key=(
            "automation-retry-test-0001"
        ),
    )

    assert opener.calls == 2
    assert result.attempt_count == 2
    assert result.http_status_code == 200
    assert result.n8n_execution_id == "n8n-retry-1"


def test_n8n_client_stops_after_configured_retry_limit(
) -> None:
    client = N8NClient(
        base_url="http://localhost:5678/webhook",
        auth_token="secret",
        timeout_seconds=10,
        max_retries=2,
        retry_backoff_seconds=0,
    )
    opener = _AlwaysFailOpener()
    client._opener = opener

    with pytest.raises(
        N8NClientError
    ) as captured:
        client.post_webhook(
            webhook_path="task-reminder",
            payload={
                "safe": True,
            },
            idempotency_key=(
                "automation-retry-test-0002"
            ),
        )

    assert opener.calls == 3
    assert captured.value.attempts == 3
    assert (
        captured.value.error_type
        == "N8NConnectionError"
    )

def test_n8n_client_builds_only_relative_configured_url(
) -> None:
    client = N8NClient(
        base_url="http://localhost:5678/webhook",
        auth_token="secret",
        timeout_seconds=10,
        max_retries=0,
        retry_backoff_seconds=0,
    )

    assert client._build_url(
        "task-reminder"
    ) == (
        "http://localhost:5678/webhook/task-reminder"
    )
