from __future__ import annotations

from hmac import compare_digest
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Path,
    Query,
    status,
)
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import settings
from backend.app.schemas.executive_briefs import (
    GenerateExecutiveBriefResponse,
    LatestExecutiveBriefResponse,
)
from backend.app.schemas.automations import (
    AutomationCallbackRequest,
    AutomationCallbackResponse,
    AutomationLogDetailResponse,
    AutomationLogListResponse,
    AutomationTriggerResponse,
    IssueAutomationTriggerRequest,
    TaskAutomationTriggerRequest,
)
from backend.app.services.executive_brief_service import (
    generate_daily_executive_brief,
    get_latest_executive_brief,
)
from backend.app.services.automation_service import (
    get_automation_log_detail,
    get_automation_log_list,
    prepare_daily_executive_brief_delivery,
    record_n8n_callback,
    trigger_high_priority_alert,
    trigger_overdue_escalation,
    trigger_task_reminder,
)


router = APIRouter(
    prefix="/api",
    tags=["Automations"],
)


CALLBACK_SECRET_HEADER = "X-N8N-Callback-Secret"
AUTOMATION_API_SECRET_HEADER = "X-Automation-API-Secret"
N8N_SERVICE_SECRET_HEADER = "X-N8N-Service-Secret"


def require_n8n_callback_secret(
    provided_secret: Annotated[
        str | None,
        Header(
            alias=CALLBACK_SECRET_HEADER,
        ),
    ] = None,
) -> None:
    """Authenticate n8n callbacks without exposing the configured secret."""

    configured_secret = settings.n8n_callback_secret

    if not configured_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The n8n callback authentication secret is not "
                "configured."
            ),
        )

    if (
        provided_secret is None
        or not compare_digest(
            provided_secret,
            configured_secret,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid n8n callback credentials.",
        )



def require_automation_api_secret(
    provided_secret: Annotated[
        str | None,
        Header(
            alias=AUTOMATION_API_SECRET_HEADER,
        ),
    ] = None,
) -> None:
    """Authenticate requests that are allowed to trigger workflows."""

    configured_secret = settings.automation_api_secret

    if not configured_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The automation trigger authentication secret is not "
                "configured."
            ),
        )

    if (
        provided_secret is None
        or not compare_digest(
            provided_secret,
            configured_secret,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid automation trigger credentials.",
        )

def require_n8n_service_secret(
    provided_secret: Annotated[
        str | None,
        Header(
            alias=N8N_SERVICE_SECRET_HEADER,
        ),
    ] = None,
) -> None:
    """Authenticate scheduled n8n service calls to protected APIs."""

    configured_secret = settings.n8n_service_secret

    if not configured_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The n8n service authentication secret is not "
                "configured."
            ),
        )

    if (
        provided_secret is None
        or not compare_digest(
            provided_secret,
            configured_secret,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid n8n service credentials.",
        )


def _raise_trigger_outcome(
    result: dict,
) -> None:
    outcome = result[
        "outcome"
    ]

    if outcome == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "The requested automation source record was not found."
            ),
        )

    if outcome == "invalid_state":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result[
                "reason"
            ],
        )

    if outcome == "disabled":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Automation execution is currently disabled."
            ),
        )

    if outcome == "not_configured":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The n8n automation connection is not fully configured."
            ),
        )

    if outcome == "delivery_failed":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The workflow request could not be delivered to n8n. "
                "The failed attempt was recorded in automation logs."
            ),
        )


@router.get(
    "/automation-logs",
    response_model=AutomationLogListResponse,
    summary="Get automation execution logs",
)
def list_automation_logs(
    execution_status: Annotated[
        str | None,
        Query(
            alias="status",
            min_length=1,
            max_length=50,
        ),
    ] = None,
    action_type: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=150,
        ),
    ] = None,
    workflow_name: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=150,
        ),
    ] = None,
    task_id: Annotated[
        int | None,
        Query(
            ge=1,
        ),
    ] = None,
    issue_id: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=220,
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
        ),
    ] = 20,
    offset: Annotated[
        int,
        Query(
            ge=0,
        ),
    ] = 0,
) -> AutomationLogListResponse:
    """Return filtered and paginated workflow execution history."""

    try:
        response_data = get_automation_log_list(
            execution_status=execution_status,
            action_type=action_type,
            workflow_name=workflow_name,
            task_id=task_id,
            issue_id=issue_id,
            limit=limit,
            offset=offset,
        )

        return AutomationLogListResponse(
            **response_data
        )

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Automation logs could not be loaded because the "
                "database operation failed."
            ),
        ) from error


@router.get(
    "/automation-logs/{automation_log_id}",
    response_model=AutomationLogDetailResponse,
    summary="Get one automation execution log",
)
def read_automation_log(
    automation_log_id: Annotated[
        int,
        Path(
            ge=1,
        ),
    ],
) -> AutomationLogDetailResponse:
    """Return one automation log by database identifier."""

    try:
        response_data = get_automation_log_detail(
            automation_log_id
        )

        if response_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "The requested automation log was not found."
                ),
            )

        return AutomationLogDetailResponse(
            **response_data
        )

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The automation log could not be loaded because the "
                "database operation failed."
            ),
        ) from error


