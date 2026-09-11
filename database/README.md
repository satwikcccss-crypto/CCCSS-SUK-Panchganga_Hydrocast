# Database Architecture & Migration Guide

<p align="center">
  <img src="../docs/assets/hydrocast_main_banner.jpg" alt="HydroCast Database Operations Command Center" width="100%">
</p>

## Relational Schema Specifications

HydroCast relies on PostgreSQL (local production, Docker PostGIS, or Supabase managed cloud) for operational time-series storage, audit logs, and analytical accuracy tracking.

## Database & Infrastructure Stack

| Area | Tool |
| :--- | :--- |
| **Databases** | ![PostgreSQL](https://img.shields.io/badge/DB-PostgreSQL_15-4169E1?style=flat&logo=postgresql&logoColor=white) ![Supabase](https://img.shields.io/badge/DB-Supabase-3ECF8E?style=flat&logo=supabase&logoColor=black) ![SQLite](https://img.shields.io/badge/DB-SQLite-003B57?style=flat&logo=sqlite&logoColor=white) ![PostGIS](https://img.shields.io/badge/DB-PostGIS-336791?style=flat&logo=postgresql&logoColor=white) |
| **Languages & Query** | ![SQL](https://img.shields.io/badge/Code-SQL_PL%2FpgSQL-CC292B?style=flat&logo=postgresql&logoColor=white) ![Python](https://img.shields.io/badge/Code-Python_asyncpg-3776AB?style=flat&logo=python&logoColor=white) ![Bash](https://img.shields.io/badge/Code-Bash-4EAA25?style=flat&logo=gnubash&logoColor=white) |
| **Infrastructure & Archival** | ![Supavisor](https://img.shields.io/badge/Infra-Supavisor_Pooler-3ECF8E?style=flat&logo=supabase&logoColor=black) ![Apache Parquet](https://img.shields.io/badge/Storage-Apache_Parquet-4B67A1?style=flat&logo=apache&logoColor=white) ![Docker](https://img.shields.io/badge/Containers-Docker-2496ED?style=flat&logo=docker&logoColor=white) |

---

### Schema Inventory

| Schema File | Target Environment | Description |
| :--- | :--- | :--- |
| `supabase_schema.sql` | PostgreSQL & Supabase (Cloud Production) | The "Single-Tree" relational schema. Includes tables for `simulation_runs`, `hydrograph_results`, `bridge_stage_forecast`, `observed_rainfall_qc`, and `pipeline_step_log` with strict `ON DELETE CASCADE` foreign keys enforcing perfect data lineage. Also includes analytical views (`v_model_accuracy_summary`, `v_bridge_alert_summary`, `v_historical_runs_ledger`). |

---

## Migration & Deployment Instructions

### 1. Cloud Deployment (Supabase)
1. Open the **SQL Editor** in your Supabase project dashboard.
2. Execute [`supabase_schema.sql`](file:///e:/hydrocast_complete/database/supabase_schema.sql).
3. The script executes idempotently with `IF NOT EXISTS` and migration safety guards.

### 2. Local Production PostgreSQL / Docker PostGIS
To run an offline or air-gapped PostgreSQL instance with PostGIS enabled:
```bash
docker compose up -d hydrocast-db
```
The container initializes automatically with `database/supabase_schema.sql` mounted into `/docker-entrypoint-initdb.d/`.

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

---

## 4. Cold Storage & Parquet Archival Strategy (`src/db/archive_runs.py`)

To prevent database disk bloat while retaining complete historical auditability:
- Operational runs older than 90 days have their granular 15-minute `hydrograph_results` and `rainfall_data` extracted and compressed into Snappy-compressed Apache Parquet format.
- Run summaries, KPI metrics, and validation scores remain permanently in PostgreSQL `simulation_runs`.
- Archival execution:
  ```bash
  python src/db/archive_runs.py --days 90 --output-dir data/archives/
  ```
- Can also be triggered securely via the authenticated admin REST endpoint:
  ```bash
  POST /api/v1/admin/archive?retention_days=90
  ```

