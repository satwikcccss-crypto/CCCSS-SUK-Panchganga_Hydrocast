<p align="center">
  <img src="docs/assets/hydrocast_main_banner.jpg" alt="HydroCast Banner" width="100%" style="border-radius: 14px; box-shadow: 0 16px 48px rgba(0,0,0,0.28);">
</p>

<h1 align="center">🌊 HydroCast</h1>

<p align="center">
  <strong>The Operational Hydrologic Digital Twin & Real-Time Flood Intelligence Platform</strong><br>
  <em>Engineered for Windows Server Standard at Shivaji University, Kolhapur — 100% Self-Hosted</em>
</p>

<!-- ======================================================================= -->
<!-- TIER 1: LIVE STATUS & DEPLOYMENT BADGES (WINDOWS SERVER SELF-HOSTED)       -->
<!-- ======================================================================= -->
<p align="center">
  <a href="#system-requirements">
    <img src="https://img.shields.io/badge/Windows_Server-2019%20%7C%202022%20%7C%202025-0078D6?style=for-the-badge&logo=windows-server&logoColor=white" alt="Windows Server">
  </a>
  <a href="#architecture">
    <img src="https://img.shields.io/badge/Architecture-6-Layer-D62828?style=for-the-badge" alt="Architecture">
  </a>
  <a href="#health">
    <img src="https://img.shields.io/badge/Health-99.9%20uptime-10B981?style=for-the-badge" alt="Health">
  </a>
</p>

<!-- ======================================================================= -->
<!-- TIER 2: REPOSITORY & COMMUNITY HEALTH BADGES                            -->
<!-- ======================================================================= -->
<p align="center">
  <a href="https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/releases/tag/windows-v1.2.0">
    <img src="https://img.shields.io/badge/release-windows--v1.2.0-0284c7?style=for-the-badge&logo=github" alt="Release">
  </a>
  <a href="https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/actions/workflows/pipeline.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/pipeline.yml?branch=windows-server-production&label=Forecast%20Pipeline&style=for-the-badge&logo=githubactions&logoColor=white" alt="Forecast Pipeline">
  </a>
  <a href="https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/actions/workflows/tests.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/tests.yml?branch=windows-server-production&label=Test%20Suite&style=for-the-badge&logo=pytest&logoColor=white" alt="Tests">
  </a>
</p>

<!-- ======================================================================= -->
<!-- TIER 3: BEAUTIFUL SKILL ICONS STRIP                                     -->
<!-- ======================================================================= -->
<p align="center">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=py,fastapi,nextjs,ts,react,tailwind,postgres,docker,githubactions,postman,git&theme=dark" alt="Technology Stack Icons" />
  </a>
</p>

---

## ⚡ Executive Overview

**HydroCast** is a mission-critical, operational hydrologic digital twin and flood early-warning platform engineered specifically for **Windows Server Standard** at Shivaji University, Kolhapur. It is **100% self-hosted**, running on university infrastructure with no Vercel, Supabase, or cloud dependency. It operates directly on local PostgreSQL 16 + PostGIS, supervised by a background watchdog daemon, and commanded via an isolated Operator Mission Control console.

During the Southwest Monsoon (June–September), torrential orographic precipitation along the Sahyadri ridge crest (100–250+ mm/day) funnels through nine steep basaltic headwater subcatchments directly into the urban river corridor of Kolhapur City. Catastrophic inundations in July 2005, August 2019, and July 2021 submerged critical transit bridges, paralyzed civic infrastructure, and proved that disaster management agencies require **48 to 72 hours of validated predictive lead time**—not retrospective observations.

HydroCast achieves this by coupling:

