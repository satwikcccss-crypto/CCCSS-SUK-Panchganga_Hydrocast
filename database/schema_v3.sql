-- ===========================================================================
-- Hydrocast Schema v3 — PostgreSQL + TimescaleDB + PostGIS
-- New in v3: gauge_stations, station_selection_log,
--            bridge_sites, rating_curves, bridge_stage_forecast,
--            pipeline_step_log
-- ===========================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ---------------------------------------------------------------------------
-- gauge_stations  — registry of all IoT rain gauge stations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gauge_stations (
    station_id      VARCHAR(30) PRIMARY KEY,
    station_name    VARCHAR(100) NOT NULL,
    subbasin_id     VARCHAR(50) NOT NULL,
    basin_id        VARCHAR(50) NOT NULL DEFAULT 'MAIN_BASIN',
    geom            GEOMETRY(Point, 4326) NOT NULL,   -- lon/lat WGS84
    elevation_m     REAL,
    owner           VARCHAR(100),        -- 'CWC', 'IMD', 'State', 'IoT'
    is_active       BOOLEAN DEFAULT TRUE,
    data_interval_min SMALLINT DEFAULT 60,
    installed_at    DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gs_subbasin ON gauge_stations (subbasin_id);
CREATE INDEX idx_gs_geom     ON gauge_stations USING GIST (geom);

-- ---------------------------------------------------------------------------
-- station_selection_log  — audit trail of which station was selected each cycle
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS station_selection_log (
    id                  BIGSERIAL PRIMARY KEY,
    cycle_id            VARCHAR(100) NOT NULL,
    subbasin_id         VARCHAR(50) NOT NULL,
    selected_station_id VARCHAR(30) REFERENCES gauge_stations(station_id),
    cumulative_mm       REAL NOT NULL,       -- 90-hr cumulative of selected station
    all_candidates_json JSONB,               -- {station_id: cumulative_mm, ...}
    selection_method    VARCHAR(30) DEFAULT 'max_cumulative',
    selected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (cycle_id, subbasin_id)
);

CREATE INDEX idx_ssl_cycle ON station_selection_log (cycle_id);

-- ---------------------------------------------------------------------------
-- bridge_sites  — CWC gauge sites at bridge locations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bridge_sites (
    site_id             VARCHAR(50) PRIMARY KEY,
    site_name           VARCHAR(100) NOT NULL,
    latitude            REAL NOT NULL,
    longitude           REAL NOT NULL,
    geom                GEOMETRY(Point, 4326) GENERATED ALWAYS AS
                            (ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)) STORED,
    river_name          VARCHAR(100),
    travel_time_hrs     REAL DEFAULT 0,   -- lag from HMS outlet to this bridge (hrs)
    -- CWC alert levels (metres above gauge datum)
    alert_stage_m       REAL NOT NULL,
    warning_stage_m     REAL NOT NULL,
    danger_stage_m      REAL NOT NULL,
    hfl_m               REAL NOT NULL,      -- Highest Flood Level ever recorded
    hfl_date            DATE,
    -- Manning's parameters for rating curve
    manning_n_main      REAL DEFAULT 0.035,
    manning_n_flood     REAL DEFAULT 0.070,
    bed_slope           REAL,
    datum_m             REAL DEFAULT 0,     -- gauge zero elevation above MSL
    -- Metadata
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO bridge_sites (site_id, site_name, latitude, longitude,
    alert_stage_m, warning_stage_m, danger_stage_m, hfl_m,
    bed_slope, datum_m)
VALUES
    ('SHIVAJI_BRIDGE', 'Shivaji Bridge', 17.6868, 74.0183,
     3.5, 5.5, 6.8, 8.5, 0.00025, 0.0),
    ('RAJARAM_BRIDGE', 'Rajaram Bridge', 17.6512, 74.0041,
     4.0, 6.0, 7.2, 9.1, 0.00020, 0.0)
ON CONFLICT (site_id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- rating_curves  — pre-computed Q vs H table for each bridge site
-- Rebuilt every time a new cross-section survey is processed
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rating_curves (
    id              BIGSERIAL PRIMARY KEY,
    site_id         VARCHAR(50) NOT NULL REFERENCES bridge_sites(site_id),
    stage_m         REAL NOT NULL,
    discharge_m3s   REAL NOT NULL,
    area_m2         REAL,
    wp_m            REAL,
    hyd_radius      REAL,
    computed_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rc_site       ON rating_curves (site_id, stage_m);
CREATE INDEX idx_rc_discharge  ON rating_curves (site_id, discharge_m3s);

-- ---------------------------------------------------------------------------
-- bridge_stage_forecast  — 90-hr stage forecast per bridge per cycle
-- One row per (site, forecast_hour, run)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bridge_stage_forecast (
    id              BIGSERIAL,
    site_id         VARCHAR(50) NOT NULL REFERENCES bridge_sites(site_id),
    forecast_run_id VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id),
    forecast_time   TIMESTAMPTZ NOT NULL,
    lead_hours      SMALLINT NOT NULL,
    discharge_m3s   REAL NOT NULL,
    stage_m         REAL NOT NULL,
    alert_level     VARCHAR(20)
                        CHECK (alert_level IN ('NORMAL','ALERT','WARNING','DANGER','HFL_EXCEEDED')),
    is_above_danger BOOLEAN GENERATED ALWAYS AS (alert_level IN ('DANGER','HFL_EXCEEDED')) STORED,
    arrival_time    TIMESTAMPTZ,           -- first hour stage crosses alert_stage_m
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, forecast_time)
);

SELECT create_hypertable('bridge_stage_forecast', 'forecast_time',
    chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);

CREATE INDEX idx_bsf_site_run  ON bridge_stage_forecast (site_id, forecast_run_id);
CREATE INDEX idx_bsf_alert     ON bridge_stage_forecast (alert_level, forecast_time DESC);

-- ---------------------------------------------------------------------------
-- pipeline_step_log  — per-step status tracking for each cycle
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pipeline_step_log (
    id              BIGSERIAL PRIMARY KEY,
    cycle_id        VARCHAR(100) NOT NULL,
    step_number     SMALLINT NOT NULL,
    step_name       VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL
                        CHECK (status IN ('pending','running','success','failed','skipped')),
    start_time      TIMESTAMPTZ,
    end_time        TIMESTAMPTZ,
    duration_seconds REAL GENERATED ALWAYS AS
                        (EXTRACT(EPOCH FROM (end_time - start_time))) STORED,
    error_message   TEXT,
    details_json    JSONB,          -- step-specific metadata (records written, etc.)
    UNIQUE (cycle_id, step_number)
);

CREATE INDEX idx_psl_cycle  ON pipeline_step_log (cycle_id);
CREATE INDEX idx_psl_status ON pipeline_step_log (status, start_time DESC);

-- Seed pipeline steps for reference
INSERT INTO pipeline_step_log (cycle_id, step_number, step_name, status)
SELECT 'TEMPLATE', s.n, s.name, 'pending' FROM (VALUES
    (1,'ECMWF IFS Fetch'),
    (2,'Gauge Station Fetch'),
    (3,'Data Validation'),
    (4,'Station Selection (max cumulative)'),
    (5,'DSS Write'),
    (6,'HMS Parameter Check'),
    (7,'HEC-HMS Execute'),
    (8,'Result Extraction'),
    (9,'Stage Conversion (bridges)'),
    (10,'Postgres Write'),
    (11,'Alert Evaluation'),
    (12,'Dashboard Broadcast')
) AS s(n, name)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Carry-forward tables from schema_v2 (abbreviated — see schema_v2.sql)
-- ---------------------------------------------------------------------------

-- subbasin_rainfall_ts (defined in v2) — add UNIQUE constraint for upsert
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name='subbasin_rainfall_ts'
          AND constraint_type='UNIQUE'
    ) THEN
        ALTER TABLE subbasin_rainfall_ts
            ADD UNIQUE (subbasin_id, valid_time, source_id);
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- VIEWS (updated)
-- ---------------------------------------------------------------------------

