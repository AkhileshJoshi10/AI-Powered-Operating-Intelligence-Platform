-- Day 39A.1 — human identity foundation
-- Apply this migration to both development and test PostgreSQL databases.

CREATE TABLE IF NOT EXISTS app_users (
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(320) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    password_hash VARCHAR(512) NOT NULL,
    role VARCHAR(20) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT app_users_email_unique
        UNIQUE (email),

    CONSTRAINT app_users_role_check
        CHECK (role IN ('Admin', 'Manager', 'Viewer')),

    CONSTRAINT app_users_email_normalized_check
        CHECK (email = LOWER(BTRIM(email)))
);

CREATE INDEX IF NOT EXISTS idx_app_users_role_active
    ON app_users(
        role,
        is_active
    );
