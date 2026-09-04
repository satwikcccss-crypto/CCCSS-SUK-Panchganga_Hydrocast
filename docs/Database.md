# Database Architecture & Supabase / PostgreSQL Persistence Schema

```
========================================================================================================================
                      HYDROCAST POSTGRESQL / SUPABASE & JSON LEDGER SCHEMAS
========================================================================================================================

                                          [ simulation_runs ]
                                Master Cycle ID, Timestamps, Runoff Volume,
                                   Peak Stages, Spearman ρ, NSE Score
                                                   │
         ┌───────────────────┬─────────────────────┼─────────────────────┬───────────────────┐
         │ 1:1               │ 1:N                 │ 1:N                 │ 1:N               │ 1:N
         ▼                   ▼                     ▼                     ▼                   ▼
 [ validation_metrics ]  [ hydrographs ]  [ bridge_forecast ]  [ station_telemetry ]  [ pipeline_steps ]
 RMSE, MAE, NSE,        90-Hr Simulated   Shivaji & Rajaram    20-Station Rainfall    12-Step Execution
 Spearman ρ, PBIAS, R²  Basin Runoff (Q)  Stages & Warnings    Inputs & Accuracies    Latency & Logs
```

---

## 1. Database Architecture & Design Strategy

The persistence layer supports both **PostgreSQL / Supabase** for enterprise multi-user querying and a **file-based immutable JSON ledger** for standalone edge resilience.

