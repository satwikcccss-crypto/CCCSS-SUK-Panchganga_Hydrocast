-- ===========================================================================
-- HydroCast Supabase Schema (Pure PostgreSQL + PostGIS)
-- Compatible with Supabase free tier (no TimescaleDB required)
-- ===========================================================================

-- 1. Enable PostGIS (Pre-installed on Supabase)
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Simulation Runs Table
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id              VARCHAR(100) PRIMARY KEY,
    cycle_date          DATE NOT NULL,
    cycle_time          VARCHAR(10) NOT NULL, -- e.g. '00z', '06z', '12z', '18z'
    start_time          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time            TIMESTAMPTZ,
    status              VARCHAR(20) NOT NULL DEFAULT 'running',
    model_version       VARCHAR(50) DEFAULT 'HEC-HMS-4.11',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sim_runs_time ON simulation_runs (start_time DESC);

-- 3. Gauge Stations Table (Panchganga Rain Gauge Network)
CREATE TABLE IF NOT EXISTS gauge_stations (
    station_id          VARCHAR(30) PRIMARY KEY,
    station_name        VARCHAR(100) NOT NULL,
    subbasin_id         VARCHAR(50) NOT NULL,
    basin_id            VARCHAR(50) NOT NULL DEFAULT 'PANCHGANGA_BASIN',
    latitude            DOUBLE PRECISION NOT NULL,
    longitude           DOUBLE PRECISION NOT NULL,
    geom                GEOMETRY(Point, 4326),
    elevation_m         REAL,
    owner               VARCHAR(100) DEFAULT 'CWC',
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Seed user's 7 Panchganga Rain Gauge Stations
INSERT INTO gauge_stations (station_id, station_name, subbasin_id, latitude, longitude, elevation_m)
VALUES
    ('KARANJPHEN', 'Karanjphen (Upper Ghats)', 'SUB_GHATS_UPPER', 16.7850973, 73.9036487, 640.0),
    ('RADHANAGARI', 'Radhanagari Dam', 'SUB_RADHANAGARI_DAM', 16.41021, 73.9971822, 615.0),
    ('SALWAN', 'Salwan (Mid Bhogawati)', 'SUB_BHOGAWATI_MID', 16.671222, 73.973457, 595.0),
    ('KOTOLI', 'Kotoli (Kasari Upper)', 'SUB_KASARI_UPPER', 16.7820174, 74.0518705, 585.0),
    ('BEED', 'Beed (Tulshi Confluence)', 'SUB_TULSHI_CONFLUENCE', 16.647984, 74.1288964, 565.0),
    ('SANGARUL', 'Sangarul (Kumbhi Mid)', 'SUB_KUMBHI_MID', 16.6841962, 74.0931627, 572.0),
    ('KARVEER', 'Karveer (Lower Panchganga)', 'SUB_PANCHGANGA_LOWER', 16.706369, 74.2481772, 550.0)
ON CONFLICT (station_id) DO UPDATE SET
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    elevation_m = EXCLUDED.elevation_m;

-- 4. Bridge Sites (CWC Monitoring Stations)
CREATE TABLE IF NOT EXISTS bridge_sites (
    site_id             VARCHAR(50) PRIMARY KEY,
    site_name           VARCHAR(100) NOT NULL,
    latitude            DOUBLE PRECISION NOT NULL,
    longitude           DOUBLE PRECISION NOT NULL,
    river_name          VARCHAR(100) DEFAULT 'Panchganga',
    travel_time_hrs     REAL DEFAULT 0,
    alert_stage_m       REAL NOT NULL,
    warning_stage_m     REAL NOT NULL,
    danger_stage_m      REAL NOT NULL,
    hfl_m               REAL NOT NULL,
    manning_n_main      REAL DEFAULT 0.035,
    manning_n_flood     REAL DEFAULT 0.070,
    bed_slope           REAL DEFAULT 0.00025,
    datum_m             REAL DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Seed Shivaji Bridge & Rajaram Weir with CWC MSL levels
INSERT INTO bridge_sites (site_id, site_name, latitude, longitude,
    alert_stage_m, warning_stage_m, danger_stage_m, hfl_m,
    bed_slope, datum_m)
VALUES
    ('SHIVAJI_BRIDGE', 'Shivaji Bridge (Panchganga Ghat)', 16.708917, 74.219278,
     535.50, 537.50, 538.50, 541.00, 0.00025, 0.0),
    ('RAJARAM_BRIDGE', 'Rajaram K.T. Weir (Kasba Bawada)', 16.736167, 74.235889,
     533.20, 535.20, 536.50, 538.20, 0.00020, 0.0)
ON CONFLICT (site_id) DO UPDATE SET
    alert_stage_m = EXCLUDED.alert_stage_m,
    warning_stage_m = EXCLUDED.warning_stage_m,
    danger_stage_m = EXCLUDED.danger_stage_m,
    hfl_m = EXCLUDED.hfl_m;

-- 5. Rating Curves Table (Q vs Stage H)
CREATE TABLE IF NOT EXISTS rating_curves (
    id                  BIGSERIAL PRIMARY KEY,
    site_id             VARCHAR(50) NOT NULL REFERENCES bridge_sites(site_id) ON DELETE CASCADE,
    stage_m             REAL NOT NULL,
    discharge_m3s       REAL NOT NULL,
    area_m2             REAL,
    wp_m                REAL,
    hyd_radius          REAL,
    computed_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rc_site_stage ON rating_curves (site_id, stage_m);
CREATE INDEX IF NOT EXISTS idx_rc_site_q ON rating_curves (site_id, discharge_m3s);

-- 6. Hydrograph Results (HEC-HMS simulation output at J_Outlet)
CREATE TABLE IF NOT EXISTS hydrograph_results (
    id                  BIGSERIAL PRIMARY KEY,
    run_id              VARCHAR(100) NOT NULL,
    basin_id            VARCHAR(50) NOT NULL DEFAULT 'PANCHGANGA_BASIN',
    outlet_node         VARCHAR(50) NOT NULL DEFAULT 'J_Outlet',
    timestamp           TIMESTAMPTZ NOT NULL,
    lead_hours          SMALLINT NOT NULL,
    discharge_m3s       REAL NOT NULL,
    surface_runoff_m3s  REAL DEFAULT 0,
    baseflow_m3s        REAL DEFAULT 45.0,
    is_peak             BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hg_run_outlet ON hydrograph_results (run_id, outlet_node);
CREATE INDEX IF NOT EXISTS idx_hg_time ON hydrograph_results (timestamp DESC);

-- 7. Peak Discharge Events
CREATE TABLE IF NOT EXISTS peak_discharge_events (
    id                      BIGSERIAL PRIMARY KEY,
    run_id                  VARCHAR(100) NOT NULL,
    basin_id                VARCHAR(50) NOT NULL DEFAULT 'PANCHGANGA_BASIN',
    outlet_node             VARCHAR(50) NOT NULL DEFAULT 'J_Outlet',
    peak_discharge_m3s      REAL NOT NULL,
    time_of_peak            TIMESTAMPTZ NOT NULL,
    lead_hours_to_peak      SMALLINT NOT NULL,
    total_runoff_volume_m3  REAL,
    forecast_run_time       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. Runoff Summary
CREATE TABLE IF NOT EXISTS runoff_summary (
    run_id                  VARCHAR(100) PRIMARY KEY,
    basin_id                VARCHAR(50) NOT NULL DEFAULT 'PANCHGANGA_BASIN',
    forecast_run_time       TIMESTAMPTZ NOT NULL,
    peak_discharge_m3s      REAL NOT NULL,
    time_of_peak            TIMESTAMPTZ NOT NULL,
    lead_hours_to_peak      SMALLINT NOT NULL,
    total_runoff_volume_m3  REAL,
    alert_level             VARCHAR(20) DEFAULT 'normal',
    hours_above_watch       SMALLINT DEFAULT 0,
    hours_above_warning     SMALLINT DEFAULT 0,
    hours_above_emergency   SMALLINT DEFAULT 0,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- 9. Bridge Stage Forecast (90-Hour Forward Time Series)
CREATE TABLE IF NOT EXISTS bridge_stage_forecast (
    id                  BIGSERIAL PRIMARY KEY,
    site_id             VARCHAR(50) NOT NULL REFERENCES bridge_sites(site_id) ON DELETE CASCADE,
    forecast_run_id     VARCHAR(100) NOT NULL,
    forecast_time       TIMESTAMPTZ NOT NULL,
    lead_hours          SMALLINT NOT NULL,
    discharge_m3s       REAL NOT NULL,
    stage_m             REAL NOT NULL,
    alert_level         VARCHAR(20) CHECK (alert_level IN ('NORMAL','ALERT','WARNING','DANGER','HFL_EXCEEDED')),
    is_above_danger     BOOLEAN DEFAULT FALSE,
    arrival_time        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bsf_site_run ON bridge_stage_forecast (site_id, forecast_run_id);
CREATE INDEX IF NOT EXISTS idx_bsf_time ON bridge_stage_forecast (forecast_time DESC);

-- 10. Pipeline Step Execution Log
CREATE TABLE IF NOT EXISTS pipeline_step_log (
    id                  BIGSERIAL PRIMARY KEY,
    cycle_id            VARCHAR(100) NOT NULL,
    step_number         SMALLINT NOT NULL,
    step_name           VARCHAR(100) NOT NULL,
    status              VARCHAR(20) NOT NULL CHECK (status IN ('pending','running','success','failed','skipped')),
    start_time          TIMESTAMPTZ,
    end_time            TIMESTAMPTZ,
    duration_seconds    REAL,
    error_message       TEXT,
    details_json        JSONB,
    UNIQUE (cycle_id, step_number)
);

CREATE INDEX IF NOT EXISTS idx_psl_cycle ON pipeline_step_log (cycle_id);

-- 11. Views for Real-Time Dashboard Queries
CREATE OR REPLACE VIEW v_bridge_alert_summary AS
SELECT DISTINCT ON (b.site_id)
    b.site_id,
    b.site_name,
    b.alert_stage_m,
    b.warning_stage_m,
    b.danger_stage_m,
    b.hfl_m,
    f.stage_m,
    f.discharge_m3s,
    f.alert_level,
    f.arrival_time,
    f.forecast_time
FROM bridge_sites b
LEFT JOIN bridge_stage_forecast f ON f.site_id = b.site_id
ORDER BY b.site_id, f.forecast_run_id DESC, f.lead_hours ASC;
