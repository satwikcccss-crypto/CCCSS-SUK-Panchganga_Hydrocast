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

