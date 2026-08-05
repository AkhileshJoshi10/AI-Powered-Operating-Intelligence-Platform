from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import settings
from backend.app.schemas.knowledge import (
    KnowledgeAccessScope,
    KnowledgeDocumentSummary,
    KnowledgeDocumentType,
    KnowledgeDocumentUploadResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from backend.app.services.knowledge_service import (
    get_knowledge_document,
    ingest_knowledge_document,
    list_knowledge_documents,
    parse_metadata_json,
    search_knowledge,
)


router = APIRouter(
    prefix="/api/knowledge",
    tags=["Knowledge"],
)


def public_access_scopes(
) -> tuple[str, ...]:
    """
    Return scopes exposed before authentication is implemented.

    Only Internal documents are exposed by the current unauthenticated
    API. Management and Restricted documents remain unavailable until
    a trusted identity and role layer is added.
    """

    return ("Internal",)


@router.post(
    "/documents/upload",
    response_model=(
        KnowledgeDocumentUploadResponse
    ),
    status_code=status.HTTP_201_CREATED,
)
async def upload_knowledge_document(
    file: Annotated[
        UploadFile,
        File(...),
    ],
    title: Annotated[
        str,
        Form(...),
    ],
    document_type: Annotated[
        KnowledgeDocumentType,
        Form(...),
    ],
    access_scope: Annotated[
        KnowledgeAccessScope,
        Form(),
    ] = KnowledgeAccessScope.INTERNAL,
    source_date: Annotated[
        date | None,
        Form(),
    ] = None,
    created_by: Annotated[
        str | None,
        Form(),
    ] = None,
    logical_document_key: Annotated[
        str | None,
        Form(),
    ] = None,
    metadata_json: Annotated[
        str,
        Form(),
    ] = "{}",
) -> dict:
    """Validate, chunk, version and store one text document."""

    try:
        file_bytes = await file.read()

        return ingest_knowledge_document(
            title=title,
            filename=(
                file.filename
                or "uploaded.txt"
            ),
            content_type=(
                file.content_type
            ),
            file_bytes=file_bytes,
            document_type=(
                document_type.value
            ),
            access_scope=(
                access_scope.value
            ),
            source_date=source_date,
            created_by=created_by,
            metadata=(
                parse_metadata_json(
                    metadata_json
                )
            ),
            logical_document_key=(
                logical_document_key
            ),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(
                error
            ),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(
                error
            ),
        ) from error

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Knowledge document could not be stored because the database operation failed."
            ),
        ) from error

    finally:
        await file.close()


@router.get(
    "/documents",
    response_model=list[
        KnowledgeDocumentSummary
    ],
)
def list_documents(
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=500,
        ),
    ] = 100,
) -> list[dict]:
    """List active Internal documents exposed by the current API."""

    try:
        return list_knowledge_documents(
            allowed_access_scopes=(
                public_access_scopes()
            ),
            status="Active",
            limit=limit,
        )

    except (
        ValueError,
        SQLAlchemyError,
    ) as error:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Knowledge documents could not be loaded because the database operation failed."
            ),
        ) from error


@router.get(
    "/documents/{document_id}",
    response_model=(
        KnowledgeDocumentSummary
    ),
)
def get_document(
    document_id: int,
) -> dict:
    """Load one visible knowledge-document summary."""

    try:
        return get_knowledge_document(
            document_id=document_id,
            allowed_access_scopes=(
                public_access_scopes()
            ),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(
                error
            ),
        ) from error

    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(
                error
            ),
        ) from error

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Knowledge document could not be loaded because the database operation failed."
            ),
        ) from error


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
)
def retrieve_knowledge(
    request: KnowledgeSearchRequest,
) -> dict:
    """Retrieve citation-ready chunks from active Internal documents."""

    try:
        return search_knowledge(
            query=request.query,
            allowed_access_scopes=(
                public_access_scopes()
            ),
            document_types=[
                document_type.value
                for document_type
                in request.document_types
            ],
            source_date_from=(
                request.source_date_from
            ),
            source_date_to=(
                request.source_date_to
            ),
            metadata_filter=(
                request.metadata_filter
            ),
            limit=request.limit,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(
                error
            ),
        ) from error

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Knowledge retrieval failed because the database operation failed."
            ),
        ) from error
