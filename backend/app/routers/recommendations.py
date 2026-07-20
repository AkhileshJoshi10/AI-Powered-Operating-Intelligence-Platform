from __future__ import annotations

from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    HTTPException,
    Path,
    Query,
    status,
)
from sqlalchemy.exc import SQLAlchemyError

from backend.app.schemas.recommendations import (
    RecommendationDetailResponse,
    RecommendationEditRequest,
    RecommendationListResponse,
)
from backend.app.services.recommendation_service import (
    change_recommendation_status,
    edit_recommendation,
    get_recommendation_detail,
    get_recommendation_list,
)


router = APIRouter(
    prefix="/api/recommendations",
    tags=["Recommendations"],
)


RecommendationStatusFilter = Literal[
    "Pending Review",
    "Accepted",
    "Edited",
    "Rejected",
    "Converted to Task",
]


def build_review_response(
    result: dict,
) -> RecommendationDetailResponse:
    """Convert a recommendation review result into an API response."""

    outcome = result["outcome"]

    if outcome == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested recommendation was not found.",
        )

    if outcome == "conflict":
        current_status = result["current_status"]

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This recommendation cannot be changed because "
                f"its current status is '{current_status}'."
            ),
        )

    return RecommendationDetailResponse(
        **result["response"]
    )


@router.get(
    "",
    response_model=RecommendationListResponse,
    summary="Get management recommendations",
)
def list_recommendations(
    recommendation_status: Annotated[
        RecommendationStatusFilter | None,
        Query(
            alias="status",
            description="Filter by recommendation review status.",
        ),
    ] = None,
    owner_role: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=100,
            description="Filter by suggested owner role.",
        ),
    ] = None,
    business_area: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=150,
            description="Filter by linked issue business area.",
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Maximum recommendations returned.",
        ),
    ] = 20,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Number of recommendations to skip.",
        ),
    ] = 0,
) -> RecommendationListResponse:
    """Return filtered and paginated recommendations."""

    try:
        response_data = get_recommendation_list(
            recommendation_status=recommendation_status,
            owner_role=owner_role,
            business_area=business_area,
            limit=limit,
            offset=offset,
        )

        return RecommendationListResponse(**response_data)

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Recommendations could not be loaded because "
                "the database is unavailable."
            ),
        ) from error


@router.get(
    "/{recommendation_id}",
    response_model=RecommendationDetailResponse,
    summary="Get one recommendation",
)
def read_recommendation(
    recommendation_id: Annotated[
        int,
        Path(
            ge=1,
            description="Database ID of the recommendation.",
        ),
    ],
) -> RecommendationDetailResponse:
    """Return one recommendation and its supporting context."""

    try:
        response_data = get_recommendation_detail(
            recommendation_id
        )

        if response_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested recommendation was not found.",
            )

        return RecommendationDetailResponse(**response_data)

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The recommendation could not be loaded because "
                "the database is unavailable."
            ),
        ) from error


@router.patch(
    "/{recommendation_id}/accept",
    response_model=RecommendationDetailResponse,
    summary="Accept a recommendation",
)
def accept_recommendation(
    recommendation_id: Annotated[
        int,
        Path(
            ge=1,
            description="Database ID of the recommendation.",
        ),
    ],
) -> RecommendationDetailResponse:
    """Accept a pending or edited recommendation."""

    try:
        result = change_recommendation_status(
            recommendation_id=recommendation_id,
            target_status="Accepted",
        )

        return build_review_response(result)

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The recommendation could not be accepted because "
                "the database is unavailable."
            ),
        ) from error


@router.patch(
    "/{recommendation_id}/edit",
    response_model=RecommendationDetailResponse,
    summary="Edit a recommendation",
)
def update_recommendation(
    recommendation_id: Annotated[
        int,
        Path(
            ge=1,
            description="Database ID of the recommendation.",
        ),
    ],
    edit_request: RecommendationEditRequest,
) -> RecommendationDetailResponse:
    """Edit selected recommendation fields before acceptance."""

    update_data = edit_request.model_dump(
        exclude_unset=True
    )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one editable field must be provided.",
        )

    if any(value is None for value in update_data.values()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Editable fields cannot be null. Omit fields that "
                "should remain unchanged."
            ),
        )

    try:
        result = edit_recommendation(
            recommendation_id=recommendation_id,
            update_data=update_data,
        )

        return build_review_response(result)

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The recommendation could not be edited because "
                "the database is unavailable."
            ),
        ) from error


@router.patch(
    "/{recommendation_id}/reject",
    response_model=RecommendationDetailResponse,
    summary="Reject a recommendation",
)
def reject_recommendation(
    recommendation_id: Annotated[
        int,
        Path(
            ge=1,
            description="Database ID of the recommendation.",
        ),
    ],
) -> RecommendationDetailResponse:
    """Reject a pending or edited recommendation."""

    try:
        result = change_recommendation_status(
            recommendation_id=recommendation_id,
            target_status="Rejected",
        )

        return build_review_response(result)

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The recommendation could not be rejected because "
                "the database is unavailable."
            ),
        ) from error