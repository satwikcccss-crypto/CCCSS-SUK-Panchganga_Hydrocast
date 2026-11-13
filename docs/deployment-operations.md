# Production Deployment, Operations & Automation Manual (Windows Server Edition)

# Production Deployment, Operations & Automation Manual

---

## Interactive diagram consoles

The console below is the rendered reference for this page: it carries the same structure, tier boundaries and failure branches that the prose describes.

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 06</span>
      <strong>Hybrid OS Deployment Topology</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/06-deployment-docker-os.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/06-deployment-docker-os.html?embed=1" title="Hybrid OS Deployment Topology Console"></iframe>
</div>

---

## 1. Unified Windows Server Deployment (Primary Path)

HydroCast on Windows Server Standard is **100% self-hosted**, running on university infrastructure with no Vercel, no Supabase, and no cloud dependency. All services are registered as native Windows Services via NSSM (Non-Sucking Service Manager). The full deployment stack consists of:

* **HydroCast-Backend** (FastAPI on port 8000) — REST API & WebSocket hub
* **HydroCast-Scheduler** (6-hourly pipeline daemon) — Triggers 12-step forecast cycles
* **HydroCast-Watchdog** (15s heartbeat probe) — Supervises scheduler and backend
* **HydroCast-PublicWeb** (Next.js on port 3000) — Public disaster intelligence portal
* **HydroCast-OperatorConsole** (Next.js on port 3001) — Operator mission control console

### 1.1 Server Prerequisites & Specifications

| Resource | Specification | Notes |
| :--- | :--- | :--- |
| **Operating System** | Windows Server Standard (2019 / 2022 / 2025) | 64-bit required |
| **System Memory** | 16 GB RAM minimum (24+ GB recommended) | Allocated for GIS and routing operations |
| **Storage Architecture** | C:\ (OS & Binaries), E:\ (Data & Database) | E:\ stores PostgreSQL data, DSS runs, and backup archives |
| **Database Engine** | PostgreSQL 16.x x64 with PostGIS 3.4 | Port 5432, local bound only (firewalled to localhost/VPN) |
| **Python Runtime** | Python 3.12.x 64-bit | In PATH, virtualenv recommended |
| **Node.js Runtime** | Node.js v18.x or v20.x LTS | Powers ports 3000 and 3001 |
| **Hydrologic Engine** | HEC-HMS 4.13 x64 | `C:\Program Files\HEC\HEC-HMS\4.13\HEC-HMS.exe` (for Jython path) |

---

### 1.2 Step-by-Step Clean-Slate Build & Installation Runbook

Execute these steps in an elevated **Administrator PowerShell** prompt. All steps are idempotent — re-running is safe.

#### Step 1: Run Pre-Flight Diagnostics

Validate that all system ports, runtimes, dependencies, and file permissions are ready:

```powershell
 powershell -ExecutionPolicy Bypass -File .\windows\system_diag.ps1
```

*Verification criteria: Output must report `System status: READY FOR PRODUCTION`.*

#### Step 2: Initialize PostgreSQL Database

Create the `rainfall_runoff` database, tables, spatial indexes, and approved accounts:

```powershell
 powershell -ExecutionPolicy Bypass -File .\windows\init_database.ps1 -PgUser "postgres" -PgPassword "YourAdminPassword"
```

*Verification criteria: `[SUCCESS] PostgreSQL Database initialized and ready for production.`*

Then run the schema and migrations:

```powershell
 psql -U postgres -d rainfall_runoff -f database/schema.sql
 psql -U postgres -d rainfall_runoff -f database/auth/01_admin_auth.sql
 psql -U postgres -d rainfall_runoff -f database/auth/02_admin_users_upgrade.sql
```

#### Step 3: Configure Environment Secrets

Copy the example environment file and configure all secrets. **Never commit the `.env` file.**

```powershell
 copy .env.example .env
```

Edit `.env` with your secure values (refer to SECURITY.md for the complete list). Key variables:

- `JWT_SECRET` — 48+ random bytes for token signing
- `API_KEY` — random service-to-service key
- `ADMIN_PASSWORD` — strong, unique password (do not use hardcoded defaults like `Dev@Adm1` or `PI@Adm1`)
- `DATABASE_URL` — `postgresql://postgres:PASSWORD@127.0.0.1:5432/rainfall_runoff`
- `INTERNAL_KEY` — 16+ random characters for broadcast operations
- `CORS_ORIGINS` — explicit allowlist (e.g., `https://dashboard.yourdomain.org`)
- `VISIT_HASH_SALT` — random salt for IP hashing
- `TELEGRAM_WEBHOOK_SECRET` — random secret for Telegram webhook validation

