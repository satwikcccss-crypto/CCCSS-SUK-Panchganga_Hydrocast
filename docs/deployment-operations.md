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

## 1. Unified Container Deployment (Docker & Docker Compose)

HydroCast is fully containerized for reproducible 1-command deployment across cloud virtual machines (AWS EC2, GCP Compute Engine, Azure VM, DigitalOcean) and on-premise workstations:

### 1.1 Image Build Targets (`Dockerfile`)

The backend image is a single multi-stage Dockerfile. Compilers, GDAL headers
and the full JDK exist only in the `builder` stage; the runtime stage ships the
JRE, the shared libraries and a dedicated `hydrocast` user (uid/gid 1000), with
`tini` as PID 1 so `docker stop` reaches uvicorn and in-flight requests drain.

| Target | Purpose | Base |
| :--- | :--- | :--- |
| `runner` *(default)* | Production FastAPI service on `:8000` | `python:3.12-slim-bookworm` + JRE 17, GDAL, eccodes |
| `docs` | MkDocs Material site, built with `--strict` to `/app/site` | `python:3.12-slim-bookworm` + `requirements-docs.txt` |
| `dev` | `runner` + black, isort, mypy, pytest, JupyterLab | production runtime |

> **Optional extras.** The runner image installs `requirements.lock`, which contains
> only the tested core runtime. `cfgrib`, `eccodes`, and `pydsstools` are deliberately
> excluded: `pydsstools` currently requires `numpy<2`, which conflicts with the pinned
> `numpy` 2.x stack. Use a separate image or virtual environment for HEC-DSS writing or
> GRIB decoding. The FastAPI service and Python twin do not require them.

```
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
| :--- | :--- | :--- |
| `PORT` | `8000` | HTTP listen port (also used by `HEALTHCHECK`) |
| `WEB_CONCURRENCY` | `2` | uvicorn worker processes |
| `GRACEFUL_TIMEOUT` | `30` | Seconds to finish in-flight requests on `SIGTERM` |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Trusted proxies for `X-Forwarded-For` |

!!! warning "`FORWARDED_ALLOW_IPS` and rate limiting"
    Rate limiting keys on the client IP, so setting `FORWARDED_ALLOW_IPS=*`
    would let any caller spoof `X-Forwarded-For` and bypass its quota. Set it
    to the load balancer address only when a trusted proxy is actually in front.

### 1.2 Architecture & Services (`docker-compose.yml`)

```
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
| :--- | :--- | :--- |
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

```
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

| ECMWF Cycle | Global Model Time | Indian Std Time(IST) | Automated Pipeline Run |
|:---|:---|:---|:---|
| 00z Forecast | 00:00 UTC | 05:30 AM IST | 06:45 AM IST (01:15 UTC) |
| 06z Forecast | 06:00 UTC | 11:30 AM IST | 12:45 PM IST (07:15 UTC) |
| 12z Forecast | 12:00 UTC | 05:30 PM IST | 06:45 PM IST (13:15 UTC) |
| 18z Forecast | 18:00 UTC | 11:30 PM IST | 12:45 AM IST (19:15 UTC) |


### Linux Crontab Configuration

```
# Edit with: crontab -e
# 6-Hourly Forecast Pipeline Execution
15 1,7,13,19 * * * cd /opt/hydrocast && /opt/hydrocast/venv/bin/python -m src.ecmwf.open_meteo >> data/logs/cron_forecast.log 2>&1

# Weekly Cold Storage Parquet Archival (Sunday 02:00 UTC)
0 2 * * 0 cd /opt/hydrocast && /opt/hydrocast/venv/bin/python -m src.db.archive_runs --retention-days 90 >> data/logs/cron_archive.log 2>&1
```

---

## 3. Multi-Channel Emergency Alerting Setup (DDMA & SDRF)

HydroCast integrates an automated Telegram alert bot and webhook dispatcher (`src/alerts/telegram_bot.py`):

### 3.1 Telegram Bot Configuration

1. Create a bot via `@BotFather` on Telegram to obtain `TELEGRAM_BOT_TOKEN`.
2. Add the bot to your District Disaster Management Authority (DDMA) channel, District Collectorate channel, and Emergency Operations Center (EOC) groups.
3. Configure target chat IDs in `.env`:

```
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
   TELEGRAM_CHAT_ID=-1001234567890
   DDMA_TELEGRAM_CHATS=-1001234567890,-1009876543210
