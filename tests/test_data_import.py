from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.app.services.data_import_service import (
    ImportValidationError,
)


IMPORTED_AT = "2026-08-03T12:00:00"


SUCCESS_RESPONSE = {
    "status": "success",
    "imported_at": IMPORTED_AT,
    "dataset_name": "products",
    "source_file_name": "products_data.csv",
    "destination_table": "products",
    "import_mode": "upsert",
    "total_rows": 25,
    "successful_rows": 25,
    "failed_rows": 0,
    "raw_validation_warnings": [
        "One optional text field was blank."
    ],
    "cleaning_summary": {
        "initial_rows": 25,
        "final_rows": 25,
        "duplicates_removed": 0,
        "text_values_normalized": 4,
    },
    "message": (
        "25 rows were imported into products using upsert mode."
    ),
}


def build_upload(
    *,
    file_name: str = "products_data.csv",
) -> dict[str, tuple[str, bytes, str]]:
    """Build one multipart CSV upload."""

    csv_content = (
        b"product_id,product_name,category\n"
        b"P001,Sample Product,Groceries\n"
    )

    return {
        "file": (
            file_name,
            csv_content,
            "text/csv",
        )
    }


def test_import_dataset_returns_success_and_closes_file(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A valid CSV should return the controlled upsert response."""

    captured_values: dict[str, Any] = {}

    async def mock_import_uploaded_dataset(
        *,
        dataset_name: str,
        uploaded_file: Any,
    ) -> dict[str, Any]:
        captured_values["dataset_name"] = dataset_name
        captured_values["uploaded_file"] = uploaded_file
        captured_values["file_name"] = uploaded_file.filename

        assert uploaded_file.file.closed is False

        return SUCCESS_RESPONSE

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "import_uploaded_dataset",
        mock_import_uploaded_dataset,
    )

    response = client.post(
        "/api/data/import",
        data={"dataset_name": "products"},
        files=build_upload(),
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "success"
    assert response_data["dataset_name"] == "products"
    assert response_data["source_file_name"] == "products_data.csv"
    assert response_data["destination_table"] == "products"
    assert response_data["import_mode"] == "upsert"
    assert response_data["total_rows"] == 25
    assert response_data["successful_rows"] == 25
    assert response_data["failed_rows"] == 0
    assert len(response_data["raw_validation_warnings"]) == 1

    assert response_data["cleaning_summary"] == {
        "initial_rows": 25,
        "final_rows": 25,
        "duplicates_removed": 0,
        "text_values_normalized": 4,
    }

    assert captured_values["dataset_name"] == "products"
    assert captured_values["file_name"] == "products_data.csv"
    assert captured_values["uploaded_file"].file.closed is True


def test_import_dataset_rejects_unsupported_dataset_name(
    client: Any,
) -> None:
    """An unsupported dataset name should return HTTP 422."""

    response = client.post(
        "/api/data/import",
        data={"dataset_name": "customers"},
        files=build_upload(
            file_name="customers_data.csv",
        ),
    )

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        "dataset_name" in error["loc"]
        for error in error_details
    )


def test_import_dataset_rejects_missing_dataset_name(
    client: Any,
) -> None:
    """The dataset_name multipart field is required."""

    response = client.post(
        "/api/data/import",
        files=build_upload(),
    )

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        "dataset_name" in error["loc"]
        for error in error_details
    )


def test_import_dataset_rejects_missing_file(
    client: Any,
) -> None:
    """The uploaded CSV multipart field is required."""

    response = client.post(
        "/api/data/import",
        data={"dataset_name": "products"},
    )

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        "file" in error["loc"]
        for error in error_details
    )


def test_import_dataset_returns_422_for_validation_rejection(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Raw-data validation failures should preserve errors and warnings."""

    captured_upload: dict[str, Any] = {}

    async def raise_import_validation_error(
        *,
        dataset_name: str,
        uploaded_file: Any,
    ) -> dict[str, Any]:
        assert dataset_name == "products"

        captured_upload["file"] = uploaded_file

        raise ImportValidationError(
            "The uploaded dataset failed raw-data validation.",
            errors=[
                "Duplicate product_id values were found.",
                "One product has a negative cost price.",
            ],
            warnings=[
                "One optional description is missing.",
            ],
        )

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "import_uploaded_dataset",
        raise_import_validation_error,
    )

    response = client.post(
        "/api/data/import",
        data={"dataset_name": "products"},
        files=build_upload(
            file_name="products_invalid.csv",
        ),
    )

    assert response.status_code == 422

    assert response.json() == {
        "detail": {
            "message": (
                "The uploaded dataset failed raw-data validation."
            ),
            "errors": [
                "Duplicate product_id values were found.",
                "One product has a negative cost price.",
            ],
            "warnings": [
                "One optional description is missing.",
            ],
        }
    }

    assert captured_upload["file"].file.closed is True


