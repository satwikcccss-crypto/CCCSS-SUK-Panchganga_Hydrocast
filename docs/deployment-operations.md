# Production Deployment, Operations & Automation Manual

```
========================================================================================
             HYDROCAST PRODUCTION INFRASTRUCTURE & ORCHESTRATION
========================================================================================

                [ Automated 6-Hourly Cron / GHA Scheduler (00z, 06z, 12z, 18z) ]
                                           │
                                           ▼
                 Python Pipeline Orchestrator (src/ecmwf/open_meteo.py)
                 - Open-Meteo ECMWF QPF with Exponential Retries & Jitter
                 - Dynamic Conservative Maximum-Rainfall Station Selection
                 - Live Discrepancy Detection & Real-Time ML Recalibration
                 - WRD-Anchored PCHIP Hydraulic Conversion & Peak Horizon (±2.0h CI)
                 - Multi-Channel DDMA Telegram Broadcast & Agency Webhooks
                                           │
                ┌──────────────────────────┴──────────────────────────┐
                ▼                                                     ▼
    [ Docker Compose / systemd ]                            [ Next.js 14 Web App ]
    hydrocast-backend (FastAPI :8000)                       hydrocast-frontend (:3000)
    hydrocast-db (PostGIS :5432)                            Standalone SSR Container
    Rate Limiting & JWT Auth                                Vercel Edge Serverless
```

---

## 1. Unified Container Deployment (Docker & Docker Compose)

HydroCast is fully containerized for reproducible 1-command deployment across cloud virtual machines (AWS EC2, GCP Compute Engine, Azure VM, DigitalOcean) and on-premise workstations:

### 1.1 Image Build Targets (`Dockerfile`)

The backend image is a single multi-stage Dockerfile. Compilers, GDAL headers
and the full JDK exist only in the `builder` stage; the runtime stage ships the
JRE, the shared libraries and a dedicated `hydrocast` user (uid/gid 1000), with
`tini` as PID 1 so `docker stop` reaches uvicorn and in-flight requests drain.

| Target | Purpose | Base |
|:---|:---|:---|
| `runner` *(default)* | Production FastAPI service on `:8000` | `python:3.12-slim-bookworm` + JRE 17, GDAL, eccodes |
| `docs` | MkDocs Material site, built with `--strict` to `/app/site` | `python:3.12-slim-bookworm` + `requirements-docs.txt` |
| `dev` | `runner` + black, isort, mypy, pytest, JupyterLab | production runtime |

```bash
# Production image (embeds OCI labels: version, git SHA, build date)
docker build -t hydrocast-backend:2.0.0 \
  --build-arg APP_VERSION=2.0.0 \
  --build-arg VCS_REF="$(git rev-parse --short HEAD)" \
  --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" .

# Multi-architecture release (buildx is required for cross-platform builds)
docker buildx build --platform linux/amd64,linux/arm64 --push \
  -t ghcr.io/satwikcccss-crypto/hydrocast-backend:2.0.0 .

# Documentation site — `--strict` fails the build on a broken anchor,
# a missing nav entry or an unresolved mkdocstrings identifier
docker build --target docs -t hydrocast-docs .

# Developer image: interactive shell with the full toolchain
docker build --target dev -t hydrocast-dev .
```

The runtime honours four optional environment variables, all defaulted inside
the image so the container starts with no configuration:

| Variable | Default | Purpose |
|:---|:---|:---|
| `PORT` | `8000` | HTTP listen port (also used by `HEALTHCHECK`) |
| `WEB_CONCURRENCY` | `2` | uvicorn worker processes |
| `GRACEFUL_TIMEOUT` | `30` | Seconds to finish in-flight requests on `SIGTERM` |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Trusted proxies for `X-Forwarded-For` |

!!! warning "`FORWARDED_ALLOW_IPS` and rate limiting"
    Rate limiting keys on the client IP, so setting `FORWARDED_ALLOW_IPS=*`
    would let any caller spoof `X-Forwarded-For` and bypass its quota. Set it
    to the load balancer address only when a trusted proxy is actually in front.

### 1.2 Architecture & Services (`docker-compose.yml`)

