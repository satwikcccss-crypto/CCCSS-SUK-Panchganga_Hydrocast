-- ============================================================================
-- 01_admin_users.sql — HydroCast Administrative RBAC & Audit Log
-- ============================================================================

-- Table 1: Administrator Accounts & Roles
CREATE TABLE IF NOT EXISTS admin_users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(64) UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,                          -- bcrypt hash
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

-- -------------------------------------------------------
-- 2️⃣  Insert the four approved accounts (bcrypt hashes below)
-- -------------------------------------------------------
-- *** These hashes were generated via bcrypt.hashpw(password, gensalt()) ***
-- *** and must match the passwords listed in the project README ***
INSERT INTO admin_users (username, password_hash, role) VALUES
    ('satwikcccss@gmail.com', '$2b$12$5hno8ira5Zx5lzk3vX4EJOtuX3xpLJfWA3GO4tLC3jJ2t/tHTZbE2', 'dev'),
    ('panhalkarsachin@gmail.com', '$2b$12$UMfPS2hcdnEecFkm6xH1KemlQNWf0q7E.LMirJ1MqBucibOMkui5.', 'pi'),
    ('gonioelect@gmail.com', '$2b$12$03ioLRLwrnZPNOewfMSXduX6e4zh78LCeLn4QD8BBLPe5Nz5rqUUi', 'co_pi'),
    ('nikhilpawar6297@gmail.com', '$2b$12$JBzCM.wyS45SlSr78Jg2wuPj7vea7zJDtqEDNshbnQkgTQyYFfl1W', 'jrf');
-- (If any of the INSERT rows conflict with an existing username, DO NOTHING – the row is simply left unchanged.)

-- +migrate Down
DROP TABLE IF EXISTS admin_login_log;
DROP TABLE IF EXISTS admin_users;
```

Now I need to stage this file and the `02_visitor_counter_setup.sql`, and also make sure the frontend files are staged. Let me check git status.</think>
<tool_call>
<function=shell>
<parameter=command>
git status --short