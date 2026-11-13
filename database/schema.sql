-- =============================================================================
-- HydroCast Panchganga - Consolidated Schema for Docker
-- Executed by PostgreSQL container on first startup
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Core schema tables
\ir schema/01_core_tables.sql
\ir schema/02_simulation_runs.sql
\ir schema/03_forecast_validation_metrics.sql
\ir schema/04_hydrograph_results.sql
\ir schema/05_bridge_stage_forecast.sql
\ir schema/06_wrd_field_benchmarks.sql
\ir schema/07_pipeline_step_log.sql
\ir schema/08_visitor_counts.sql

-- Auth tables
\ir auth/01_admin_users.sql

-- Seed reference data
\ir seeds/01_subbasins.sql
\ir seeds/02_gauge_stations.sql
\ir seeds/03_bridge_sites.sql
\ir seeds/04_wrd_field_benchmarks.sql

-- Verification
SELECT 'subbasins' AS table_name, COUNT(*) AS row_count FROM subbasins
UNION ALL SELECT 'gauge_stations', COUNT(*) FROM gauge_stations
UNION ALL SELECT 'bridge_sites', COUNT(*) FROM bridge_sites
UNION ALL SELECT 'wrd_field_benchmarks', COUNT(*) FROM wrd_field_benchmarks
UNION ALL SELECT 'admin_users', COUNT(*) FROM admin_users
UNION ALL SELECT 'visitor_counts', COUNT(*) FROM visitor_counts;