```yaml
# Obsolete top-level `version:` key intentionally omitted — Compose v2 selects
# the current schema itself and warns when the key is present.
x-hydrocast-env: &hydrocast-env
  DATABASE_URL: postgresql://hms_app:${POSTGRES_PASSWORD}@hydrocast-db:5432/rainfall_runoff
  API_KEY: ${API_KEY}
  INTERNAL_KEY: ${INTERNAL_KEY}
  API_BASE_URL: http://hydrocast-backend:8000
  RATE_LIMIT_PUBLIC: 100/minute
  JWT_SECRET: ${JWT_SECRET}
  ADMIN_USERNAME: ${ADMIN_USERNAME:-admin}
  ADMIN_PASSWORD: ${ADMIN_PASSWORD}
  ARCHIVE_RETENTION_DAYS: 90
  ARCHIVE_DIR: /app/data/archives
  RAW_DIR: /app/data/raw

services:
  hydrocast-db:
    image: postgis/postgis:15-3.4
    container_name: hydrocast-db
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: rainfall_runoff
      POSTGRES_USER: hms_app
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/supabase_schema.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hms_app -d rainfall_runoff"]
      interval: 10s
      timeout: 5s
      retries: 5

  hydrocast-backend:
    build:
      context: .
      dockerfile: Dockerfile
      target: runner
    container_name: hydrocast-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    depends_on:
      hydrocast-db:
        condition: service_healthy
    environment:
      <<: *hydrocast-env
      WEB_CONCURRENCY: ${WEB_CONCURRENCY:-2}
      FORWARDED_ALLOW_IPS: ${FORWARDED_ALLOW_IPS:-127.0.0.1}
    volumes:
      - hydrocast_runs:/app/data/runs
      - hydrocast_telemetry:/app/data/telemetry
      - hydrocast_forecast:/app/data/openmeteo_dss
      - hydrocast_raw:/app/data/raw
      - hydrocast_archives:/app/data/archives
      - hydrocast_logs:/app/data/logs
    stop_grace_period: 45s
    healthcheck:
      test: ["CMD", "curl", "-fsS", "--max-time", "4", "http://localhost:8000/api/v1/health"]
      interval: 15s
      timeout: 5s
      retries: 3
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]

  hydrocast-frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        NEXT_PUBLIC_API_URL: http://localhost:8000
        NEXT_PUBLIC_WS_URL: ws://localhost:8000/ws/live
    container_name: hydrocast-frontend
    restart: unless-stopped
    ports:
      - "3000:3000"
    depends_on:
      hydrocast-backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3000/"]
      interval: 20s
      timeout: 5s
      retries: 3

  hydrocast-docs:      # opt-in: docker compose --profile docs up docs
    build:
      context: .
      target: docs
    profiles: ["docs"]
    ports: ["8001:8001"]
    volumes:
      - ./docs:/app/docs:ro
      - ./src:/app/src:ro
      - ./mkdocs.yml:/app/mkdocs.yml:ro

  hydrocast-dev:       # opt-in: docker compose --profile dev up dev
    build:
      context: .
      target: dev
    profiles: ["dev"]
    ports: ["8000:8000", "8888:8888"]
    environment:
      <<: *hydrocast-env
    command: ["bash"]
```

### 1.3 Persistent State: Why Volumes Are Mounted Per Directory

`/app/data` holds two different kinds of content, and only one of them is
mutable:

| Path | Kind | Mounted? |
|:---|:---|:---|
| `data/hms/HMS_Automation_RJKT/` | versioned HEC-HMS basin project | baked into the image |
| `data/Shapefiles_Panchganga basin/`, `data/wrd_cross_sections/`, `data/stations/` | GIS, rating and gauge reference data | baked into the image |
| `data/runs/` | cycle ledger served by `/api/v1/runs` | named volume, seeded from the image |
| `data/telemetry/`, `data/openmeteo_dss/` | ThingSpeak cache, forecast DSS output | named volume |
| `data/raw/`, `data/archives/`, `data/logs/` | GRIB downloads, parquet cold storage, logs | named volume |

!!! danger "A single `hydrocast_data:/app/data` mount hides the reference data"
    A volume mounted over `/app/data` **shadows** everything baked into the
    image at build time. The HEC-HMS basin files, the GIS layers and the entire
    historical run ledger would vanish and the API would answer
    `/api/v1/runs` with an empty list. Compose therefore mounts the six mutable
    subdirectories individually; Docker seeds each empty named volume from the
    image, so the first `docker compose up` still starts with a populated
    ledger and keeps accumulating cycles from then on.

### 1.4 Startup & Management Commands
```bash
# Build images and start all services in detached mode
docker compose up -d --build

# Inspect container health and port bindings
docker compose ps

# Stream unified application logs
docker compose logs -f

# Stop and gracefully shut down services
docker compose down

# Local documentation preview with live reload (http://localhost:8001)
docker compose --profile docs up docs

# Interactive backend with black / mypy / pytest / JupyterLab
docker compose --profile dev up dev
docker compose --profile dev run --rm dev pytest -q
```

---

## 2. Automated Cron Scheduling (ECMWF Operational Cycles)

The European Centre for Medium-Range Weather Forecasts releases operational IFS runs four times daily. HydroCast triggers automated forecast cycles 45 minutes after official model availability to allow for global numerical assimilation:

```
+---------------+---------------------+---------------------+-------------------------+
| ECMWF Cycle   | Global Model Time   | Indian Std Time(IST)| Automated Pipeline Run  |
+---------------+---------------------+---------------------+-------------------------+
| 00z Forecast  | 00:00 UTC           | 05:30 AM IST        | 06:45 AM IST (01:15 UTC)|
| 06z Forecast  | 06:00 UTC           | 11:30 AM IST        | 12:45 PM IST (07:15 UTC)|
| 12z Forecast  | 12:00 UTC           | 05:30 PM IST        | 06:45 PM IST (13:15 UTC)|
| 18z Forecast  | 18:00 UTC           | 11:30 PM IST        | 12:45 AM IST (19:15 UTC)|
+---------------+---------------------+---------------------+-------------------------+
```

