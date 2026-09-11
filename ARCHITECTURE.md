# HydroCast — Rainfall-Runoff & Flood Intelligence System
## System Architecture Specification v3.0 (Operational Release)

---

## 1. High-Level System Architecture

HydroCast is an enterprise-grade operational hydrologic forecasting and early warning platform engineered specifically for the **$2,140\text{ km}^2$ Panchganga River Basin** in Western Maharashtra, India. The platform couples numerical weather prediction, physical watershed routing, calibrated river hydraulics, real-time IoT radar telemetry, and closed-loop machine learning parameter recalibration into an autonomous 90-hour predictive continuum.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 1. METEOROLOGICAL INGESTION LAYER                                      │
│  Open-Meteo REST API / ECMWF IFS HRES (9 km Grid) ──> 90-Hour Forward Quantitative Precipitation (QPF) │
│  Exponential Backoff & Jitter Wrappers (src/ecmwf/retry_utils.py) ──> Physical Range & NaN QC Checks   │
└───────────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 2. SPATIAL TOPOLOGY & SOIL MOISTURE LAYER                              │
│  18 Panchganga Stations (Karvir, Gaganbawda...) ──> Dynamic Conservative Maximum-Rainfall Selector     │
│  90-Day Antecedent Re-Analysis ──> Dynamic SCS Curve Number (AMC-I / AMC-II / AMC-III)                 │
└───────────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 3. HYDROLOGICAL RUNOFF ENGINE LAYER                                    │
│  Dual Execution Engine: USACE HEC-HMS 4.x Headless + High-Speed Pure-Python SCS-CN/Clark/Muskingum      │
│  Subbasins S1–S9 Loss & Convolution ──> Reach Routing (R1–R5) ──> Sink Outlet Hydrograph (J_Outlet)   │
└───────────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 4. CALIBRATED HYDRAULIC RATING ENGINE                                  │
│  Dual-Regime Monotonic PCHIP Rating (dQ/dh > 0) ──> Bed Slope S₀ = 0.005858 (Shivaji) / 0.002318 (RJKT)│
│  Anchored to 19 Official Maharashtra WRD Field Records (530.18m Datum to 545.33m HFL Benchmark)        │
└───────────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           5. REAL-TIME ML ADAPTIVE RECALIBRATION & CONFIDENCE BAND                     │
│  Discrepancy Detection vs ThingSpeak Ultrasonic Telemetry (|Δt| ≥ 1.0h or Δh > 0.25m)                  │
│  L-BFGS-B Optimization: Muskingum α_K, Subbasin α_lag, ΔCN, Muskingum X ──> Syncs Basin_1.basin (.bak)│
│  Peak Flood Arrival Window Calculation: T_peak ± 2.0h (95% Confidence Interval) at Shivaji & Rajaram   │
└───────────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 6. PERSISTENCE, COLD STORAGE & SECURITY                                │
│  Transactional Relational: PostgreSQL 15 / Supabase with asyncpg Pool & Step Logging                   │
│  Cold Storage Parquet Archival (src/db/archive_runs.py): 90-day columnar pruning into Snappy Parquet   │
│  Enterprise Security (src/api/security.py): HMAC-SHA256 JWT Admin + slowapi Rate Limiting (100 req/min)│
└───────────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 7. ALERTING & DECISION SUPPORT LAYER                                   │
│  DDMA Multi-Channel Telegram Bot Dispatcher (src/alerts/telegram_bot.py) + Agency Webhooks             │
│  WebSocket Live Push (/ws/live) ──> Next.js 14 Responsive Dashboard (Chart.js, Leaflet, 2D SVG X-Sec) │
│  Peak Strike Horizon Card ──> 1-Click Run Ledger Inspector ──> Dual-Unit (m MSL / ft) Prediction Log   │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack & Component Inventory

