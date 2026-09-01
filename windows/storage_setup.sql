-- ===========================================================================
-- HydroCast Storage Management
-- PostgreSQL + TimescaleDB — 3512 GB dedicated tablespace on E:\
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 1. TABLESPACE — move large hypertables to dedicated drive
-- ---------------------------------------------------------------------------

-- Hypertables generate the bulk of data; move to E:\ tablespace
ALTER TABLE ecmwf_forecast       SET TABLESPACE hydrocast_data;
ALTER TABLE subbasin_rainfall_ts SET TABLESPACE hydrocast_data;
ALTER TABLE rainfall_data        SET TABLESPACE hydrocast_data;
ALTER TABLE hydrograph_results   SET TABLESPACE hydrocast_data;
ALTER TABLE bridge_stage_forecast SET TABLESPACE hydrocast_data;
ALTER TABLE system_logs          SET TABLESPACE hydrocast_data;

-- Smaller relational tables stay on default (pg_default → C:\)

-- ---------------------------------------------------------------------------
-- 2. TIMESCALEDB COMPRESSION
-- Compresses chunks older than retention window.
-- Typical compression ratio: 5–10x for time-series data.
-- ---------------------------------------------------------------------------

-- ecmwf_forecast: raw grid data — compress after 3 days
ALTER TABLE ecmwf_forecast
    SET (timescaledb.compress,
         timescaledb.compress_segmentby = 'grid_lat,grid_lon',
         timescaledb.compress_orderby   = 'valid_time DESC');
SELECT add_compression_policy('ecmwf_forecast',
    compress_after => INTERVAL '3 days', if_not_exists => TRUE);

-- subbasin_rainfall_ts
ALTER TABLE subbasin_rainfall_ts
    SET (timescaledb.compress,
         timescaledb.compress_segmentby = 'subbasin_id,source_id',
         timescaledb.compress_orderby   = 'valid_time DESC');
SELECT add_compression_policy('subbasin_rainfall_ts',
    compress_after => INTERVAL '7 days', if_not_exists => TRUE);

-- rainfall_data (gauge observations)
ALTER TABLE rainfall_data
    SET (timescaledb.compress,
         timescaledb.compress_segmentby = 'gauge_id,subbasin_id',
         timescaledb.compress_orderby   = 'timestamp DESC');
SELECT add_compression_policy('rainfall_data',
    compress_after => INTERVAL '7 days', if_not_exists => TRUE);

-- hydrograph_results
ALTER TABLE hydrograph_results
    SET (timescaledb.compress,
         timescaledb.compress_segmentby = 'run_id,outlet_node',
         timescaledb.compress_orderby   = 'timestamp DESC');
SELECT add_compression_policy('hydrograph_results',
    compress_after => INTERVAL '7 days', if_not_exists => TRUE);

-- bridge_stage_forecast
ALTER TABLE bridge_stage_forecast
    SET (timescaledb.compress,
         timescaledb.compress_segmentby = 'site_id,forecast_run_id',
         timescaledb.compress_orderby   = 'forecast_time DESC');
SELECT add_compression_policy('bridge_stage_forecast',
    compress_after => INTERVAL '7 days', if_not_exists => TRUE);

-- system_logs
ALTER TABLE system_logs
    SET (timescaledb.compress,
         timescaledb.compress_segmentby = 'log_level,step_name',
         timescaledb.compress_orderby   = 'timestamp DESC');
SELECT add_compression_policy('system_logs',
    compress_after => INTERVAL '3 days', if_not_exists => TRUE);

-- ---------------------------------------------------------------------------
-- 3. DATA RETENTION (drop old chunks entirely)
-- Tune based on your operational requirements.
-- ---------------------------------------------------------------------------

-- Keep raw ECMWF grid for 90 days (historical analysis)
SELECT add_retention_policy('ecmwf_forecast',
    drop_after => INTERVAL '90 days', if_not_exists => TRUE);

-- Keep gauge observations indefinitely (delete policy: never)
-- If storage fills: SELECT add_retention_policy('rainfall_data', INTERVAL '5 years', ...);

-- Keep hydrograph results indefinitely (tiny table — 90 rows × 4/day × 365 = 131k/yr)

