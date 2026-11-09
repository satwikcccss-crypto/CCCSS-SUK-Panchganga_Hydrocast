-- =============================================================================
-- END-TO-END TEST: Insert complete forecast cycle
-- =============================================================================

-- 1. Insert a simulation run (cycle)
INSERT INTO simulation_runs (
    run_id, cycle_date, cycle_time, start_time, end_time,
    status, model_version, peak_discharge_m3s, peak_stage_m,
    lead_hours_to_peak, total_volume_mcm, total_rainfall_mm,
    total_rainfall_volume_mcm, alert_level, spearman_rho, nse_score, error_message
) VALUES (
    'CYCLE_2026_11_07_00Z', '2026-11-07', '00z',
    NOW(), NOW() + interval '45 minutes',
    'completed', 'HEC-HMS-4.13', 1845.50, 542.85,
    12, 42.30, 85.60, 157.20, 'WARNING', 0.9421, 0.8915, NULL
) RETURNING *;

-- 2. Insert pipeline step log (all 10 steps)
INSERT INTO pipeline_step_log (cycle_id, step_number, step_name, status, start_time, end_time, duration_seconds, details_json, error_message) VALUES
('CYCLE_2026_11_07_00Z', 1, 'ECMWF Weather Ingestion', 'success', NOW(), NOW() + interval '3 minutes', 180, '{"subbasins": 9, "hours": 90}', NULL),
('CYCLE_2026_11_07_00Z', 2, 'Rain Gauge Station Selection', 'success', NOW() + interval '3 minutes', NOW() + interval '4 minutes', 60, '{"selected": 9, "candidates": 20}', NULL),
('CYCLE_2026_11_07_00Z', 3, 'DSS File Generation', 'success', NOW() + interval '4 minutes', NOW() + interval '5 minutes', 60, '{"dss_file": "CYCLE_2026_11_07_00Z.dss", "records": 450}', NULL),
('CYCLE_2026_11_07_00Z', 4, 'HEC-HMS Simulation', 'success', NOW() + interval '5 minutes', NOW() + interval '20 minutes', 900, '{"basin": "PANCHGANGA", "subbasins": 9, "reaches": 5}', NULL),
('CYCLE_2026_11_07_00Z', 5, 'Hydrograph Extraction', 'success', NOW() + interval '20 minutes', NOW() + interval '21 minutes', 60, '{"outlet": "J_Outlet", "points": 90}', NULL),
('CYCLE_2026_11_07_00Z', 6, 'Stage Conversion (PCHIP)', 'success', NOW() + interval '21 minutes', NOW() + interval '22 minutes', 60, '{"bridges": 2, "method": "PCHIP"}', NULL),
('CYCLE_2026_11_07_00Z', 7, 'Alert Classification', 'success', NOW() + interval '22 minutes', NOW() + interval '23 minutes', 60, '{"alert": "WARNING", "sites_above_danger": 0}', NULL),
('CYCLE_2026_11_07_00Z', 8, 'Peak Detection', 'success', NOW() + interval '23 minutes', NOW() + interval '24 minutes', 60, '{"peak_q": 1845.5, "peak_stage": 542.85}', NULL),
('CYCLE_2026_11_07_00Z', 9, 'Result Storage', 'success', NOW() + interval '24 minutes', NOW() + interval '25 minutes', 60, '{"tables": 5, "rows_inserted": 270}', NULL),
('CYCLE_2026_11_07_00Z', 10, 'Alert Dispatch', 'success', NOW() + interval '25 minutes', NOW() + interval '26 minutes', 60, '{"telegram": true, "recipients": 5}', NULL);

