from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import settings
from backend.app.db.database import check_database_connection


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get(
    "",
    summary="Check API health",
)
def health_check() -> dict[str, str]:
    """Confirm that the FastAPI application is running."""

    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get(
    "/database",
    summary="Check PostgreSQL health",
)
def database_health_check() -> dict[str, str]:
    """Confirm that FastAPI can connect to PostgreSQL."""

    try:
        database_status = check_database_connection()

        return {
            "status": "healthy",
            "service": settings.app_name,
            "database_status": "connected",
            "database_name": database_status["database_name"],
        }

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL database connection failed.",
        ) from error