#### Step 4: Build Frontend Production Assets

Compile the Next.js production builds for both portals. This must be done **after** the `.env` is configured, as the build reads `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` from the environment.

```powershell
 cd frontend-public
 npm ci
 npm run build
 cd ..

 cd frontend-admin
 npm ci
 npm run build
 cd ..
```

*Success looks like: Next.js compilation complete, bundles output to `out/` directories, no TypeScript errors.*

#### Step 5: Register Windows Services (NSSM)

Install the backend, scheduler, watchdog, public portal, and operator console as native Windows Services:

```powershell
 powershell -ExecutionPolicy Bypass -File .\windows\install_services.ps1
```

*Verification criteria: All 5 services registered with `SERVICE_AUTO_START` and failure restart actions:*

- `HydroCast-Backend` (port 8000) — FastAPI + WebSocket
- `HydroCast-Scheduler` (6-hourly pipeline daemon) — Triggers forecast cycles
- `HydroCast-Watchdog` (15s heartbeat probe) — Supervises scheduler/backend
- `HydroCast-PublicWeb` (port 3000) — Next.js public portal
- `HydroCast-OperatorConsole` (port 3001) — Next.js operator console

#### Step 6: Launch and Verify Services

Start all registered services and inspect their status:

```powershell
 powershell -ExecutionPolicy Bypass -File .\windows\service_control.ps1 -Action start
 powershell -ExecutionPolicy Bypass -File .\windows\service_control.ps1 -Action status
```

*Success looks like: All 5 services running, backend responding on http://127.0.0.1:8000, admin console on http://127.0.0.1:3001.*

#### Step 7: Smoke-Test a Manual Forecast Cycle

Execute a test run directly from PowerShell to verify the entire pipeline:

```powershell
 powershell -ExecutionPolicy Bypass -File .\windows\run_pipeline_manual.ps1
```

#### Step 8: Verify Health Endpoints

```powershell
 curl http://127.0.0.1:8000/api/v1/health
 curl http://127.0.0.1:8000/healthz/live
 curl http://127.0.0.1:8000/healthz/ready
```

*Success looks like:* JSON response with `"status": "healthy"` from `/health`, `"ready": true` from `/healthz/ready`.

---

### 1.3 Caddyfile Reverse Proxy (Production)

All external traffic terminates at a reverse proxy. The Caddyfile routes traffic to the correct internal ports. **TLS is terminated at the proxy**; the backend services bind to `127.0.0.1` only.

```caddyfile
; HydroCast Windows Server Reverse Proxy

; Public portal (port 3000) — accessible to citizens & officials
dashboard.example.org/* {
    reverse_proxy 127.0.0.1:3000
}

; Operator console (port 3001) — campus intranet / VPN only
admin.example.org/* {
    reverse_proxy 127.0.0.1:3001
}

; FastAPI backend (port 8000) — API & WebSocket routes
api.example.org/* {
    reverse_proxy 127.0.0.1:8000
}

; Health probes
health.example.org {
    header X-Request-ID "{uuid}"
    reverse_proxy 127.0.0.1:8000
}
```

Key Caddy configurations:
* `X-Forwarded-For` forwarded only from trusted proxy IP
* `FORWARDED_ALLOW_IPS` set to reverse proxy IP only (never `*`) — this prevents client IP spoofing and rate-limit bypass
* GZip compression enabled on backend
* TLS terminated at proxy; HTTP redirects to HTTPS

---

### 1.4 Windows Services Reference

| Script | Purpose |
| :--- | :--- |
| `windows/install_postgres.ps1` | PostgreSQL 16 installation with PostGIS 3.4 |
| `windows/init_database.ps1` | Database initialization: creates `rainfall_runoff`, tables, spatial indexes, approved accounts |
| `windows/install_services.ps1` | NSSM service installation: registers all 5 Windows Services |
| `windows/service_control.ps1` | Start/stop/status controller for all NSSM services |
| `windows/backup_database.ps1` | Automated daily `pg_dump` + 30-day retention backup |
| `windows/run_pipeline_manual.ps1` | Manual pipeline execution CLI — interactive or single-step mode |
| `windows/system_diag.ps1` | System health diagnostics: ports, runtimes, dependencies, file permissions |
| `windows/storage_setup.sql` | PostgreSQL tablespace configuration (E:\pgdata dedicated tablespace) |

---

### 1.5 Service Control Operations

