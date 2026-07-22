from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    HTTPException,
    Path,
    Query,
    status,
)
from sqlalchemy.exc import SQLAlchemyError

from backend.app.schemas.tasks import (
    TaskAssignmentRequest,
    TaskAssignmentResponse,
    TaskConversionResponse,
    TaskDetailResponse,
    TaskListResponse,
    TaskPriority,
    TaskStatus,
    TaskStatusUpdateRequest,
    TaskStatusUpdateResponse,
)
from backend.app.services.task_service import (
    assign_task,
    convert_recommendation_to_task,
    get_task_detail,
    get_task_list,
    update_task_status,
)


router = APIRouter(
    prefix="/api",
    tags=["Tasks"],
)


@router.post(
    "/recommendations/{recommendation_id}/convert-to-task",
    response_model=TaskConversionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Convert an accepted recommendation into a task",
)
def create_task_from_recommendation(
    recommendation_id: Annotated[
        int,
        Path(
            ge=1,
            description="Database ID of the accepted recommendation.",
        ),
    ],
) -> TaskConversionResponse:
    """Create one task from an accepted recommendation."""

    try:
        result = convert_recommendation_to_task(
            recommendation_id
        )

        outcome = result["outcome"]

        if outcome == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested recommendation was not found.",
            )

        if outcome == "invalid_status":
            current_status = result["current_status"]

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Only an Accepted recommendation can be "
                    "converted into a task. The current status is "
                    f"'{current_status}'."
                ),
            )

        if outcome == "already_converted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This recommendation has already been converted "
                    f"into task {result['task_id']}."
                ),
            )

        return TaskConversionResponse(
            **result["response"]
        )

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The task could not be created because the "
                "database operation failed."
            ),
        ) from error


@router.get(
    "/tasks",
    response_model=TaskListResponse,
    summary="Get tasks",
)
def list_tasks(
    task_status: Annotated[
        TaskStatus | None,
        Query(
            alias="status",
            description="Filter tasks by Kanban status.",
        ),
    ] = None,
    priority_level: Annotated[
        TaskPriority | None,
        Query(
            alias="priority",
            description="Filter tasks by priority level.",
        ),
    ] = None,
    assigned_role: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=100,
            description="Filter tasks by assigned role.",
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Maximum tasks returned.",
        ),
    ] = 20,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Number of tasks to skip.",
        ),
    ] = 0,
) -> TaskListResponse:
    """Return filtered and paginated tasks."""

    try:
        response_data = get_task_list(
            task_status=task_status,
            priority_level=priority_level,
            assigned_role=assigned_role,
            limit=limit,
            offset=offset,
        )

        return TaskListResponse(**response_data)

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Tasks could not be loaded because the "
                "database operation failed."
            ),
        ) from error


@router.get(
    "/tasks/{task_id}",
    response_model=TaskDetailResponse,
    summary="Get one task",
)
def read_task(
    task_id: Annotated[
        int,
        Path(
            ge=1,
            description="Database ID of the task.",
        ),
    ],
) -> TaskDetailResponse:
    """Return one task with linked issue and recommendation context."""

    try:
        response_data = get_task_detail(task_id)

        if response_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested task was not found.",
            )

        return TaskDetailResponse(**response_data)

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The task could not be loaded because the "
                "database operation failed."
            ),
        ) from error


@router.patch(
    "/tasks/{task_id}/status",
    response_model=TaskStatusUpdateResponse,
    summary="Change a task's Kanban status",
)
def change_task_status(
    task_id: Annotated[
        int,
        Path(
            ge=1,
            description="Database ID of the task.",
        ),
    ],
    status_request: TaskStatusUpdateRequest,
) -> TaskStatusUpdateResponse:
    """Move a task through the controlled Kanban workflow."""

    try:
        result = update_task_status(
            task_id=task_id,
            target_status=status_request.status,
        )

        outcome = result["outcome"]

        if outcome == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested task was not found.",
            )

        if outcome == "no_change":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "The task is already in status "
                    f"'{result['current_status']}'."
                ),
            )

        if outcome == "invalid_transition":
            allowed_statuses = result["allowed_statuses"]

            if allowed_statuses:
                allowed_text = ", ".join(allowed_statuses)
            else:
                allowed_text = "none"

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "The task cannot move from "
                    f"'{result['current_status']}' to "
                    f"'{result['target_status']}'. "
                    f"Allowed next statuses: {allowed_text}."
                ),
            )

        return TaskStatusUpdateResponse(
            **result["response"]
        )

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The task status could not be changed because "
                "the database operation failed."
            ),
        ) from error


@router.patch(
    "/tasks/{task_id}/assignment",
    response_model=TaskAssignmentResponse,
    summary="Assign a task to an employee",
)
def update_task_assignment(
    task_id: Annotated[
        int,
        Path(
            ge=1,
            description="Database ID of the task.",
        ),
    ],
    assignment_request: TaskAssignmentRequest,
) -> TaskAssignmentResponse:
    """Assign or reassign a task to a specific employee."""

    try:
        result = assign_task(
            task_id=task_id,
            assigned_to=assignment_request.assigned_to,
            assigned_role=assignment_request.assigned_role,
        )

        outcome = result["outcome"]

        if outcome == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested task was not found.",
            )

        if outcome == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A completed task cannot be assigned "
                    "or reassigned."
                ),
            )

        return TaskAssignmentResponse(
            **result["response"]
        )

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The task could not be assigned because the "
                "database operation failed."
            ),
        ) from error