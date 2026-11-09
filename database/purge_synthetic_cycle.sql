-- Purge the synthetic E2E test cycle CYCLE_2026_11_07_00Z and its side effects.
BEGIN;

DELETE FROM station_selection_log WHERE cycle_id = 'CYCLE_2026_11_07_00Z';
DELETE FROM peak_discharge_events WHERE run_id = 'CYCLE_2026_11_07_00Z';
DELETE FROM subbasin_rainfall_ts
 WHERE forecast_run_time = '2026-11-07 15:48:36.603147+05:30';
DELETE FROM alert_events WHERE status = 'cancelled';
DELETE FROM simulation_runs WHERE run_id = 'CYCLE_2026_11_07_00Z';

COMMIT;

SELECT 'simulation_runs' AS t, COUNT(*) FROM simulation_runs
UNION ALL SELECT 'hydrograph_results', COUNT(*) FROM hydrograph_results
UNION ALL SELECT 'bridge_stage_forecast', COUNT(*) FROM bridge_stage_forecast
UNION ALL SELECT 'subbasin_rainfall_ts', COUNT(*) FROM subbasin_rainfall_ts
UNION ALL SELECT 'station_selection_log', COUNT(*) FROM station_selection_log
UNION ALL SELECT 'peak_discharge_events', COUNT(*) FROM peak_discharge_events
UNION ALL SELECT 'alert_events', COUNT(*) FROM alert_events;
