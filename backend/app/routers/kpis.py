from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from backend.app.schemas.kpis import KPIResponse
from backend.app.services.kpi_service import get_kpi_response


router = APIRouter(
    prefix="/api/kpis",
    tags=["KPIs"],
)


@router.get(
    "",
    response_model=KPIResponse,
    summary="Get current business KPIs",
)
def get_kpis() -> KPIResponse:
    """Return the latest calculated business KPIs."""

    try:
        response_data = get_kpi_response()

        return KPIResponse(**response_data)

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Business KPIs could not be loaded because the "
                "database is unavailable."
            ),
        ) from error