-- 3. Insert ECMWF rainfall data for all 9 subbasins (90 hours each)
INSERT INTO subbasin_rainfall_ts (subbasin_id, valid_time, lead_hours, rainfall_mm_hr, source_id, forecast_run_time)
SELECT
    s.subbasin_id,
    NOW() + (i * interval '1 hour'),
    i,
    CAST(CASE
        WHEN i BETWEEN 0 AND 12 THEN 0.0
        WHEN i BETWEEN 13 AND 24 THEN 2.5 + (random() * 2.0)
        WHEN i BETWEEN 25 AND 48 THEN 8.0 + (random() * 5.0)
        WHEN i BETWEEN 49 AND 72 THEN 15.0 + (random() * 10.0)
        WHEN i BETWEEN 73 AND 90 THEN 5.0 + (random() * 3.0)
    END AS NUMERIC(6,2)),
    'ecmwf_ifs',
    NOW()
FROM subbasins s, generate_series(0, 89) i;

-- 4. Insert hydrograph results (90 points at outlet)
INSERT INTO hydrograph_results (run_id, basin_id, outlet_node, timestamp, lead_hours, discharge_m3s, surface_runoff_m3s, baseflow_m3s, is_peak)
SELECT
    'CYCLE_2026_11_07_00Z',
    'PANCHGANGA_BASIN',
    'J_Outlet',
    NOW() + (i * interval '1 hour'),
    i,
    CAST(CASE
        WHEN i = 12 THEN 1845.50
        WHEN i BETWEEN 10 AND 14 THEN 1700.0 + (random() * 100.0)
        WHEN i BETWEEN 5 AND 9 THEN 200.0 + (random() * 100.0)
        WHEN i BETWEEN 15 AND 30 THEN 1200.0 - ((i-15) * 40.0) + (random() * 20.0)
        WHEN i BETWEEN 31 AND 60 THEN 400.0 - ((i-31) * 5.0) + (random() * 10.0)
        ELSE 100.0 + (random() * 50.0)
    END AS NUMERIC(10,2)),
    CAST(CASE
        WHEN i BETWEEN 10 AND 30 THEN 1500.0 + (random() * 100.0)
        ELSE 50.0 + (random() * 30.0)
    END AS NUMERIC(10,2)),
    91.1,
    (i = 12)
FROM generate_series(0, 89) i;

-- 5. Insert bridge stage forecasts for SHIVAJI_BRIDGE
INSERT INTO bridge_stage_forecast (site_id, forecast_run_id, forecast_time, lead_hours, discharge_m3s, stage_m, alert_level, is_above_danger, arrival_time)
SELECT
    'SHIVAJI_BRIDGE',
    'CYCLE_2026_11_07_00Z',
    NOW() + (i * interval '1 hour'),
    i,
    CAST((SELECT discharge_m3s FROM hydrograph_results WHERE run_id='CYCLE_2026_11_07_00Z' AND lead_hours=i) AS NUMERIC(10,2)),
    CAST(CASE
        WHEN i = 12 THEN 542.85
        WHEN i BETWEEN 10 AND 14 THEN 542.30 + (random() * 0.30)
        WHEN i BETWEEN 5 AND 9 THEN 541.50 + (random() * 0.20)
        WHEN i BETWEEN 15 AND 30 THEN 541.80 - ((i-15) * 0.02) + (random() * 0.05)
        ELSE 540.80 + (random() * 0.40)
    END AS NUMERIC(6,2)),
    CASE
        WHEN i >= 10 AND i <= 14 THEN 'WARNING'
        ELSE 'NORMAL'
    END,
    (CASE WHEN i >= 10 AND i <= 14 THEN true ELSE false END),
    CASE WHEN i = 10 THEN NOW() + (10 * interval '1 hour') ELSE NULL END
FROM generate_series(0, 89) i;