| Layer | Technology | Operational Function |
|---|---|---|
| **NWP Meteorological Data** | ECMWF IFS HRES 9km (0.1°), Open-Meteo REST API | Quantitative precipitation forecast (90 hours, 1-hr step) |
| **Ingestion Resilience** | Python `requests`, `openmeteo-requests`, SQLite Cache | Exponential backoff, full jitter, physical rainfall bounds (250 mm/hr) |
| **Hydrological Engine** | USACE HEC-HMS 4.x + Pure-Python Vectorized Emulator | Loss (SCS-CN), Transform (Clark UH), Channel Routing (Muskingum) |
| **Hydraulic Rating** | SciPy PCHIP (`scipy.interpolate.PchipInterpolator`) | Strictly monotonic rating curves ($dQ/dh > 0$), surveyed bed slopes |
| **Real-Time ML Recalibration** | SciPy `optimize.minimize` (L-BFGS-B), NumPy | Dynamic optimization of $\alpha_K$, $\alpha_{\text{lag}}$, $\Delta\text{CN}$, $X$ based on ThingSpeak telemetry |
| **IoT Level Telemetry** | MathWorks ThingSpeak (Channel 3424513) | Solar-powered ultrasonic sensor at Shivaji Bridge deck ($549.35\text{ m MSL}$) |
| **Database & Spatial** | PostgreSQL 15 + PostGIS + Supabase Pooler | Master cycle runs, hyetographs, hydrographs, step logs |
| **Cold Storage Archival** | PyArrow + Apache Parquet (Snappy compression) | Columnar pruning of high-frequency telemetry older than 90 days |
| **API Backend** | FastAPI 0.111+, Starlette, Uvicorn, asyncpg | RESTful endpoints, async connection pool, WebSocket live push |
| **API Security & Limits** | PyJWT (HS256), `slowapi` (Limiter), constant-time HMAC | Dual-mode auth (Bearer JWT / Master API Key), 100 req/min rate limit |
| **Emergency Alerting** | Telegram Bot API (`python-telegram-bot`), HTTP Webhooks | Automated CWC/DDMA flood bulletins to district control room & SDRF |
| **Executive UI Dashboard** | Next.js 14 (App Router, SSR), React 18, Tailwind CSS | High-density operations dashboard, Leaflet GIS map, Chart.js, SVG X-Section |
| **Containerization** | Docker, Docker Compose | Multi-stage backend container (Python 3.12 + OpenJDK 17 + GDAL), standalone Next.js container |
| **Automation & CI/CD** | GitHub Actions workflows | 6-hourly operational runs + 1-hourly ThingSpeak verification |

---

## 3. The 12-Step Automated Pipeline Continuum

