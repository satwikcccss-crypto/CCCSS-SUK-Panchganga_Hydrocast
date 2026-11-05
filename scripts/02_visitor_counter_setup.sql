-- ============================================================================
-- 02_visitor_counter_setup.sql — Tables and Policies for HydroCast Visitor Counter
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

-- Seed initial project baseline counts if empty
INSERT INTO site_visits (visit_date, visit_count)
VALUES (CURRENT_DATE, 42)
ON CONFLICT (visit_date) DO UPDATE
SET visit_count = GREATEST(site_visits.visit_count, EXCLUDED.visit_count);

-- Enable RLS
ALTER TABLE site_visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_visitor_ips ENABLE ROW LEVEL SECURITY;

-- Allow public / anon / authenticated to read visits
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
-- The Next.js route calls this RPC so de-duplication, increment and read all
-- happen in one transaction. Without it, concurrent requests can lose updates
-- (read-modify-write) and the odometer appears to stall or go backwards.
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

