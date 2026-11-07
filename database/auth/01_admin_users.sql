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

-- Approved SUK Official Accounts with Bcrypt Hashes (Cost 12)
INSERT INTO admin_users (username, password_hash, role) VALUES
    ('satwikcccss@gmail.com', '$2b$12$5hno8ira5Zx5lzk3vX4EJOtuX3xpLJfWA3GO4tLC3jJ2t/tHTZbE2', 'dev'),
    ('panhalkarsachin@gmail.com', '$2b$12$UMfPS2hcdnEecFkm6xH1KemlQNWf0q7E.LMirJ1MqBucibOMkui5.', 'pi'),
    ('gonioelect@gmail.com', '$2b$12$03ioLRLwrnZPNOewfMSXduX6e4zh78LCeLn4QD8BBLPe5Nz5rqUUi', 'co_pi'),
    ('nikhilpawar6297@gmail.com', '$2b$12$JBzCM.wyS45SlSr78Jg2wuPj7vea7zJDtqEDNshbnQkgTQyYFfl1W', 'jrf')
ON CONFLICT (username) DO NOTHING;