### Linux Crontab Configuration:
```cron
# Edit with: crontab -e
# 6-Hourly Forecast Pipeline Execution
15 1,7,13,19 * * * cd /opt/hydrocast && /opt/hydrocast/venv/bin/python -m src.ecmwf.open_meteo >> data/logs/cron_forecast.log 2>&1

# Weekly Cold Storage Parquet Archival (Sunday 02:00 UTC)
0 2 * * 0 cd /opt/hydrocast && /opt/hydrocast/venv/bin/python -m src.db.archive_runs --retention-days 90 >> data/logs/cron_archive.log 2>&1
```

---

## 3. Multi-Channel Emergency Alerting Setup (DDMA & SDRF)

HydroCast integrates an automated Telegram alert bot and webhook dispatcher ([`src/alerts/telegram_bot.py`](file:///e:/hydrocast_complete/src/alerts/telegram_bot.py)):

### 3.1 Telegram Bot Configuration
1. Create a bot via `@BotFather` on Telegram to obtain `TELEGRAM_BOT_TOKEN`.
2. Add the bot to your District Disaster Management Authority (DDMA) channel, District Collectorate channel, and Emergency Operations Center (EOC) groups.
3. Configure target chat IDs in `.env`:
   ```ini
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
   TELEGRAM_CHAT_ID=-1001234567890
   DDMA_TELEGRAM_CHATS=-1001234567890,-1009876543210
   ```

### 3.2 Agency Webhook Endpoints
To automatically push flood alerts to state disaster management agency dispatch APIs:
```ini
DISASTER_MANAGEMENT_WEBHOOKS=https://alert-dispatch.district.gov.in/api/v1/cwc-hook,https://sdrf.maharashtra.gov.in/api/v1/flood
```
Whenever river stage breaches the CWC **Warning** ($542.70\text{ m}$) or **Danger** ($543.30\text{ m}$) mark, HydroCast broadcasts formatted HTML bulletins to all Telegram channels and POSTs structured JSON alerts to webhooks within $< 500\text{ ms}$.

---

## 4. Cold Storage & Telemetry Archival Automation

Implemented in [`src/db/archive_runs.py`](file:///e:/hydrocast_complete/src/db/archive_runs.py):
- **Objective:** Prevent high-frequency time-series tables (`hydrograph_results`, `bridge_stage_forecast`, `rainfall_data`, `station_rainfall_telemetry`, `subbasin_rainfall_ts`) from bloating PostgreSQL storage and degrading query speed.
- **Mechanism:** Records older than `ARCHIVE_RETENTION_DAYS` (default 90 days) are written to Snappy-compressed Apache Parquet partitions (`data/archives/{table}/year=YYYY/month=MM/`), followed by atomic database pruning.
- **Manual Execution:**
  ```bash
  # Dry run (inspect row counts without deleting)
  python -m src.db.archive_runs --dry-run

  # Execute archival with 90-day retention
  python -m src.db.archive_runs --retention-days 90
  ```
- **API Invocation:** Authenticated administrators can trigger archival via `POST /api/v1/admin/archive`.

---

## 5. API Security, JWT Authentication & Rate Limiting

### 5.1 Environment Security Variables (`.env`)
```ini
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
```bash
curl -X POST http://localhost:8000/api/v1/admin/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_strong_admin_password"}'
```
Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in_seconds": 86400
}
```

---

## 6. Process Management without Docker (Systemd & PM2)

For hosts where Docker is not available:

### 6.1 Backend Systemd Unit (`/etc/systemd/system/hydrocast-api.service`)
```ini
[Unit]
Description=HydroCast FastAPI Backend & WebSocket Service
After=network.target postgresql.service

[Service]
Type=simple
User=hydrocast
WorkingDirectory=/opt/hydrocast
ExecStart=/opt/hydrocast/venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5
EnvironmentFile=/opt/hydrocast/.env

[Install]
WantedBy=multi-user.target
```

### 6.2 Frontend PM2 Process
```bash
cd /opt/hydrocast/frontend
npm run build
pm2 start npm --name "hydrocast-frontend" -- start -- -p 3000
pm2 save
pm2 startup
```

---

## 7. Continuous 1-Hour Telemetry Validation (GitHub Actions)

Autonomous physical verification runs via [`.github/workflows/telemetry_validation.yml`](file:///e:/hydrocast_complete/.github/workflows/telemetry_validation.yml):
- **Interval:** Every hour at minute 0 (`cron: "0 * * * *"`).
- Pulls 800 raw ultrasonic pings from ThingSpeak Channel `3424513`.
- Resamples into hourly averages and converts to stage in meters MSL ($549.35\text{m} - \text{ft} \times 0.3048$).
- Computes genuine RMSE, MAE, NSE, PBIAS, Spearman $\rho$, and Pearson $R^2$.
- Updates `frontend/public/data/latest_pipeline_state.json` and mirrored run archives in `frontend/public/data/runs/`.
- Commits and pushes back to GitHub, triggering immediate Vercel production synchronization.