1. **High-Resolution NWP Forcing:** 90-hour Quantitative Precipitation Forecasts (QPF) from ECMWF IFS HRES (0.1° / ~9 km) with automated spatial centroid mapping and exponential backoff retry policies.
2. **Dual-Core Hydrologic Simulation:** Continuous basin-wide runoff routing using SCS-CN infiltration loss, SCS Dimensionless Unit Hydrograph transforms, and Muskingum-Cunge channel routing ($R1 \rightarrow R5$). Powered by an official USACE HEC-HMS 4.13 headless runner with an automated, zero-dependency pure-Python vectorized digital twin fallback.
3. **Monotonic Hydraulic Rating Engine:** Government Water Resources Department (WRD) cross-section surveys converted into monotonic piecewise cubic Hermite (PCHIP) rating curves for Rajaram Weir and Shivaji Bridge with millimeter datum alignment.
4. **Adaptive ML Telemetry Recalibration:** Continuous error-residual auditing against live ultrasonic water level sensors (ThingSpeak IoT channel 3424513 @ Shivaji Bridge) triggering bounded parameter optimization ($\alpha_K, \alpha_{\text{lag}}, \Delta CN, X$).
5. **Decisive Multi-Channel Alerting:** Central Water Commission (CWC) compliant flood bulletins pushed via WebSocket to operational dashboards, and dispatched directly to the District Disaster Management Authority (DDMA) and Telegram control rooms.

---

## 🛠️ Complete Technology Stack

| Architecture Domain | Core Technologies & Frameworks |
| :--- | :--- |
| **Simulation Core** | Python 3.12 · USACE HEC-HMS 4.13 · Vectorized Python Digital Twin · Jython |
| **Scientific & Spatial Computing** | NumPy · SciPy (PCHIP Monotonic Splines) · Pandas · GeoPandas · Shapely |
| **Numerical Meteorology** | ECMWF IFS HRES (0.1° / 9 km QPF) · Open-Meteo REST API |
| **Backend & API Engine** | FastAPI 0.110+ · Pydantic v2 · Uvicorn · Starlette · asyncpg connection pool · Ruff linter |
| **Database & Spatial Store** | **PostgreSQL 16** · **PostGIS 3.4** Spatial Extension — **100% self-hosted, no cloud sync** |
| **Frontend & Control Room UI**| Next.js 14 (App Router) · React 18 · TypeScript 5 · Tailwind CSS · Lucide Icons · Leaflet GIS · KaTeX |
| **Authentication & RBAC** | JWT/API key auth · Fail-closed secret handling · DB-backed admin auth with role-based access |
| **DevOps & Local Delivery** | NSSM Windows Services · Caddyfile reverse proxy · Native Windows installation |
| **Disaster Alerting & Dispatch** | DDMA Kolhapur Webhook Bridge · CWC Stage Classification · Telegram Emergency Bot API |

---

## 🏛️ System Architecture

HydroCast on Windows Server follows a **6-Layer Decoupled Architecture**, ensuring that computational simulations, persistence, and real-time dashboard delivery scale independently and remain fault-tolerant on-premises:

