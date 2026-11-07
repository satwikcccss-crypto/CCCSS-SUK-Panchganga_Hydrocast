-- ===========================================================================
-- HydroCast Panchganga Operational PostgreSQL Production Schema
-- Tailored for Shivaji University Kolhapur (SUK) Windows Server Standard
-- Engine: PostgreSQL 16 + PostGIS
-- Database: rainfall_runoff
-- ===========================================================================

-- 1. Enable PostGIS Extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- ---------------------------------------------------------------------------
-- 2. Subbasins (Official Panchganga Delineation, Total Area: 1,837.213 km²)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subbasins (
    subbasin_id         VARCHAR(32) PRIMARY KEY,
    subbasin_name       VARCHAR(100) NOT NULL,
    drainage_area_km2   NUMERIC(8,3) NOT NULL,
    primary_station_id  VARCHAR(64) NOT NULL,
    centroid_lat        NUMERIC(8,4) NOT NULL,
    centroid_lon        NUMERIC(8,4) NOT NULL,
    tributary_stream    VARCHAR(100) NOT NULL,
    curve_number_amc3   NUMERIC(4,1) DEFAULT 88.0,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 3. Gauge Stations (Full 20 Primary & Alternate Rain Gauge Network)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gauge_stations (
    station_id          VARCHAR(64) PRIMARY KEY,
    station_name        VARCHAR(100) NOT NULL,
    subbasin_id         VARCHAR(32) NOT NULL REFERENCES subbasins(subbasin_id) ON DELETE CASCADE,
    latitude            DOUBLE PRECISION NOT NULL,
    longitude           DOUBLE PRECISION NOT NULL,
    elevation_m         NUMERIC(6,1),
    is_primary          BOOLEAN DEFAULT TRUE,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gs_subbasin ON gauge_stations (subbasin_id);

-- ---------------------------------------------------------------------------
-- 4. Bridge Sites (River Flood Monitoring & Warning Datums)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bridge_sites (
    site_id             VARCHAR(50) PRIMARY KEY,
    site_name           VARCHAR(100) NOT NULL,
    latitude            DOUBLE PRECISION NOT NULL,
    longitude           DOUBLE PRECISION NOT NULL,
    river_name          VARCHAR(100) DEFAULT 'Panchganga',
    alert_stage_m       NUMERIC(6,2) NOT NULL,
    warning_stage_m     NUMERIC(6,2) NOT NULL,
    danger_stage_m      NUMERIC(6,2) NOT NULL,
    hfl_m               NUMERIC(6,2) NOT NULL,
    bed_slope           NUMERIC(8,6) NOT NULL,
    zero_datum_m        NUMERIC(6,2) NOT NULL DEFAULT 530.18,
    sensor_datum_m      NUMERIC(6,2) DEFAULT 549.35,
    manning_n_bed       NUMERIC(4,3) DEFAULT 0.035,
    manning_n_floodplain NUMERIC(4,3) DEFAULT 0.070,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 5. Simulation Runs (Computation Cycle Master Ledger)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id                      VARCHAR(100) PRIMARY KEY,
    cycle_date                  DATE NOT NULL DEFAULT CURRENT_DATE,
    cycle_time                  VARCHAR(32) NOT NULL DEFAULT '00z',
    start_time                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time                    TIMESTAMPTZ,
    status                      VARCHAR(32) NOT NULL DEFAULT 'completed',
    model_version               VARCHAR(64) DEFAULT 'HEC-HMS-4.13',
    peak_discharge_m3s          NUMERIC(10,2),
    peak_stage_m                NUMERIC(6,2),
    lead_hours_to_peak          SMALLINT,
    total_volume_mcm            NUMERIC(10,2),
    total_rainfall_mm           NUMERIC(8,2),
    total_rainfall_volume_mcm   NUMERIC(10,2),
    alert_level                 VARCHAR(32) DEFAULT 'NORMAL',
    spearman_rho                NUMERIC(6,4),
    nse_score                   NUMERIC(6,4),
    error_message               TEXT,
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sim_runs_date ON simulation_runs (cycle_date DESC, start_time DESC);

-- ---------------------------------------------------------------------------
-- 6. Forecast Validation Metrics (RMSE, NSE, Spearman, PBIAS Accuracy Matrix)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS forecast_validation_metrics (
    id                          BIGSERIAL PRIMARY KEY,
    run_id                      VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    spearman_rho                NUMERIC(6,4) NOT NULL,
    spearman_rho_q              NUMERIC(6,4) NOT NULL,
    pearson_r2                  NUMERIC(6,4) NOT NULL,
    nse_stage                   NUMERIC(6,4) NOT NULL,
    nse_discharge               NUMERIC(6,4) NOT NULL,
    rmse_stage_m                NUMERIC(6,4) NOT NULL,
    mae_stage_m                 NUMERIC(6,4) NOT NULL,
    rmse_q_m3s                  NUMERIC(8,2),
    mae_q_m3s                   NUMERIC(8,2),
    pbias_stage_pct             NUMERIC(6,2) NOT NULL,
    pbias_discharge_pct         NUMERIC(6,2),
    basin_rainfall_accuracy_pct NUMERIC(5,2) NOT NULL,
    performance_grade           VARCHAR(32) DEFAULT 'EXCELLENT',
    sample_size_hours           SMALLINT DEFAULT 48,
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (run_id)
);

CREATE INDEX IF NOT EXISTS idx_fvm_run ON forecast_validation_metrics (run_id);

-- ---------------------------------------------------------------------------
-- 7. Hydrograph Results (HEC-HMS 90-Hour Basin Outflow)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hydrograph_results (
    id                  BIGSERIAL PRIMARY KEY,
    run_id              VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    basin_id            VARCHAR(50) NOT NULL DEFAULT 'PANCHGANGA_BASIN',
    outlet_node         VARCHAR(50) NOT NULL DEFAULT 'J_Outlet',
    timestamp           TIMESTAMPTZ NOT NULL,
    lead_hours          SMALLINT NOT NULL,
    discharge_m3s       NUMERIC(10,2) NOT NULL,
    surface_runoff_m3s  NUMERIC(10,2) NOT NULL DEFAULT 0,
    baseflow_m3s        NUMERIC(10,2) NOT NULL DEFAULT 45.0,
    is_peak             BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hg_run_lead ON hydrograph_results (run_id, lead_hours);
CREATE INDEX IF NOT EXISTS idx_hg_timestamp ON hydrograph_results (timestamp DESC);

-- ---------------------------------------------------------------------------
-- 8. Bridge Stage Forecast (90-Hour Forward Water Level Time Series)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bridge_stage_forecast (
    id                  BIGSERIAL PRIMARY KEY,
    site_id             VARCHAR(50) NOT NULL REFERENCES bridge_sites(site_id) ON DELETE CASCADE,
    forecast_run_id     VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    forecast_time       TIMESTAMPTZ NOT NULL,
    lead_hours          SMALLINT NOT NULL,
    discharge_m3s       NUMERIC(10,2) NOT NULL,
    stage_m             NUMERIC(6,2) NOT NULL,
    alert_level         VARCHAR(32) NOT NULL CHECK (alert_level IN ('NORMAL','ALERT','WARNING','DANGER','HFL_EXCEEDED')),
    is_above_danger     BOOLEAN DEFAULT FALSE,
    arrival_time        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bsf_site_run ON bridge_stage_forecast (site_id, forecast_run_id);

-- ---------------------------------------------------------------------------
-- 9. WRD Official Rating Benchmarks
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wrd_field_benchmarks (
    record_id           SERIAL PRIMARY KEY,
    stage_m             NUMERIC(6,2) NOT NULL,
    stage_feet_inches   VARCHAR(32) NOT NULL,
    discharge_cusecs    NUMERIC(10,1) NOT NULL,
    discharge_m3s       NUMERIC(10,2) NOT NULL,
    source_agency       VARCHAR(100) DEFAULT 'Maharashtra Water Resources Dept (WRD)',
    is_danger_threshold BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 10. Pipeline Step Execution Telemetry Log
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pipeline_step_log (
    cycle_id            VARCHAR(100) NOT NULL,
    step_number         SMALLINT NOT NULL,
    step_name           VARCHAR(256) NOT NULL,
    status              VARCHAR(32) NOT NULL DEFAULT 'running',
    start_time          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time            TIMESTAMPTZ,
    duration_seconds    NUMERIC(10,2),
    details_json        JSONB,
    error_message       TEXT,
    PRIMARY KEY (cycle_id, step_number)
);

CREATE INDEX IF NOT EXISTS idx_psl_cycle ON pipeline_step_log (cycle_id);

-- ---------------------------------------------------------------------------
-- 11. Visitor Analytics (Public Website Counter)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS visitor_counts (
    visit_date          DATE PRIMARY KEY DEFAULT CURRENT_DATE,
    unique_visitors     INTEGER NOT NULL DEFAULT 1,
    total_pageviews     INTEGER NOT NULL DEFAULT 1,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

