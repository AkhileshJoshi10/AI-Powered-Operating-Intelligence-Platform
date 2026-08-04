from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)
from sqlalchemy.exc import SQLAlchemyError

from backend.app.schemas.chief_of_staff import (
    ChiefOfStaffRunRequest,
    ChiefOfStaffRunResponse,
)
from backend.app.services.chief_of_staff_service import (
    run_chief_of_staff_workflow,
)


router = APIRouter(
    prefix="/api/chief-of-staff",
    tags=["Chief of Staff"],
)


@router.post(
    "/run",
    response_model=ChiefOfStaffRunResponse,
    summary="Run the complete AI Chief of Staff workflow",
)
async def run_chief_of_staff(
    request: ChiefOfStaffRunRequest,
) -> ChiefOfStaffRunResponse:
    """
    Run all deterministic Chief of Staff agents in sequence.

    The workflow monitors business performance, prioritizes issues,
    generates root-cause analyses and proposed recommendations, and
    creates or updates the Daily Executive Brief.

    Recommendations remain subject to human review and are not
    automatically accepted or converted into tasks.
    """

    try:
        response_data = (
            await run_chief_of_staff_workflow(
                request
            )
        )

        return ChiefOfStaffRunResponse(
            **response_data
        )

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "The Chief of Staff workflow could not run "
                "because a database operation failed."
            ),
        ) from error

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "The Chief of Staff workflow could not be "
                "processed because its internal result was invalid."
            ),
        ) from error