```

### 3.2 Agency Webhook Endpoints

To automatically push flood alerts to state disaster management agency dispatch APIs:

```
DISASTER_MANAGEMENT_WEBHOOKS=https://alert-dispatch.district.gov.in/api/v1/cwc-hook,https://sdrf.maharashtra.gov.in/api/v1/flood
```

Whenever river stage breaches the CWC **Warning** ($542.70\text{ m}$) or **Danger** ($543.30\text{ m}$) mark, HydroCast broadcasts formatted HTML bulletins to all Telegram channels and POSTs structured JSON alerts to webhooks within $< 500\text{ ms}$.

---

## 4. Cold Storage & Telemetry Archival Automation

Implemented in `src/db/archive_runs.py`:

- **Objective:** Prevent high-frequency time-series tables (`hydrograph_results`, `bridge_stage_forecast`, `rainfall_data`, `station_rainfall_telemetry`, `subbasin_rainfall_ts`) from bloating PostgreSQL storage and degrading query speed.
- **Mechanism:** Records older than `ARCHIVE_RETENTION_DAYS` (default 90 days) are written to Snappy-compressed Apache Parquet partitions (`data/archives/{table}/year=YYYY/month=MM/`), followed by atomic database pruning.
- **Manual Execution:**

```
  # Dry run (inspect row counts without deleting)
  python -m src.db.archive_runs --dry-run

  # Execute archival with 90-day retention
  python -m src.db.archive_runs --retention-days 90
```

- **API Invocation:** Authenticated administrators can trigger archival via `POST /api/v1/admin/archive`.

---

## 5. API Security, JWT Authentication & Rate Limiting

The public surface is deliberately small and every route is authenticated except
`/health` and `/api/v1/status`. Admin routes carry an HS256 JWT with a 60-minute
expiry; machine callers use a static API key in `X-API-Key`. Requests are rate
limited per client at 60 per minute, and failed authentication is logged with the
source address before the 401 is returned.

### 5.1 Environment Security Variables (`.env`)

```
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

```json
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

Autonomous physical verification runs via `.github/workflows/telemetry_validation.yml`:

- **Interval:** Every hour at minute 0 (`cron: "0 * * * *"`).
- Pulls 800 raw ultrasonic pings from ThingSpeak Channel `3424513`.
- Resamples into hourly averages and converts to stage in meters MSL ($549.35\text{m} - \text{ft} \times 0.3048$).
- Computes genuine RMSE, MAE, NSE, PBIAS, Spearman $\rho$, and Pearson $R^2$.
- Updates `frontend/public/data/latest_pipeline_state.json` and mirrored run archives in `frontend/public/data/runs/`.
- Commits and pushes back to GitHub, triggering immediate Vercel production synchronization.

---

## 8. Comprehensive Test Architecture & Continuous Verification Suite

HydroCast enforces rigorous software and hydrological quality assurance through an automated suite of **271 total automated tests**:

```mermaid
flowchart TD
    Suite["HydroCast Automated Verification Suite<br/>(284+ Verified Invariants)"]

    Suite --> Unit["Backend Unit & Integration Tests<br/>(256 tests, &lt;10s execution)"]
    Suite --> PostGIS["PostgreSQL & PostGIS Tests<br/>(Database container & spatial types)"]
    Suite --> Integrity["Documentation & Navigation Integrity<br/>(Strict MkDocs & Link Crawler)"]

    style Suite fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0f172a
    style Unit fill:#f8fafc,stroke:#64748b,stroke-width:1px,color:#0f172a
    style PostGIS fill:#f8fafc,stroke:#64748b,stroke-width:1px,color:#0f172a
    style Integrity fill:#ecfdf5,stroke:#10b981,stroke-width:1px,color:#0f172a