-- Latest bridge stage summary across all sites
CREATE OR REPLACE VIEW v_bridge_alert_summary AS
SELECT DISTINCT ON (b.site_id)
    b.site_id,
    b.site_name,
    b.danger_stage_m,
    b.hfl_m,
    f.stage_m,
    f.discharge_m3s,
    f.alert_level,
    f.arrival_time,
    f.forecast_time
FROM bridge_sites b
LEFT JOIN bridge_stage_forecast f ON f.site_id=b.site_id
ORDER BY b.site_id, f.forecast_run_id DESC, f.lead_hours ASC;


-- Current pipeline status for the latest cycle
CREATE OR REPLACE VIEW v_current_pipeline AS
WITH latest AS (
    SELECT run_id AS cycle_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1
)
SELECT
    p.step_number, p.step_name, p.status,
    p.start_time, p.end_time, p.duration_seconds,
    p.error_message
FROM pipeline_step_log p
JOIN latest ON p.cycle_id = latest.cycle_id
ORDER BY p.step_number;


-- ===========================================================================
-- PERMISSIONS
-- ===========================================================================
GRANT SELECT, INSERT, UPDATE ON gauge_stations         TO hms_app;
GRANT SELECT, INSERT, UPDATE ON station_selection_log  TO hms_app;
GRANT SELECT, INSERT, UPDATE ON bridge_sites           TO hms_app;
GRANT SELECT, INSERT, UPDATE ON rating_curves          TO hms_app;
GRANT SELECT, INSERT, UPDATE ON bridge_stage_forecast  TO hms_app;
GRANT SELECT, INSERT, UPDATE ON pipeline_step_log      TO hms_app;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public            TO hms_app;