def test_import_dataset_returns_409_for_database_constraint_conflict(
    client: Any,
    monkeypatch: Any,
) -> None:
    """Relationship or constraint conflicts should return HTTP 409."""

    captured_upload: dict[str, Any] = {}

    async def raise_integrity_error(
        *,
        dataset_name: str,
        uploaded_file: Any,
    ) -> dict[str, Any]:
        del dataset_name

        captured_upload["file"] = uploaded_file

        raise IntegrityError(
            "INSERT INTO products ...",
            {},
            Exception("Simulated foreign-key conflict."),
        )

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "import_uploaded_dataset",
        raise_integrity_error,
    )

    response = client.post(
        "/api/data/import",
        data={"dataset_name": "products"},
        files=build_upload(),
    )

    assert response.status_code == 409

    assert response.json() == {
        "detail": (
            "The dataset passed file validation but conflicts "
            "with the current PostgreSQL relationships or "
            "database constraints."
        )
    }

    assert captured_upload["file"].file.closed is True


def test_import_dataset_returns_400_for_invalid_upload(
    client: Any,
    monkeypatch: Any,
) -> None:
    """User-correctable file problems should return HTTP 400."""

    captured_upload: dict[str, Any] = {}

    async def raise_value_error(
        *,
        dataset_name: str,
        uploaded_file: Any,
    ) -> dict[str, Any]:
        del dataset_name

        captured_upload["file"] = uploaded_file

        raise ValueError(
            "Only CSV files can be imported."
        )

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "import_uploaded_dataset",
        raise_value_error,
    )

    response = client.post(
        "/api/data/import",
        data={"dataset_name": "products"},
        files={
            "file": (
                "products.txt",
                b"invalid file content",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400

    assert response.json() == {
        "detail": "Only CSV files can be imported."
    }

    assert captured_upload["file"].file.closed is True


def test_import_dataset_returns_503_on_database_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    """General SQLAlchemy failures should return HTTP 503."""

    captured_upload: dict[str, Any] = {}

    async def raise_database_error(
        *,
        dataset_name: str,
        uploaded_file: Any,
    ) -> dict[str, Any]:
        del dataset_name

        captured_upload["file"] = uploaded_file

        raise SQLAlchemyError(
            "Simulated dataset-import database failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "import_uploaded_dataset",
        raise_database_error,
    )

    response = client.post(
        "/api/data/import",
        data={"dataset_name": "products"},
        files=build_upload(),
    )

    assert response.status_code == 503

    assert response.json() == {
        "detail": (
            "The dataset could not be imported because the "
            "database operation failed."
        )
    }

    assert captured_upload["file"].file.closed is True


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
    ],
)
def test_import_dataset_returns_500_for_processing_failure(
    client: Any,
    monkeypatch: Any,
    exception_type: type[Exception],
) -> None:
    """Unexpected import-processing failures should return HTTP 500."""

    captured_upload: dict[str, Any] = {}

    async def raise_processing_error(
        *,
        dataset_name: str,
        uploaded_file: Any,
    ) -> dict[str, Any]:
        del dataset_name

        captured_upload["file"] = uploaded_file

        raise exception_type(
            "Simulated dataset-import processing failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "import_uploaded_dataset",
        raise_processing_error,
    )

    response = client.post(
        "/api/data/import",
        data={"dataset_name": "products"},
        files=build_upload(),
    )

    assert response.status_code == 500

    assert response.json() == {
        "detail": (
            "The uploaded dataset could not be processed."
        )
    }

    assert captured_upload["file"].file.closed is True