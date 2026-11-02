-- ============================================================================
-- 01_admin_users.sql — HydroCast Administrative RBAC & Audit Log
-- ============================================================================

-- Table 1: Administrator Accounts & Roles
CREATE TABLE IF NOT EXISTS admin_users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(64) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,                          -- bcrypt hash
    role          VARCHAR(32) NOT NULL DEFAULT 'dev',     -- 'govt' or 'dev'
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    last_login    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users (username);

-- Table 2: Administrative Login Audit Trail
CREATE TABLE IF NOT EXISTS admin_login_log (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(64) NOT NULL,
    role        VARCHAR(32),
    ip_address  VARCHAR(64),
    success     BOOLEAN NOT NULL,
    attempted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_login_log_username ON admin_login_log (username);
CREATE INDEX IF NOT EXISTS idx_admin_login_log_attempted_at ON admin_login_log (attempted_at);