```mermaid
graph TD
    subgraph L0["LAYER 0: External Forcings & Sensors"]
        ECMWF["ECMWF IFS HRES 9km<br/>90-h QPF"]
        IoT["ThingSpeak Channel 3424513<br/>Ultrasonic Level Sensor @ Shivaji Bridge"]
        WRD["Maharashtra WRD Gauges<br/>Telemetry & Reservoir Outflows"]
    end

    subgraph L1["LAYER 1: Ingestion, Spatial Mapping & QC"]
        Selector["Station Selector<br/>(Argmax volume & Thiessen)"]
        QC["Precipitation QC & Imputation<br/>Range validation & spike rejection"]
    end

    subgraph L2["LAYER 2: Hydrologic Continuum & Channel Routing"]
        Loss["SCS-CN Infiltration Loss Engine<br/>9 Subbasins (S1 to S9)"]
        Transform["SCS Dimensionless Unit Hydrograph<br/>Runoff transforms"]
        Routing["Muskingum-Cunge Channel Routing<br/>Reaches R1 → R5"]
    end

    subgraph L3["LAYER 3: Hydraulic Rating & Datum Alignment"]
        Rating["WRD-Anchored Monotonic PCHIP<br/>Rajaram Weir & Shivaji Bridge"]
        Datum["Datum Adjustment<br/>-0.648 m shift Shivaji Bridge"]
        Classifier["CWC Threshold Classifier<br/>Normal / Alert / Warning / Danger"]
    end

    subgraph L4["LAYER 4: IoT Sensor QC & Adaptive ML Recalibration"]
        Discrepancy["Timing & Stage Error Detector<br/>(|Δt| ≥ 1.0 h or Δh > 0.25 m)"]
        Optimizer["Bounded L-BFGS-B Optimizer<br/>Tuning (α_K, α_lag, ΔCN, X)"]
        BasinSync["Atomic Basin Parameter Writer<br/>Basin_1.basin snapshots"]
    end

    subgraph L5["LAYER 5: Enterprise Persistence & Cold Storage"]
        Postgres["PostgreSQL 16 + PostGIS<br/>Local data directory: E:\\pgdata"]
        Parquet["Cold Storage Pruning<br/>Snappy-compressed (90-day retention)"]
    end

    subgraph L6["LAYER 6: Edge Presentation, Control Room & Alerts"]
        FastAPI["FastAPI REST API (:8000)<br/>HMAC-SHA256 JWT & API Key Auth"]
        WS["WebSocket Broadcaster<br/>Pushing 90-h Hourly Forecasts"]
        Dashboard["Next.js 14 Control Room (:3001)<br/>Live 12-step pipeline monitoring"]
        Alerts["Multi-Channel Alerting<br/>DDMA, CWC & Telegram broadcasts"]
    end

    ECMWF --> Selector --> QC --> Loss
    Loss --> Transform --> Routing --> Rating
    Rating --> Datum --> Classifier --> Postgres
    IoT --> Discrepancy
    Routing -.-> Discrepancy
    Discrepancy --> Optimizer --> BasinSync --> Loss
    Postgres --> Parquet
    Postgres --> FastAPI
    FastAPI --> WS --> Dashboard
    Classifier --> Alerts
```

--- 

## 🗺️ Panchganga Basin Catchment & Subbasin Parameters

The Panchganga basin is segmented into **nine primary hydrologic subbasins** draining through five interconnected reaches:

| Subbasin Code | Subbasin Name | Drainage Area ($km^2$) | Initial $CN$ | Lag Time ($min$) | Primary Rain Gauge | Centroid Coordinates |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **S1** | Karveer | 86.21 | 74.85 | 2,151.96 | Karveer | `16.68°N, 74.22°E` |
| **S2** | Sangarul | 153.77 | 65.74 | 3,154.25 | Sangarul | `16.63°N, 74.13°E` |
| **S3** | Kotoli | 261.32 | 64.82 | 3,997.70 | Kotoli | `16.78°N, 74.05°E` |
| **S4** | Karanjphen | 262.00 | 61.89 | 3,115.51 | Karanjphen | `16.83°N, 73.91°E` |
| **S5** | Padasali | 106.39 | 60.97 | 2,117.09 | Gaganbawda | `16.59°N, 73.88°E` |
| **S6** | Gaganbawda | 227.72 | 61.78 | 3,318.07 | Gaganbawda | `16.54°N, 73.83°E` |
| **S7** | Garivade | 195.39 | 61.28 | 3,362.27 | Radhanagari | `16.42°N, 73.97°E` |
| **S8** | Beed | 177.44 | 65.76 | 3,387.15 | Beed | `16.55°N, 74.06°E` |
| **S9** | Radhanagari | 366.97 | 64.31 | 5,199.04 | Radhanagari | `16.38°N, 74.01°E` |
| **TOTAL** | **Full Catchment** | **1,837.21 $km^2$** | *Weighted Avg* | — | — | **Sahyadri Ridge Crest** |

### Reach Routing Network (Muskingum-Cunge)

* **Reach R1** (Kasari Upper): $K = 2.899\text{ h},\; X = 0.20$
* **Reach R2** (Kasari Lower $\rightarrow$ Shivaji Bridge): $K = 11.827\text{ h},\; X = 0.20$
* **Reach R3** (Kumbhi Reach): $K = 3.829\text{ h},\; X = 0.20$
* **Reach R4** (Bhogawati Reach): $K = 1.224\text{ h},\; X = 0.20$
* **Reach R5** (Panchganga Trunk $\rightarrow$ Rajaram Weir Outlet): $K = 4.619\text{ h},\; X = 0.20$