-- 6. Insert bridge stage forecasts for RAJARAM_BRIDGE
INSERT INTO bridge_stage_forecast (site_id, forecast_run_id, forecast_time, lead_hours, discharge_m3s, stage_m, alert_level, is_above_danger, arrival_time)
SELECT
    'RAJARAM_BRIDGE',
    'CYCLE_2026_11_07_00Z',
    NOW() + (i * interval '1 hour'),
    i,
    CAST((SELECT discharge_m3s FROM hydrograph_results WHERE run_id='CYCLE_2026_11_07_00Z' AND lead_hours=i) * 0.85 AS NUMERIC(10,2)),
    CAST(CASE
        WHEN i = 12 THEN 541.95
        WHEN i BETWEEN 10 AND 14 THEN 541.40 + (random() * 0.25)
        WHEN i BETWEEN 5 AND 9 THEN 540.60 + (random() * 0.15)
        WHEN i BETWEEN 15 AND 30 THEN 540.90 - ((i-15) * 0.015) + (random() * 0.04)
        ELSE 539.90 + (random() * 0.35)
    END AS NUMERIC(6,2)),
    CASE
        WHEN i >= 10 AND i <= 14 THEN 'ALERT'
        ELSE 'NORMAL'
    END,
    (CASE WHEN i >= 10 AND i <= 14 THEN true ELSE false END),
    CASE WHEN i = 10 THEN NOW() + (10 * interval '1 hour') ELSE NULL END
FROM generate_series(0, 89) i;

-- 7. Insert station selection log
INSERT INTO station_selection_log (subbasin_id, selected_station_id, cumulative_mm, all_candidates_json, selected_at, cycle_id)
SELECT
    s.subbasin_id,
    CASE s.subbasin_id
        WHEN 'S1' THEN 'KARVEER'
        WHEN 'S2' THEN 'SANGARUL'
        WHEN 'S3' THEN 'KOTOLI'
        WHEN 'S4' THEN 'KARANJPHEN'
        WHEN 'S5' THEN 'PADASALI'
        WHEN 'S6' THEN 'GAGANBAWDA'
        WHEN 'S7' THEN 'GARIVADE'
        WHEN 'S8' THEN 'BEED'
        WHEN 'S9' THEN 'RADHANAGARI'
    END,
    CAST(ROUND(50.0 + (random() * 40.0), 2) AS NUMERIC(8,2)),
    '{"candidates": ["KARVEER", "BALINGA", "KALE"], "selected": "KARVEER", "distance_rank": 1}'::JSONB,
    NOW(),
    'CYCLE_2026_11_07_00Z'
FROM subbasins s;

-- 8. Insert active alerts
INSERT INTO alert_events (site_id, alert_level, stage_m, discharge_m3s, issued_at, status, message)
VALUES
    ('SHIVAJI_BRIDGE', 'WARNING', 542.85, 1845.50, NOW(), 'active', 'Stage 542.85m exceeds Warning threshold 542.70m at Shivaji Bridge'),
    ('RAJARAM_BRIDGE', 'ALERT', 541.95, 1568.68, NOW(), 'active', 'Stage 541.95m exceeds Alert threshold 541.50m at Rajaram Bridge');

-- 9. Insert forecast validation metrics
INSERT INTO forecast_validation_metrics (
    run_id, spearman_rho, spearman_rho_q, pearson_r2, nse_stage, nse_discharge,
    rmse_stage_m, mae_stage_m, rmse_q_m3s, mae_q_m3s, pbias_stage_pct, pbias_discharge_pct,
    basin_rainfall_accuracy_pct, performance_grade, sample_size_hours
) VALUES (
    'CYCLE_2026_11_07_00Z', 0.9421, 0.9185, 0.8876, 0.8915, 0.8543,
    0.15, 0.12, 45.30, 38.20, 2.50, 3.10, 94.50, 'EXCELLENT', 90
);

-- Verification row counts
SELECT 'simulation_runs' as table_name, COUNT(*) as row_count FROM simulation_runs
UNION ALL SELECT 'pipeline_step_log', COUNT(*) FROM pipeline_step_log
UNION ALL SELECT 'subbasin_rainfall_ts', COUNT(*) FROM subbasin_rainfall_ts
UNION ALL SELECT 'hydrograph_results', COUNT(*) FROM hydrograph_results
UNION ALL SELECT 'bridge_stage_forecast', COUNT(*) FROM bridge_stage_forecast
UNION ALL SELECT 'station_selection_log', COUNT(*) FROM station_selection_log
UNION ALL SELECT 'alert_events', COUNT(*) FROM alert_events
UNION ALL SELECT 'forecast_validation_metrics', COUNT(*) FROM forecast_validation_metrics;
