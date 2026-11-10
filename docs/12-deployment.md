# 12 — Deployment

## Scope

This document covers Windows Server deployment, service configuration, environment setup, and backup procedures. Audience: **Maintainer**.

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10/11 or Windows Server 2019+ | Windows Server 2022 |
| RAM | 4 GB | 8 GB |
| Storage | 20 GB | 50 GB (database growth) |
| Python | 3.12+ | 3.12 |
| Node.js | 18+ | 20 LTS |
| PostgreSQL | 16+ with PostGIS | 16.x |
| Network | Outbound HTTPS (Open-Meteo, ThingSpeak) | Static IP recommended |

## Directory Structure

```
E:\Hydrocast Windows Server\
  backend\           Python backend (FastAPI, pipeline, ML)
  frontend-public\   Next.js public dashboard
  frontend-admin\    Next.js admin console
  database\          SQL schemas and migrations
  windows\           PowerShell deployment scripts
  data\              Runtime data (logs, cache, runs)
  docs\              Documentation suite
  .env               Environment configuration (DO NOT COMMIT)
```

## Environment Variables

All configuration is via the `.env` file at the project root. See `.env.example` for the template.

### Required Categories

| Category | Variables | Description |
|----------|----------|-------------|
| Database | `DATABASE_URL` | PostgreSQL connection string |
| Auth | `JWT_SECRET`, `ADMIN_JWT_SECRET` | Token signing keys (startup aborts if missing) |
| Auth | `API_KEY` | Service-to-service API key |
| Auth | `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Emergency fallback credentials |
| ThingSpeak | Channel IDs and read API keys | One pair per sensor station (SS, NW, IK) |
| Frontend | `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL` | API and WebSocket URLs |

## Installation Steps

### 1. PostgreSQL Setup

```powershell
.\windows\install_postgres.ps1
.\windows\init_database.ps1
```

Then run the schema and migrations:

```powershell
psql -U <db_user> -d rainfall_runoff -f database/supabase_schema.sql
psql -U <db_user> -d rainfall_runoff -f database/auth/01_admin_auth.sql
psql -U <db_user> -d rainfall_runoff -f database/auth/02_admin_users_upgrade.sql
```

### 2. Seed Admin Users

```powershell
python -m backend.scripts.seed_adm1
```

This creates the 5 @Adm1 primary administrators. The initial password is printed to the console and must be changed on first login.

### 3. Python Backend

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Start Public API
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Start Admin API (separate terminal)
uvicorn backend.api.admin_app:app --host 0.0.0.0 --port 8001 --workers 2
```

### 4. Frontend Dashboards

```powershell
# Public Dashboard
cd frontend-public
npm install
npm run build
npm start  # Port 3000

# Admin Console (separate terminal)
cd frontend-admin
npm install
npm run build
npm start  # Port 3001
```

## Windows Services

Install as persistent Windows Services using NSSM:

```powershell
.\windows\install_services.ps1
```

Creates services for:
- `HydroCast-PublicAPI` (port 8000)
- `HydroCast-AdminAPI` (port 8001)
- `HydroCast-PublicDashboard` (port 3000)
- `HydroCast-AdminConsole` (port 3001)
- `HydroCast-Scheduler` (6-hourly pipeline daemon)

Service control:

```powershell
.\windows\service_control.ps1 -Action start
.\windows\service_control.ps1 -Action stop
.\windows\service_control.ps1 -Action status
```

## Database Backup

```powershell
.\windows\backup_database.ps1
```

Creates a timestamped `pg_dump` in the configured backup directory.

## System Diagnostics

```powershell
.\windows\system_diag.ps1
```

Checks: PostgreSQL connectivity, API health endpoints, frontend build status, disk space, service status.

## Docker Deployment (Alternative)

For Linux/cloud deployment, the system is fully containerized:

```bash
docker build -t hydrocast-backend:2.0.0 .
docker-compose up -d
```

See the Dockerfile for multi-stage build targets (runner, docs, dev).

## Windows Scripts Reference

| Script | Purpose |
|--------|---------|
| `windows/install_postgres.ps1` | PostgreSQL installation |
| `windows/init_database.ps1` | Database initialization |
| `windows/install_services.ps1` | NSSM service installation |
| `windows/service_control.ps1` | Start/stop/status services |
| `windows/backup_database.ps1` | Database backup |
| `windows/run_pipeline_manual.ps1` | Manual pipeline execution |
| `windows/system_diag.ps1` | System health diagnostics |
| `windows/storage_setup.sql` | PostgreSQL tablespace configuration |

## Firewall Configuration

Ensure these ports are open:

| Port | Service | Access |
|------|---------|--------|
| 8000 | Public API | LAN / Internet (behind reverse proxy) |
| 8001 | Admin API | LAN only (restricted) |
| 3000 | Public Dashboard | LAN / Internet |
| 3001 | Admin Console | LAN only (restricted) |
| 5432 | PostgreSQL | Localhost only |

## HTTPS (Production)

For production deployment behind a reverse proxy (Nginx, Caddy, IIS ARR):
- Terminate TLS at the proxy
- Forward to localhost ports
- Set `FORWARDED_ALLOW_IPS` to the proxy IP only
- Enable HSTS headers (already configured in Next.js)