--- 

## 🌊 Hydraulic Rating & Monotonic PCHIP Conversions

HydroCast eliminates non-physical rating curve oscillations by computing monotonic piecewise cubic Hermite interpolating polynomials (PCHIP) directly from official Government Water Resources Department (WRD) cross-sectional survey tables:

$$\frac{dQ}{dh} > 0 \quad \forall \; h \in [h_{\min}, h_{\max}]$$

```
           CHHATRAPATI SHIVAJI MAHARAJ BRIDGE                     RAJARAM K.T. WEIR (BASIN SINK)
 ▲ 545.30m ──────────────────────── DANGER LEVEL         ▲ 541.00m ──────────────────────── DANGER LEVEL
 │ 543.30m ------------------------ WARNING LEVEL        │ 539.00m ------------------------ WARNING LEVEL
 │ 542.70m ........................ ALERT LEVEL          │ 535.95m ........................ TOP OF WEIR CREST
 │ 531.54m ~~~~~~~~~~~~~~~~~~~~~~~~ Monsoon Baseflow     │ 532.19m ~~~~~~~~~~~~~~~~~~~~~~~~ Dry Bed Level
 └──────────────────────────────────────────────────     └──────────────────────────────────────────────────
           Datum Shift: -0.648m (WRD Benchmark)                    Primary Downstream Dynamic Rating Station
```

### CWC Emergency Alert Thresholds

| Alert Classification | Rajaram Weir Stage (m MSL) | Shivaji Bridge Stage (m MSL) | Operational Civic Action |
| :--- | :---: | :---: | :--- |
| **NORMAL** | $< 541.50$ | $< 540.85$ | Standard monitoring; normal sluice operations |
| **ALERT** | $541.50 - 542.70$ | $540.85 - 542.05$ | Internal advisory to irrigation engineers |
| **WARNING** | $542.70 - 543.30$ | $542.05 - 542.65$ | Floodplain evacuation notices issued |
| **DANGER** | $543.30 - 545.33$ | $542.65 - 544.68$ | Mandatory evacuation; NDRF/SDRF deployment |
| **HISTORIC PEAK (HFL)** | $\ge 545.33$ | $\ge 544.68$ | Extreme disaster protocols (2019/2021 flood level) |

--- 

## 🔄 12-Step Automated Forecast State Machine

Every 6 hours (`00Z`, `06Z`, `12Z`, `18Z`), HydroCast executes a deterministic 12-step forecast cycle:

| Step | State Identifier | Subsystem | Action & Quality Verification | Output Artifact |
| :---: | :--- | :--- | :--- | :--- |
| **01** | `FETCH_ECMWF` | NWP Ingestion | Ingest 90-hr ECMWF IFS QPF via Open-Meteo REST API | `ecmwf_90h_raw.json` |
| **02** | `SELECT_STATIONS` | Spatial QC | Map rainfall volume to subbasin centroids | `selected_stations.json` |
| **03** | `INGEST_THINGSPEAK` | IoT Sensors | Pull ultrasonic stage data from ThingSpeak Ch. 3424513 | `thingspeak_stage.json` |
| **04** | `QC_SENSOR_DATA` | Telemetry QC | Range validation, spike rejection & noise filtering | `sensor_qc_report.json` |
| **05** | `BUILD_HYETOGRAPHS` | Processing | Generate hourly subbasin hyetographs for HEC-HMS | `hyetographs.csv` |
| **06** | `POPULATE_DSS` | Boundary Prep | Format boundary time-series into HEC-DSS records | `boundary_forcing.dss` |
| **07** | `EXECUTE_HMS` | Simulation | Execute USACE HEC-HMS 4.13 or Vectorized Twin | `hms_runoff_out.dss` |
| **08** | `APPLY_RATING_CURVE` | Hydraulics | Convert $Q(t) \rightarrow h(t)$ via monotonic PCHIP splines | `stage_hydrographs.json` |
| **09** | `DETECT_DISCREPANCIES`| ML Auditor | Compute timing lag $\Delta t$ and stage error $\Delta h$ | `discrepancy_log.json` |
| **10** | `CALIBRATE_PARAMS` | ML Calibration | Bounded L-BFGS-B optimization ($\alpha_K, \alpha_{\text{lag}}, \Delta CN$) | `calibrated_params.json` |
| **11** | `CHECK_ALERTS` | Risk Assessment| Evaluate stages against CWC Warning & Danger thresholds | `cwc_bulletin.json` |
| **12** | `DISPATCH_NOTIFICATIONS`| Broadcast | Transmit bulletins to DDMA, Telegram & Next.js dashboard | `dispatch_receipt.json` |

