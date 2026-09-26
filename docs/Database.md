# HydroCast Database Architecture & Cold Storage Archival Engine

```
====================================================================================================
             PANCHGANGA HYDROCAST - UNIFIED SINGLE-TREE DATABASE SCHEMA
====================================================================================================

      +----------------------------------------------------------------------------------+
      |                                simulation_runs                                   |
      |----------------------------------------------------------------------------------|
      | PK run_id                 VARCHAR(64)                                            |
      |    cycle_id               VARCHAR(32)                                            |
      |    start_time             TIMESTAMPTZ                                            |
      |    end_time               TIMESTAMPTZ                                            |
      |    peak_discharge_m3s     DOUBLE PRECISION                                       |
      |    peak_stage_m           DOUBLE PRECISION                                       |
      |    lead_hours_to_peak     INTEGER                                                |
      |    status                 VARCHAR(32)                                            |
      +----------------------------------------------------------------------------------+
               |                               |                               |
               | 1:N                           | 1:N                           | 1:N
               v                               v                               v
+-------------------------------+ +-------------------------------+ +-------------------------------+
|     hydrograph_results        | |    bridge_stage_forecast      | |       rainfall_data           |
|-------------------------------| |-------------------------------| |-------------------------------|
| PK  id           BIGSERIAL    | | PK  id           BIGSERIAL    | | PK  id           BIGSERIAL    |
| FK  run_id       VARCHAR(64)  | | FK  run_id       VARCHAR(64)  | | FK  run_id       VARCHAR(64)  |
|     node_id      VARCHAR(32)  | |     bridge_id    VARCHAR(32)  | |     station_id   VARCHAR(32)  |
|     timestamp    TIMESTAMPTZ  | |     forecast_time TIMESTAMPTZ | |     timestamp    TIMESTAMPTZ  |
|     discharge    DOUBLE PREC. | |     stage_m      DOUBLE PREC. | |     rainfall_mm  DOUBLE PREC. |
|     baseflow     DOUBLE PREC. | |     discharge    DOUBLE PREC. | |     subbasin_id  VARCHAR(16)  |
+-------------------------------+ +-------------------------------+ +-------------------------------+
               |                               |                               |
               +-------------------------------+-------------------------------+
                                               |
                                               v (Records > 90 Days)
                               +-------------------------------+
                               |  Parquet Cold Storage Engine  |
                               |  (src/db/archive_runs.py)     |
                               +-------------------------------+
                               | Partitions:                   |
                               | data/archives/year=YYYY/      |
                               |   month=MM/<table_YYYYMM>.pq  |
                               | Snappy PyArrow Compression    |
                               | PostgreSQL Table Pruning      |
                               +-------------------------------+
```

---

## 1. Single-Tree PostgreSQL & PostGIS Schema Architecture

HydroCast utilizes an enterprise PostgreSQL 15+ database hosted on Supabase (`database/supabase_schema.sql`). The schema is structured with strict foreign key constraints, declarative check constraints, and PostGIS spatial indexing.

### 1.1 Master Simulation Runs Ledger (`simulation_runs`)
Stores top-level metadata and executive KPIs for every 6-hourly automated computation cycle:

```sql
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    cycle_id VARCHAR(32) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    peak_discharge_m3s DOUBLE PRECISION,
    peak_stage_m DOUBLE PRECISION,
    lead_hours_to_peak INTEGER,
    total_volume_mcm DOUBLE PRECISION,
    status VARCHAR(32) DEFAULT 'COMPLETED',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_simulation_runs_cycle ON simulation_runs(cycle_id);
```

### 1.2 Time-Series Tables

1. **`hydrograph_results`:** 90-hour discrete hydrograph coordinates for subbasin outlets and river reaches.
2. **`bridge_stage_forecast`:** Hourly stage and discharge projections for Chhatrapati Shivaji Maharaj Bridge and Rajaram K.T. Weir.
3. **`rainfall_data`:** Ingested ECMWF IFS 90-hour hyetographs across 18 stations.
4. **`wrd_field_benchmarks`:** Authoritative Maharashtra Water Resources Department (WRD) historical staff gauge benchmarks (11.0 ft to 49.8 ft HFL).

---

## 2. Parquet Cold Storage & Archival Engine (`src/db/archive_runs.py`)

### 2.1 The Big Data Challenge in Hydrology
Running 4 forecast cycles per day generates:
- $4 \\times 90 = 360$ rows per run in `hydrograph_results` across multiple nodes ($\approx 1.5\\text{ million rows/year}$)
- High-frequency 5-minute IoT sensor readings ($\approx 105,000\\text{ rows/year}$)
Unchecked growth degrades B-Tree index scan speeds and increases cloud database storage costs.

### 2.2 Cold Storage Architecture
The archival engine (`src/db/archive_runs.py`) solves this by migrating data older than **90 days** (`ARCHIVE_RETENTION_DAYS`) into compressed **Apache Parquet** columnar partitions:

```bash
# Automated Archival Command
python -m src.db.archive_runs --retention-days 90
```

1. **Partition Structure on Disk:**
   ```
   data/archives/
   ├── year=2026/
   │   ├── month=06/
   │   │   ├── hydrograph_results_202606.parquet
   │   │   └── bridge_stage_forecast_202606.parquet
   │   └── month=07/
   │       └── ...
   ```
2. **Storage Efficiency:** PyArrow with Snappy compression achieves an **88% to 92% storage reduction** compared to raw PostgreSQL heap pages.
3. **Database Pruning:** Rows successfully written to Parquet are transactionally deleted from PostgreSQL in batches of 50,000 rows, preserving sub-second query performance.
4. **Indefinite History:** `simulation_runs` summary rows are **NEVER pruned**, ensuring complete historical auditability.
