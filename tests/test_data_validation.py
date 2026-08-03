from __future__ import annotations

from typing import Any

import pytest


VALIDATED_AT = "2026-08-03T11:30:00"


VALID_RESPONSE = {
    "status": "valid",
    "validated_at": VALIDATED_AT,
    "dataset_name": "products",
    "source_file_name": "products_data.csv",
    "validation_scope": (
        "Uploaded dataset with existing reference datasets"
    ),
    "total_rows": 25,
    "total_columns": 13,
    "is_valid": True,
    "error_count": 0,
    "warning_count": 0,
    "errors": [],
    "warnings": [],
    "dataset_summary": [
        "Dataset: products",
        "Rows validated: 25",
        "No validation errors found.",
    ],
}


INVALID_RESPONSE = {
    "status": "invalid",
    "validated_at": VALIDATED_AT,
    "dataset_name": "products",
    "source_file_name": "products_invalid.csv",
    "validation_scope": (
        "Uploaded dataset with existing reference datasets"
    ),
    "total_rows": 3,
    "total_columns": 13,
    "is_valid": False,
    "error_count": 2,
    "warning_count": 1,
    "errors": [
        "Duplicate product_id values were found.",
        "One product has a negative cost price.",
    ],
    "warnings": [
        "One product has no vendor reference.",
    ],
    "dataset_summary": [
        "Dataset: products",
        "Rows validated: 3",
        "Validation errors were found.",
    ],
}


SUPPORTED_DATASETS = [
    "products",
    "stores",
    "vendors",
    "employees",
    "sales",
    "inventory",
    "complaints",
    "finance",
    "vendor_deliveries",
]


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


def test_validate_dataset_returns_valid_response_and_closes_file(
    client: Any,
    monkeypatch: Any,
) -> None:
    """A valid uploaded dataset should return validation details."""

    captured_values: dict[str, Any] = {}

    async def mock_validate_uploaded_dataset(
        *,
        dataset_name: str,
        uploaded_file: Any,
    ) -> dict[str, Any]:
        captured_values["dataset_name"] = dataset_name
        captured_values["uploaded_file"] = uploaded_file
        captured_values["file_name"] = uploaded_file.filename

        assert uploaded_file.file.closed is False

        return VALID_RESPONSE

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "validate_uploaded_dataset",
        mock_validate_uploaded_dataset,
    )

    response = client.post(
        "/api/data/validate",
        data={"dataset_name": "products"},
        files=build_upload(),
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "valid"
    assert response_data["dataset_name"] == "products"
    assert response_data["source_file_name"] == "products_data.csv"
    assert response_data["total_rows"] == 25
    assert response_data["total_columns"] == 13
    assert response_data["is_valid"] is True
    assert response_data["error_count"] == 0
    assert response_data["warning_count"] == 0
    assert response_data["errors"] == []
    assert response_data["warnings"] == []

    assert captured_values["dataset_name"] == "products"
    assert captured_values["file_name"] == "products_data.csv"
    assert captured_values["uploaded_file"].file.closed is True


def test_validate_dataset_returns_errors_and_warnings(
    client: Any,
    monkeypatch: Any,
) -> None:
    """An invalid dataset should return structured validation results."""

    async def mock_validate_uploaded_dataset(
        *,
        dataset_name: str,
        uploaded_file: Any,
    ) -> dict[str, Any]:
        assert dataset_name == "products"
        assert uploaded_file.filename == "products_invalid.csv"

        return INVALID_RESPONSE

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "validate_uploaded_dataset",
        mock_validate_uploaded_dataset,
    )

    response = client.post(
        "/api/data/validate",
        data={"dataset_name": "products"},
        files=build_upload(
            file_name="products_invalid.csv",
        ),
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "invalid"
    assert response_data["is_valid"] is False
    assert response_data["error_count"] == 2
    assert response_data["warning_count"] == 1
    assert len(response_data["errors"]) == 2
    assert len(response_data["warnings"]) == 1
    assert (
        response_data["errors"][0]
        == "Duplicate product_id values were found."
    )


@pytest.mark.parametrize(
    "dataset_name",
    SUPPORTED_DATASETS,
)
def test_validate_dataset_accepts_supported_dataset_names(
    client: Any,
    monkeypatch: Any,
    dataset_name: str,
) -> None:
    """All nine configured business datasets should be accepted."""

    async def mock_validate_uploaded_dataset(
        *,
        dataset_name: str,
        uploaded_file: Any,
    ) -> dict[str, Any]:
        return {
            **VALID_RESPONSE,
            "dataset_name": dataset_name,
            "source_file_name": uploaded_file.filename,
        }

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "validate_uploaded_dataset",
        mock_validate_uploaded_dataset,
    )

    file_name = f"{dataset_name}_data.csv"

    response = client.post(
        "/api/data/validate",
        data={"dataset_name": dataset_name},
        files=build_upload(file_name=file_name),
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["dataset_name"] == dataset_name
    assert response_data["source_file_name"] == file_name


def test_validate_dataset_rejects_unsupported_dataset_name(
    client: Any,
) -> None:
    """An unsupported dataset name should return HTTP 422."""

    response = client.post(
        "/api/data/validate",
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


def test_validate_dataset_rejects_missing_dataset_name(
    client: Any,
) -> None:
    """The dataset_name multipart field is required."""

    response = client.post(
        "/api/data/validate",
        files=build_upload(),
    )

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        "dataset_name" in error["loc"]
        for error in error_details
    )


def test_validate_dataset_rejects_missing_file(
    client: Any,
) -> None:
    """The CSV file multipart field is required."""

    response = client.post(
        "/api/data/validate",
        data={"dataset_name": "products"},
    )

    assert response.status_code == 422

    error_details = response.json()["detail"]

    assert any(
        "file" in error["loc"]
        for error in error_details
    )


def test_validate_dataset_returns_400_for_validation_failure(
    client: Any,
    monkeypatch: Any,
) -> None:
    """User-correctable upload failures should return HTTP 400."""

    captured_upload: dict[str, Any] = {}

    async def raise_validation_error(
        *,
        dataset_name: str,
        uploaded_file: Any,
    ) -> dict[str, Any]:
        del dataset_name

        captured_upload["file"] = uploaded_file

        raise ValueError(
            "Only CSV files are supported."
        )

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "validate_uploaded_dataset",
        raise_validation_error,
    )

    response = client.post(
        "/api/data/validate",
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
        "detail": "Only CSV files are supported."
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
def test_validate_dataset_returns_500_for_processing_failure(
    client: Any,
    monkeypatch: Any,
    exception_type: type[Exception],
) -> None:
    """Unexpected validation-processing failures should return 500."""

    captured_upload: dict[str, Any] = {}

    async def raise_processing_error(
        *,
        dataset_name: str,
        uploaded_file: Any,
    ) -> dict[str, Any]:
        del dataset_name

        captured_upload["file"] = uploaded_file

        raise exception_type(
            "Simulated validation processing failure."
        )

    monkeypatch.setattr(
        "backend.app.routers.data_management."
        "validate_uploaded_dataset",
        raise_processing_error,
    )

    response = client.post(
        "/api/data/validate",
        data={"dataset_name": "products"},
        files=build_upload(),
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": (
            "The uploaded dataset could not be validated."
        )
    }

    assert captured_upload["file"].file.closed is True