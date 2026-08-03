from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError


GENERATED_AT = "2026-08-03T12:30:00"


SAMPLE_IMPORT_RECORD = {
    "import_id": 101,
    "dataset_name": "products",
    "source_file_name": "products_data.csv",
    "total_rows": 25,
    "successful_rows": 25,
    "failed_rows": 0,
    "import_status": "Success",
    "error_message": None,
    "imported_at": "2026-08-03T12:00:00",
}


def test_import_history_returns_paginated_records(
    client: Any,
    monkeypatch: Any,
) -> None:
    """The endpoint should return valid import-history records."""

    def mock_get_import_history(
        *,
        dataset_name: str | None,
        import_status: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        assert dataset_name is None
        assert import_status is None
        assert limit == 20
        assert offset == 0

        return {
            "status": "success",
            "generated_at": GENERATED_AT,
            "total_records": 1,
            "matching_records": 1,
            "limit": 20,
            "offset": 0,
            "imports": [SAMPLE_IMPORT_RECORD],
        }

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "get_import_history",
        mock_get_import_history,
    )

    response = client.get("/api/data/import-history")

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "success"
    assert response_data["generated_at"] == GENERATED_AT
    assert response_data["total_records"] == 1
    assert response_data["matching_records"] == 1
    assert response_data["limit"] == 20
    assert response_data["offset"] == 0
    assert len(response_data["imports"]) == 1

    import_record = response_data["imports"][0]

    assert import_record["import_id"] == 101
    assert import_record["dataset_name"] == "products"
    assert import_record["import_status"] == "Success"
    assert import_record["successful_rows"] == 25
    assert import_record["failed_rows"] == 0
    assert import_record["error_message"] is None


def test_import_history_forwards_filters_and_pagination(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Filters and pagination should reach the service correctly."""

    captured_parameters: dict[str, Any] = {}

    def mock_get_import_history(
        *,
        dataset_name: str | None,
        import_status: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        captured_parameters.update(
            {
                "dataset_name": dataset_name,
                "import_status": import_status,
                "limit": limit,
                "offset": offset,
            }
        )

        return {
            "status": "success",
            "generated_at": GENERATED_AT,
            "total_records": 10,
            "matching_records": 1,
            "limit": limit,
            "offset": offset,
            "imports": [SAMPLE_IMPORT_RECORD],
        }

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "get_import_history",
        mock_get_import_history,
    )

    response = client.get(
        "/api/data/import-history",
        params={
            "dataset_name": "products",
            "import_status": "Success",
            "limit": 10,
            "offset": 5,
        },
    )

    assert response.status_code == 200

    assert captured_parameters == {
        "dataset_name": "products",
        "import_status": "Success",
        "limit": 10,
        "offset": 5,
    }

    response_data = response.json()

    assert response_data["total_records"] == 10
    assert response_data["matching_records"] == 1
    assert response_data["limit"] == 10
    assert response_data["offset"] == 5


def test_import_history_accepts_empty_result(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A valid query with no matching imports should return an empty list."""

    def mock_get_import_history(
        *,
        dataset_name: str | None,
        import_status: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        del dataset_name
        del import_status

        return {
            "status": "success",
            "generated_at": GENERATED_AT,
            "total_records": 10,
            "matching_records": 0,
            "limit": limit,
            "offset": offset,
            "imports": [],
        }

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "get_import_history",
        mock_get_import_history,
    )

    response = client.get(
        "/api/data/import-history",
        params={
            "dataset_name": "finance",
            "import_status": "Rejected",
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "status": "success",
        "generated_at": GENERATED_AT,
        "total_records": 10,
        "matching_records": 0,
        "limit": 20,
        "offset": 0,
        "imports": [],
    }


@pytest.mark.parametrize(
    ("query_parameters", "invalid_field"),
    [
        (
            {"dataset_name": "customers"},
            "dataset_name",
        ),
        (
            {"import_status": "A"},
            "import_status",
        ),
        (
            {"limit": 0},
            "limit",
        ),
        (
            {"limit": 101},
            "limit",
        ),
        (
            {"offset": -1},
            "offset",
        ),
    ],
)
def test_import_history_rejects_invalid_query_parameters(
    client: Any,
    query_parameters: dict[str, Any],
    invalid_field: str,
) -> None:
    """Invalid filters and pagination should return HTTP 422."""

    response = client.get(
        "/api/data/import-history",
        params=query_parameters,
    )

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        invalid_field in error["loc"]
        for error in error_details
    )


def test_import_history_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A database failure should return a controlled HTTP 503."""

    def raise_database_error(
        **_: Any,
    ) -> dict[str, Any]:
        raise SQLAlchemyError(
            "Simulated import-history database failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "get_import_history",
        raise_database_error,
    )

    response = client.get("/api/data/import-history")

    assert response.status_code == 503

    assert response.json() == {
        "detail": (
            "Import history could not be loaded because "
            "the database operation failed."
        )
    }


@pytest.mark.parametrize(
    "exception_type",
    [
        pytest.param(
            KeyError,
            id="key-error",
        ),
        pytest.param(
            TypeError,
            id="type-error",
        ),
        pytest.param(
            ValueError,
            id="value-error",
        ),
    ],
)
def test_import_history_returns_500_on_processing_failure(
    client: Any,
    monkeypatch: Any,
    exception_type: type[Exception],
) -> None:
    """Unexpected import-history processing failures should return 500."""

    def raise_processing_error(
        **_: Any,
    ) -> dict[str, Any]:
        raise exception_type(
            "Simulated import-history processing failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "get_import_history",
        raise_processing_error,
    )

    response = client.get("/api/data/import-history")

    assert response.status_code == 500

    assert response.json() == {
        "detail": "Import history could not be processed."
    }