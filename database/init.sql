-- =============================================================================
-- HydroCast Panchganga - Complete Database Init for Docker
-- Self-contained: schema + seeds, no external file references
-- Mounted to /docker-entrypoint-initdb.d/01-init.sql
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Subbasins
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

-- Gauge Stations
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

-- Bridge Sites
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

-- Simulation Runs
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

-- Forecast Validation Metrics
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

-- Hydrograph Results
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

-- Bridge Stage Forecast
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

-- WRD Field Benchmarks
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

-- Pipeline Step Log
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

-- Visitor Counts
CREATE TABLE IF NOT EXISTS visitor_counts (
    visit_date          DATE PRIMARY KEY DEFAULT CURRENT_DATE,
    unique_visitors     INTEGER NOT NULL DEFAULT 1,
    total_pageviews     INTEGER NOT NULL DEFAULT 1,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- AUTH TABLES
-- =============================================================================

CREATE TABLE IF NOT EXISTS admin_users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(64) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          VARCHAR(32) NOT NULL DEFAULT 'dev',
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    last_login    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users (username);

CREATE TABLE IF NOT EXISTS admin_login_log (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(64) NOT NULL,
    role          VARCHAR(32),
    ip_address    VARCHAR(64),
    success       BOOLEAN NOT NULL,
    attempted_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_admin_login_log_username ON admin_login_log (username);
CREATE INDEX IF NOT EXISTS idx_admin_login_log_attempted_at ON admin_login_log (attempted_at DESC);

-- =============================================================================
-- SEED DATA
-- =============================================================================

-- Subbasins S1-S9
INSERT INTO subbasins (subbasin_id, subbasin_name, drainage_area_km2, primary_station_id, centroid_lat, centroid_lon, tributary_stream)
VALUES
    ('S1', 'Karveer (Outlet Reach)',       86.213, 'KARVEER',     16.7064, 74.2482, 'Panchganga Mainstem'),
    ('S2', 'Sangarul (Tulsi Lower)',      153.770, 'SANGARUL',    16.6842, 74.0932, 'Tulsi River'),
    ('S3', 'Kotoli (Kasari Lower)',       261.320, 'KOTOLI',      16.7820, 74.0519, 'Kasari River'),
    ('S4', 'Karanjphen (Kasari Headwater)',262.000,'KARANJPHEN',  16.7851, 73.9036, 'Kasari River'),
    ('S5', 'Padasali (Kumbhi Basin)',     106.390, 'PADASALI',    16.7019, 73.8436, 'Kumbhi River'),
    ('S6', 'Gaganbawda (Crest Reach)',    227.720, 'GAGANBAWDA',  16.5470, 73.8347, 'Dhamani River'),
    ('S7', 'Garivade (Ridge Catchment)',  195.390, 'GARIVADE',    16.5204, 73.9184, 'Dhamani/Bhogawati Divide'),
    ('S8', 'Beed (Bhogawati Mid-reach)',  177.440, 'BEED',        16.6480, 74.1289, 'Bhogawati River'),
    ('S9', 'Radhanagari (Upper Catchment)',366.970,'RADHANAGARI', 16.4102, 73.9972, 'Bhogawati River')
ON CONFLICT (subbasin_id) DO UPDATE SET
    drainage_area_km2 = EXCLUDED.drainage_area_km2,
    primary_station_id = EXCLUDED.primary_station_id,
    centroid_lat = EXCLUDED.centroid_lat,
    centroid_lon = EXCLUDED.centroid_lon;

-- Gauge Stations (20 stations)
INSERT INTO gauge_stations (station_id, station_name, subbasin_id, latitude, longitude, elevation_m, is_primary)
VALUES
    ('KARVEER', 'Karveer', 'S1', 16.706369, 74.2481772, 550.0, TRUE),
    ('SANGARUL', 'Sangarul', 'S2', 16.6841962, 74.0931627, 572.0, TRUE),
    ('BALINGA', 'Balinga', 'S2', 16.6878443, 74.17031, 560.0, FALSE),
    ('KALE', 'Kale', 'S2', 16.7228087, 74.0564499, 580.0, FALSE),
    ('KOTOLI', 'Kotoli', 'S3', 16.7820174, 74.0518705, 585.0, TRUE),
    ('BAJAR_BHOGAON', 'Bajar Bhogaon', 'S3', 16.8086769, 74.1107824, 590.0, FALSE),
    ('PADAL', 'Padal', 'S3', 16.7446006, 74.115187, 575.0, FALSE),
    ('KARANJPHEN', 'Karanjphen', 'S4', 16.7850973, 73.9036487, 640.0, TRUE),
    ('PADASALI', 'Padasali', 'S5', 16.701934, 73.843584, 620.0, TRUE),
    ('SALWAN', 'Salwan', 'S5', 16.6712, 73.9735, 595.0, FALSE),
    ('GAGANBAWDA', 'Gaganbawda', 'S6', 16.5469926, 73.8346738, 680.0, TRUE),
    ('GARIVADE', 'Garivade', 'S7', 16.520366, 73.918419, 610.0, TRUE),
    ('BEED', 'Beed', 'S8', 16.647984, 74.1288964, 565.0, TRUE),
    ('SHIROLI_DHUMALA', 'Shiroli-Dhumala', 'S8', 16.6166768, 74.1062828, 560.0, FALSE),
    ('RADHANAGARI', 'Radhanagari', 'S9', 16.41021, 73.9971822, 615.0, TRUE),
    ('HALADI', 'Haladi', 'S9', 16.5932632, 74.156292, 555.0, FALSE),
    ('RASHIWADE_BK', 'Rashiwade Bk.', 'S9', 16.5475641, 74.1019728, 570.0, FALSE),
    ('AAVALI_BK', 'Aavali Bk.', 'S9', 16.481009, 74.0549812, 585.0, FALSE),
    ('KASABA_TARALE', 'Kasaba Tarale', 'S9', 16.4478876, 74.021589, 595.0, FALSE),
    ('KASABA_WALAWE', 'Kasaba Walawe', 'S9', 16.41021, 73.9971822, 615.0, FALSE)
ON CONFLICT (station_id) DO UPDATE SET
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    elevation_m = EXCLUDED.elevation_m;

-- Bridge Sites
INSERT INTO bridge_sites (site_id, site_name, latitude, longitude,
    alert_stage_m, warning_stage_m, danger_stage_m, hfl_m,
    bed_slope, zero_datum_m, sensor_datum_m)
VALUES
    ('SHIVAJI_BRIDGE', 'Chhatrapati Shivaji Maharaj Bridge (Panchganga Ghat)', 16.708917, 74.219278,
     542.10, 542.70, 543.30, 545.33, 0.005858, 530.18, 549.35),
    ('RAJARAM_BRIDGE', 'Rajaram K.T. Weir (Kasba Bawada)', 16.736167, 74.235889,
     541.50, 542.07, 543.30, 545.33, 0.002318, 530.18, 548.90)
ON CONFLICT (site_id) DO UPDATE SET
    alert_stage_m = EXCLUDED.alert_stage_m,
    warning_stage_m = EXCLUDED.warning_stage_m,
    danger_stage_m = EXCLUDED.danger_stage_m,
    hfl_m = EXCLUDED.hfl_m;

-- WRD Field Benchmarks
INSERT INTO wrd_field_benchmarks (stage_m, stage_feet_inches, discharge_cusecs, discharge_m3s, is_danger_threshold)
VALUES
    (533.54, '11''.0"',  2825.0,   80.0, FALSE),
    (533.56, '11''.1"',  2869.0,   81.2, FALSE),
    (533.59, '11''.2"',  2913.0,   82.5, FALSE),
    (533.64, '11''.4"',  3002.0,   85.0, FALSE),
    (533.66, '11''.5"',  3046.0,   86.3, FALSE),
    (533.69, '11''.6"',  3090.0,   87.5, FALSE),
    (533.71, '11''.7"',  3134.0,   88.7, FALSE),
    (533.99, '12''.6"',  3902.0,  110.5, FALSE),
    (535.21, '16''.6"',  7684.0,  217.6, FALSE),
    (535.59, '17''.9"',  8958.0,  253.7, FALSE),
    (535.77, '18''.4"',  9690.0,  274.4, FALSE),
    (536.41, '20''.5"', 13087.0,  370.6, FALSE),
    (538.16, '26''.2"', 21650.0,  613.1, FALSE),
    (539.02, '29''.0"', 28270.0,  800.5, FALSE),
    (540.00, '32''.2"', 38000.0, 1076.0, FALSE),
    (542.10, '39''.1"', 58000.0, 1642.4, FALSE),
    (542.70, '41''.1"', 72000.0, 2038.8, FALSE),
    (543.30, '43''.0"', 94500.0, 2675.9, TRUE),
    (545.33, '49''.8"',136000.0, 3851.1, TRUE)
ON CONFLICT DO NOTHING;

-- Admin Users
INSERT INTO admin_users (username, password_hash, role) VALUES
    ('satwikcccss@gmail.com', '$2b$12$5hno8ira5Zx5lzk3vX4EJOtuX3xpLJfWA3GO4tLC3jJ2t/tHTZbE2', 'dev'),
    ('panhalkarsachin@gmail.com', '$2b$12$UMfPS2hcdnEecFkm6xH1KemlQNWf0q7E.LMirJ1MqBucibOMkui5.', 'pi'),
    ('gonioelect@gmail.com', '$2b$12$03ioLRLwrnZPNOewfMSXduX6e4zh78LCeLn4QD8BBLPe5Nz5rqUUi', 'co_pi'),
    ('nikhilpawar6297@gmail.com', '$2b$12$JBzCM.wyS45SlSr78Jg2wuPj7vea7zJDtqEDNshbnQkgTQyYFfl1W', 'jrf')
ON CONFLICT (username) DO NOTHING;

-- Verification
SELECT 'subbasins' AS table_name, COUNT(*) AS row_count FROM subbasins
UNION ALL SELECT 'gauge_stations', COUNT(*) FROM gauge_stations
UNION ALL SELECT 'bridge_sites', COUNT(*) FROM bridge_sites
UNION ALL SELECT 'wrd_field_benchmarks', COUNT(*) FROM wrd_field_benchmarks
UNION ALL SELECT 'admin_users', COUNT(*) FROM admin_users
UNION ALL SELECT 'visitor_counts', COUNT(*) FROM visitor_counts;
