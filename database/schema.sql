-- =============================================================================
-- HydroCast Panchganga - Consolidated Schema for Docker
-- Executed by PostgreSQL container on first startup
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Core schema tables
\ir /docker-entrypoint-initdb.d/schema/01_core_tables.sql
\ir /docker-entrypoint-initdb.d/schema/02_simulation_runs.sql
\ir /docker-entrypoint-initdb.d/schema/03_forecast_validation_metrics.sql
\ir /docker-entrypoint-initdb.d/schema/04_hydrograph_results.sql
\ir /docker-entrypoint-initdb.d/schema/05_bridge_stage_forecast.sql
\ir /docker-entrypoint-initdb.d/schema/06_wrd_field_benchmarks.sql
\ir /docker-entrypoint-initdb.d/schema/07_pipeline_step_log.sql
\ir /docker-entrypoint-initdb.d/schema/08_visitor_counts.sql

-- Auth tables
\ir /docker-entrypoint-initdb.d/auth/01_admin_users.sql

-- Seed reference data
\ir /docker-entrypoint-initdb.d/seeds/01_subbasins.sql
\ir /docker-entrypoint-initdb.d/seeds/02_gauge_stations.sql
\ir /docker-entrypoint-initdb.d/seeds/03_bridge_sites.sql
\ir /docker-entrypoint-initdb.d/seeds/04_wrd_field_benchmarks.sql

-- Verification
SELECT 'subbasins' AS table_name, COUNT(*) AS row_count FROM subbasins
UNION ALL SELECT 'gauge_stations', COUNT(*) FROM gauge_stations
UNION ALL SELECT 'bridge_sites', COUNT(*) FROM bridge_sites
UNION ALL SELECT 'wrd_field_benchmarks', COUNT(*) FROM wrd_field_benchmarks
UNION ALL SELECT 'admin_users', COUNT(*) FROM admin_users
UNION ALL SELECT 'visitor_counts', COUNT(*) FROM visitor_counts;
