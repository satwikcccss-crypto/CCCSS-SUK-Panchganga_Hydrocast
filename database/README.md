# Database Architecture & Migration Guide

## Relational Schema Specifications

HydroCast relies on PostgreSQL (local production or Supabase managed cloud) for operational time-series storage, audit logs, and analytical accuracy tracking.

### Schema Inventory

| Schema File | Target Environment | Description |
| :--- | :--- | :--- |
| `schema_v3.sql` | Self-Hosted PostgreSQL 15+ | Core relational schema including tables for `simulation_runs`, `hydrograph_results`, `peak_discharge_events`, `bridge_sites`, `rating_curves`, and `alert_events`. |
| `supabase_schema.sql` | Supabase (Cloud Production) | Hardened schema with idempotent migration guards, analytical views (`v_active_alerts`, `v_latest_bridge_forecast`, `v_station_selection_latest`), subbasin topology, and RMSE accuracy matrices. |

---

## Migration & Deployment Instructions

### 1. Cloud Deployment (Supabase)
1. Open the **SQL Editor** in your Supabase project dashboard.
2. Execute [`supabase_schema.sql`](file:///e:/hydrocast_complete/database/supabase_schema.sql).
3. The script executes idempotently with `IF NOT EXISTS` and migration safety guards.

### 2. Local Production PostgreSQL (Windows / Linux)
1. On Windows Server, run the PowerShell setup script:
   ```powershell
   powershell -ExecutionPolicy Bypass -File windows/install_postgres.ps1
   ```
2. Apply the foundational schema:
   ```bash
   psql -U hms_app -d rainfall_runoff -f database/schema_v3.sql
   ```
3. Set your environment variable:
   ```bash
   DATABASE_URL="postgresql://hms_app:password@localhost:5432/rainfall_runoff"
   ```

### 3. CI/CD & GitHub Actions Configuration (Critical IPv4/IPv6 Notice)
> [!IMPORTANT]
> **GitHub Actions runners operate in IPv4-only environments.**
> Supabase direct connections (`db.[project-ref].supabase.co`) resolve exclusively to **IPv6** addresses. Connecting directly from a GitHub Actions workflow will result in:
> `ERROR: connection to server at "db.[project-ref].supabase.co", port 5432 failed: Network is unreachable`

To resolve this, you **must use the Supabase Connection Pooler (Supavisor)** which provides public IPv4 routing:
1. In your **Supabase Dashboard**, navigate to **Project Settings** > **Database** > **Connection Pooling**.
2. Select **Transaction mode** (Port `6543`) or **Session mode** (Port `5432`).
3. Note the connection URI format:
   ```ini
   DATABASE_URL="postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require"
   ```
   *(Notice that the username must include your project reference: `postgres.[PROJECT_REF]`)*
4. Set this URI as your repository secret `DATABASE_URL` under **GitHub Repo > Settings > Secrets and variables > Actions**.
