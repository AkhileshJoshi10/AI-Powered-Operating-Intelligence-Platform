from __future__ import annotations

from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable

from sqlalchemy import text
from sqlalchemy.engine import Engine

from backend.app.core.config import settings
from backend.app.db.database import engine


ALLOWED_DOCUMENT_TYPES = {
    "Business Rule",
    "KPI Definition",
    "Policy",
    "SOP",
    "Vendor Contract",
    "Escalation Rule",
    "Historical Report",
    "Meeting Note",
    "User Guide",
    "Other",
}

ALLOWED_ACCESS_SCOPES = {
    "Internal",
    "Management",
    "Restricted",
}

ALLOWED_DOCUMENT_STATUSES = {
    "Active",
    "Quarantined",
    "Superseded",
    "Archived",
}

PROMPT_INJECTION_PATTERNS: tuple[
    tuple[str, re.Pattern[str]],
    ...,
] = (
    (
        "ignore_previous_instructions",
        re.compile(
            r"\bignore\s+(?:all\s+|any\s+|the\s+)?"
            r"(?:previous|prior|above)\s+instructions?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "follow_instructions_instead",
        re.compile(
            r"\bfollow\s+(?:these|my|the following)\s+"
            r"instructions?\s+instead\b",
            re.IGNORECASE,
        ),
    ),
    (
        "system_or_developer_prompt_reference",
        re.compile(
            r"\b(?:system|developer)\s+"
            r"(?:prompt|message|instructions?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "reveal_hidden_prompt",
        re.compile(
            r"\breveal\s+(?:the\s+)?"
            r"(?:"
            r"hidden\s+(?:(?:system|developer)\s+)?"
            r"|(?:system|developer)\s+"
            r")prompt\b",
            re.IGNORECASE,
        ),
    ),
    (
        "role_tag_injection",
        re.compile(
            r"<\s*(?:system|developer|assistant)\s*>",
            re.IGNORECASE,
        ),
    ),
)


def clean_text(
    value: object,
) -> str:
    """Convert one value into compact normalized text."""

    if value is None:
        return ""

    return " ".join(
        str(value).split()
    )


def validate_controlled_value(
    value: str,
    *,
    allowed_values: set[str],
    field_name: str,
) -> str:
    """Validate one controlled text value."""

    normalized = clean_text(
        value
    )

    if normalized not in allowed_values:
        raise ValueError(
            f"{field_name} must be one of: "
            + ", ".join(
                sorted(
                    allowed_values
                )
            )
            + "."
        )

    return normalized


def parse_metadata_json(
    metadata_json: str | None,
) -> dict[str, Any]:
    """Parse upload metadata and require a JSON object."""

    normalized = (
        metadata_json.strip()
        if metadata_json is not None
        else ""
    )

    if not normalized:
        return {}

    try:
        parsed = json.loads(
            normalized
        )
    except json.JSONDecodeError as error:
        raise ValueError(
            "metadata_json must contain valid JSON."
        ) from error

    if not isinstance(
        parsed,
        dict,
    ):
        raise ValueError(
            "metadata_json must contain a JSON object."
        )

    return parsed


def build_logical_document_key(
    title: str,
) -> str:
    """Build a stable document-family key from a title."""

    normalized_title = clean_text(
        title
    ).casefold()

    if not normalized_title:
        raise ValueError(
            "Document title cannot be empty."
        )

    key = re.sub(
        r"[^a-z0-9]+",
        "-",
        normalized_title,
    ).strip("-")

    if not key:
        raise ValueError(
            "Document title must contain letters or numbers."
        )

    return key[:220]


def detect_prompt_injection(
    content_text: str,
) -> list[str]:
    """Return matched prompt-injection signal names."""

    matches: list[str] = []

    for signal_name, pattern in (
        PROMPT_INJECTION_PATTERNS
    ):
        if pattern.search(
            content_text
        ):
            matches.append(
                signal_name
            )

    return matches


def validate_and_decode_document(
    *,
    filename: str,
    content_type: str | None,
    file_bytes: bytes,
    max_file_bytes: int | None = None,
    allowed_extensions: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Validate a text document and return normalized ingestion data."""

    safe_filename = Path(
        filename
    ).name

    if not clean_text(
        safe_filename
    ):
        raise ValueError(
            "Uploaded filename cannot be empty."
        )

    extension = Path(
        safe_filename
    ).suffix.casefold()

    configured_extensions = {
        str(value).strip().casefold()
        for value in (
            allowed_extensions
            or settings.knowledge_allowed_extensions
        )
        if str(value).strip()
    }

    if extension not in configured_extensions:
        raise ValueError(
            "Unsupported knowledge-document extension. "
            "Allowed extensions: "
            + ", ".join(
                sorted(
                    configured_extensions
                )
            )
            + "."
        )

    size_limit = (
        max_file_bytes
        if max_file_bytes is not None
        else settings.knowledge_max_file_bytes
    )

    if size_limit < 1:
        raise ValueError(
            "Knowledge file-size limit must be positive."
        )

    if not file_bytes:
        raise ValueError(
            "Uploaded knowledge document is empty."
        )

    if len(file_bytes) > size_limit:
        raise ValueError(
            "Uploaded knowledge document exceeds the "
            f"{size_limit}-byte limit."
        )

    if b"\x00" in file_bytes:
        raise ValueError(
            "Binary content is not allowed in the text-document "
            "ingestion endpoint."
        )

    try:
        content_text = file_bytes.decode(
            "utf-8-sig"
        )
    except UnicodeDecodeError as error:
        raise ValueError(
            "Knowledge documents must use UTF-8 text encoding."
        ) from error

    content_text = (
        content_text
        .replace(
            "\r\n",
            "\n",
        )
        .replace(
            "\r",
            "\n",
        )
        .strip()
    )

    if not content_text:
        raise ValueError(
            "Uploaded knowledge document contains no readable text."
        )

    if extension == ".json":
        try:
            json.loads(
                content_text
            )
        except json.JSONDecodeError as error:
            raise ValueError(
                "Uploaded JSON document is not valid JSON."
            ) from error

    return {
        "safe_filename": safe_filename,
        "file_extension": extension,
        "mime_type": (
            clean_text(
                content_type
            )
            or "text/plain"
        ),
        "content_text": content_text,
        "checksum_sha256": hashlib.sha256(
            file_bytes
        ).hexdigest(),
        "file_size_bytes": len(
            file_bytes
        ),
        "prompt_injection_matches": (
            detect_prompt_injection(
                content_text
            )
        ),
    }


def find_section_title(
    content_text: str,
    position: int,
) -> str | None:
    """Return the latest Markdown heading before a character position."""

    latest_title: str | None = None

    for match in re.finditer(
        r"(?m)^#{1,6}\s+(.+?)\s*$",
        content_text[:position],
    ):
        latest_title = clean_text(
            match.group(1)
        )

    return latest_title


def estimate_token_count(
    chunk_text: str,
) -> int:
    """Return a conservative provider-independent token estimate."""

    return max(
        1,
        len(
            chunk_text.split()
        ),
        math.ceil(
            len(chunk_text) / 4
        ),
    )


def split_text_into_chunks(
    content_text: str,
    *,
    chunk_size_chars: int | None = None,
    overlap_chars: int | None = None,
    max_chunks: int | None = None,
) -> list[dict[str, Any]]:
    """Split normalized text into deterministic overlapping chunks."""

    text_value = content_text.strip()

    if not text_value:
        raise ValueError(
            "Cannot chunk empty document text."
        )

    chunk_size = (
        chunk_size_chars
        if chunk_size_chars is not None
        else settings.knowledge_chunk_size_chars
    )
    overlap = (
        overlap_chars
        if overlap_chars is not None
        else settings.knowledge_chunk_overlap_chars
    )
    maximum_chunks = (
        max_chunks
        if max_chunks is not None
        else settings.knowledge_max_chunks_per_document
    )

    if chunk_size < 200:
        raise ValueError(
            "Knowledge chunk size must be at least 200 characters."
        )

    if overlap < 0:
        raise ValueError(
            "Knowledge chunk overlap cannot be negative."
        )

    if overlap >= chunk_size:
        raise ValueError(
            "Knowledge chunk overlap must be smaller than "
            "the chunk size."
        )

    if maximum_chunks < 1:
        raise ValueError(
            "Maximum knowledge chunks must be positive."
        )

    chunks: list[dict[str, Any]] = []
    start = 0
    text_length = len(
        text_value
    )

    while start < text_length:
        target_end = min(
            start + chunk_size,
            text_length,
        )
        end = target_end

        if target_end < text_length:
            search_start = min(
                target_end,
                start + max(
                    1,
                    int(
                        chunk_size * 0.60
                    ),
                ),
            )

            best_break = max(
                text_value.rfind(
                    "\n\n",
                    search_start,
                    target_end,
                ),
                text_value.rfind(
                    "\n",
                    search_start,
                    target_end,
                ),
                text_value.rfind(
                    " ",
                    search_start,
                    target_end,
                ),
            )

            if best_break > start:
                end = best_break

        raw_chunk = text_value[
            start:end
        ]
        chunk_text = raw_chunk.strip()

        if chunk_text:
            leading_whitespace = (
                len(raw_chunk)
                - len(
                    raw_chunk.lstrip()
                )
            )
            trailing_length = len(
                raw_chunk.rstrip()
            )
            actual_start = (
                start
                + leading_whitespace
            )
            actual_end = (
                start
                + trailing_length
            )

            chunks.append(
                {
                    "chunk_index": len(
                        chunks
                    ),
                    "section_title": (
                        find_section_title(
                            text_value,
                            actual_start,
                        )
                    ),
                    "chunk_text": chunk_text,
                    "character_start": (
                        actual_start
                    ),
                    "character_end": (
                        actual_end
                    ),
                    "character_count": len(
                        chunk_text
                    ),
                    "token_estimate": (
                        estimate_token_count(
                            chunk_text
                        )
                    ),
                }
            )

        if len(chunks) > maximum_chunks:
            raise ValueError(
                "Document produced more than "
                f"{maximum_chunks} chunks."
            )

        if end >= text_length:
            break

        next_start = max(
            0,
            end - overlap,
        )

        if next_start <= start:
            next_start = end

        start = next_start

    if not chunks:
        raise ValueError(
            "No knowledge chunks were generated."
        )

    return chunks


def build_citation_id(
    *,
    document_id: int,
    version_number: int,
    chunk_index: int,
) -> str:
    """Build a stable user-visible citation identifier."""

    return (
        f"DOC-{document_id}-V{version_number}:"
        f"CHUNK-{chunk_index + 1}"
    )


def build_scope_clause(
    allowed_access_scopes: Iterable[str],
) -> tuple[str, dict[str, str]]:
    """Build a parameterized SQL IN clause for trusted scopes."""

    normalized_scopes: list[str] = []

    for scope in allowed_access_scopes:
        validated_scope = validate_controlled_value(
            str(scope),
            allowed_values=ALLOWED_ACCESS_SCOPES,
            field_name="access_scope",
        )

        if validated_scope not in normalized_scopes:
            normalized_scopes.append(
                validated_scope
            )

    if not normalized_scopes:
        raise ValueError(
            "At least one access scope must be supplied."
        )

    parameters = {
        f"scope_{index}": scope
        for index, scope in enumerate(
            normalized_scopes
        )
    }
    placeholders = ", ".join(
        f":{parameter_name}"
        for parameter_name in parameters
    )

    return (
        f"d.access_scope IN ({placeholders})",
        parameters,
    )


def row_to_document_summary(
    row: dict[str, Any],
) -> dict[str, Any]:
    """Convert a stored row into API-safe document data."""

    metadata = row.get(
        "metadata"
    )

    if not isinstance(
        metadata,
        dict,
    ):
        metadata = {}

    return {
        "document_id": int(
            row["document_id"]
        ),
        "logical_document_key": str(
            row["logical_document_key"]
        ),
        "title": str(
            row["title"]
        ),
        "original_filename": str(
            row["original_filename"]
        ),
        "document_type": str(
            row["document_type"]
        ),
        "mime_type": str(
            row["mime_type"]
        ),
        "file_extension": str(
            row["file_extension"]
        ),
        "checksum_sha256": str(
            row["checksum_sha256"]
        ),
        "version_number": int(
            row["version_number"]
        ),
        "access_scope": str(
            row["access_scope"]
        ),
        "source_date": row.get(
            "source_date"
        ),
        "status": str(
            row["status"]
        ),
        "prompt_injection_detected": bool(
            row["prompt_injection_detected"]
        ),
        "chunk_count": int(
            row.get(
                "chunk_count",
                0,
            )
        ),
        "metadata": metadata,
        "created_by": row.get(
            "created_by"
        ),
        "created_at": row[
            "created_at"
        ],
        "updated_at": row[
            "updated_at"
        ],
    }


def ingest_knowledge_document(
    *,
    title: str,
    filename: str,
    content_type: str | None,
    file_bytes: bytes,
    document_type: str,
    access_scope: str,
    source_date: date | None,
    created_by: str | None,
    metadata: dict[str, Any],
    logical_document_key: str | None = None,
    database_engine: Engine | None = None,
) -> dict[str, Any]:
    """Validate, version, chunk and persist one knowledge document."""

    if not settings.knowledge_enabled:
        raise RuntimeError(
            "Knowledge ingestion is disabled."
        )

    normalized_title = clean_text(
        title
    )

    if not normalized_title:
        raise ValueError(
            "Document title cannot be empty."
        )

    normalized_document_type = (
        validate_controlled_value(
            document_type,
            allowed_values=(
                ALLOWED_DOCUMENT_TYPES
            ),
            field_name="document_type",
        )
    )
    normalized_access_scope = (
        validate_controlled_value(
            access_scope,
            allowed_values=(
                ALLOWED_ACCESS_SCOPES
            ),
            field_name="access_scope",
        )
    )

    validated_file = (
        validate_and_decode_document(
            filename=filename,
            content_type=content_type,
            file_bytes=file_bytes,
        )
    )

    prompt_matches = list(
        validated_file[
            "prompt_injection_matches"
        ]
    )
    prompt_injection_detected = bool(
        prompt_matches
    )
    document_status = (
        "Quarantined"
        if prompt_injection_detected
        else "Active"
    )

    document_key = (
        build_logical_document_key(
            logical_document_key
            or normalized_title
        )
    )

    chunks = split_text_into_chunks(
        validated_file["content_text"]
    )

    active_engine = (
        database_engine
        or engine
    )

    with active_engine.begin() as connection:
        duplicate_row = connection.execute(
            text(
                """
                SELECT
                    d.document_id,
                    d.logical_document_key,
                    d.title,
                    d.original_filename,
                    d.document_type,
                    d.mime_type,
                    d.file_extension,
                    d.checksum_sha256,
                    d.version_number,
                    d.access_scope,
                    d.source_date,
                    d.status,
                    d.prompt_injection_detected,
                    d.metadata,
                    d.created_by,
                    d.created_at,
                    d.updated_at,
                    COUNT(c.chunk_id) AS chunk_count
                FROM knowledge_documents AS d
                LEFT JOIN knowledge_chunks AS c
                    ON c.document_id = d.document_id
                WHERE
                    d.checksum_sha256 = :checksum_sha256
                GROUP BY d.document_id
                ORDER BY d.document_id DESC
                LIMIT 1;
                """
            ),
            {
                "checksum_sha256": (
                    validated_file[
                        "checksum_sha256"
                    ]
                ),
            },
        ).mappings().first()

        if duplicate_row is not None:
            return {
                "status": "success",
                "duplicate": True,
                "message": (
                    "An identical knowledge document already exists."
                ),
                "document": (
                    row_to_document_summary(
                        dict(
                            duplicate_row
                        )
                    )
                ),
                "prompt_injection_matches": (
                    prompt_matches
                ),
            }

        version_number = int(
            connection.execute(
                text(
                    """
                    SELECT
                        COALESCE(
                            MAX(version_number),
                            0
                        ) + 1
                    FROM knowledge_documents
                    WHERE
                        logical_document_key
                        = :logical_document_key;
                    """
                ),
                {
                    "logical_document_key": (
                        document_key
                    ),
                },
            ).scalar_one()
        )

        if document_status == "Active":
            connection.execute(
                text(
                    """
                    UPDATE knowledge_documents
                    SET
                        status = 'Superseded',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE
                        logical_document_key
                        = :logical_document_key
                        AND status = 'Active';
                    """
                ),
                {
                    "logical_document_key": (
                        document_key
                    ),
                },
            )

        inserted_document = connection.execute(
            text(
                """
                INSERT INTO knowledge_documents (
                    logical_document_key,
                    title,
                    original_filename,
                    document_type,
                    mime_type,
                    file_extension,
                    checksum_sha256,
                    file_size_bytes,
                    content_text,
                    version_number,
                    access_scope,
                    source_date,
                    status,
                    prompt_injection_detected,
                    prompt_injection_matches,
                    metadata,
                    created_by
                )
                VALUES (
                    :logical_document_key,
                    :title,
                    :original_filename,
                    :document_type,
                    :mime_type,
                    :file_extension,
                    :checksum_sha256,
                    :file_size_bytes,
                    :content_text,
                    :version_number,
                    :access_scope,
                    :source_date,
                    :status,
                    :prompt_injection_detected,
                    CAST(
                        :prompt_matches_json
                        AS JSONB
                    ),
                    CAST(
                        :metadata_json
                        AS JSONB
                    ),
                    :created_by
                )
                RETURNING
                    document_id,
                    logical_document_key,
                    title,
                    original_filename,
                    document_type,
                    mime_type,
                    file_extension,
                    checksum_sha256,
                    version_number,
                    access_scope,
                    source_date,
                    status,
                    prompt_injection_detected,
                    metadata,
                    created_by,
                    created_at,
                    updated_at;
                """
            ),
            {
                "logical_document_key": document_key,
                "title": normalized_title,
                "original_filename": (
                    validated_file[
                        "safe_filename"
                    ]
                ),
                "document_type": (
                    normalized_document_type
                ),
                "mime_type": (
                    validated_file[
                        "mime_type"
                    ]
                ),
                "file_extension": (
                    validated_file[
                        "file_extension"
                    ]
                ),
                "checksum_sha256": (
                    validated_file[
                        "checksum_sha256"
                    ]
                ),
                "file_size_bytes": (
                    validated_file[
                        "file_size_bytes"
                    ]
                ),
                "content_text": (
                    validated_file[
                        "content_text"
                    ]
                ),
                "version_number": (
                    version_number
                ),
                "access_scope": (
                    normalized_access_scope
                ),
                "source_date": source_date,
                "status": (
                    document_status
                ),
                "prompt_injection_detected": (
                    prompt_injection_detected
                ),
                "prompt_matches_json": (
                    json.dumps(
                        prompt_matches
                    )
                ),
                "metadata_json": (
                    json.dumps(
                        metadata
                    )
                ),
                "created_by": (
                    clean_text(
                        created_by
                    )
                    or None
                ),
            },
        ).mappings().one()

        document_id = int(
            inserted_document[
                "document_id"
            ]
        )

        for chunk in chunks:
            connection.execute(
                text(
                    """
                    INSERT INTO knowledge_chunks (
                        document_id,
                        chunk_index,
                        section_title,
                        chunk_text,
                        character_start,
                        character_end,
                        character_count,
                        token_estimate,
                        metadata
                    )
                    VALUES (
                        :document_id,
                        :chunk_index,
                        :section_title,
                        :chunk_text,
                        :character_start,
                        :character_end,
                        :character_count,
                        :token_estimate,
                        CAST(
                            :metadata_json
                            AS JSONB
                        )
                    );
                    """
                ),
                {
                    "document_id": (
                        document_id
                    ),
                    "chunk_index": (
                        chunk[
                            "chunk_index"
                        ]
                    ),
                    "section_title": (
                        chunk[
                            "section_title"
                        ]
                    ),
                    "chunk_text": (
                        chunk[
                            "chunk_text"
                        ]
                    ),
                    "character_start": (
                        chunk[
                            "character_start"
                        ]
                    ),
                    "character_end": (
                        chunk[
                            "character_end"
                        ]
                    ),
                    "character_count": (
                        chunk[
                            "character_count"
                        ]
                    ),
                    "token_estimate": (
                        chunk[
                            "token_estimate"
                        ]
                    ),
                    "metadata_json": (
                        json.dumps(
                            {
                                "document_type": (
                                    normalized_document_type
                                ),
                                "access_scope": (
                                    normalized_access_scope
                                ),
                                "source_date": (
                                    source_date.isoformat()
                                    if source_date
                                    else None
                                ),
                            }
                        )
                    ),
                },
            )

        stored_document = dict(
            inserted_document
        )
        stored_document[
            "chunk_count"
        ] = len(
            chunks
        )

    return {
        "status": "success",
        "duplicate": False,
        "message": (
            "Knowledge document was quarantined because "
            "prompt-injection signals were detected."
            if prompt_injection_detected
            else (
                "Knowledge document was validated, versioned, "
                "chunked, and stored successfully."
            )
        ),
        "document": (
            row_to_document_summary(
                stored_document
            )
        ),
        "prompt_injection_matches": (
            prompt_matches
        ),
    }


def list_knowledge_documents(
    *,
    allowed_access_scopes: Iterable[str],
    status: str = "Active",
    limit: int = 100,
    database_engine: Engine | None = None,
) -> list[dict[str, Any]]:
    """List documents visible to supplied trusted scopes."""

    normalized_status = validate_controlled_value(
        status,
        allowed_values=(
            ALLOWED_DOCUMENT_STATUSES
        ),
        field_name="status",
    )

    if limit < 1 or limit > 500:
        raise ValueError(
            "Document list limit must be between 1 and 500."
        )

    scope_clause, scope_parameters = (
        build_scope_clause(
            allowed_access_scopes
        )
    )

    query = f"""
        SELECT
            d.document_id,
            d.logical_document_key,
            d.title,
            d.original_filename,
            d.document_type,
            d.mime_type,
            d.file_extension,
            d.checksum_sha256,
            d.version_number,
            d.access_scope,
            d.source_date,
            d.status,
            d.prompt_injection_detected,
            d.metadata,
            d.created_by,
            d.created_at,
            d.updated_at,
            COUNT(c.chunk_id) AS chunk_count
        FROM knowledge_documents AS d
        LEFT JOIN knowledge_chunks AS c
            ON c.document_id = d.document_id
        WHERE
            d.status = :status
            AND {scope_clause}
        GROUP BY d.document_id
        ORDER BY
            d.updated_at DESC,
            d.document_id DESC
        LIMIT :limit;
    """

    active_engine = (
        database_engine
        or engine
    )

    with active_engine.connect() as connection:
        rows = connection.execute(
            text(
                query
            ),
            {
                "status": normalized_status,
                "limit": limit,
                **scope_parameters,
            },
        ).mappings().all()

    return [
        row_to_document_summary(
            dict(
                row
            )
        )
        for row in rows
    ]


def get_knowledge_document(
    *,
    document_id: int,
    allowed_access_scopes: Iterable[str],
    database_engine: Engine | None = None,
) -> dict[str, Any]:
    """Load one visible knowledge-document summary."""

    if document_id < 1:
        raise ValueError(
            "document_id must be positive."
        )

    scope_clause, scope_parameters = (
        build_scope_clause(
            allowed_access_scopes
        )
    )

    query = f"""
        SELECT
            d.document_id,
            d.logical_document_key,
            d.title,
            d.original_filename,
            d.document_type,
            d.mime_type,
            d.file_extension,
            d.checksum_sha256,
            d.version_number,
            d.access_scope,
            d.source_date,
            d.status,
            d.prompt_injection_detected,
            d.metadata,
            d.created_by,
            d.created_at,
            d.updated_at,
            COUNT(c.chunk_id) AS chunk_count
        FROM knowledge_documents AS d
        LEFT JOIN knowledge_chunks AS c
            ON c.document_id = d.document_id
        WHERE
            d.document_id = :document_id
            AND {scope_clause}
        GROUP BY d.document_id;
    """

    active_engine = (
        database_engine
        or engine
    )

    with active_engine.connect() as connection:
        row = connection.execute(
            text(
                query
            ),
            {
                "document_id": document_id,
                **scope_parameters,
            },
        ).mappings().first()

    if row is None:
        raise LookupError(
            "Knowledge document was not found."
        )

    return row_to_document_summary(
        dict(
            row
        )
    )


def search_knowledge(
    *,
    query: str,
    allowed_access_scopes: Iterable[str],
    document_types: list[str] | None = None,
    source_date_from: date | None = None,
    source_date_to: date | None = None,
    metadata_filter: dict[str, Any] | None = None,
    limit: int | None = None,
    database_engine: Engine | None = None,
) -> dict[str, Any]:
    """Search active chunks using PostgreSQL full-text ranking."""

    normalized_query = clean_text(
        query
    )

    if len(normalized_query) < 2:
        raise ValueError(
            "Knowledge search query must contain at least "
            "two characters."
        )

    result_limit = (
        limit
        if limit is not None
        else settings.knowledge_default_search_limit
    )

    if (
        result_limit < 1
        or result_limit
        > settings.knowledge_max_search_limit
    ):
        raise ValueError(
            "Knowledge search limit must be between 1 and "
            f"{settings.knowledge_max_search_limit}."
        )

    if (
        source_date_from is not None
        and source_date_to is not None
        and source_date_from > source_date_to
    ):
        raise ValueError(
            "source_date_from cannot be later than "
            "source_date_to."
        )

    scopes = tuple(
        allowed_access_scopes
    )
    scope_clause, parameters = (
        build_scope_clause(
            scopes
        )
    )

    where_clauses = [
        "d.status = 'Active'",
        scope_clause,
        (
            "to_tsvector('english', c.chunk_text) "
            "@@ websearch_to_tsquery('english', :query)"
        ),
    ]

    parameters.update(
        {
            "query": normalized_query,
            "limit": result_limit,
        }
    )

    normalized_document_types: list[str] = []

    for document_type in (
        document_types
        or []
    ):
        validated_type = validate_controlled_value(
            document_type,
            allowed_values=(
                ALLOWED_DOCUMENT_TYPES
            ),
            field_name="document_type",
        )

        if (
            validated_type
            not in normalized_document_types
        ):
            normalized_document_types.append(
                validated_type
            )

    if normalized_document_types:
        placeholders: list[str] = []

        for index, document_type in enumerate(
            normalized_document_types
        ):
            parameter_name = (
                f"document_type_{index}"
            )
            parameters[
                parameter_name
            ] = document_type
            placeholders.append(
                f":{parameter_name}"
            )

        where_clauses.append(
            "d.document_type IN ("
            + ", ".join(
                placeholders
            )
            + ")"
        )

    if source_date_from is not None:
        where_clauses.append(
            "d.source_date >= :source_date_from"
        )
        parameters[
            "source_date_from"
        ] = source_date_from

    if source_date_to is not None:
        where_clauses.append(
            "d.source_date <= :source_date_to"
        )
        parameters[
            "source_date_to"
        ] = source_date_to

    if metadata_filter:
        where_clauses.append(
            "d.metadata @> "
            "CAST(:metadata_filter_json AS JSONB)"
        )
        parameters[
            "metadata_filter_json"
        ] = json.dumps(
            metadata_filter
        )

    query_sql = """
        SELECT
            c.chunk_id,
            c.chunk_index,
            c.section_title,
            c.chunk_text,
            d.document_id,
            d.title,
            d.document_type,
            d.version_number,
            d.access_scope,
            d.source_date,
            d.metadata AS document_metadata,
            ts_rank_cd(
                to_tsvector(
                    'english',
                    c.chunk_text
                ),
                websearch_to_tsquery(
                    'english',
                    :query
                )
            ) AS relevance_score
        FROM knowledge_chunks AS c
        INNER JOIN knowledge_documents AS d
            ON d.document_id = c.document_id
        WHERE
    """ + "\n AND ".join(
        where_clauses
    ) + """
        ORDER BY
            relevance_score DESC,
            d.document_id ASC,
            c.chunk_index ASC
        LIMIT :limit;
    """

    active_engine = (
        database_engine
        or engine
    )

    with active_engine.begin() as connection:
        rows = connection.execute(
            text(
                query_sql
            ),
            parameters,
        ).mappings().all()

        results: list[
            dict[str, Any]
        ] = []

        for raw_row in rows:
            row = dict(
                raw_row
            )
            citation_id = build_citation_id(
                document_id=int(
                    row["document_id"]
                ),
                version_number=int(
                    row["version_number"]
                ),
                chunk_index=int(
                    row["chunk_index"]
                ),
            )

            document_metadata = row.get(
                "document_metadata"
            )

            if not isinstance(
                document_metadata,
                dict,
            ):
                document_metadata = {}

            results.append(
                {
                    "citation_id": citation_id,
                    "document_id": int(
                        row["document_id"]
                    ),
                    "chunk_id": int(
                        row["chunk_id"]
                    ),
                    "chunk_index": int(
                        row["chunk_index"]
                    ),
                    "title": str(
                        row["title"]
                    ),
                    "document_type": str(
                        row["document_type"]
                    ),
                    "version_number": int(
                        row["version_number"]
                    ),
                    "access_scope": str(
                        row["access_scope"]
                    ),
                    "source_date": row.get(
                        "source_date"
                    ),
                    "section_title": row.get(
                        "section_title"
                    ),
                    "chunk_text": str(
                        row["chunk_text"]
                    ),
                    "relevance_score": round(
                        float(
                            row[
                                "relevance_score"
                            ]
                            or 0.0
                        ),
                        6,
                    ),
                    "metadata": (
                        document_metadata
                    ),
                }
            )

        citations = [
            result["citation_id"]
            for result in results
        ]

        connection.execute(
            text(
                """
                INSERT INTO knowledge_retrieval_logs (
                    search_query,
                    retrieval_method,
                    access_scopes,
                    filters,
                    result_count,
                    returned_citations
                )
                VALUES (
                    :search_query,
                    'PostgreSQL Full-Text Search',
                    CAST(
                        :access_scopes_json
                        AS JSONB
                    ),
                    CAST(
                        :filters_json
                        AS JSONB
                    ),
                    :result_count,
                    CAST(
                        :citations_json
                        AS JSONB
                    )
                );
                """
            ),
            {
                "search_query": (
                    normalized_query
                ),
                "access_scopes_json": (
                    json.dumps(
                        list(
                            scopes
                        )
                    )
                ),
                "filters_json": (
                    json.dumps(
                        {
                            "document_types": (
                                normalized_document_types
                            ),
                            "source_date_from": (
                                source_date_from.isoformat()
                                if source_date_from
                                else None
                            ),
                            "source_date_to": (
                                source_date_to.isoformat()
                                if source_date_to
                                else None
                            ),
                            "metadata_filter": (
                                metadata_filter
                                or {}
                            ),
                        }
                    )
                ),
                "result_count": len(
                    results
                ),
                "citations_json": (
                    json.dumps(
                        citations
                    )
                ),
            },
        )

    return {
        "status": "success",
        "query": normalized_query,
        "retrieval_method": (
            "PostgreSQL Full-Text Search"
        ),
        "result_count": len(
            results
        ),
        "results": results,
        "citations": citations,
        "warnings": [
            (
                "This Part 1 retrieval uses PostgreSQL full-text "
                "search. Vector similarity is added in Day 34 Part 2."
            )
        ],
    }