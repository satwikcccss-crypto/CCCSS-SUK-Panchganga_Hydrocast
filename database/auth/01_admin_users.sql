-- ===========================================================================
-- HydroCast Panchganga - Admin Users & Authentication
-- Target: PostgreSQL 16 + PostGIS on Windows Server Standard (SUK)
-- ===========================================================================

-- Table 1: Administrator Accounts & Roles
CREATE TABLE IF NOT EXISTS admin_users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(64) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,                     -- bcrypt hash with cost factor 12
    role          VARCHAR(32) NOT NULL DEFAULT 'dev', -- 'admin', 'pi', 'co_pi', 'jrf', 'dev', 'govt'
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    last_login    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users (username);

-- Table 2: Administrative Login Audit Trail
CREATE TABLE IF NOT EXISTS admin_login_log (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(64) NOT NULL,
    role          VARCHAR(32),
    ip_address    VARCHAR(64),
    success       BOOLEAN NOT NULL,
    attempted_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_login_log_username ON admin_login_log (username);
CREATE INDEX IF NOT EXISTS idx_admin_login_log_attempted_at ON admin_login_log (attempted_at DESC);

-- Approved SUK Official Accounts (Provision via CLI)
-- Bootstrap administrator accounts are NOT seeded from this file.
-- Provision them with the CLI so no password hash is ever committed:
--   python -m backend.scripts.manage_users add --username <username> --password <password> --role admin --name "<Full Name>"
-- For offline bootstrap, copy database/auth/03_seed_adm1_users.sql and fill
-- the placeholders locally; never commit the filled file.
