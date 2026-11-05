-- ============================================================================
-- 01_admin_users_seed.sql — Production Seed for HydroCast Admin & Operations
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

-- ============================================================================
-- Visitor Counter Tables & Open RLS Policies
-- ============================================================================
CREATE TABLE IF NOT EXISTS site_visits (
    visit_date DATE PRIMARY KEY,
    visit_count INT DEFAULT 1
);

CREATE TABLE IF NOT EXISTS site_visitor_ips (
    ip_hash TEXT,
    visit_date DATE,
    PRIMARY KEY (ip_hash, visit_date)
);

INSERT INTO site_visits (visit_date, visit_count)
VALUES (CURRENT_DATE, 42)
ON CONFLICT (visit_date) DO NOTHING;

ALTER TABLE site_visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_visitor_ips ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read site_visits" ON site_visits;
CREATE POLICY "Allow public read site_visits" ON site_visits FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow public write site_visits" ON site_visits;
CREATE POLICY "Allow public write site_visits" ON site_visits FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow public read site_visitor_ips" ON site_visitor_ips;
CREATE POLICY "Allow public read site_visitor_ips" ON site_visitor_ips FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow public write site_visitor_ips" ON site_visitor_ips;
CREATE POLICY "Allow public write site_visitor_ips" ON site_visitor_ips FOR ALL USING (true) WITH CHECK (true);

-- ----------------------------------------------------------------------------
-- Atomic visit recording
-- ----------------------------------------------------------------------------
-- Keep this in sync with scripts/02_visitor_counter_setup.sql. The Next.js
-- route uses this RPC for an atomic de-duplicate + increment + read.
CREATE OR REPLACE FUNCTION record_site_visit(p_ip_hash TEXT, p_visit_date DATE)
RETURNS TABLE (daily INTEGER, total INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_inserted INTEGER := 0;
BEGIN
    INSERT INTO site_visitor_ips (ip_hash, visit_date)
    VALUES (p_ip_hash, p_visit_date)
    ON CONFLICT (ip_hash, visit_date) DO NOTHING;

    GET DIAGNOSTICS v_inserted = ROW_COUNT;

    IF v_inserted > 0 THEN
        INSERT INTO site_visits (visit_date, visit_count)
        VALUES (p_visit_date, 1)
        ON CONFLICT (visit_date) DO UPDATE
            SET visit_count = site_visits.visit_count + 1;
    END IF;

    RETURN QUERY
        SELECT
            COALESCE(
                (SELECT sv.visit_count FROM site_visits sv WHERE sv.visit_date = p_visit_date),
                0
            )::INTEGER AS daily,
            COALESCE((SELECT SUM(sv.visit_count) FROM site_visits sv), 0)::INTEGER AS total;
END;
$$;

REVOKE ALL ON FUNCTION record_site_visit(TEXT, DATE) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION record_site_visit(TEXT, DATE) TO anon, authenticated, service_role;
