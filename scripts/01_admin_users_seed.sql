-- ============================================================================
-- 01_admin_users_seed.sql — Production Seed for HydroCast Admin Accounts
-- ============================================================================

CREATE TABLE IF NOT EXISTS admin_users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(64) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          VARCHAR(32) NOT NULL DEFAULT 'dev',
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    last_login    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users (username);

CREATE TABLE IF NOT EXISTS admin_login_log (
    id           SERIAL PRIMARY KEY,
    username     VARCHAR(64) NOT NULL,
    role         VARCHAR(32),
    ip_address   VARCHAR(64),
    success      BOOLEAN NOT NULL,
    attempted_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_admin_login_log_username ON admin_login_log (username);
CREATE INDEX IF NOT EXISTS idx_admin_login_log_attempted_at ON admin_login_log (attempted_at);

-- Insert or update approved accounts
INSERT INTO admin_users (username, password_hash, role) VALUES
    ('Dev@Adm1', '$2b$12$6FDq14ZXsk23fj5C0jIa3e6/kRD29KinyTi8qs0mDKMACX1igh/DK', 'dev'),
    ('PI@Adm1', '$2b$12$AIHCpRK/zbmd7Zu8WqerYOXj9iNsKKVmbiEpnfE1pIMB6zVScUEOW', 'pi'),
    ('COPI@Adm1', '$2b$12$IgRi4F794sZtITlqIgUx.ecmDxm2tOEGfLCvSjzoeHz0Ll6JPUtfG', 'co_pi'),
    ('JRF@Adm1', '$2b$12$HcJEEi6XHlXtKkblcNESKuXeJZW8P2gzo7Gx6ok4TlpP1sV2iaIAi', 'jrf')
ON CONFLICT (username) DO UPDATE 
SET password_hash = EXCLUDED.password_hash,
    role = EXCLUDED.role;