@router.post(
    "/automations/log",
    response_model=AutomationCallbackResponse,
    summary="Record an authenticated n8n execution result",
)
def create_automation_log_callback(
    callback: AutomationCallbackRequest,
    _: Annotated[
        None,
        Depends(
            require_n8n_callback_secret
        ),
    ],
) -> AutomationCallbackResponse:
    """Receive one protected completion/failure callback from n8n."""

    try:
        result = record_n8n_callback(
            idempotency_key=callback.idempotency_key,
            execution_status=callback.execution_status,
            n8n_execution_id=callback.n8n_execution_id,
            message=callback.message,
            error_type=callback.error_type,
            error_message=callback.error_message,
        )

        outcome = result[
            "outcome"
        ]

        if outcome == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "No automation request exists for the supplied "
                    "idempotency key."
                ),
            )

        if outcome == "conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "The automation already has terminal status "
                    f"'{result['current_status']}' and cannot be "
                    "overwritten by a conflicting callback."
                ),
            )

        return AutomationCallbackResponse(
            **result[
                "response"
            ]
        )

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The automation callback could not be recorded because "
                "the database operation failed."
            ),
        ) from error


@router.post(
    "/automations/daily-executive-brief/prepare",
    response_model=AutomationTriggerResponse,
    summary="Prepare today's scheduled Executive Brief delivery",
)
def prepare_daily_executive_brief(
    _: Annotated[
        None,
        Depends(
            require_n8n_service_secret
        ),
    ],
) -> AutomationTriggerResponse:
    """Create today's idempotent automation-log anchor for n8n."""

    try:
        result = prepare_daily_executive_brief_delivery()

        if result["outcome"] not in {
            "success",
            "duplicate",
        }:
            _raise_trigger_outcome(result)

        return AutomationTriggerResponse(
            **result["response"]
        )

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The scheduled Executive Brief delivery could not be "
                "prepared because the database operation failed."
            ),
        ) from error


@router.post(
    "/automations/daily-executive-brief/generate",
    response_model=GenerateExecutiveBriefResponse,
    summary="Generate today's Executive Brief for the n8n service",
)
def generate_daily_executive_brief_for_n8n(
    _: Annotated[
        None,
        Depends(
            require_n8n_service_secret
        ),
    ],
) -> GenerateExecutiveBriefResponse:
    """Generate the deterministic brief through a protected service route."""

    try:
        response_data = generate_daily_executive_brief()

        return GenerateExecutiveBriefResponse(
            **response_data
        )

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The Daily Executive Brief could not be generated "
                "because a database operation failed."
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
                "The Daily Executive Brief could not be generated "
                "from the current business data."
            ),
        ) from error


@router.get(
    "/automations/daily-executive-brief/latest",
    response_model=LatestExecutiveBriefResponse,
    summary="Get the latest Executive Brief for the n8n service",
)
def read_latest_executive_brief_for_n8n(
    _: Annotated[
        None,
        Depends(
            require_n8n_service_secret
        ),
    ],
) -> LatestExecutiveBriefResponse:
    """Return the latest stored brief through a protected service route."""

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


@router.post(
    "/automations/high-priority-alert",
    response_model=AutomationTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a high-priority issue alert",
)
def create_high_priority_alert(
    request: IssueAutomationTriggerRequest,
    _: Annotated[
        None,
        Depends(
            require_automation_api_secret
        ),
    ],
) -> AutomationTriggerResponse:
    """Trigger the configured high-priority alert workflow."""

    try:
        result = trigger_high_priority_alert(
            request.issue_id
        )

        if result[
            "outcome"
        ] not in {
            "success",
            "duplicate",
        }:
            _raise_trigger_outcome(
                result
            )

        return AutomationTriggerResponse(
            **result[
                "response"
            ]
        )

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The alert workflow could not be prepared because the "
                "database operation failed."
            ),
        ) from error


@router.post(
    "/automations/task-reminder",
    response_model=AutomationTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a task reminder",
)
def create_task_reminder(
    request: TaskAutomationTriggerRequest,
    _: Annotated[
        None,
        Depends(
            require_automation_api_secret
        ),
    ],
) -> AutomationTriggerResponse:
    """Trigger the configured task-reminder workflow."""

    try:
        result = trigger_task_reminder(
            request.task_id
        )

        if result[
            "outcome"
        ] not in {
            "success",
            "duplicate",
        }:
            _raise_trigger_outcome(
                result
            )

        return AutomationTriggerResponse(
            **result[
                "response"
            ]
        )

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The reminder workflow could not be prepared because "
                "the database operation failed."
            ),
        ) from error


@router.post(
    "/automations/overdue-escalation",
    response_model=AutomationTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger an overdue-task escalation",
)
def create_overdue_escalation(
    request: TaskAutomationTriggerRequest,
    _: Annotated[
        None,
        Depends(
            require_automation_api_secret
        ),
    ],
) -> AutomationTriggerResponse:
    """Trigger the configured overdue-task escalation workflow."""

    try:
        result = trigger_overdue_escalation(
            request.task_id
        )

        if result[
            "outcome"
        ] not in {
            "success",
            "duplicate",
        }:
            _raise_trigger_outcome(
                result
            )

        return AutomationTriggerResponse(
            **result[
                "response"
            ]
        )

    except HTTPException:
        raise

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The escalation workflow could not be prepared because "
                "the database operation failed."
            ),
        ) from error