--- 

## 🛡️ Security & Governance

### Fail-Closed Security Posture
* **Fail-closed admin login**: If `ADMIN_PASSWORD`/`ADMIN_USERNAME` are unset, **no** login succeeds. (Previously a blank submitted password matched an unset secret.)
* **Constant-time secrets**: Passwords, API keys and internal keys use `hmac.compare_digest` / `crypto.timingSafeEqual`. Passwords are compared exactly (no trimming).
* **Login throttling**: `POST /api/v1/admin/auth/token` is capped at `RATE_LIMIT_LOGIN` (default 5/min) per IP.
* **JWT hardening**: Only HMAC algorithms (`HS256/384/512`) are accepted; unsupported values fall back to HS256. Parser errors are not echoed back.
* **Public API key**: `X-API-Key` compared in constant time; an unset server key authorises nobody.
* **Internal broadcast**: `INTERNAL_KEY` must be ≥16 chars; otherwise the endpoint returns 503.

### Required Production Environment

```bash
APP_ENV=production
JWT_SECRET=<48+ random bytes>
API_KEY=<random>
HYDROCAST_READONLY_KEY=<random, read-only>
CONSUMER_API_KEYS=                              # optional, for rotation
INTERNAL_KEY=<16+ random chars>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<strong, unique>
CORS_ORIGINS=https://your-dashboard.example.org   # explicit, never '*'
DATABASE_URL=postgresql://postgres:PASSWORD@127.0.0.1:5432/rainfall_runoff
VISIT_HASH_SALT=<random>
TELEGRAM_WEBHOOK_SECRET=<random>
```

Generate values with:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Deployment Checklist
- [ ] TLS terminated at a reverse proxy; HTTP redirects to HTTPS.
- [ ] Secrets injected from CI secrets store — never committed.
- [ ] `CORS_ORIGINS` is an explicit allowlist (no `*`).
- [ ] Admin credentials verified; login rate limit verified.
- [ ] Reverse proxy forwards `X-Forwarded-For` **only** from trusted hops.
- [ ] Database user has least privilege (no superuser).
- [ ] Backups + restore drills verified.
- [ ] `/docs` exposure reviewed (disable via reverse proxy if not needed).
- [ ] NSSM services registered and set to `SERVICE_AUTO_START`.
- [ ] Health endpoints verified: `/healthz/live`, `/healthz/ready`.

--- 

## ⚡ API Gateway Route Matrix

FastAPI provides an asynchronous REST API running on port **8000** with the following routes:

