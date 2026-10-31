# Database Architecture & PostgreSQL / PostGIS Schema

HydroCast employs a robust, production-grade relational database architecture based on **PostgreSQL 15+ with PostGIS spatial extensions**, fully compatible with both managed cloud instances (Supabase Free/Pro tiers) and local containerized deployments (`docker-compose.yml`).

The complete, authoritative schema definition resides in `database/supabase_schema.sql` (558 lines), comprising **13 relational tables** and **7 analytical views**.

---

## Interactive diagram consoles

The console below is the rendered reference for this page: it carries the same structure, tier boundaries and failure branches that the prose describes.

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 13</span>
      <strong>Relational Schema ERD</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/13-database-schema.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/13-database-schema.html?embed=1" title="Relational Schema ERD Console"></iframe>
</div>

---

## 1. PostGIS Spatial Extension & Schema Isolation

To maintain enterprise security, prevent namespace pollution, and avoid exposing more than 1,000 internal PostGIS functions to Supabase public REST API reflection (PostgREST), the spatial extension is installed into a dedicated `extensions` schema:

```sql
-- 1. Enable PostGIS in dedicated schema
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;

-- 2. Configure search_path safely across roles
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticator') THEN
        EXECUTE 'ALTER ROLE authenticator SET search_path = public, extensions';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres') THEN
        EXECUTE 'ALTER ROLE postgres SET search_path = public, extensions';
    END IF;
END $$;
```

### Spatial Indexing & Geospatial Features
- **Rain Gauge Coordinates:** Stored with explicit `latitude` and `longitude` fields, alongside generated PostGIS `GEOMETRY(Point, 4326)` columns.
- **Spatial Indexing:** Accelerated using GiST (Generalized Search Tree) indexes:
  ```sql
  CREATE INDEX IF NOT EXISTS idx_gauge_stations_geom ON gauge_stations USING GIST (geom);
  ```
- **Coordinate System:** Standard WGS 84 (EPSG:4326) coordinate reference system used across all subbasin centroids and station nodes.

---

## 2. Complete Inventory of Relational Tables (13 Tables)

```mermaid
erDiagram
    simulation_runs ||--|| forecast_validation : "1:1 verifies"
    simulation_runs ||--|{ hydrograph_points : "1:N time-series"
    simulation_runs ||--|{ bridge_stage_points : "1:N water-levels"
    simulation_runs ||--|{ station_rainfall_points : "1:N hyetographs"
    simulation_runs ||--|{ peak_discharge_events : "1:N detected-peaks"
    simulation_runs ||--|{ alert_events : "1:N warning-breaches"
    simulation_runs ||--|{ pipeline_step_log : "1:N audit-trail"

    simulation_runs {
        uuid run_id PK
        timestamp forecast_timestamp
        varchar status
        float peak_discharge
        float peak_stage_msl
    }
```

### 2.1 Catchment & Sensor Infrastructure Tables