```powershell
; Start all services
 .\windows\service_control.ps1 -Action start

; Stop all services
 .\windows\service_control.ps1 -Action stop

; Check status of all services
 .\windows\service_control.ps1 -Action status

; Restart a specific service (e.g., Backend)
 .\windows\service_control.ps1 -Action restart -Service HydroCast-Backend
```

---

### 1.6 Database Backup

```powershell
 .\windows\backup_database.ps1
```

Creates a timestamped `pg_dump` in the configured backup directory (`E:\pgbackups\hydrocast\`). Includes SHA-256 hash verification in the backup audit log. Recommended: run every morning at 03:00 UTC via Windows Task Scheduler.

---

### 1.7 System Diagnostics

```powershell
 .\windows\system_diag.ps1
```

Checks: PostgreSQL connectivity, API health endpoints, frontend build status, disk space (C: and E:), service status, and reports `System status: READY FOR PRODUCTION` if all checks pass.

---

### 1.8 Firewall Configuration (Windows Defender Firewall)

Ensure these ports are open:

| Port | Service | Access |
| :--- | :--- | :--- |
| **8000** | FastAPI (Public API) | LAN / Internet (behind reverse proxy only) |
| **8001** | Admin API | LAN only (restricted to campus intranet/VPN) |
| **3000** | Public Dashboard (Next.js) | LAN / Internet |
| **3001** | Operator Console (Next.js) | LAN only (restricted to campus intranet/VPN) |
| **5432** | PostgreSQL | **Localhost only** — must NOT be exposed to public internet |

*Rule direction: Inbound TCP. Profiles: Domain, Private. Remote address: for 5432, restrict to 127.0.0.1.*

---

### 1.9 HTTPS (Production)

For production deployment behind a reverse proxy (Caddy, NGINX, IIS ARR):

* Terminate TLS at the reverse proxy
* Forward to localhost ports (127.0.0.1:8000, 127.0.0.1:3000, 127.0.0.1:3001)
* Set `FORWARDED_ALLOW_IPS` to the proxy IP only (never `*`)
* Enable HSTS headers (already configured in Next.js production build)
* Ensure `CORS_ORIGINS` in `.env` matches the production dashboard domain

---

## 2. Automated Cron Scheduling (ECMWF Operational Cycles)

The European Centre for Medium-Range Weather Forecasts releases operational IFS runs four times daily. HydroCast triggers automated forecast cycles on Windows Server via the `HydroCast-Scheduler` service, 45 minutes after official model availability to allow for global numerical assimilation:

| ECMWF Cycle | Global Model Time | Local Time (IST) | Scheduled Service Trigger |
|:---|:---|:---|:---|
| 00z Forecast | 00:00 UTC | 05:30 AM IST | 06:45 AM IST (01:15 UTC) |
| 06z Forecast | 06:00 UTC | 11:30 AM IST | 12:45 PM IST (07:15 UTC) |
| 12z Forecast | 12:00 UTC | 05:30 PM IST | 06:45 PM IST (13:15 UTC) |
| 18z Forecast | 18:00 UTC | 11:30 PM IST | 12:45 AM IST (19:15 UTC) |

The `HydroCast-Scheduler` Windows Service triggers at the times above and executes `python -m backend.orchestrator` (or the downstream module directly, depending on configuration).

---

## 3. Multi-Channel Emergency Alerting Setup (DDMA & SDRF)

HydroCast integrates an automated Telegram alert bot and webhook dispatcher (`backend/alerts/telegram_bot.py`):

### 3.1 Telegram Bot Configuration

1. Create a bot via `@BotFather` on Telegram to obtain `TELEGRAM_BOT_TOKEN`.
2. Add the bot to your District Disaster Management Authority (DDMA) channel, District Collectorate channel, and Emergency Operations Center (EOC) groups.
3. Configure target chat IDs in `.env`:

```powershell
 TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
 TELEGRAM_CHAT_ID=-1001234567890
 DDMA_TELEGRAM_CHATS=-1001234567890,-1009876543210
```

### 3.2 Agency Webhook Endpoints

To automatically push flood alerts to state disaster management agency dispatch APIs:

```powershell
 DISASTER_MANAGEMENT_WEBHOOKS=https://alert-dispatch.district.gov.in/api/v1/cwc-hook,https://sdrf.maharashtra.gov.in/api/v1/flood
```

Whenever river stage breaches the CWC **Warning** ($542.70\text{ m}$) or **Danger** ($543.30\text{ m}$) mark, HydroCast broadcasts formatted HTML bulletins to all Telegram channels and POSTs structured JSON alerts to webhooks within $< 500\text{ ms}$.

---

## 4. Cold Storage & Telemetry Archival Automation

Implemented in `backend/scripts/archive_runs.py`:

* **Objective:** Prevent high-frequency time-series tables (`hydrograph_results`, `bridge_stage_forecast`, `rainfall_data`, `station_rainfall_telemetry`, `subbasin_rainfall_ts`) from bloating PostgreSQL storage and degrading query speed.
* **Mechanism:** Records older than `ARCHIVE_RETENTION_DAYS` (default 90 days) are written to Snappy-compressed Apache Parquet partitions (`data/archives/{table}/year=YYYY/month=MM/`), followed by atomic database pruning.
* **Manual Execution:**

```powershell
; Dry run (inspect row counts without deleting)
python -m backend.scripts.archive_runs --dry-run

; Execute archival with 90-day retention
python -m backend.scripts.archive_runs --retention-days 90
```

* **API Invocation:** Authenticated administrators can trigger archival via `POST /api/v1/admin/archive`.

---

## 5. API Security, JWT Authentication & Rate Limiting

The public surface is deliberately small and every route is authenticated except `/health` and `/api/v1/status`. Admin routes carry an HS256 JWT with a 60-minute expiry; machine callers use a static API key in `X-API-Key`. Requests are rate limited per client at 60 per minute (configurable via `RATE_LIMIT_PUBLIC`), and failed authentication is logged with the source address before the 401 is returned.

### 5.1 Environment Security Variables (`.env`)

```powershell
# Enterprise Security & Authentication
API_KEY=Hydrocast_PCH
INTERNAL_KEY=your_internal_broadcast_key_min_32_chars
JWT_SECRET=your_jwt_secret_key_minimum_32_characters_random
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_strong_admin_password

# Rate Limiting
RATE_LIMIT_PUBLIC=100/minute
```

### 5.2 Obtaining an Admin JWT Bearer Token

```powershell
 curl -X POST http://localhost:8000/api/v1/admin/auth/token \
   -H "Content-Type: application/json" \
   -d '{"username": "admin", "password": "your_strong_admin_password"}'
```

Response:

```json
{
  "access_token": "<JWT_ACCESS_TOKEN>",
  "token_type": "bearer",
  "expires_in_seconds": 86400
}
```

---

## 6. Process Management without Docker (Native Windows Services)

For the primary Windows Server deployment, Docker is **not required**. All services run as native Windows Services via NSSM.

### 6.1 Service Overview (NSSM-Installed)

All 5 services are installed during Step 5 of the runbook:

| Service Name | Port | Description | Auto-Start |
| :--- | :---: | :--- | :---: |
| `HydroCast-Backend` | 8000 | FastAPI + WebSocket hub | ✅ |
| `HydroCast-Scheduler` | N/A | 6-hourly pipeline daemon | ✅ |
| `HydroCast-Watchdog` | N/A | 15s heartbeat supervisor | ✅ |
| `HydroCast-PublicWeb` | 3000 | Next.js public portal | ✅ |
| `HydroCast-OperatorConsole` | 3001 | Next.js operator console | ✅ |

### 6.2 Service Control

All services are controlled via the single PowerShell script:

```powershell
; Start all services
 .\windows\service_control.ps1 -Action start

; Stop all services
 .\windows\service_control.ps1 -Action stop

; Check status of all services
 .\windows\service_control.ps1 -Action status

; Restart a specific service
 .\windows\service_control.ps1 -Action restart -Service HydroCast-Backend
```

Each service is configured with `SERVICE_AUTO_START`, meaning they launch automatically upon Windows Server boot within 30 seconds.

---

## 7. Continuous 1-Hour Telemetry Validation

The `HydroCast-Watchdog` service checks the scheduler heartbeat every 15 seconds. If the heartbeat is older than 45 seconds, the watchdog records a crash dump and restarts the scheduler process. This ensures the 6-hourly forecast cycles remain uninterrupted.

Telemetry validation runs hourly via the watchdog's integrated validator, pulling 800 raw ultrasonic pings from ThingSpeak Channel `3424513`, resampling into hourly averages, and converting to stage in meters MSL ($549.35\text{m} - \text{ft} \times 0.3048$).

---

## 8. Comprehensive Test Architecture & Continuous Verification Suite

HydroCast enforces rigorous software and hydrological quality assurance through an automated suite of tests. On Windows Server, run:

```powershell
 pytest
; Output: 256 passed, 3 skipped in under 10 seconds
```

### Test Inventory & Module Breakdown

| Test Module | Test Count | Focus Area |
| :--- | :---: | :--- |
| `tests/test_golden_emulator.py` | 2 | Bit-level determinism & regression lock |
| `tests/test_runner_emulator.py` | 16 | Hydrologic Twin Solver |
| `tests/test_ml_calibration.py` | 8 | Adaptive Calibrator |
| `tests/test_low_flow_stage_bias.py` | 44 | Rating Physics Autopsy |
| `tests/test_cross_section_survey.py` | 17 | Survey Geometry |
| `tests/test_rating_physics.py` | 6 | Pure Geometry Core |
| `tests/test_realtime_validator.py` | 13 | Sensor Ingestion |
| `tests/test_telemetry_metrics.py` | 6 | Statistical Core |
| `tests/test_hydrosim_integration.py` | 17 | 2D Handoff Boundary API |
| `tests/test_rate_limiting_and_auth.py` | 7 | Authentication & Limits |
| `tests/test_security_hardening.py` | 13 | Security Hardening |
| `tests/test_api_endpoints.py` | 28 | FastAPI Surface |
| `tests/test_write_paths.py` | 21 | Persistence Ledger |
| `tests/test_db_connection.py` | 6 | Database Connection |
| `tests/test_soil_moisture.py` | 5 | NWP Soil Moisture |
| `tests/test_station_selector.py` | 4 | Rainfall Mapping |
| `tests/test_qc_pipeline.py` | 4 | Quality Control |
| `tests/test_retry_utils.py` | 6 | Network Resilience |
| `tests/test_alerts_dispatcher.py` | 15 | Emergency Alerting |
| `tests/test_orchestrator.py` | 8 | 12-Step Pipeline |
| `tests/test_archival.py` | 3 | Cold Storage |
| `tests/test_hydrology.py` | 5 | Hydraulic Rating |
| `tests/test_validation_metrics.py` | 2 | Accuracy Matrix |
| `tests/test_postgres_integration.py` | 3 | PostgreSQL/PostGIS |

### 8.1 Fast Local Development Suite (< 10 seconds)

```powershell
 pytest
```

Executes all 256 unit and integration tests with in-memory SQLite and mock telemetry. Expected: `256 passed, 3 skipped` in under 10 seconds.

### 8.2 Golden Regression Lock Verification

```powershell
 pytest tests/test_golden_emulator.py -v
```

Verifies bit-level determinism and ensures peak discharge ($3,345.6\text{ m}^3/s$) and volume ($754.115\text{ MCM}$) have not drifted.

### 8.3 Rating Curve & Low-Flow Stage Bias Verification

```powershell
 pytest tests/test_low_flow_stage_bias.py tests/test_cross_section_survey.py -v
```

Validates bed invert levels and confirms zero low-flow stage bias across the entire operating range.

### 8.4 Real-PostgreSQL PostGIS Integration Suite

```powershell
 $env:HYDROCAST_TEST_DATABASE_URL = "postgresql://hms_app:password@localhost:5432/rainfall_runoff"
 pytest tests/test_postgres_integration.py -v
```

Requires a running PostgreSQL/PostGIS container or local installation. Applies `database/schema.sql` and verifies schema, tables, views, and write paths.

### 8.5 Documentation Integrity & Strict Build Verification

```powershell
 python -m mkdocs build --strict
 pytest tests/test_milestone1_integrity.py -v
```

Validates zero warnings or errors in documentation builds and verifies all internal links and canonical anchors across the generated HTML site.

---

## 9. Docker Deployment (Alternative, Linux/Cloud Only)

For cloud or Linux environments, the system is fully containerized via Docker Compose. **This is NOT the primary Windows Server deployment path.**

```bash
 docker build -t hydrocast-backend:2.0.0 .
 docker compose up -d
```

See the Dockerfile for multi-stage build targets (runner, docs, dev). The Docker path is provided for contributors who wish to test on Linux/macOS or deploy to cloud VMs; production Windows Server deployment uses native NSSM services.

---

## 10. Firewall Configuration (Reiteration)

Ensure these ports are open on Windows Server:

| Port | Service | Access |
| :--- | :--- | :--- |
| 8000 | Public API | LAN / Internet (behind reverse proxy) |
| 8001 | Admin API | LAN only (restricted) |
| 3000 | Public Dashboard | LAN / Internet |
| 3001 | Admin Console | LAN only (restricted) |
| 5432 | PostgreSQL | **Localhost only** |

---

## 11. HTTPS (Production, Reiteration)

For production deployment behind a reverse proxy (Nginx, Caddy, IIS ARR):

* Terminate TLS at the proxy
* Forward to localhost ports
* Set `FORWARDED_ALLOW_IPS` to the proxy IP only
* Enable HSTS headers (already configured in Next.js)