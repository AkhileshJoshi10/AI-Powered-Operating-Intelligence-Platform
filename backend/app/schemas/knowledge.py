from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class KnowledgeDocumentType(str, Enum):
    """Supported business-knowledge document categories."""

    BUSINESS_RULE = "Business Rule"
    KPI_DEFINITION = "KPI Definition"
    POLICY = "Policy"
    SOP = "SOP"
    VENDOR_CONTRACT = "Vendor Contract"
    ESCALATION_RULE = "Escalation Rule"
    HISTORICAL_REPORT = "Historical Report"
    MEETING_NOTE = "Meeting Note"
    USER_GUIDE = "User Guide"
    OTHER = "Other"


class KnowledgeAccessScope(str, Enum):
    """Document visibility metadata used by retrieval filters."""

    INTERNAL = "Internal"
    MANAGEMENT = "Management"
    RESTRICTED = "Restricted"


class KnowledgeDocumentStatus(str, Enum):
    """Lifecycle status for one knowledge-document version."""

    ACTIVE = "Active"
    QUARANTINED = "Quarantined"
    SUPERSEDED = "Superseded"
    ARCHIVED = "Archived"


class KnowledgeDocumentSummary(BaseModel):
    """Compact stored-document representation."""

    model_config = ConfigDict(
        extra="forbid",
    )

    document_id: int
    logical_document_key: str
    title: str
    original_filename: str
    document_type: KnowledgeDocumentType
    mime_type: str
    file_extension: str
    checksum_sha256: str
    version_number: int
    access_scope: KnowledgeAccessScope
    source_date: date | None = None
    status: KnowledgeDocumentStatus
    prompt_injection_detected: bool
    chunk_count: int
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentUploadResponse(BaseModel):
    """Response returned after secure document ingestion."""

    model_config = ConfigDict(
        extra="forbid",
    )

    status: str
    duplicate: bool
    message: str
    document: KnowledgeDocumentSummary
    prompt_injection_matches: list[str] = Field(
        default_factory=list,
    )


class KnowledgeSearchRequest(BaseModel):
    """Controlled lexical-retrieval request."""

    model_config = ConfigDict(
        extra="forbid",
    )

    query: str = Field(
        min_length=2,
        max_length=500,
    )
    document_types: list[
        KnowledgeDocumentType
    ] = Field(
        default_factory=list,
        max_length=20,
    )
    source_date_from: date | None = None
    source_date_to: date | None = None
    metadata_filter: dict[str, Any] = Field(
        default_factory=dict,
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    @field_validator("query")
    @classmethod
    def normalize_query(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(
            value.split()
        )

        if not normalized:
            raise ValueError(
                "Search query cannot be empty."
            )

        return normalized

    @model_validator(mode="after")
    def validate_date_range(
        self,
    ) -> "KnowledgeSearchRequest":
        if (
            self.source_date_from is not None
            and self.source_date_to is not None
            and self.source_date_from
            > self.source_date_to
        ):
            raise ValueError(
                "source_date_from cannot be later than "
                "source_date_to."
            )

        return self


class KnowledgeSearchResult(BaseModel):
    """One citation-ready retrieved knowledge chunk."""

    model_config = ConfigDict(
        extra="forbid",
    )

    citation_id: str
    document_id: int
    chunk_id: int
    chunk_index: int
    title: str
    document_type: KnowledgeDocumentType
    version_number: int
    access_scope: KnowledgeAccessScope
    source_date: date | None = None
    section_title: str | None = None
    chunk_text: str
    relevance_score: float = Field(
        ge=0,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class KnowledgeSearchResponse(BaseModel):
    """Grounded retrieval response with explicit citations."""

    model_config = ConfigDict(
        extra="forbid",
    )

    status: str
    query: str
    retrieval_method: str
    result_count: int
    results: list[
        KnowledgeSearchResult
    ]
    citations: list[str]
    warnings: list[str] = Field(
        default_factory=list,
    )
