-- =============================================================================
-- Missing views for full end-to-end pipeline
-- =============================================================================
-- These mirror the canonical definitions in database/supabase_schema.sql
-- (GitHub origin/main) but are adapted to this branch's simplified schema.
-- Apply with:
--   psql -h 127.0.0.1 -U hydrocast -d rainfall_runoff -f database/missing_views.sql
-- =============================================================================

-- Cycle performance (used by GET /api/v1/pipeline/history)
CREATE OR REPLACE VIEW v_cycle_performance AS
SELECT
    r.run_id AS cycle_id,
    r.cycle_date,
    r.cycle_time,
    r.start_time,
    r.end_time,
    r.status,
    r.alert_level,
    r.peak_discharge_m3s,
    r.peak_stage_m,
    EXTRACT(EPOCH FROM (COALESCE(r.end_time, NOW()) - r.start_time))::NUMERIC(10,2) AS duration_seconds,
    COUNT(l.step_number) FILTER (WHERE l.status = 'success') AS steps_completed,
    COUNT(l.step_number) FILTER (WHERE l.status = 'failed') AS steps_failed,
    MAX(l.error_message) AS error_message
FROM simulation_runs r
LEFT JOIN pipeline_step_log l ON l.cycle_id = r.run_id
GROUP BY
    r.run_id, r.cycle_date, r.cycle_time, r.start_time, r.end_time,
    r.status, r.alert_level, r.peak_discharge_m3s, r.peak_stage_m;

-- Latest peak-discharge summary for the newest run
CREATE OR REPLACE VIEW v_latest_peak_summary AS
SELECT p.*
FROM peak_discharge_events p
WHERE p.run_id = (
    SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1
);
