-- =============================================================================
-- HydroCast Panchganga - Complete PostgreSQL Setup Script
-- Target: PostgreSQL 16 + PostGIS on Windows Server
-- Execute with: psql -U postgres -d rainfall_runoff -f database/setup_postgresql.sql
-- =============================================================================

-- Step 0: Create database and user (run as postgres superuser first)
-- CREATE USER hms_app WITH PASSWORD 'hms_secret_2026';
-- CREATE DATABASE rainfall_runoff OWNER hms_app;
-- \connect rainfall_runoff

-- Step 1: Create extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Step 2: Create tablespace on E:\ drive (3512 GB dedicated storage)
-- NOTE: The directory E:/pg_tablespace/hydrocast_ts must exist and be writable by the postgres service account
-- CREATE TABLESPACE hydrocast_ts OWNER = hms_app LOCATION 'E:/pg_tablespace/hydrocast_ts';
-- ALTER DATABASE rainfall_runoff SET default_tablespace = hydrocast_ts;

-- Step 3: Core schema tables
\ir database/schema/01_core_tables.sql
\ir database/schema/02_simulation_runs.sql
\ir database/schema/03_forecast_validation_metrics.sql
\ir database/schema/04_hydrograph_results.sql
\ir database/schema/05_bridge_stage_forecast.sql
\ir database/schema/06_wrd_field_benchmarks.sql
\ir database/schema/07_pipeline_step_log.sql
\ir database/schema/08_visitor_counts.sql

-- Step 4: Auth tables
\ir database/auth/01_admin_users.sql

-- Step 5: Seed reference data
\ir database/seeds/01_subbasins.sql
\ir database/seeds/02_gauge_stations.sql
\ir database/seeds/03_bridge_sites.sql
\ir database/seeds/04_wrd_field_benchmarks.sql

-- Step 6: Verify setup
SELECT 'subbasins' AS table_name, COUNT(*) AS row_count FROM subbasins
UNION ALL SELECT 'gauge_stations', COUNT(*) FROM gauge_stations
UNION ALL SELECT 'bridge_sites', COUNT(*) FROM bridge_sites
UNION ALL SELECT 'wrd_field_benchmarks', COUNT(*) FROM wrd_field_benchmarks
UNION ALL SELECT 'admin_users', COUNT(*) FROM admin_users
UNION ALL SELECT 'visitor_counts', COUNT(*) FROM visitor_counts;

-- =============================================================================
-- END OF SETUP
-- =============================================================================