| Method | Endpoint | Auth Tier | Description |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/v1/health` | Public | Container and probe liveness verification |
| `GET` | `/api/v1/status` | Public | System status, cycle timestamp & engine state |
| `GET` | `/api/v1/visits` | Public | Reads persisted visitor counts without incrementing |
| `POST`| `/api/v1/visits/record` | Public (Throttled) | Records unique daily visit via atomic operation |
| `GET` | `/api/v1/rainfall/ecmwf` | Public | 90-hr precipitation hyetographs across 9 subbasins |
| `GET` | `/api/v1/rainfall/stations` | Public | Station selection logic and volume ranking |
| `GET` | `/api/v1/hydrograph` | Public | Basin outlet and bridge runoff hydrographs |
| `GET` | `/api/v1/alerts/cwc` | Public | Central Water Commission stage thresholds & alerts |
| `GET` | `/api/v1/admin/runtime` | Admin / Token | Active engine telemetry and runtime execution latency |
| `GET` | `/api/v1/admin/pipeline` | Admin / Token | 12-step automated pipeline verification state |
| `GET` | `/api/v1/admin/health-log` | Admin / Token | Historical system health and error events |
| `POST`| `/api/admin/dispatch` | Admin / Token | Webhook bridge dispatching GitHub Actions workflows |
| `WS`  | `/ws/live` | Public | Real-time WebSocket streaming live stage updates |
| `GET` | `/healthz/live` | Public | K8s/liveness probe probe |
| `GET` | `/healthz/ready` | Public | K8s/readiness probe (DB connected) |
| `GET` | `/metrics` | Public | Prometheus metrics endpoint |

--- 

## 💻 Quickstart & Windows Server Deployment

### Prerequisites
* Windows Server Standard (2019 / 2022 / 2025), 64-bit
* 16 GB RAM minimum (24+ GB recommended)
* 50 GB+ storage: C:\ (OS & Binaries), E:\ (Data & Database)
* PostgreSQL 16.x x64 with PostGIS 3.4 (Port 5432, local bound)
* Python 3.12.x 64-bit, in PATH
* Node.js v18.x or v20.x LTS (Powers ports 3000 and 3001)
* HEC-HMS 4.13 x64 installed at `C:\Program Files\HEC\HEC-HMS\4.13\HEC-HMS.exe`

### Step 1: Run Pre-Flight Diagnostics
Validate that all system ports, runtimes, dependencies, and file permissions are ready:

```powershell
 powershell -ExecutionPolicy Bypass -File .\windows\system_diag.ps1
```
*Verification criteria: Output must report `System status: READY FOR PRODUCTION`.*

### Step 2: Initialize PostgreSQL Database
Create the `rainfall_runoff` database, tables, spatial indexes, and approved accounts:

```powershell
 powershell -ExecutionPolicy Bypass -File .\windows\init_database.ps1 -PgUser "postgres" -PgPassword "YourAdminPassword"
```
*Verification criteria: `[SUCCESS] PostgreSQL Database initialized and ready for production.`*

### Step 3: Configure Environment Secrets
Copy the example environment file and configure all secrets. **Never commit the `.env` file.**

```powershell
copy .env.example .env
```
Edit `.env` with your secure values:
- `JWT_SECRET` — 48+ random bytes for token signing
- `API_KEY` — random service-to-service key
- `ADMIN_PASSWORD` — strong, unique password (do not use hardcoded defaults like `Dev@Adm1` or `PI@Adm1`)
- `DATABASE_URL` — `postgresql://postgres:PASSWORD@127.0.0.1:5432/rainfall_runoff`
- `INTERNAL_KEY` — 16+ random characters for broadcast operations
- `CORS_ORIGINS` — explicit allowlist (e.g., `https://dashboard.yourdomain.org`)
- `VISIT_HASH_SALT` — random salt for IP hashing
- `TELEGRAM_WEBHOOK_SECRET` — random secret for Telegram webhook validation

### Step 4: Build Frontend Production Assets
Compile the Next.js production builds for both portals:

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

### Step 5: Register Windows Services (NSSM)
Install the backend, scheduler, watchdog, public portal, and operator console as native Windows Services:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\install_services.ps1
```
*Verification criteria: All 5 services registered with `SERVICE_AUTO_START` and failure restart actions:*
- `HydroCast-Backend` (port 8000)
- `HydroCast-Scheduler` (6-hourly pipeline daemon)
- `HydroCast-Watchdog` (15s heartbeat probe)
- `HydroCast-PublicWeb` (port 3000)
- `HydroCast-OperatorConsole` (port 3001)

### Step 6: Launch and Verify Services
Start all registered services and inspect their status:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\service_control.ps1 -Action start
powershell -ExecutionPolicy Bypass -File .\windows\service_control.ps1 -Action status
```
*Success looks like: All 5 services running, backend responding on http://127.0.0.1:8000, admin console on http://127.0.0.1:3001.*

