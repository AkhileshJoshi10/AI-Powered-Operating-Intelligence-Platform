from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)

from backend.app.schemas.data_management import (
    DataImportResponse,
    DataValidationResponse,
    DatasetName,
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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