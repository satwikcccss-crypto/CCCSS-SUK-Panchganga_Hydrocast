# HydroCast Panchganga - Database Schema & Seeds

## Overview

This directory contains the complete database schema, seed data, storage configuration, and authentication setup for the HydroCast Panchganga flood forecasting system.

## Directory Structure

```
database/
├── README.md                     # This file
├── schema/                       # Canonical table definitions (DDL)
│   ├── 01_core_tables.sql        # subbasins, gauge_stations, bridge_sites
│   ├── 02_simulation_runs.sql    # simulation_runs
│   ├── 03_forecast_validation_metrics.sql
│   ├── 04_hydrograph_results.sql
│   ├── 05_bridge_stage_forecast.sql
│   ├── 06_wrd_field_benchmarks.sql
│   ├── 07_pipeline_step_log.sql
│   └── 08_visitor_counts.sql
├── seeds/                        # Reference/seed data
│   ├── 01_subbasins.sql          # S1-S9 subbasin definitions
│   ├── 02_gauge_stations.sql     # 20 rain gauge stations
│   ├── 03_bridge_sites.sql       # Shivaji Bridge & Rajaram Weir
│   └── 04_wrd_field_benchmarks.sql  # WRD official rating benchmarks
├── storage/                      # Storage configuration
│   ├── 01_tablespace.sql         # Dedicated tablespace on E:\ drive
│   └── 02_retention_policies.sql # TimescaleDB compression & retention
├── auth/                         # Authentication & authorization
│   └── 01_admin_users.sql        # Admin users & login audit trail
├── migrations/                   # Alembic migration files
│   └── versions/
│       └── 001_initial_schema.py
└── README.md                     # This documentation
```

## Loading Order

Apply files in this order on a fresh PostgreSQL 16 + PostGIS database:

```sql
-- 1. Create extensions and tablespace
\i database/storage/01_tablespace.sql

-- 2. Create core schema
\i database/schema/01_core_tables.sql
\i database/schema/02_simulation_runs.sql
\i database/schema/03_forecast_validation_metrics.sql
\i database/schema/04_hydrograph_results.sql
\i database/schema/05_bridge_stage_forecast.sql
\i database/schema/06_wrd_field_benchmarks.sql
\i database/schema/07_pipeline_step_log.sql
\i database/schema/08_visitor_counts.sql

-- 3. Seed reference data
\i database/seeds/01_subbasins.sql
\i database/seeds/02_gauge_stations.sql
\i database/seeds/03_bridge_sites.sql
\i database/seeds/04_wrd_field_benchmarks.sql

-- 4. Create admin users
\i database/auth/01_admin_users.sql

-- 5. Apply storage policies (compression, retention)
\i database/storage/02_retention_policies.sql
```

## Table Reference

| Table | Description | Rows (approx) |
|-------|-------------|---------------|
| `subbasins` | 9 Panchganga subbasin definitions | 9 |
| `gauge_stations` | 20 rain gauge stations | 20 |
| `bridge_sites` | Shivaji Bridge & Rajaram Weir | 2 |
| `simulation_runs` | Forecast cycle ledger | Grows per cycle |
| `forecast_validation_metrics` | Accuracy metrics per run | 1 per run |
| `hydrograph_results` | 90-hour discharge hydrographs | ~90 per run |
| `bridge_stage_forecast` | Stage forecasts per bridge | ~180 per run |
| `wrd_field_benchmarks` | WRD official rating benchmarks | ~20 |
| `pipeline_step_log` | 12-step pipeline execution log | ~12 per cycle |
| `visitor_counts` | Daily visitor statistics | 1 per day |

## Environment Variables

Set these environment variables before running the database setup:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://hms_app:hms_secret_2026@127.0.0.1:5432/rainfall_runoff` |
| `POSTGRES_USER` | Database username | `hms_app` |
| `POSTGRES_PASSWORD` | Database password | `hms_secret_2026` |
| `POSTGRES_DB` | Database name | `rainfall_runoff` |

## Tablespace

The `hydrocast_ts` tablespace is created on the `E:\` drive (3512 GB dedicated storage for simulation data). The `E:\` drive must be pre-formatted and accessible by the PostgreSQL service account before running `01_tablespace.sql`.

## Migration Management

Schema changes are tracked via Alembic migrations in the `alembic/` directory at the project root:

```
alembic/
├── alembic.ini
├── env.py
└── versions/
    └── 001_initial_schema.py
```

To create a new migration:
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Reset Database

To drop all tables and recreate from scratch:

```sql
DROP TABLE IF EXISTS visitor_counts CASCADE;
DROP TABLE IF EXISTS pipeline_step_log CASCADE;
DROP TABLE IF EXISTS wrd_field_benchmarks CASCADE;
DROP TABLE IF EXISTS bridge_stage_forecast CASCADE;
DROP TABLE IF EXISTS hydrograph_results CASCADE;
DROP TABLE IF EXISTS forecast_validation_metrics CASCADE;
DROP TABLE IF EXISTS simulation_runs CASCADE;
DROP TABLE IF EXISTS bridge_sites CASCADE;
DROP TABLE IF EXISTS gauge_stations CASCADE;
DROP TABLE IF EXISTS subbasins CASCADE;
DROP TABLE IF EXISTS admin_login_log CASCADE;
DROP TABLE IF EXISTS admin_users CASCADE;
DROP EXTENSION IF EXISTS postgis;
```

Then re-run the schema and seeds in order.