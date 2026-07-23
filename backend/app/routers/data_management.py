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

from backend.app.schemas.data_management import (
    DataValidationResponse,
    DatasetName,
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