### Step 7: Smoke-Test a Manual Forecast Cycle
Execute a test run directly from PowerShell to verify the entire pipeline:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\run_pipeline_manual.ps1
```

### Step 8: Verify Health Endpoints
```powershell
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/healthz/live
curl http://127.0.0.1:8000/healthz/ready
```
*Success looks like:* JSON response with `"status": "healthy"` from `/health`, `"ready": true` from `/healthz/ready`.

--- 

## 📈 Release & Upgrade Runbook (Windows Server)

### Cutting windows-v1.0.0
1. Ensure all intended changes are merged into `windows-server-production`.
2. Update `CHANGELOG.md` with `## [1.0.0] - 2026-11-13 — Windows Server Base Release (windows-v1.0.0)`.
3. Tag the release: `git tag windows-v1.0.0` and `git push windows-v1.0.0`.
4. Verify health gates:
   - All health endpoints return healthy status.
   - Database migration scripts run without error.
   - Frontend builds pass: `npm ci && npm run build` on both `frontend-public` and `frontend-admin`.
   - NSSM services restart cleanly after tag.

### Deploying windows-v1.0.0 to Windows Server
1. Pull the tagged release on the Windows Server:
   ```powershell
   git pull origin windows-v1.0.0
   ```
2. Re-run the full installation runbook (Steps 1–7 above). All steps are idempotent.
3. Verify the new health endpoints `/healthz/live` and `/healthz/ready`.
4. Confirm the version reported in API responses matches `API-Version: 1.2.0`.

### Rolling back to prior version
1. Identify the prior tag: `git tag --list | sort -V`.
2. Check out the prior release:
   ```powershell
   git checkout <previous-windows-tag>
   ```
3. Re-run the installation runbook (Steps 1–7). All scripts are backward-compatible.
4. Verify health endpoints report the prior version.
5. Return to `windows-server-production` once the rollback is confirmed successful.

--- 

## 🤝 Contributing & Community Standards

We actively welcome contributions to HydroCast! Whether you are improving hydrologic algorithms, optimizing data pipelines, or enhancing the control room UI:

* Read our [**Contributing Guide**](CONTRIBUTING.md) for branch policies, PR standards, and local testing workflows.
* Review our [**Code of Conduct**](CODE_OF_CONDUCT.md) for community pledges and standards.
* Report bugs or request features via [GitHub Issues](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues).

--- 

## 📖 Citation & Research Attribution

If you use HydroCast in your academic research, hydrologic studies, disaster resilience operations, or governmental flood planning, please cite the platform as:

> **Satwik K. Udupi, Sachin S. Panhalkar, Ganesh S. Nhivekar, Nikhil D. Pawar, Center for Climate Change and Sustainability Studies, Shivaji University, Kolhapur (2026).**  
> *HydroCast: Operational Hydrologic Digital Twin & Real-Time Flood Intelligence Platform for the Panchganga River Catchment.*  
> GitHub Repository: [https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast)

### BibTeX Format
```bibtex
@software{hydrocast2026,
  author    = {Udupi, Satwik K. and Panhalkar, Sachin S. and Nhivekar, Ganesh S. and Pawar, Nikhil D.},
  title     = {HydroCast: Operational Hydrologic Digital Twin & Real-Time Flood Intelligence Platform for the Panchganga River Catchment},
  institution = {Center for Climate Change and Sustainability Studies, Shivaji University, Kolhapur},
  year      = {2026},
  publisher = {GitHub},
  version   = {1.0.0},
  url       = {https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast}
}
```

--- 

## 🏛️ Institutional Partners & Funding

HydroCast is developed at the **Centre for Climate Change and Sustainability Studies (CCCSS)**, **Shivaji University, Kolhapur (SUK)**.

* **Research Grant & Funding:** Supported by the **Department of Science & Technology (DST-SERB)**, Government of India.
* **Institutional Partner:** Water Resources Department (WRD), Government of Maharashtra.
* **Disaster Coordination Partner:** District Disaster Management Authority (DDMA), Kolhapur.

<p align="center">
  Released under the <strong>Academic & Civil Disaster Resilience License</strong>.<br>
  Built with ❤️ by CCCSS, Shivaji University for the safety, resilience, and flood defense of Kolhapur District.
</p>
</content>