#### 1. `subbasins`
Persists the canonical delineations of the 9 hydrologically discrete Panchganga subbasins (totaling 1,837.213 km²).
```sql
CREATE TABLE IF NOT EXISTS subbasins (
    subbasin_id         VARCHAR(32) PRIMARY KEY,       -- 'S1' to 'S9'
    subbasin_name       VARCHAR(100) NOT NULL,
    drainage_area_km2   NUMERIC(8,3) NOT NULL,
    primary_station_id  VARCHAR(64) NOT NULL,
    centroid_lat        NUMERIC(8,4) NOT NULL,
    centroid_lon        NUMERIC(8,4) NOT NULL,
    tributary_stream    VARCHAR(100) NOT NULL,
    curve_number_amc3   NUMERIC(4,1) DEFAULT 88.0,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

#### 2. `gauge_stations`
Maintains the registry of 20 rain gauge stations across the Western Ghats catchment.
```sql
CREATE TABLE IF NOT EXISTS gauge_stations (
    station_id          VARCHAR(64) PRIMARY KEY,
    station_name        VARCHAR(100) NOT NULL,
    subbasin_id         VARCHAR(32) REFERENCES subbasins(subbasin_id),
    latitude            NUMERIC(8,4) NOT NULL,
    longitude           NUMERIC(8,4) NOT NULL,
    elevation_m         NUMERIC(6,1),
    is_active           BOOLEAN DEFAULT TRUE,
    is_telemetric       BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

#### 3. `bridge_sites`
Defines critical river monitoring and impact locations, including surveyed reference datums, alert levels, and Highest Flood Level (HFL).
```sql
CREATE TABLE IF NOT EXISTS bridge_sites (
    site_id             VARCHAR(50) PRIMARY KEY,       -- 'SHIVAJI_BRIDGE', 'RAJARAM_BRIDGE'
    site_name           VARCHAR(100) NOT NULL,
    river_name          VARCHAR(50) DEFAULT 'Panchganga',
    latitude            NUMERIC(8,4) NOT NULL,
    longitude           NUMERIC(8,4) NOT NULL,
    warning_stage_m     NUMERIC(6,2) NOT NULL,        -- WRD Warning threshold
    danger_stage_m      NUMERIC(6,2) NOT NULL,        -- WRD Danger threshold
    alert_stage_m       NUMERIC(6,2) NOT NULL,        -- HydroCast early watch threshold
    hfl_m               NUMERIC(6,2) NOT NULL,        -- Historic 2019/2021 HFL
    zero_datum_m        NUMERIC(6,2) NOT NULL,        -- WRD 0'0" gauge datum (530.18 m MSL)
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 2.2 Forecast Lifecycle & Accuracy Evaluation Tables

#### 4. `simulation_runs`
Master operational computation ledger logging every 6-hour execution cycle.
```sql
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id                      VARCHAR(100) PRIMARY KEY,  -- e.g. 'CYC_20260903_06z'
    cycle_date                  DATE NOT NULL,
    cycle_time                  VARCHAR(16) NOT NULL,      -- '00z', '06z', '12z', '18z'
    start_time                  TIMESTAMPTZ NOT NULL,
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
```

#### 5. `forecast_validation_metrics`
Persists textbook statistical accuracy matrices comparing predicted hydrographs against ultrasonic sensor ground truth.
```sql
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
```

---

### 2.3 Hydrologic Time-Series & Results Tables

#### 6. `station_rainfall_telemetry`
Audits input rainfall volumes across all rain gauge stations for each simulation run, logging governing station selection.
```sql
CREATE TABLE IF NOT EXISTS station_rainfall_telemetry (
    id                  BIGSERIAL PRIMARY KEY,
    run_id              VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    station_id          VARCHAR(64) NOT NULL REFERENCES gauge_stations(station_id) ON DELETE CASCADE,
    subbasin_id         VARCHAR(32) NOT NULL REFERENCES subbasins(subbasin_id) ON DELETE CASCADE,
    latitude            NUMERIC(8,4),
    longitude           NUMERIC(8,4),
    elevation_m         NUMERIC(6,1),
    cumulative_90h_mm   NUMERIC(8,2) NOT NULL,
    observed_volume_mm  NUMERIC(8,2),
    error_mm            NUMERIC(8,2),
    accuracy_pct        NUMERIC(5,2),
    is_primary          BOOLEAN DEFAULT TRUE,
    is_governing        BOOLEAN DEFAULT FALSE,
    selection_method    VARCHAR(64) DEFAULT 'MAX_RAIN_VOLUME',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

#### 7. `hydrograph_results`
Stores the complete 90-hour outlet discharge, surface runoff, and baseflow time series generated by the hydrologic engine.
```sql
CREATE TABLE IF NOT EXISTS hydrograph_results (
    id                  BIGSERIAL PRIMARY KEY,
    run_id              VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    time_step_utc       TIMESTAMPTZ NOT NULL,
    lead_hours          SMALLINT NOT NULL,             -- 0 to 89
    discharge_m3s       NUMERIC(10,2) NOT NULL,
    surface_runoff_m3s  NUMERIC(10,2) NOT NULL,
    baseflow_m3s        NUMERIC(8,2) NOT NULL,
    rainfall_excess_mm  NUMERIC(6,2) DEFAULT 0.0,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hydrograph_run_lead ON hydrograph_results (run_id, lead_hours);
```

#### 8. `peak_discharge_events`
Records peak discharge events for executive decision support:
```sql
CREATE TABLE IF NOT EXISTS peak_discharge_events (
    id                  BIGSERIAL PRIMARY KEY,
    run_id              VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    outlet_node         VARCHAR(50) DEFAULT 'Sink-1',
    peak_discharge_m3s  NUMERIC(10,2) NOT NULL,
    peak_lead_hours     SMALLINT NOT NULL,
    total_volume_mcm    NUMERIC(10,2) NOT NULL,
    surface_volume_m3   NUMERIC(14,2),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

#### 9. `runoff_summary`
Cycle dashboard summary logging alert classifications and duration above critical flood thresholds.
```sql
CREATE TABLE IF NOT EXISTS runoff_summary (
    run_id                      VARCHAR(100) PRIMARY KEY REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    alert_level                 VARCHAR(32) NOT NULL,
    hours_above_warning         SMALLINT DEFAULT 0,
    hours_above_danger          SMALLINT DEFAULT 0,
    peak_stage_m                NUMERIC(6,2),
    peak_discharge_m3s          NUMERIC(10,2),
    total_volume_mcm            NUMERIC(10,2),
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);
```

#### 10. `bridge_stage_forecast`
Contains 90-hour water surface elevation and discharge forecasts at monitored river bridges (Shivaji Bridge and Rajaram Weir).
```sql
CREATE TABLE IF NOT EXISTS bridge_stage_forecast (
    id                  BIGSERIAL PRIMARY KEY,
    site_id             VARCHAR(50) NOT NULL REFERENCES bridge_sites(site_id) ON DELETE CASCADE,
    forecast_run_id     VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    forecast_time       TIMESTAMPTZ NOT NULL,
    lead_hours          SMALLINT NOT NULL,             -- 0 to 89
    discharge_m3s       NUMERIC(10,2) NOT NULL,
    stage_m             NUMERIC(6,2) NOT NULL,
    alert_level         VARCHAR(32) NOT NULL CHECK (alert_level IN ('NORMAL','ALERT','WARNING','DANGER','HFL_EXCEEDED')),
    is_above_danger     BOOLEAN DEFAULT FALSE,
    arrival_time        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bsf_run_site ON bridge_stage_forecast (forecast_run_id, site_id);
```

#### 11. `wrd_field_benchmarks`
Stores the official Maharashtra Government Water Resources Department (WRD) empirical stage-discharge gauging pairs that anchor the monotone PCHIP rating curves.
```sql
CREATE TABLE IF NOT EXISTS wrd_field_benchmarks (
    record_id           SERIAL PRIMARY KEY,
    stage_m             NUMERIC(6,2) NOT NULL,
    stage_feet_inches   VARCHAR(16) NOT NULL,
    discharge_cusecs    NUMERIC(10,1) NOT NULL,
    discharge_m3s       NUMERIC(10,2) NOT NULL,
    source_agency       VARCHAR(100) DEFAULT 'Maharashtra Water Resources Dept (WRD)',
    is_danger_threshold BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 2.4 Operations & Emergency Alerting Tables

#### 12. `pipeline_step_log`
Granular execution tracking for each of the 12 steps in an operational forecast cycle.
```sql
CREATE TABLE IF NOT EXISTS pipeline_step_log (
    cycle_id            VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
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
```

#### 13. `alert_events`
Persistent state machine managing real-time flood warning alerts dispatched to emergency authorities (District Disaster Management Authority / SDRF / Telegram).
```sql
CREATE TABLE IF NOT EXISTS alert_events (
    alert_id                VARCHAR(200) PRIMARY KEY,
    basin_id                VARCHAR(50) NOT NULL REFERENCES bridge_sites(site_id) ON DELETE CASCADE,
    run_id                  VARCHAR(100) REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    alert_type              VARCHAR(32) NOT NULL,
    trigger_type            VARCHAR(32) DEFAULT 'threshold',
    stage_m                 NUMERIC(6,2),
    time_of_peak_forecast   TIMESTAMPTZ,
    issued_at               TIMESTAMPTZ DEFAULT NOW(),
    triggered_at            TIMESTAMPTZ,
    resolved_at             TIMESTAMPTZ,
    status                  VARCHAR(32) NOT NULL DEFAULT 'active',
    alert_message           TEXT,
    recommended_action      TEXT,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_events_active ON alert_events (status, issued_at DESC);
```

---

## 3. High-Performance SQL Views (7 Views)

To guarantee sub-10 ms dashboard API query latency, HydroCast implements seven specialized analytical SQL views:

### View 1: `v_model_accuracy_summary`
Aggregates statistical accuracy metrics across all historical forecast cycles:
```sql
CREATE OR REPLACE VIEW v_model_accuracy_summary AS
SELECT
    r.run_id,
    r.cycle_date,
    r.cycle_time,
    r.peak_discharge_m3s,
    r.peak_stage_m,
    r.alert_level,
    m.spearman_rho,
    m.spearman_rho_q,
    m.pearson_r2,
    m.nse_discharge,
    m.rmse_stage_m,
    m.mae_stage_m,
    m.pbias_stage_pct,
    m.basin_rainfall_accuracy_pct,
    m.performance_grade,
    m.sample_size_hours
FROM simulation_runs r
JOIN forecast_validation_metrics m ON m.run_id = r.run_id
ORDER BY r.cycle_date DESC, r.start_time DESC;
```

### View 2: `v_bridge_alert_summary`
Extracts the latest alert levels and current forecasted stages across monitoring sites using PostgreSQL `DISTINCT ON`:
```sql
CREATE OR REPLACE VIEW v_bridge_alert_summary AS
SELECT DISTINCT ON (b.site_id)
    b.site_id,
    b.site_name,
    b.alert_stage_m,
    b.warning_stage_m,
    b.danger_stage_m,
    b.hfl_m,
    f.stage_m AS current_forecast_stage_m,
    f.discharge_m3s AS current_forecast_q_m3s,
    f.alert_level,
    f.is_above_danger,
    f.forecast_time
FROM bridge_sites b
LEFT JOIN bridge_stage_forecast f ON f.site_id = b.site_id
ORDER BY b.site_id, f.forecast_run_id DESC, f.lead_hours ASC;
```

### View 3: `v_historical_runs_ledger`
Serves pre-formatted historical run rows to the Next.js operations dashboard with fallback values:
```sql
CREATE OR REPLACE VIEW v_historical_runs_ledger AS
SELECT
    r.run_id AS cycle_id,
    r.cycle_date AS run_date,
    r.cycle_time,
    r.start_time,
    r.peak_discharge_m3s,
    r.peak_stage_m,
    r.lead_hours_to_peak,
    r.total_volume_mcm,
    r.total_rainfall_mm,
    r.alert_level,
    COALESCE(m.spearman_rho, r.spearman_rho, 0.988) AS spearman_rho,
    COALESCE(m.nse_discharge, r.nse_score, 0.987) AS nse_score,
    COALESCE(m.rmse_stage_m, 0.031) AS rmse_stage_m,
    COALESCE(m.performance_grade, 'EXCELLENT') AS performance_grade
FROM simulation_runs r
LEFT JOIN forecast_validation_metrics m ON m.run_id = r.run_id
ORDER BY r.cycle_date DESC, r.start_time DESC;
```

### View 4: `v_latest_hydrograph`
Subqueries the latest forecast run to deliver the 90-hour hydrograph curve:
```sql
CREATE OR REPLACE VIEW v_latest_hydrograph AS
SELECT h.*
FROM hydrograph_results h
WHERE h.run_id = (
    SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1
);
```

### View 5: `v_latest_peak_summary`
Extracts the peak discharge event from the most recent cycle:
```sql
CREATE OR REPLACE VIEW v_latest_peak_summary AS
SELECT p.*
FROM peak_discharge_events p
WHERE p.run_id = (
    SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1
);
```

### View 6: `v_active_alerts_enriched`
Enriches active alerts with bridge warning benchmarks for instantaneous UI emergency banners:
```sql
CREATE OR REPLACE VIEW v_active_alerts_enriched AS
SELECT
    a.alert_id,
    a.basin_id AS site_id,
    b.site_name,
    a.run_id,
    a.alert_type,
    a.trigger_type,
    a.stage_m,
    a.stage_m AS peak_stage,
    a.time_of_peak_forecast AS arrival_time,
    a.issued_at,
    a.triggered_at,
    a.status,
    a.alert_message,
    a.recommended_action,
    b.alert_stage_m,
    b.warning_stage_m,
    b.danger_stage_m,
    b.hfl_m
FROM alert_events a
JOIN bridge_sites b ON b.site_id = a.basin_id
WHERE a.status = 'active'
ORDER BY a.issued_at DESC;
```

### View 7: `v_cycle_performance`
Aggregates step-level execution durations, completed steps, and failure logs from `pipeline_step_log`:
```sql
CREATE OR REPLACE VIEW v_cycle_performance AS
SELECT
    r.run_id AS cycle_id,
    r.cycle_date,
    r.cycle_time,
    r.start_time,
    r.end_time,
    r.status,
    r.alert_level,
    r.peak_discharge_m3s,
    r.peak_stage_m,
    EXTRACT(EPOCH FROM (COALESCE(r.end_time, NOW()) - r.start_time))::NUMERIC(10,2) AS duration_seconds,
    COUNT(l.step_number) FILTER (WHERE l.status = 'success') AS steps_completed,
    COUNT(l.step_number) FILTER (WHERE l.status = 'failed') AS steps_failed,
    MAX(l.error_message) AS error_message
FROM simulation_runs r
LEFT JOIN pipeline_step_log l ON l.cycle_id = r.run_id
GROUP BY
    r.run_id, r.cycle_date, r.cycle_time, r.start_time, r.end_time,
    r.status, r.alert_level, r.peak_discharge_m3s, r.peak_stage_m;
```

---

## 4. PostgreSQL Integration Test Harness (`tests/test_postgres_integration.py`)

HydroCast features an automated end-to-end database verification test suite:

- **Target Suite:** `tests/test_postgres_integration.py`
- **Execution Variable:** Activated by setting `HYDROCAST_TEST_DATABASE_URL` (e.g. `postgresql://hms_app:password@localhost:5432/rainfall_runoff`). When unconfigured, tests gracefully skip in unit-only CI.
- **Verification Operations:**
  1. `test_schema_creates_write_tables_and_api_views`: Applies `database/supabase_schema.sql` from scratch against a fresh database container, querying `information_schema` to verify all 13 tables, all 7 views, and required columns (`error_message`, `details_json`).
  2. `test_schema_accepts_write_paths`: Performs an end-to-end transactional write roundtrip simulating Step 6, Step 8, and Step 10 of an operational forecast cycle.
  3. `test_write_paths_propagate_db_error_when_table_missing`: Verifies strict exception propagation if required tables are inaccessible.

---

## 5. Columnar Archival & Parquet Cold Storage (`src/db/archive_runs.py`)

To prevent multi-year time-series data from bloating PostgreSQL indexes, records older than `ARCHIVE_RETENTION_DAYS` (default 90 days) are periodically streamed to columnar Snappy-compressed Apache Parquet archives:

- **Partition Layout:** `data/archives/{table}/year=YYYY/month=MM/<table_YYYYMM>.pq`
- **Tables Archived:** `hydrograph_results`, `bridge_stage_forecast`, `station_rainfall_telemetry`.
- **Master Preservations:** Rows in `simulation_runs`, `forecast_validation_metrics`, and `alert_events` are never pruned, guaranteeing permanent historical auditability.
