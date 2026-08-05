CREATE TABLE IF NOT EXISTS issues (
    issue_id VARCHAR(220) PRIMARY KEY,
    title TEXT NOT NULL,
    issue_type VARCHAR(150) NOT NULL,
    business_area VARCHAR(150) NOT NULL,
    priority_level VARCHAR(20) NOT NULL,
    priority_score NUMERIC(5, 2) NOT NULL,
    priority_reason TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'Open',
    entity_type VARCHAR(100),
    entity_id VARCHAR(150),
    store_id VARCHAR(20),
    product_id VARCHAR(20),
    vendor_id VARCHAR(20),
    period_label VARCHAR(30),
    finding_count INTEGER NOT NULL DEFAULT 0,
    high_finding_count INTEGER NOT NULL DEFAULT 0,
    medium_finding_count INTEGER NOT NULL DEFAULT 0,
    low_finding_count INTEGER NOT NULL DEFAULT 0,
    root_cause_status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    summary TEXT,
    evidence_summary TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT issues_priority_level_check
        CHECK (priority_level IN ('High', 'Medium', 'Low')),

    CONSTRAINT issues_status_check
        CHECK (status IN ('Open', 'In Progress', 'Resolved', 'Rejected'))
);

CREATE TABLE IF NOT EXISTS issue_evidence (
    evidence_id BIGSERIAL PRIMARY KEY,
    issue_id VARCHAR(220) NOT NULL REFERENCES issues(issue_id)
        ON DELETE CASCADE,
    source_finding_id VARCHAR(250) NOT NULL,
    source_report VARCHAR(150) NOT NULL,
    source_module VARCHAR(100) NOT NULL,
    analysis_type VARCHAR(150),
    business_area VARCHAR(150),
    severity VARCHAR(20),
    entity_type VARCHAR(100),
    entity_id VARCHAR(150),
    store_id VARCHAR(20),
    product_id VARCHAR(20),
    vendor_id VARCHAR(20),
    summary TEXT,
    evidence TEXT,
    detected_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_issue_evidence
        UNIQUE (issue_id, source_finding_id)
);

CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id BIGSERIAL PRIMARY KEY,
    issue_id VARCHAR(220) NOT NULL REFERENCES issues(issue_id)
        ON DELETE CASCADE,
    recommendation_title TEXT NOT NULL,
    recommendation_text TEXT NOT NULL,
    suggested_owner_role VARCHAR(100),
    suggested_deadline DATE,
    expected_impact TEXT,
    confidence_score NUMERIC(5, 2),
    status VARCHAR(50) NOT NULL DEFAULT 'Pending Review',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id BIGSERIAL PRIMARY KEY,
    issue_id VARCHAR(220) REFERENCES issues(issue_id)
        ON DELETE SET NULL,
    recommendation_id BIGINT REFERENCES recommendations(recommendation_id)
        ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    assigned_to VARCHAR(150),
    assigned_role VARCHAR(100),
    due_date DATE,
    priority_level VARCHAR(20),
    status VARCHAR(50) NOT NULL DEFAULT 'Unassigned',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS automation_logs (
    automation_log_id BIGSERIAL PRIMARY KEY,
    task_id BIGINT REFERENCES tasks(task_id)
        ON DELETE SET NULL,
    workflow_name VARCHAR(150) NOT NULL,
    action_type VARCHAR(150) NOT NULL,
    execution_status VARCHAR(50) NOT NULL,
    message TEXT,
    executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS executive_briefs (
    brief_id BIGSERIAL PRIMARY KEY,
    brief_date DATE NOT NULL,
    brief_type VARCHAR(100) NOT NULL,
    summary_text TEXT NOT NULL,
    brief_data JSONB NOT NULL DEFAULT '{}'::JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'Draft',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_runs (
    agent_run_id BIGSERIAL PRIMARY KEY,
    agent_name VARCHAR(150) NOT NULL,
    agent_version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    run_type VARCHAR(100),
    execution_status VARCHAR(50) NOT NULL,
    input_summary TEXT,
    output_summary TEXT,

    model_provider VARCHAR(100),
    model_name VARCHAR(200),
    prompt_name VARCHAR(150),
    prompt_version VARCHAR(50),

    input_tokens BIGINT,
    output_tokens BIGINT,
    total_tokens BIGINT,
    estimated_cost_usd NUMERIC(14, 8),
    llm_latency_ms NUMERIC(14, 2),

    used_fallback BOOLEAN NOT NULL DEFAULT FALSE,
    tool_calls JSONB NOT NULL DEFAULT '[]'::JSONB,
    run_metadata JSONB NOT NULL DEFAULT '{}'::JSONB,

    error_type VARCHAR(150),
    error_message TEXT,
    llm_error_type VARCHAR(150),
    llm_error_message TEXT,

    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,

    CONSTRAINT agent_runs_token_usage_check
        CHECK (
            (
                input_tokens IS NULL
                AND output_tokens IS NULL
                AND total_tokens IS NULL
            )
            OR
            (
                input_tokens >= 0
                AND output_tokens >= 0
                AND total_tokens = input_tokens + output_tokens
            )
        ),

    CONSTRAINT agent_runs_estimated_cost_check
        CHECK (
            estimated_cost_usd IS NULL
            OR estimated_cost_usd >= 0
        ),

    CONSTRAINT agent_runs_llm_latency_check
        CHECK (
            llm_latency_ms IS NULL
            OR llm_latency_ms >= 0
        ),

    CONSTRAINT agent_runs_tool_calls_json_check
        CHECK (
            JSONB_TYPEOF(tool_calls) = 'array'
        ),

    CONSTRAINT agent_runs_run_metadata_json_check
        CHECK (
            JSONB_TYPEOF(run_metadata) = 'object'
        )
);

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_log_id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(220),
    action_type VARCHAR(100) NOT NULL,
    actor_name VARCHAR(150),
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_issues_priority
    ON issues(priority_level, priority_score DESC);

CREATE INDEX IF NOT EXISTS idx_issues_status
    ON issues(status);

CREATE INDEX IF NOT EXISTS idx_issue_evidence_issue_id
    ON issue_evidence(issue_id);

CREATE INDEX IF NOT EXISTS idx_recommendations_issue_id
    ON recommendations(issue_id);

CREATE INDEX IF NOT EXISTS idx_tasks_issue_id
    ON tasks(issue_id);

CREATE INDEX IF NOT EXISTS idx_tasks_status
    ON tasks(status);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_recommendation_unique
    ON tasks(recommendation_id)
    WHERE recommendation_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_started
    ON agent_runs(
        agent_name,
        started_at DESC
    );

CREATE INDEX IF NOT EXISTS idx_agent_runs_provider_model
    ON agent_runs(
        model_provider,
        model_name
    )
    WHERE model_provider IS NOT NULL;