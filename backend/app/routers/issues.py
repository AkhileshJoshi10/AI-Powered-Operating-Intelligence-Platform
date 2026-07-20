from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from backend.app.schemas.issues import (
    IssueDetailResponse,
    IssueListResponse,
)
from backend.app.services.issue_service import (
    get_issue_detail,
    get_issue_list,
)


router = APIRouter(
    prefix="/api/issues",
    tags=["Issues"],
)


PriorityFilter = Literal["High", "Medium", "Low"]

IssueStatusFilter = Literal[
    "Open",
    "In Progress",
    "Resolved",
    "Rejected",
]


@router.get(
    "",
    response_model=IssueListResponse,
    summary="Get business issues",
)
def list_issues(
    priority: Annotated[
        PriorityFilter | None,
        Query(
            description="Filter issues by priority level.",
        ),
    ] = None,
    business_area: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=150,
            description="Filter issues by business area.",
        ),
    ] = None,
    issue_status: Annotated[
        IssueStatusFilter | None,
        Query(
            alias="status",
            description="Filter issues by workflow status.",
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Maximum issues returned.",
        ),
    ] = 20,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Number of issues to skip.",
        ),
    ] = 0,
) -> IssueListResponse:
    """Return filtered and paginated business issues."""

    try:
        response_data = get_issue_list(
            priority=priority,
            business_area=business_area,
            issue_status=issue_status,
            limit=limit,
            offset=offset,
        )

        return IssueListResponse(**response_data)

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Business issues could not be loaded because "
                "the database is unavailable."
            ),
        ) from error


@router.get(
    "/{issue_id}",
    response_model=IssueDetailResponse,
    summary="Get one issue with evidence",
)
def read_issue(issue_id: str) -> IssueDetailResponse:
    """Return an issue, supporting evidence, and root cause."""

    try:
        response_data = get_issue_detail(issue_id)

        if response_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested issue was not found.",
            )

        return IssueDetailResponse(**response_data)

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The issue could not be loaded because "
                "the database is unavailable."
            ),
        ) from error