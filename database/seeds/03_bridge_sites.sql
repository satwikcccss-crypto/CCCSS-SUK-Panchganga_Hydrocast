-- ===========================================================================
-- HydroCast Panchganga - Seed Data
-- Part 03: Bridge Sites
-- Target: PostgreSQL 16 + PostGIS on Windows Server Standard (SUK)
-- ===========================================================================

INSERT INTO bridge_sites (site_id, site_name, latitude, longitude,
    alert_stage_m, warning_stage_m, danger_stage_m, hfl_m,
    bed_slope, zero_datum_m, sensor_datum_m)
VALUES
    ('SHIVAJI_BRIDGE', 'Chhatrapati Shivaji Maharaj Bridge (Panchganga Ghat)', 16.708917, 74.219278,
     542.10, 542.70, 543.30, 545.33, 0.005858, 530.18, 549.35),
    ('RAJARAM_BRIDGE', 'Rajaram K.T. Weir (Kasba Bawada)', 16.736167, 74.235889,
     541.50, 542.07, 543.30, 545.33, 0.002318, 530.18, 548.90)
ON CONFLICT (site_id) DO UPDATE SET
    alert_stage_m = EXCLUDED.alert_stage_m,
    warning_stage_m = EXCLUDED.warning_stage_m,
    danger_stage_m = EXCLUDED.danger_stage_m,
    hfl_m = EXCLUDED.hfl_m;