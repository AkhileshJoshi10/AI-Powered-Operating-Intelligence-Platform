from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)

from backend.app.schemas.data_management import (
    DataImportHistoryResponse,
    DataImportResponse,
    DataValidationResponse,
    DatasetName,
)
from backend.app.services.data_import_history_service import (
    get_import_history,
)
from backend.app.services.data_import_service import (
    ImportValidationError,
    import_uploaded_dataset,
)
from backend.app.services.data_validation_service import (
    validate_uploaded_dataset,
)


router = APIRouter(
    prefix="/api/data",
    tags=["Data Management"],
)


@router.post(
    "/validate",
    response_model=DataValidationResponse,
    summary="Validate an uploaded raw CSV dataset",
)
async def validate_data(
    dataset_name: Annotated[
        DatasetName,
        Form(
            description=(
                "Business dataset represented by the uploaded CSV."
            ),
        ),
    ],
    file: Annotated[
        UploadFile,
        File(
            description=(
                "Raw CSV file to validate without saving or importing."
            ),
        ),
    ],
) -> DataValidationResponse:
    """Validate an uploaded dataset without changing stored data."""

    try:
        response_data = await validate_uploaded_dataset(
            dataset_name=dataset_name,
            uploaded_file=file,
        )

        return DataValidationResponse(
            **response_data
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    except (
        KeyError,
        TypeError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "The uploaded dataset could not be validated."
            ),
        ) from error

    finally:
        await file.close()


@router.post(
    "/import",
    response_model=DataImportResponse,
    summary="Validate, clean and import a raw CSV dataset",
)
async def import_data(
    dataset_name: Annotated[
        DatasetName,
        Form(
            description=(
                "Business dataset represented by the uploaded CSV."
            ),
        ),
    ],
    file: Annotated[
        UploadFile,
        File(
            description=(
                "Raw CSV file to validate, clean and import."
            ),
        ),
    ],
) -> DataImportResponse:
    """
    Import one dataset using safe upsert behavior.

    Existing rows with matching primary keys are updated.
    New primary keys are inserted. Other rows are not deleted.
    """

    try:
        response_data = await import_uploaded_dataset(
            dataset_name=dataset_name,
            uploaded_file=file,
        )

        return DataImportResponse(
            **response_data
        )

    except ImportValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": str(error),
                "errors": error.errors,
                "warnings": error.warnings,
            },
        ) from error

    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The dataset passed file validation but conflicts "
                "with the current PostgreSQL relationships or "
                "database constraints."
            ),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The dataset could not be imported because the "
                "database operation failed."
            ),
        ) from error

    except (
        KeyError,
        TypeError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "The uploaded dataset could not be processed."
            ),
        ) from error

    finally:
        await file.close()


@router.get(
    "/import-history",
    response_model=DataImportHistoryResponse,
    summary="Get dataset import history",
)
def read_import_history(
    dataset_name: Annotated[
        DatasetName | None,
        Query(
            description=(
                "Filter import records by business dataset."
            ),
        ),
    ] = None,
    import_status: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=50,
            description=(
                "Filter by import status, such as Success, "
                "Failed, or Rejected."
            ),
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description=(
                "Maximum number of import records returned."
            ),
        ),
    ] = 20,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description=(
                "Number of matching import records to skip."
            ),
        ),
    ] = 0,
) -> DataImportHistoryResponse:
    """Return the latest data import records."""

    try:
        response_data = get_import_history(
            dataset_name=dataset_name,
            import_status=import_status,
            limit=limit,
            offset=offset,
        )

        return DataImportHistoryResponse(
            **response_data
        )

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Import history could not be loaded because "
                "the database operation failed."
            ),
        ) from error

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Import history could not be processed."
            ),
        ) from error