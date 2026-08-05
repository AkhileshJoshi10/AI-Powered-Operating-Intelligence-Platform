CREATE TABLE IF NOT EXISTS knowledge_documents (
    document_id BIGSERIAL PRIMARY KEY,
    logical_document_key VARCHAR(220) NOT NULL,
    title TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    mime_type VARCHAR(150) NOT NULL,
    file_extension VARCHAR(20) NOT NULL,
    checksum_sha256 CHAR(64) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    content_text TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    access_scope VARCHAR(30) NOT NULL DEFAULT 'Internal',
    source_date DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    prompt_injection_detected BOOLEAN NOT NULL DEFAULT FALSE,
    prompt_injection_matches JSONB NOT NULL DEFAULT '[]'::JSONB,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_by VARCHAR(150),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT knowledge_documents_type_check
        CHECK (
            document_type IN (
                'Business Rule',
                'KPI Definition',
                'Policy',
                'SOP',
                'Vendor Contract',
                'Escalation Rule',
                'Historical Report',
                'Meeting Note',
                'User Guide',
                'Other'
            )
        ),

    CONSTRAINT knowledge_documents_access_scope_check
        CHECK (
            access_scope IN (
                'Internal',
                'Management',
                'Restricted'
            )
        ),

    CONSTRAINT knowledge_documents_status_check
        CHECK (
            status IN (
                'Active',
                'Quarantined',
                'Superseded',
                'Archived'
            )
        ),

    CONSTRAINT knowledge_documents_version_check
        CHECK (version_number >= 1),

    CONSTRAINT knowledge_documents_file_size_check
        CHECK (file_size_bytes > 0),

    CONSTRAINT knowledge_documents_checksum_check
        CHECK (
            checksum_sha256
            ~ '^[0-9a-f]{64}$'
        ),

    CONSTRAINT knowledge_documents_prompt_matches_json_check
        CHECK (
            JSONB_TYPEOF(
                prompt_injection_matches
            ) = 'array'
        ),

    CONSTRAINT knowledge_documents_metadata_json_check
        CHECK (
            JSONB_TYPEOF(metadata) = 'object'
        ),

    CONSTRAINT knowledge_documents_quarantine_check
        CHECK (
            NOT prompt_injection_detected
            OR status IN (
                'Quarantined',
                'Archived'
            )
        ),

    CONSTRAINT knowledge_documents_version_unique
        UNIQUE (
            logical_document_key,
            version_number
        ),

    CONSTRAINT knowledge_documents_checksum_unique
        UNIQUE (checksum_sha256)
);


CREATE TABLE IF NOT EXISTS knowledge_chunks (
    chunk_id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL
        REFERENCES knowledge_documents(document_id)
        ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    section_title TEXT,
    chunk_text TEXT NOT NULL,
    character_start INTEGER NOT NULL,
    character_end INTEGER NOT NULL,
    character_count INTEGER NOT NULL,
    token_estimate INTEGER NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    embedding_status VARCHAR(30) NOT NULL DEFAULT 'Not Generated',
    embedding_provider VARCHAR(100),
    embedding_model VARCHAR(200),
    embedding_dimensions INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT knowledge_chunks_index_check
        CHECK (chunk_index >= 0),

    CONSTRAINT knowledge_chunks_character_range_check
        CHECK (
            character_start >= 0
            AND character_end >= character_start
            AND character_count > 0
        ),

    CONSTRAINT knowledge_chunks_token_estimate_check
        CHECK (token_estimate > 0),

    CONSTRAINT knowledge_chunks_metadata_json_check
        CHECK (
            JSONB_TYPEOF(metadata) = 'object'
        ),

    CONSTRAINT knowledge_chunks_embedding_status_check
        CHECK (
            embedding_status IN (
                'Not Generated',
                'Pending',
                'Complete',
                'Failed'
            )
        ),

    CONSTRAINT knowledge_chunks_embedding_dimensions_check
        CHECK (
            embedding_dimensions IS NULL
            OR embedding_dimensions > 0
        ),

    CONSTRAINT knowledge_chunks_document_index_unique
        UNIQUE (
            document_id,
            chunk_index
        )
);


CREATE TABLE IF NOT EXISTS knowledge_retrieval_logs (
    retrieval_log_id BIGSERIAL PRIMARY KEY,
    search_query TEXT NOT NULL,
    retrieval_method VARCHAR(100) NOT NULL,
    access_scopes JSONB NOT NULL DEFAULT '[]'::JSONB,
    filters JSONB NOT NULL DEFAULT '{}'::JSONB,
    result_count INTEGER NOT NULL DEFAULT 0,
    returned_citations JSONB NOT NULL DEFAULT '[]'::JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT knowledge_retrieval_result_count_check
        CHECK (result_count >= 0),

    CONSTRAINT knowledge_retrieval_access_scopes_json_check
        CHECK (
            JSONB_TYPEOF(access_scopes) = 'array'
        ),

    CONSTRAINT knowledge_retrieval_filters_json_check
        CHECK (
            JSONB_TYPEOF(filters) = 'object'
        ),

    CONSTRAINT knowledge_retrieval_citations_json_check
        CHECK (
            JSONB_TYPEOF(
                returned_citations
            ) = 'array'
        )
);


CREATE INDEX IF NOT EXISTS idx_knowledge_documents_family
    ON knowledge_documents (
        logical_document_key,
        version_number DESC
    );


CREATE INDEX IF NOT EXISTS idx_knowledge_documents_status_scope
    ON knowledge_documents (
        status,
        access_scope,
        document_type
    );


CREATE INDEX IF NOT EXISTS idx_knowledge_documents_source_date
    ON knowledge_documents (
        source_date DESC
    )
    WHERE source_date IS NOT NULL;


CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document
    ON knowledge_chunks (
        document_id,
        chunk_index
    );


CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_full_text
    ON knowledge_chunks
    USING GIN (
        to_tsvector(
            'english',
            chunk_text
        )
    );


CREATE INDEX IF NOT EXISTS idx_knowledge_retrieval_created
    ON knowledge_retrieval_logs (
        created_at DESC
    );