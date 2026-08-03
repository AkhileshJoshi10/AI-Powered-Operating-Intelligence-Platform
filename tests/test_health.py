from __future__ import annotations

from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import settings


def test_api_health_returns_healthy_status(
    client: Any,
) -> None:
    """The API health endpoint should confirm the app is running."""

    response = client.get("/health")

    assert response.status_code == 200

    response_data = response.json()

    assert response_data == {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


def test_database_health_connects_to_test_database(
    client: Any,
) -> None:
    """The database health endpoint must use the test database."""

    response = client.get("/health/database")

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "healthy"
    assert response_data["service"] == settings.app_name
    assert response_data["database_status"] == "connected"
    assert (
        response_data["database_name"]
        == "ai_operating_intelligence_test"
    )


def test_database_health_returns_503_when_connection_fails(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A database failure should return a controlled 503 response."""

    def raise_database_error() -> dict[str, str]:
        raise SQLAlchemyError(
            "Simulated test database failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.health.check_database_connection",
        raise_database_error,
    )

    response = client.get("/health/database")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "PostgreSQL database connection failed."
    }