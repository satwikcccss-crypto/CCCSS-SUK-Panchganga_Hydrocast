# Database Architecture & Persistence Schema

```
========================================================================================
             HYDROCAST POSTGRESQL / SUPABASE & JSON LEDGER SCHEMAS
========================================================================================

                                  [ simulation_runs ]
                        Master Cycle ID, Timestamps, KPIs,
                               Spearman ρ, NSE, Alert
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             │ 1:N                      │ 1:N                      │ 1:N
             ▼                          ▼                          ▼
     [ hydrographs ]         [ station_telemetry ]         [ pipeline_steps ]
    90-Hour Predicted        18-Station Rainfall           12-Step Latency &
    Discharge & Stage        Volumes & Cumulatives         Status Log
             │
             │ 1:N
             ▼
     [ flood_alerts ]
    CWC Alert Levels,
    Peak Stage & Threshold
```

---

## 1. Database Architecture & Design Strategy

The persistence layer supports both **PostgreSQL / Supabase** for enterprise multi-user operations and a **file-based JSON ledger** for standalone edge resilience.

- **Primary Database:** PostgreSQL 15+ (Hosted on Supabase or self-hosted)
- **Driver:** `asyncpg` (Asynchronous connection pooling, parameterized queries)
- **Migrations:** Version-controlled SQL scripts located in [`system/database/schema_v3.sql`](file:///e:/hydrocast_complete/system/database/schema_v3.sql) and [`system/database/supabase_schema.sql`](file:///e:/hydrocast_complete/system/database/supabase_schema.sql).

---

## 2. Relational Table Definitions

### 2.1 Table: `simulation_runs`
Stores metadata for every 90-hour forecast cycle executed by the pipeline:

```sql
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id              VARCHAR(64) PRIMARY KEY,       -- e.g. 'CYC_20260903_06z'
    forecast_date       DATE NOT NULL,
    cycle_time          VARCHAR(8) NOT NULL,           -- '00z', '06z', '12z', '18z'
    start_time          TIMESTAMPTZ NOT NULL,
    end_time            TIMESTAMPTZ,
    duration_seconds    NUMERIC(6, 2),
    status              VARCHAR(20) DEFAULT 'running', -- 'running', 'completed', 'failed'
    peak_discharge_m3s  NUMERIC(10, 2),
    lead_hours_to_peak  INT,
    total_volume_mcm    NUMERIC(10, 2),
    total_rainfall_mm   NUMERIC(8, 2),
    shivaji_peak_stage  NUMERIC(6, 2),
    rajaram_peak_stage  NUMERIC(6, 2),
    alert_level         VARCHAR(20) DEFAULT 'NORMAL',  -- 'NORMAL', 'ALERT', 'WARNING', 'DANGER', 'HFL'
    spearman_rho        NUMERIC(6, 4),
    nse_score           NUMERIC(6, 4),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.2 Table: `hydrographs`
Contains the 90-hour simulated time series for each run:

```sql
CREATE TABLE IF NOT EXISTS hydrographs (
    id                  BIGSERIAL PRIMARY KEY,
    run_id              VARCHAR(64) REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    site_id             VARCHAR(32) NOT NULL,          -- 'SHIVAJI_BRIDGE', 'RAJARAM_BRIDGE', 'J_OUTLET'
    lead_hour           INT NOT NULL,                  -- 0 to 89
    forecast_time       TIMESTAMPTZ NOT NULL,
    discharge_m3s       NUMERIC(10, 2) NOT NULL,
    surface_runoff_m3s  NUMERIC(10, 2),
    baseflow_m3s        NUMERIC(10, 2),
    stage_m             NUMERIC(6, 2) NOT NULL,
    is_peak             BOOLEAN DEFAULT FALSE,
    CONSTRAINT uq_run_site_hour UNIQUE (run_id, site_id, lead_hour)
);
CREATE INDEX idx_hydrographs_lookup ON hydrographs(run_id, site_id, lead_hour);
```

### 2.3 Table: `station_telemetry`
Tracks the 18 Panchganga rain gauge observations and Open-Meteo forecasts:

```sql
CREATE TABLE IF NOT EXISTS station_telemetry (
    id                  BIGSERIAL PRIMARY KEY,
    run_id              VARCHAR(64) REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    station_id          VARCHAR(32) NOT NULL,
    subbasin_id         VARCHAR(8) NOT NULL,
    predicted_volume_mm NUMERIC(8, 2) NOT NULL,
    observed_volume_mm  NUMERIC(8, 2),
    error_mm            NUMERIC(8, 2),
    accuracy_pct        NUMERIC(5, 2),
    is_governing        BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.4 Table: `flood_alerts`
Active civil warnings generated when water stages exceed CWC thresholds:

```sql
CREATE TABLE IF NOT EXISTS flood_alerts (
    alert_id            BIGSERIAL PRIMARY KEY,
    run_id              VARCHAR(64) REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    site_id             VARCHAR(32) NOT NULL,
    alert_level         VARCHAR(20) NOT NULL,          -- 'ALERT', 'WARNING', 'DANGER', 'HFL_EXCEEDED'
    current_stage_m     NUMERIC(6, 2) NOT NULL,
    peak_stage_m        NUMERIC(6, 2) NOT NULL,
    lead_hours_to_peak  INT,
    message             TEXT NOT NULL,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 3. High-Performance SQL Views

### View: `v_cycle_performance`
Aggregates historical model execution performance:

```sql
CREATE OR REPLACE VIEW v_cycle_performance AS
SELECT 
    r.run_id,
    r.forecast_date,
    r.cycle_time,
    r.start_time,
    r.duration_seconds,
    r.status,
    r.peak_discharge_m3s,
    r.shivaji_peak_stage,
    r.alert_level,
    r.spearman_rho,
    r.nse_score,
    COUNT(h.id) AS hydrograph_points_count
FROM simulation_runs r
LEFT JOIN hydrographs h ON r.run_id = h.run_id
GROUP BY r.run_id
ORDER BY r.start_time DESC;
```

---

## 4. Standalone JSON Ledger Schema (`data/runs/`)

When running in zero-dependency mode, runs are saved to `system/data/runs/{cycle_id}.json` with the following document structure:

```json
{
  "cycle_id": "CYC_20260903_06z",
  "summary": {
    "forecast_date": "03 Sep 2026",
    "cycle_time": "06z",
    "peak_discharge_m3s": 544.4,
    "lead_hours_to_peak": 24,
    "total_volume_mcm": 74.3,
    "bridges": {
      "shivaji": { "peak_stage_m": 535.84, "alert_level": "NORMAL" },
      "rajaram": { "peak_stage_m": 536.25, "alert_level": "NORMAL" }
    }
  },
  "stations": [ ... ],
  "hydrograph": [ ... ],
  "actual_observed": [ ... ],
  "validation": {
    "performance_grade": "EXCELLENT",
    "metrics": { "spearman_rho": 0.9889, "nse_discharge": 0.9879 }
  }
}
```

The runs index is persisted in `system/data/runs/runs_index.json` and mirrored directly into `system/frontend/public/data/runs_history.json`, guaranteeing sub-millisecond query performance on the dashboard.