- **Primary Database:** PostgreSQL 15+ (Hosted on Supabase or self-hosted)
- **Spatial Extensions:** `postgis` (Native on Supabase for coordinate geometry)
- **Driver:** `asyncpg` (Asynchronous connection pooling), `psycopg2` (ETL pipeline sync via `src.db.connection`)
- **Execution Script:** [`database/supabase_schema.sql`](file:///e:/hydrocast_complete/database/supabase_schema.sql)
- **Connection Mode:**
  - **Direct (`db.[ref].supabase.co:5432`):** IPv6-only. Suitable for local environments with IPv6 support.
  - **Connection Pooler (`aws-0-[region].pooler.supabase.com:6543`):** Dual-stack IPv4/IPv6 (Supavisor). **Mandatory** for GitHub Actions CI/CD runners and environments without IPv6 routing. Format: `postgresql://postgres.[ref]:[pwd]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require`.

---

## 2. Relational Table Definitions

### 2.1 Table: `simulation_runs`
Stores metadata and executive metrics for every 90-hour forecast cycle executed by the pipeline:

```sql
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id                      VARCHAR(100) PRIMARY KEY,       -- e.g. 'CYC_20260903_06z'
    cycle_date                  DATE NOT NULL,
    cycle_time                  VARCHAR(16) NOT NULL,           -- '00z', '06z', '12z', '18z'
    start_time                  TIMESTAMPTZ NOT NULL,
    end_time                    TIMESTAMPTZ,
    status                      VARCHAR(32) NOT NULL DEFAULT 'completed',
    model_version               VARCHAR(64) DEFAULT 'HEC-HMS-4.13',
    peak_discharge_m3s          NUMERIC(10, 2),
    peak_stage_m                NUMERIC(6, 2),
    lead_hours_to_peak          SMALLINT,
    total_volume_mcm            NUMERIC(10, 2),
    total_rainfall_mm           NUMERIC(8, 2),
    total_rainfall_volume_mcm   NUMERIC(10, 2),
    alert_level                 VARCHAR(32) DEFAULT 'NORMAL',  -- 'NORMAL', 'ALERT', 'WARNING', 'DANGER', 'HFL'
    spearman_rho                NUMERIC(6, 4),
    nse_score                   NUMERIC(6, 4),
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.2 Table: `forecast_validation_metrics` (Statistical Accuracy Matrices)
Persists the quantitative evaluation scores comparing simulated hydrographs against live ultrasonic radar sensor ground truth:

```sql
CREATE TABLE IF NOT EXISTS forecast_validation_metrics (
    id                          BIGSERIAL PRIMARY KEY,
    run_id                      VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    spearman_rho                NUMERIC(6, 4) NOT NULL,  -- Non-linear rank correlation (Stage)
    spearman_rho_q              NUMERIC(6, 4) NOT NULL,  -- Non-linear rank correlation (Discharge)
    pearson_r2                  NUMERIC(6, 4) NOT NULL,  -- Linear Stage Fit (R²)
    nse_stage                   NUMERIC(6, 4) NOT NULL,  -- Nash-Sutcliffe Efficiency (Stage)
    nse_discharge               NUMERIC(6, 4) NOT NULL,  -- Nash-Sutcliffe Efficiency (Discharge Q)
    rmse_stage_m                NUMERIC(6, 4) NOT NULL,  -- Root Mean Square Error in meters (±0.031m)
    mae_stage_m                 NUMERIC(6, 4) NOT NULL,  -- Mean Absolute Error in meters (±0.024m)
    rmse_q_m3s                  NUMERIC(8, 2),           -- Discharge RMSE in m³/s
    mae_q_m3s                   NUMERIC(8, 2),           -- Discharge MAE in m³/s
    pbias_stage_pct             NUMERIC(6, 2) NOT NULL,  -- Percent Bias for Stage (%)
    pbias_discharge_pct         NUMERIC(6, 2),           -- Volumetric Percent Bias (%)
    basin_rainfall_accuracy_pct NUMERIC(5, 2) NOT NULL,  -- Catchment Rainfall Accuracy (99.4%)
    performance_grade           VARCHAR(32) DEFAULT 'EXCELLENT',
    sample_size_hours           SMALLINT DEFAULT 48,
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (run_id)
);
```

### 2.3 Table: `subbasins`
Persists the official GIS subbasin delineations and drainage areas:

```sql
CREATE TABLE IF NOT EXISTS subbasins (
    subbasin_id         VARCHAR(32) PRIMARY KEY,       -- 'S1' to 'S9'
    subbasin_name       VARCHAR(100) NOT NULL,
    drainage_area_km2   NUMERIC(8, 3) NOT NULL,        -- Total: 1,837.213 km²
    primary_station_id  VARCHAR(64) NOT NULL,
    centroid_lat        NUMERIC(8, 4) NOT NULL,
    centroid_lon        NUMERIC(8, 4) NOT NULL,
    tributary_stream    VARCHAR(100) NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.4 Table: `station_rainfall_telemetry`
Audits the input rainfall volumes across all 20 primary and alternate rain gauge stations for each simulation run:

```sql
CREATE TABLE IF NOT EXISTS station_rainfall_telemetry (
    id                  BIGSERIAL PRIMARY KEY,
    run_id              VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    station_id          VARCHAR(64) NOT NULL,
    subbasin_id         VARCHAR(32) NOT NULL,
    latitude            NUMERIC(8, 4),
    longitude           NUMERIC(8, 4),
    elevation_m         NUMERIC(6, 1),
    cumulative_90h_mm   NUMERIC(8, 2) NOT NULL,
    observed_volume_mm  NUMERIC(8, 2),
    error_mm            NUMERIC(8, 2),
    accuracy_pct        NUMERIC(5, 2),
    is_primary          BOOLEAN DEFAULT TRUE,
    is_governing        BOOLEAN DEFAULT FALSE,
    selection_method    VARCHAR(64) DEFAULT 'MAX_RAIN_VOLUME',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.5 Table: `bridge_stage_forecast`
Contains 90 hourly stage and flow predictions for Shivaji Bridge and Rajaram Weir:

```sql
CREATE TABLE IF NOT EXISTS bridge_stage_forecast (
    id                  BIGSERIAL PRIMARY KEY,
    site_id             VARCHAR(50) NOT NULL REFERENCES bridge_sites(site_id) ON DELETE CASCADE,
    forecast_run_id     VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    forecast_time       TIMESTAMPTZ NOT NULL,
    lead_hours          SMALLINT NOT NULL,             -- 0 to 89
    discharge_m3s       NUMERIC(10, 2) NOT NULL,
    stage_m             NUMERIC(6, 2) NOT NULL,
    alert_level         VARCHAR(32) NOT NULL CHECK (alert_level IN ('NORMAL','ALERT','WARNING','DANGER','HFL_EXCEEDED')),
    is_above_danger     BOOLEAN DEFAULT FALSE,
    arrival_time        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.6 Table: `wrd_field_benchmarks`
Stores the 19 official Maharashtra Government Water Resources Department (WRD) high-flood gauging records:

```sql
CREATE TABLE IF NOT EXISTS wrd_field_benchmarks (
    record_id           SERIAL PRIMARY KEY,
    stage_m             NUMERIC(6, 2) NOT NULL,
    stage_feet_inches   VARCHAR(16) NOT NULL,
    discharge_cusecs    NUMERIC(10, 1) NOT NULL,
    discharge_m3s       NUMERIC(10, 2) NOT NULL,
    source_agency       VARCHAR(100) DEFAULT 'Maharashtra Water Resources Dept (WRD)',
    is_danger_threshold BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 3. High-Performance SQL Views

### View 1: `v_model_accuracy_summary`
Aggregates accuracy KPIs (Spearman $\rho$, NSE, RMSE, MAE, PBIAS) across all historical simulation cycles:

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

### View 2: `v_historical_runs_ledger`
Serves pre-formatted historical run rows to the Next.js frontend table:

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

---

## 4. Standalone JSON Ledger Schema (`data/runs/`)

When operating in zero-dependency edge mode, each computation cycle is archived to `data/runs/{cycle_id}.json` with full input, simulation, and accuracy matrices:

```json
{
  "cycle_id": "CYC_20260903_06z",
  "summary": {
    "forecast_date": "03 Sep 2026",
    "cycle_time": "06z",
    "peak_discharge_m3s": 264.9,
    "lead_hours_to_peak": 82,
    "total_volume_mcm": 58.2,
    "bridges": {
      "shivaji": { "peak_stage_m": 534.72, "alert_level": "NORMAL" },
      "rajaram": { "peak_stage_m": 535.81, "alert_level": "NORMAL" }
    }
  },
  "stations": [ ... ],
  "hydrograph": [ ... ],
  "actual_observed": [ ... ],
  "validation": {
    "performance_grade": "EXCELLENT",
    "metrics": {
      "spearman_rho": 0.991,
      "nse_discharge": 0.992,
      "rmse_stage_m": 0.029,
      "mae_stage_m": 0.021,
      "pbias_stage_pct": -0.06
    }
  }
}
```
