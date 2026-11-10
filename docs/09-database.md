# 09 — Database

## Scope

This document describes the PostgreSQL database schema, tables, views, indexes, and migrations. Audience: **Maintainer**.

## Database Configuration

| Property | Value |
|----------|-------|
| Engine | PostgreSQL 16 + PostGIS |
| Data Directory | `E:\PostgreSQL\16` |
| Port | 5432 |
| Database Name | `rainfall_runoff` |
| Application User | `hms_app` / `hydrocast` |
| Coordinate System | WGS 84 (EPSG:4326) |

## Schema Overview

The database contains **15 relational tables** and **7 analytical views**.

### PostGIS Spatial Extension

PostGIS is installed in a dedicated `extensions` schema to prevent namespace pollution:

```sql
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;
```

Rain gauge coordinates use explicit `latitude`/`longitude` fields alongside generated PostGIS `GEOMETRY(Point, 4326)` columns with GiST spatial indexes.

## Tables

### Hydrological Data

| Table | Rows (typical) | Purpose |
|-------|----------------|---------|
| `subbasins` | 9 | Subbasin delineation: area, curve number, centroid |
| `gauge_stations` | 20 | Rain gauge registry: coordinates, elevation |
| `bridge_sites` | 2 | Shivaji Bridge and Rajaram Weir gauging stations |
| `rating_curves` | 26 x 2 sites | WRD stage-discharge anchor points |

### Forecast Data (per cycle)

| Table | Rows (typical) | Purpose |
|-------|----------------|---------|
| `simulation_runs` | 1 per cycle | Run metadata, status, peak values |
| `station_rainfall_telemetry` | 20 per run | Per-station rainfall with governing selection flag |
| `hydrograph_results` | 90 per run | 90-hr outlet discharge time series |
| `peak_discharge_events` | 1 per run | Detected peak discharge event |
| `runoff_summary` | 1 per run | Dashboard summary row per cycle |
| `bridge_stage_forecast` | 90 x 2 per run | Stage forecast at both bridges |
| `alert_events` | N | Alert tier breaches per run |
| `pipeline_step_log` | 12 per run | Per-stage execution log and timing |

### Validation

| Table | Rows | Purpose |
|-------|------|---------|
| `forecast_validation_metrics` | 1 per run | NSE, RMSE, Spearman, PBIAS accuracy metrics |
| `calibration_parameters` | N | Levenberg-Marquardt fitted parameters per event |

### Authentication

| Table | Rows | Purpose |
|-------|------|---------|
| `admin_users` | N | User accounts with bcrypt hashes and roles |
| `admin_login_log` | N | Audit trail of all login attempts |

### admin_users Schema

```sql
CREATE TABLE admin_users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    role          VARCHAR(32) DEFAULT 'govt',
    display_name  VARCHAR(128),
    email         VARCHAR(256),
    is_active     BOOLEAN DEFAULT TRUE,
    must_change_password BOOLEAN DEFAULT FALSE,
    reset_token   VARCHAR(128),
    reset_token_expires TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX idx_admin_users_email ON admin_users (email) WHERE email IS NOT NULL;
```

## Views (7)

| View | Purpose |
|------|---------|
| `v_model_accuracy_summary` | Latest validation metrics summary |
| `v_bridge_alert_summary` | Active alerts per bridge |
| `v_historical_runs_ledger` | Paginated run history |
| `v_latest_hydrograph` | Most recent 90-hr hydrograph |
| `v_latest_peak_summary` | Latest peak discharge and stage |
| `v_active_alerts_enriched` | Active alerts with bridge metadata |
| `v_cycle_performance` | Pipeline step timing and status |

## Migrations

Migration files are in `database/auth/`:

| File | Purpose |
|------|---------|
| `01_admin_auth.sql` | Initial admin_users and admin_login_log tables |
| `02_admin_users_upgrade.sql` | Add display_name, email, is_active, reset_token columns |
| `03_seed_adm1_users.sql` | Template for seeding @Adm1 primary administrators |

## Connection Management

The backend uses `asyncpg` for async PostgreSQL connections with a resilient connection pool (`backend/db/resilient_pool.py`):

- Connection pooling with configurable min/max connections
- Automatic reconnection on connection loss
- Staged transaction replay for database recovery scenarios
- Health checks before query execution

## Backup

Database backups are managed by the Windows service script `windows/backup_database.ps1`:
- Full `pg_dump` to timestamped SQL file
- Configurable retention policy
- Can be triggered manually via the admin console

## Source Files

| File | Purpose |
|------|---------|
| `database/supabase_schema.sql` | Complete schema definition (558 lines) |
| `database/auth/` | Migration scripts |
| `backend/db/connection.py` | Database connection configuration |
| `backend/db/resilient_pool.py` | Resilient async connection pool |
| `backend/db/store_results.py` | Forecast result persistence |
| `backend/db/archive_runs.py` | Cold-storage Parquet archival |
| `windows/backup_database.ps1` | Backup automation script |
