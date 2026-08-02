from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)
from sqlalchemy.exc import SQLAlchemyError

from backend.app.schemas.executive_briefs import (
    LatestExecutiveBriefResponse,
)
from backend.app.services.executive_brief_service import (
    get_latest_executive_brief,
)


router = APIRouter(
    prefix="/api/executive-brief",
    tags=["Executive Brief"],
)


@router.get(
    "/latest",
    response_model=LatestExecutiveBriefResponse,
    summary="Get the latest stored Executive Brief",
)
def read_latest_executive_brief(
) -> LatestExecutiveBriefResponse:
    """Return the most recently stored executive brief."""

    try:
        response_data = get_latest_executive_brief()

        if response_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "No Executive Brief has been generated yet."
                ),
            )

        return LatestExecutiveBriefResponse(
            **response_data
        )

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The latest Executive Brief could not be loaded "
                "because the database operation failed."
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
                "The latest Executive Brief could not be processed."
            ),
        ) from error