```

### 8.1 Test Inventory & Module Breakdown

| Test Module | Test Count | Focus Area & Verified Scientific Invariants |
| :--- | :---: | :--- |
| `tests/test_golden_emulator.py` | 2 | **Bit-level determinism & regression lock:** Freezes baseline peak ($Q=3,345.6\text{ m}^3/s$, $T=105\text{ h}$, $V=754.115\text{ MCM}$, AMC-III). |
| `tests/test_runner_emulator.py` | 16 | **Hydrologic Twin Solver:** Muskingum mass conservation, stability under long reach travel times, Control_1 restoration. |
| `tests/test_ml_calibration.py` | 8 | **Adaptive Calibrator:** Parameter bounds, early/late arrival wave scaling, atomic `.basin` syncing with timestamped backups. |
| `tests/test_low_flow_stage_bias.py` | 44 | **Rating Physics Autopsy:** Bed datum reconciliation ($528.670\text{ m}$ / $529.318\text{ m}$), removal of $40\text{ m}^3/s$ floor, eradication of ~2 m low-flow bias. |
| `tests/test_cross_section_survey.py` | 17 | **Survey Geometry:** Chainage calculations, surveyed coordinates, wetted area/perimeter monotonicity, Manning overprediction checks. |
| `tests/test_rating_physics.py` | 6 | **Pure Geometry Core:** Vectorized trapezoidal channel properties (`wetted_properties`, `station_from_points`). |
| `tests/test_realtime_validator.py` | 13 | **Sensor Ingestion:** ThingSpeak ping parsing, hourly mean resampling, lifecycle verification states (`ACCUMULATING_TELEMETRY`, `COMPLETED`). |
| `tests/test_telemetry_metrics.py` | 6 | **Statistical Core:** Variance floor ($\text{std} < 0.05\text{ m}$), sample size gating ($n \ge 6$), cycle ID datetime parsing. |
| `tests/test_hydrosim_integration.py` | 17 | **2D Handoff Boundary API:** Consumer key scoping, read-only guarantees, JSON/CSV boundary shapes, 404 behavior. |
| `tests/test_rate_limiting_and_auth.py` | 7 | **Authentication & Limits:** JWT lifecycle, bcrypt verification, SlowAPI request throttle enforcement (100 req/min). |
| `tests/test_security_hardening.py` | 13 | **Security Hardening:** Blank password lockout, tampered JWT rejection, run-id path traversal rejection. |
| `tests/test_api_endpoints.py` | 28 | **FastAPI Surface:** Endpoint response contracts, CORS headers, body size limit enforcement. |
| `tests/test_write_paths.py` | 21 | **Persistence Ledger:** HEC-DSS records, database table commits, runoff summary alert classifications. |
| `tests/test_db_connection.py` | 6 | **Database Connection:** Supabase connection pooler URL formatting, IPv4/IPv6 dual-stack resolution. |
| `tests/test_soil_moisture.py` | 5 | **NWP Soil Moisture:** Open-Meteo multi-layer soil moisture ingestion and antecedent indexing. |
| `tests/test_station_selector.py` | 4 | **Rainfall Mapping:** Subbasin-to-station assignment and governing gauge selection. |
| `tests/test_qc_pipeline.py` | 4 | **Quality Control:** Rainfall spatial sanity bounds and rate-of-change checks. |
| `tests/test_retry_utils.py` | 6 | **Network Resilience:** Exponential backoff, jitter distribution, retry exceptions. |
| `tests/test_alerts_dispatcher.py` | 15 | **Emergency Alerting:** Telegram broadcast formatting, webhook payloads, deduplication. |
| `tests/test_orchestrator.py` | 8 | **12-Step Pipeline:** End-to-end cycle execution order, error logging, and status tracking. |
| `tests/test_archival.py` | 3 | **Cold Storage:** Snappy-compressed Parquet exports and retention pruning. |
| `tests/test_hydrology.py` | 5 | **Hydraulic Rating:** WRD sheet anchor alignment and cross-site stage offset verification. |
| `tests/test_validation_metrics.py` | 2 | **Accuracy Matrix:** In-process evaluation of stored simulation payloads. |
| `tests/test_postgres_integration.py` | 3 | **PostgreSQL/PostGIS:** Fresh container schema application, write-path roundtrip, error propagation. |
| `tests/test_milestone1_integrity.py` | 12 | **Documentation Integrity:** Navigation links existence, canonical anchor contracts, deduplication enforcement, and HTML link crawling. |

### 8.2 Execution Runbooks

#### Fast Local Development Suite (< 10 seconds)
```powershell
pytest
```
Executes all 256 unit and integration tests with in-memory SQLite and mock telemetry. Expected: `256 passed, 3 skipped` in under 10 seconds.

#### Golden Regression Lock Verification
```powershell
pytest tests/test_golden_emulator.py -v
```
Verifies bit-level determinism and ensures peak discharge ($3,345.6\text{ m}^3/s$) and volume ($754.115\text{ MCM}$) have not drifted.

#### Rating Curve & Low-Flow Stage Bias Verification
```powershell
pytest tests/test_low_flow_stage_bias.py tests/test_cross_section_survey.py -v
```
Validates bed invert levels and confirms zero low-flow stage bias across the entire operating range.

#### Real-PostgreSQL PostGIS Integration Suite
```powershell
$env:HYDROCAST_TEST_DATABASE_URL = "postgresql://hms_app:password@localhost:5432/rainfall_runoff"
pytest tests/test_postgres_integration.py -v
```
Requires a running PostgreSQL/PostGIS container (`docker compose up -d hydrocast-db`). Applies `database/supabase_schema.sql` and verifies schema, tables, views, and write paths.

#### Documentation Integrity & Strict Build Verification
```powershell
python -m mkdocs build --strict
pytest tests/test_milestone1_integrity.py -v
```
Validates zero warnings or errors in documentation builds and verifies all internal links and canonical anchors across the generated HTML site.
