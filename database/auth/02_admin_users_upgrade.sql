-- ===========================================================================
-- HydroCast Panchganga - Admin Users Schema Upgrade
-- Adds: email, display_name, is_active, password reset tokens
-- ===========================================================================

ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS display_name VARCHAR(128);
ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS email VARCHAR(256);
ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE;
ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(128);
ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_users_email ON admin_users (email) WHERE email IS NOT NULL;

-- Backfill: set email = username for existing accounts that use email-style usernames
UPDATE admin_users SET email = username WHERE email IS NULL AND username LIKE '%@%';