The orchestrator ([`src/orchestrator.py`](file:///e:/hydrocast_complete/src/orchestrator.py), [`src/ecmwf/open_meteo.py`](file:///e:/hydrocast_complete/src/ecmwf/open_meteo.py)) executes the following transactional sequence on every 6-hour cycle (00z, 06z, 12z, 18z):

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: METEOROLOGICAL FORCING INGESTION                                                               │
│    Query Open-Meteo ECMWF IFS HRES 9km API with exponential backoff & full jitter (retry_utils.py).     │
│    Sanitize NaNs, enforce non-negative bounds, clip anomalies (> 250 mm/hr), pad to 90 hours.            │
│                                                                                                         │
│  STEP 2: GAUGE FETCHING & SPATIAL STATION ROUTING                                                       │
│    Ingest 18 rain gauge nodes across 9 subbasins. Evaluate cumulative volume.                           │
│    Dynamic conservative router selects maximum-threat station as governing hyetograph per subbasin.     │
│                                                                                                         │
│  STEP 3: ANTECEDENT SOIL MOISTURE (AMC) CLASSIFICATION                                                  │
│    Evaluate 90-day precipitation history; compute 5-day antecedent rainfall (P5).                       │
│    Dynamically adjust SCS Curve Numbers between AMC-I (dry), AMC-II (normal), and AMC-III (saturated).   │
│                                                                                                         │
│  STEP 4: HEC-DSS METEOROLOGICAL BOUNDARY PREPARATION                                                    │
│    Generate DSS binary input tables (/PANCHGANGA/S1..S9/PRECIP-INC/.../1HOUR/FORECAST/) via pydsstools.   │
│                                                                                                         │
│  STEP 5: REAL-TIME ML ADAPTIVE RECALIBRATION CHECK                                                      │
│    Pull live ThingSpeak radar telemetry (Channel 3424513). Check previous cycle hydrograph vs observed. │
│    If |Δt| ≥ 1.0h or Δh > 0.25m: solve L-BFGS-B loss for α_K, α_lag, ΔCN, Muskingum X.                 │
│    Atomically update Basin_1.basin (with .bak backup) and Python emulator parameters.                   │
│                                                                                                         │
│  STEP 6: HYDROLOGICAL WATERSHED RUNOFF EXECUTION                                                        │
│    Execute USACE HEC-HMS 4.x headless batch run (Control_1.control + Basin_1.basin + Met_1.met).        │
│    Fail-safe fallback: execute pure-Python SCS-CN/Clark UH emulator (< 20ms execution time).            │
│                                                                                                         │
│  STEP 7: SINK OUTLET HYDROGRAPH EXTRACTION                                                              │
│    Extract 90-point discharge hydrograph at basin sink (J_Outlet). Calculate peak Q, Tp, and volume.   │
│                                                                                                         │
│  STEP 8: MONOTONIC HYDRAULIC RATING STAGE CONVERSION                                                    │
│    Apply surveyed bed slope S₀ = 0.005858 (Shivaji Bridge) and S₀ = 0.002318 (Rajaram Weir).            │
│    Evaluate dual-regime PCHIP rating curves (dQ/dh > 0) to produce 90 hourly stage and flow forecasts.  │
│                                                                                                         │
│  STEP 9: PEAK FLOOD STRIKE HORIZON & CONFIDENCE INTERVAL COMPUTATION                                    │
│    Calculate peak arrival time and permissible ±2.0h uncertainty window (95% CI) at Shivaji and Rajaram.│
│    Compute 95% stage confidence envelope (±0.12m to ±0.35m) and discharge band (±6% rating tolerance).  │
│                                                                                                         │
│  STEP 10: REAL-TIME ACCURACY & VALIDATION AUDITING                                                      │
│    Compute Spearman rank correlation (ρ), Nash-Sutcliffe Efficiency (NSE), RMSE, MAE, and PBIAS.        │
│    Audit 18-station rainfall volumetric fidelity (target > 95%).                                        │
│                                                                                                         │
│  STEP 11: MULTI-CHANNEL CWC / DDMA EMERGENCY ALERT DISPATCH                                             │
│    Evaluate bridge stages against WRD datums (Warning: 542.70m, Danger: 543.30m, HFL: 545.33m MSL).    │
│    Format official DDMA HTML flood bulletin; broadcast via Telegram Bot & dispatch agency webhooks.     │
│                                                                                                         │
│  STEP 12: PERSISTENCE, ARCHIVAL & REAL-TIME DASHBOARD BROADCAST                                         │
│    Commit cycle to PostgreSQL (simulation_runs, hydrograph_results, bridge_stage_forecast, step_log).    │
│    Write immutable JSON ledger (data/runs/{cycle_id}.json, frontend/public/data/latest_pipeline_state). │
│    Broadcast cycle completion via WebSocket (/ws/live) to all connected Next.js operational dashboards. │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Subbasin Delineation & Reach Geometry (Panchganga Basin)

The basin delineation is formalized in [`data/hms/HMS_Automation_RJKT/Basin_1.basin`](file:///e:/hydrocast_complete/data/hms/HMS_Automation_RJKT/Basin_1.basin):

### Subbasin Catchment Summary ($1,837.21\text{ km}^2$ Gauged Area)
| Subbasin ID | Catchment Name | Drainage Area ($\text{km}^2$) | Baseline Curve Number ($CN$) | Subbasin Lag ($t_{\text{lag}}$, min) | Primary Governing Station |
|---|---|---|---|---|---|
| **S1** | Karveer (Outlet) | 86.21 | 74.85 | 2,152.0 | KARVIR (550m) |
| **S2** | Sangarul | 153.77 | 65.74 | 3,154.3 | SANGARUL (572m) |
| **S3** | Kotoli | 261.32 | 64.82 | 3,997.7 | KOTOLI (585m) |
| **S4** | Karanjphen | 262.00 | 61.89 | 3,115.5 | KARANJPHEN (640m) |
| **S5** | Padasali | 106.39 | 60.97 | 2,117.1 | SALWAN (595m) |
| **S6** | Gaganbawda | 227.72 | 61.78 | 3,318.1 | GAGANBAWDA (680m) |
| **S7** | Garivade | 195.39 | 61.28 | 3,362.3 | RADHANAGARI (615m) |
| **S8** | Beed | 177.44 | 65.76 | 3,387.1 | BEED (565m) |
| **S9** | Radhanagari | 366.97 | 64.31 | 5,199.0 | KASABA_WALAWE (560m) |

### Muskingum Channel Reach Routing Parameters
| Reach ID | River Reach Segment | Upstream Inflow Node | Downstream Outflow Node | Travel Time $K$ (hours) | Storage Factor $X$ |
|---|---|---|---|---|---|
| **R1** | Kasari Lower Reach | J_Kasari | J_Confluence | 4.50 | 0.25 |
| **R2** | Kumbhi-Tulsi Middle | J_Kumbhi_Tulsi | J_Confluence | 16.50 | 0.25 |
| **R3** | Bhogawati Main Canal | J_Bhogawati | J_Confluence | 9.48 | 0.25 |
| **R4** | Confluence to Shivaji | J_Confluence | J_Shivaji | 8.08 | 0.25 |
| **R5** | Shivaji to Rajaram Weir | J_Shivaji | J_Outlet (Rajaram) | 18.34 | 0.25 |

---

## 5. Hydraulic Calibration & Official WRD Datum Datums

### Official Reference Benchmarks (Maharashtra WRD Irrigation Department)
```
  Elevation Profile of Bridge Gauge Stations:

  546 m +                                     ================================= HFL (2019): 545.33 m MSL
        |
  544 m +                                     --------------------------------- Danger Level: 543.30 m MSL
        |                                     - - - - - - - - - - - - - - - - - Warning Level: 542.70 m MSL
  542 m +                                     . . . . . . . . . . . . . . . . . Shivaji Alert: 542.10 m MSL
        |                                     . . . . . . . . . . . . . . . . . Rajaram Alert: 541.50 m MSL
  536 m +                      ~~~~~~~~~~~~~~ Weir Crest Level: 535.77 m MSL
        |
  533 m +     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Normal Monsoon Stage: 533.28 m MSL (Q ≈ 109 m³/s)
        |
  530 m +==== River Bed Zero Datum: 530.18 m MSL (0' 0" Gauge Mark) =======================================
```

| Regulatory Level | Stage (m MSL) | Gauge Height (ft-in) | Discharge ($m^3/s$) | Discharge (cusecs) | CWC Alert Tier |
|---|---|---|---|---|---|
| **Zero Gauge Datum** | **$530.18\text{ m}$** | $00'\ 00''$ | $0.00\text{ m}^3/s$ | $0\text{ cfs}$ | DRY / BASELINE |
| **Normal Monsoon Level** | **$533.28\text{ m}$** | $10'\ 02''$ | $109.20\text{ m}^3/s$ | $3,856\text{ cfs}$ | NORMAL |
| **Rajaram Weir Overflow** | **$535.77\text{ m}$** | $18'\ 04''$ | $274.39\text{ m}^3/s$ | $9,690\text{ cfs}$ | NORMAL |
| **Rajaram Alert Level** | **$541.50\text{ m}$** | $37'\ 01''$ | $1,480.00\text{ m}^3/s$ | $52,266\text{ cfs}$ | ALERT |
| **Shivaji Alert Level** | **$542.10\text{ m}$** | $39'\ 01''$ | $1,800.00\text{ m}^3/s$ | $63,567\text{ cfs}$ | ALERT |
| **Warning Level** | **$542.70\text{ m}$** | $41'\ 01''$ | $2,200.00\text{ m}^3/s$ | $77,692\text{ cfs}$ | WARNING |
| **Danger Level** | **$543.30\text{ m}$** | $43'\ 00''$ | $2,675.00\text{ m}^3/s$ | $94,467\text{ cfs}$ | DANGER |
| **Highest Flood Level (HFL)** | **$545.33\text{ m}$** | $49'\ 08''$ | $3,850.00\text{ m}^3/s$ | $135,961\text{ cfs}$ | HFL_EXCEEDED |

---

## 6. Cold Storage & Telemetry Archival Strategy

To preserve sub-second querying latency in PostgreSQL/Supabase over years of operational cycles, HydroCast implements an automated cold storage archival engine ([`src/db/archive_runs.py`](file:///e:/hydrocast_complete/src/db/archive_runs.py)):

1. **Retention Threshold:** High-frequency records older than $90\text{ days}$ (configurable via `ARCHIVE_RETENTION_DAYS`) are selected for cold storage.
2. **Columnar Parquet Compression:** Time-series tables (`hydrograph_results`, `bridge_stage_forecast`, `rainfall_data`, `station_rainfall_telemetry`, `subbasin_rainfall_ts`) are exported into Snappy-compressed Apache Parquet files.
3. **Partition Structure:** Partitioned logically by table, year, and month:
   ```
   data/archives/
    ├── hydrograph_results/
    │    └── year=2026/
    │         └── month=06/
    │              └── hydrograph_results_202606_20260910_120000.parquet
    └── bridge_stage_forecast/
         └── year=2026/
              └── month=06/
   ```
4. **Pruning Transaction:** Once Parquet integrity is validated on disk, pruned rows are deleted in PostgreSQL inside a safe database transaction. Summary KPIs in `simulation_runs` are kept indefinitely.
5. **Execution:** Can be run via scheduled weekly cron or via authenticated API: `POST /api/v1/admin/archive`.

---

## 7. Enterprise Security, JWT Authentication & Rate Limiting

HydroCast implements multi-tier security ([`src/api/security.py`](file:///e:/hydrocast_complete/src/api/security.py), [`src/api/admin.py`](file:///e:/hydrocast_complete/src/api/admin.py)):

1. **Public Endpoint Rate Limiting:**
   - Enforced using `slowapi` at $100\text{ requests/minute}$ per IP address (`RATE_LIMIT_PUBLIC`).
   - Protects public and GIS endpoints (`/api/v1/runoff/*`, `/api/v1/rainfall/*`, `/api/v1/alerts`) against scraping and DDoS exhaustion.
2. **Dual-Mode Administrative Authentication:**
   - **Mode A (Signed JWT Bearer Token):** Administrators authenticate at `POST /api/v1/admin/auth/token` with constant-time password verification (`hmac.compare_digest`), receiving an HMAC-SHA256 signed JWT token valid for 24 hours.
   - **Mode B (Master API Key):** System-to-system automated orchestrators authenticate via `X-API-Key: <key>` header matching `API_KEY` from `.env`.
3. **Administrative Operations Router (`/api/v1/admin`):**
   - `POST /api/v1/admin/trigger-run`: Triggers on-demand manual 12-step hydrologic cycle (synchronous or background task).
   - `POST /api/v1/admin/archive`: Triggers cold storage Parquet archival.
   - `POST /api/v1/admin/recalibrate`: Manually forces ML parameter recalibration and disk synchronization.
   - `GET  /api/v1/admin/me`: Displays active session claims and authenticated roles.

---

## 8. Containerized Deployment Architecture (Docker Compose)

HydroCast is fully containerized for 1-command reproducible deployment:

```yaml
services:
  hydrocast-db:        # PostgreSQL 15 + PostGIS 3.4 (port 5432)
  hydrocast-backend:   # Python 3.12 + OpenJDK 17 + GDAL + FastAPI (port 8000)
  hydrocast-frontend:  # Next.js 14 Standalone SSR Server (port 3000)
```

- **Backend Multi-Stage Build ([`Dockerfile`](file:///e:/hydrocast_complete/Dockerfile)):**
  - Stage 1 (Builder): Installs C/C++ compilers, OpenJDK 17, `libgdal-dev`, `libeccodes-dev`, and builds Python wheels.
  - Stage 2 (Runner): Minimal runtime image with OpenJDK 17 JRE, `libgdal32`, non-root user `hydrocast`, and health check probe at `/api/v1/health`.
- **Frontend Standalone Build ([`frontend/Dockerfile`](file:///e:/hydrocast_complete/frontend/Dockerfile)):**
  - Node.js 20 Alpine multi-stage builder packaging static assets and standalone server bundle.
- **Unified Orchestration ([`docker-compose.yml`](file:///e:/hydrocast_complete/docker-compose.yml)):**
  - 1-command startup: `docker-compose up -d`.
  - Automated database initialization with [`database/supabase_schema.sql`](file:///e:/hydrocast_complete/database/supabase_schema.sql).
