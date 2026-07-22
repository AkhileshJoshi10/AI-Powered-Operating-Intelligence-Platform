from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.exc import SQLAlchemyError

from backend.app.schemas.sales_analytics import (
    SalesAnalyticsResponse,
    SalesSeverity,
)
from backend.app.services.sales_analytics_service import (
    get_sales_analytics,
)


router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"],
)


@router.get(
    "/sales",
    response_model=SalesAnalyticsResponse,
    summary="Get current sales analytics",
)
def read_sales_analytics(
    severity: Annotated[
        SalesSeverity | None,
        Query(
            description="Filter findings by severity.",
        ),
    ] = None,
    analysis_type: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=150,
            description=(
                "Filter findings by exact analysis type."
            ),
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Maximum findings returned.",
        ),
    ] = 50,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Number of findings to skip.",
        ),
    ] = 0,
) -> SalesAnalyticsResponse:
    """Return current deterministic sales findings."""

    try:
        response_data = get_sales_analytics(
            severity=severity,
            analysis_type=analysis_type,
            limit=limit,
            offset=offset,
        )

        return SalesAnalyticsResponse(
            **response_data
        )

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Sales analytics could not be loaded because "
                "the database operation failed."
            ),
        ) from error

    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Sales analytics could not be processed."
            ),
        ) from error