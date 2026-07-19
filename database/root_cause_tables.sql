CREATE TABLE IF NOT EXISTS root_cause_analyses (
    root_cause_analysis_id BIGSERIAL PRIMARY KEY,
    issue_id VARCHAR(220) NOT NULL UNIQUE
        REFERENCES issues(issue_id)
        ON DELETE CASCADE,

    root_cause_category VARCHAR(200) NOT NULL,
    root_cause_summary TEXT NOT NULL,
    root_cause_explanation TEXT NOT NULL,

    confidence_score NUMERIC(5, 2) NOT NULL,
    supporting_evidence JSONB NOT NULL DEFAULT '[]'::JSONB,
    evidence_count INTEGER NOT NULL DEFAULT 0,

    analysis_status VARCHAR(50) NOT NULL DEFAULT 'Generated',
    review_status VARCHAR(50) NOT NULL DEFAULT 'Pending Review',
    reviewer_name VARCHAR(150),
    review_notes TEXT,

    analysis_version INTEGER NOT NULL DEFAULT 1,

    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT root_cause_analysis_status_check
        CHECK (analysis_status IN ('Generated', 'Reviewed', 'Superseded')),

    CONSTRAINT root_cause_review_status_check
        CHECK (
            review_status IN (
                'Pending Review',
                'Accepted',
                'Edited',
                'Rejected'
            )
        )
);

CREATE INDEX IF NOT EXISTS idx_root_cause_analyses_issue_id
    ON root_cause_analyses(issue_id);

CREATE INDEX IF NOT EXISTS idx_root_cause_analyses_review_status
    ON root_cause_analyses(review_status);