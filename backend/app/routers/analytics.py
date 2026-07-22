from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.exc import SQLAlchemyError

from backend.app.schemas.complaint_analytics import (
    ComplaintAnalyticsResponse,
    ComplaintFindingSeverity,
)
from backend.app.schemas.inventory_analytics import (
    InventoryAnalyticsResponse,
    InventorySeverity,
)
from backend.app.schemas.sales_analytics import (
    SalesAnalyticsResponse,
    SalesSeverity,
)
from backend.app.services.complaint_analytics_service import (
    get_complaint_analytics,
)
from backend.app.services.inventory_analytics_service import (
    get_inventory_analytics,
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
            description="Filter by exact analysis type.",
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
            detail="Sales analytics could not be processed.",
        ) from error


@router.get(
    "/inventory",
    response_model=InventoryAnalyticsResponse,
    summary="Get current inventory analytics",
)
def read_inventory_analytics(
    severity: Annotated[
        InventorySeverity | None,
        Query(
            description="Filter findings by severity.",
        ),
    ] = None,
    analysis_type: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=150,
            description="Filter by exact analysis type.",
        ),
    ] = None,
    store_id: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=20,
            description="Filter by store ID.",
        ),
    ] = None,
    product_id: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=20,
            description="Filter by product ID.",
        ),
    ] = None,
    vendor_id: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=20,
            description="Filter by vendor ID.",
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
) -> InventoryAnalyticsResponse:
    """Return current deterministic inventory findings."""

    try:
        response_data = get_inventory_analytics(
            severity=severity,
            analysis_type=analysis_type,
            store_id=store_id,
            product_id=product_id,
            vendor_id=vendor_id,
            limit=limit,
            offset=offset,
        )

        return InventoryAnalyticsResponse(
            **response_data
        )

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Inventory analytics could not be loaded because "
                "the database operation failed."
            ),
        ) from error

    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Inventory analytics could not be processed."
            ),
        ) from error


@router.get(
    "/complaints",
    response_model=ComplaintAnalyticsResponse,
    summary="Get current complaint analytics",
)
def read_complaint_analytics(
    severity: Annotated[
        ComplaintFindingSeverity | None,
        Query(
            description="Filter findings by severity.",
        ),
    ] = None,
    analysis_type: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=150,
            description="Filter by exact analysis type.",
        ),
    ] = None,
    store_id: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=20,
            description="Filter by store ID.",
        ),
    ] = None,
    product_id: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=20,
            description="Filter by product ID.",
        ),
    ] = None,
    region: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=50,
            description="Filter by region.",
        ),
    ] = None,
    complaint_type: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=150,
            description="Filter by complaint type.",
        ),
    ] = None,
    complaint_status: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=50,
            description=(
                "Filter by complaint status, such as Open "
                "or In Progress."
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
) -> ComplaintAnalyticsResponse:
    """Return current deterministic complaint findings."""

    try:
        response_data = get_complaint_analytics(
            severity=severity,
            analysis_type=analysis_type,
            store_id=store_id,
            product_id=product_id,
            region=region,
            complaint_type=complaint_type,
            complaint_status=complaint_status,
            limit=limit,
            offset=offset,
        )

        return ComplaintAnalyticsResponse(
            **response_data
        )

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Complaint analytics could not be loaded because "
                "the database operation failed."
            ),
        ) from error

    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Complaint analytics could not be processed."
            ),
        ) from error