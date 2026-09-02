-- Automation API / n8n foundation migration.
-- Run once against each existing project database before starting the API.
-- This migration is idempotent and preserves existing automation log rows.

BEGIN;

ALTER TABLE automation_logs
    ADD COLUMN IF NOT EXISTS issue_id VARCHAR(220),
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(200),
    ADD COLUMN IF NOT EXISTS n8n_execution_id VARCHAR(200),
    ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS http_status_code INTEGER,
    ADD COLUMN IF NOT EXISTS error_type VARCHAR(150),
    ADD COLUMN IF NOT EXISTS error_message TEXT,
    ADD COLUMN IF NOT EXISTS request_metadata JSONB NOT NULL DEFAULT '{}'::JSONB;

UPDATE automation_logs
SET idempotency_key = 'legacy-automation-log-' || automation_log_id::TEXT
WHERE idempotency_key IS NULL;

ALTER TABLE automation_logs
    ALTER COLUMN idempotency_key SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'automation_logs_issue_id_fkey'
    ) THEN
        ALTER TABLE automation_logs
            ADD CONSTRAINT automation_logs_issue_id_fkey
            FOREIGN KEY (issue_id)
            REFERENCES issues(issue_id)
            ON DELETE SET NULL;
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'automation_logs_attempt_count_check'
    ) THEN
        ALTER TABLE automation_logs
            ADD CONSTRAINT automation_logs_attempt_count_check
            CHECK (attempt_count >= 1);
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'automation_logs_http_status_code_check'
    ) THEN
        ALTER TABLE automation_logs
            ADD CONSTRAINT automation_logs_http_status_code_check
            CHECK (
                http_status_code IS NULL
                OR http_status_code BETWEEN 100 AND 599
            );
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'automation_logs_request_metadata_json_check'
    ) THEN
        ALTER TABLE automation_logs
            ADD CONSTRAINT automation_logs_request_metadata_json_check
            CHECK (
                JSONB_TYPEOF(request_metadata) = 'object'
            );
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_automation_logs_idempotency_key_unique
    ON automation_logs(idempotency_key);

CREATE INDEX IF NOT EXISTS idx_automation_logs_status_executed
    ON automation_logs(
        execution_status,
        executed_at DESC
    );

CREATE INDEX IF NOT EXISTS idx_automation_logs_task_id
    ON automation_logs(task_id)
    WHERE task_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_automation_logs_issue_id
    ON automation_logs(issue_id)
    WHERE issue_id IS NOT NULL;

COMMIT;
