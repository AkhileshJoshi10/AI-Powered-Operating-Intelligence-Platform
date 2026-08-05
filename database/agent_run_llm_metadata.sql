BEGIN;

ALTER TABLE agent_runs
    ADD COLUMN IF NOT EXISTS agent_version VARCHAR(50)
        NOT NULL DEFAULT '1.0.0',
    ADD COLUMN IF NOT EXISTS model_provider VARCHAR(100),
    ADD COLUMN IF NOT EXISTS model_name VARCHAR(200),
    ADD COLUMN IF NOT EXISTS prompt_name VARCHAR(150),
    ADD COLUMN IF NOT EXISTS prompt_version VARCHAR(50),
    ADD COLUMN IF NOT EXISTS input_tokens BIGINT,
    ADD COLUMN IF NOT EXISTS output_tokens BIGINT,
    ADD COLUMN IF NOT EXISTS total_tokens BIGINT,
    ADD COLUMN IF NOT EXISTS estimated_cost_usd NUMERIC(14, 8),
    ADD COLUMN IF NOT EXISTS llm_latency_ms NUMERIC(14, 2),
    ADD COLUMN IF NOT EXISTS used_fallback BOOLEAN
        NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS tool_calls JSONB
        NOT NULL DEFAULT '[]'::JSONB,
    ADD COLUMN IF NOT EXISTS run_metadata JSONB
        NOT NULL DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS error_type VARCHAR(150),
    ADD COLUMN IF NOT EXISTS error_message TEXT,
    ADD COLUMN IF NOT EXISTS llm_error_type VARCHAR(150),
    ADD COLUMN IF NOT EXISTS llm_error_message TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE
            conname = 'agent_runs_token_usage_check'
            AND conrelid = 'agent_runs'::REGCLASS
    ) THEN
        ALTER TABLE agent_runs
            ADD CONSTRAINT agent_runs_token_usage_check
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
            );
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE
            conname = 'agent_runs_estimated_cost_check'
            AND conrelid = 'agent_runs'::REGCLASS
    ) THEN
        ALTER TABLE agent_runs
            ADD CONSTRAINT agent_runs_estimated_cost_check
            CHECK (
                estimated_cost_usd IS NULL
                OR estimated_cost_usd >= 0
            );
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE
            conname = 'agent_runs_llm_latency_check'
            AND conrelid = 'agent_runs'::REGCLASS
    ) THEN
        ALTER TABLE agent_runs
            ADD CONSTRAINT agent_runs_llm_latency_check
            CHECK (
                llm_latency_ms IS NULL
                OR llm_latency_ms >= 0
            );
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE
            conname = 'agent_runs_tool_calls_json_check'
            AND conrelid = 'agent_runs'::REGCLASS
    ) THEN
        ALTER TABLE agent_runs
            ADD CONSTRAINT agent_runs_tool_calls_json_check
            CHECK (
                JSONB_TYPEOF(tool_calls) = 'array'
            );
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE
            conname = 'agent_runs_run_metadata_json_check'
            AND conrelid = 'agent_runs'::REGCLASS
    ) THEN
        ALTER TABLE agent_runs
            ADD CONSTRAINT agent_runs_run_metadata_json_check
            CHECK (
                JSONB_TYPEOF(run_metadata) = 'object'
            );
    END IF;
END
$$;

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

COMMIT;