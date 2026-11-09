-- Fix station_selection_log (ROUND function issue)
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
    CAST(50.0 + (random() * 40.0) AS NUMERIC(8,2)),
    '{"candidates": ["KARVEER", "BALINGA", "KALE"], "selected": "KARVEER", "distance_rank": 1}'::JSONB,
    NOW(),
    'CYCLE_2026_11_07_00Z'
FROM subbasins s;

-- Verify all tables
SELECT 'simulation_runs' as table_name, COUNT(*) as row_count FROM simulation_runs
UNION ALL SELECT 'pipeline_step_log', COUNT(*) FROM pipeline_step_log
UNION ALL SELECT 'subbasin_rainfall_ts', COUNT(*) FROM subbasin_rainfall_ts
UNION ALL SELECT 'hydrograph_results', COUNT(*) FROM hydrograph_results
UNION ALL SELECT 'bridge_stage_forecast', COUNT(*) FROM bridge_stage_forecast
UNION ALL SELECT 'station_selection_log', COUNT(*) FROM station_selection_log
UNION ALL SELECT 'alert_events', COUNT(*) FROM alert_events
UNION ALL SELECT 'forecast_validation_metrics', COUNT(*) FROM forecast_validation_metrics;