-- Keep bridge stage forecasts for 1 year
SELECT add_retention_policy('bridge_stage_forecast',
    drop_after => INTERVAL '365 days', if_not_exists => TRUE);

-- Keep system logs for 180 days
SELECT add_retention_policy('system_logs',
    drop_after => INTERVAL '180 days', if_not_exists => TRUE);

-- ---------------------------------------------------------------------------
-- 4. CONTINUOUS AGGREGATES — materialised hourly/daily summaries for dashboard
-- These are computed once and stored, not re-queried from raw data.
-- ---------------------------------------------------------------------------

-- Daily rainfall summary per subbasin (for long-range charts)
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_subbasin_rainfall
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', valid_time)   AS day,
    subbasin_id,
    source_id,
    SUM(rainfall_mm_hr)                AS total_mm,
    MAX(rainfall_mm_hr)                AS peak_mm_hr,
    COUNT(*)                           AS records
FROM subbasin_rainfall_ts
GROUP BY day, subbasin_id, source_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy('daily_subbasin_rainfall',
    start_offset => INTERVAL '3 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- Hourly discharge summary (for dashboard KPI)
CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_outlet_discharge
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS hour,
    outlet_node,
    AVG(discharge_m3s)               AS avg_q,
    MAX(discharge_m3s)               AS max_q
FROM hydrograph_results
GROUP BY hour, outlet_node
WITH NO DATA;

SELECT add_continuous_aggregate_policy('hourly_outlet_discharge',
    start_offset => INTERVAL '7 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- ---------------------------------------------------------------------------
-- 5. MAINTENANCE JOBS (pg_cron — runs inside Postgres)
-- ---------------------------------------------------------------------------

-- pg_cron must be enabled: add 'pg_cron' to shared_preload_libraries
-- and set: cron.database_name = 'rainfall_runoff'

-- Weekly VACUUM ANALYZE on relational tables
SELECT cron.schedule(
    'weekly-vacuum',
    '0 3 * * 0',    -- Sunday 03:00
    $$VACUUM ANALYZE simulation_runs, peak_discharge_events,
             runoff_summary, alert_events, pipeline_step_log;$$
);

-- Daily chunk compression trigger (in case background worker missed)
SELECT cron.schedule(
    'daily-compress',
    '30 2 * * *',
    $$SELECT compress_chunk(i, if_not_compressed => true)
      FROM show_chunks('ecmwf_forecast', older_than => INTERVAL '3 days') i;$$
);

-- Daily: cancel alerts that are no longer active (older than 48h without ack)
SELECT cron.schedule(
    'auto-cancel-alerts',
    '0 4 * * *',
    $$UPDATE alert_events
      SET status='cancelled', cancelled_at=NOW()
      WHERE status='active'
        AND issued_at < NOW() - INTERVAL '48 hours';$$
);

-- ---------------------------------------------------------------------------
-- 6. STORAGE ESTIMATION (at 3512 GB capacity)
-- ---------------------------------------------------------------------------
/*
 Table                    Raw size/yr   Compressed/yr   Retention
 ─────────────────────────────────────────────────────────────────
 ecmwf_forecast           ~400 GB       ~50 GB          90 days
 subbasin_rainfall_ts     ~2 GB         ~0.3 GB         indefinite
 rainfall_data            ~5 GB         ~0.7 GB         indefinite
 hydrograph_results       ~0.1 GB       ~0.02 GB        indefinite
 bridge_stage_forecast    ~0.5 GB       ~0.1 GB         1 year
 system_logs              ~1 GB         ~0.2 GB         180 days
 ─────────────────────────────────────────────────────────────────
 Total active             ~50 GB/yr compressed + GRIB2 archive files
 3512 GB supports ~50+ years of compressed operational data

 The 3512 GB is more than enough. Most of it can be used as a local
 archive for raw GRIB2/NetCDF files (data/raw/) alongside PostgreSQL.
 Mount data/raw/ on E:\ as well for unified storage management.
*/

-- Check current usage
SELECT
    tablespace_name,
    pg_size_pretty(pg_tablespace_size(tablespace_name)) AS size
FROM pg_tablespace
ORDER BY pg_tablespace_size(tablespace_name) DESC;

-- Per-table sizes
SELECT
    relname                                 AS table_name,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
    pg_size_pretty(pg_relation_size(c.oid))       AS table_size
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 20;
