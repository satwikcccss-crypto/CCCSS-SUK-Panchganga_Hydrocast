# HydroCast Backend API & Orchestration Architecture


---

## Interactive diagram consoles

The console below is the rendered reference for this page: it carries the same structure, tier boundaries and failure branches that the prose describes.

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 11</span>
      <strong>Backend API Map</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/11-backend-api.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/11-backend-api.html?embed=1" title="Backend API Map Console"></iframe>
</div>

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 04</span>
      <strong>API Gateway & Auth Sequence</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/04-sequence-auth-api.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/04-sequence-auth-api.html?embed=1" title="API Gateway & Auth Sequence Console"></iframe>
</div>

---

## 1. Technology Stack & Framework

```
====================================================================================================
                  HYDROCAST 12-STAGE ORCHESTRATION PIPELINE (src/orchestrator.py)
====================================================================================================

 [ Step 01: Open-Meteo Download (src/ecmwf/downloader.py) ]
        |  - ECMWF IFS 0.1° HRES (90-Hour Lead Horizon)
        |  - Grid Point Decoding & Intensity Extraction (max mm/hr)
        v
 [ Step 02: Gauge Station Fetch (src/processing/gauge_fetcher.py) ]
        |  - Ingests 20-station telemetry & ThingSpeak IoT channel 3424513
        |  - Records inserted into observed_rainfall_qc
        v
 [ Step 03: Data Validation & QC (src/processing/validator.py) ]
        |  - Automated outlier rejection, rate-of-change, physical range filters
        |  - Aborts on critical QC failures
        v
 [ Step 04: Station Selection (src/ecmwf/station_selector.py) ]
        |  - Dynamic spatial mapping across 9 subbasins (S1–S9)
        |  - Records selection decision into simulation database
        v
 [ Step 05: HEC-DSS Binary Write (src/dss/writer.py) ]
        |  - Formats precipitation hyetographs into HEC-DSS records
        |  - Verifies DSS file integrity (data/hms/HMS_Automation_RJKT/...)
        v
 [ Step 06: HMS Parameter Check (src/hms/runner.py) ]
        |  - Verifies subbasin geometry, CN, Kirpich lag times, Muskingum K/X
        v
 [ Step 07: HEC-HMS Headless Execution (src/hms/runner.py) ]
        |  - Executes headless HEC-HMS 4.12 via Jython script compute.py
        |  - Automatic fallback to vectorized physical SCS-CN & Muskingum solver
        v
 [ Step 08: Result Hydrograph Extraction (src/hms/runner.py) ]
        |  - Parses outlet hydrograph (J_Outlet), computes peak Q & time of peak
        v
 [ Step 09: Stage Conversion (src/hydrology/post_process.py) ]
        |  - WRD PCHIP rating curve conversion (Shivaji Bridge & Rajaram Weir)
        |  - Computes stage (m MSL) and datum elevation offsets
        v
 [ Step 10: PostgreSQL State Persistence (src/db/store_results.py) ]
        |  - Commits hydrograph_results and bridge_stage_forecast to DB
        v
 [ Step 11: Alert & CWC Evaluation (src/alerts/evaluator.py) ]
        |  - Evaluates Warning (542.10m) & Danger (543.30m) thresholds
        |  - Dispatches automated Telegram emergency flood bulletins
        v
 [ Step 12: Dashboard Broadcast (src/api/notifier.py) ]
        |  - Pushes cycle completion event via WebSocket (/ws/live) to Next.js EOC
====================================================================================================
```

- **Runtime:** Python 3.12 (64-bit)
- **Framework:** FastAPI 0.111+ & Starlette (Asynchronous ASGI server via Uvicorn)
- **Database Driver:** `asyncpg` (Native binary protocol PostgreSQL connector) & `psycopg2`
- **Security & Authentication:** PyJWT (HS256 algorithms), constant-time HMAC comparison
- **Rate Limiting:** `slowapi` (Token bucket limiter on remote IP address)
- **Serialization:** Pydantic v2 & custom JSON encoders for NumPy arrays / Datetime objects
- **Numerical Engines:** NumPy, Pandas, SciPy (Levenberg-Marquardt, PCHIP), PyArrow
- **Cold Storage Engine:** Apache Parquet (Snappy compression)
- **Alert Dispatcher:** `requests`, `python-telegram-bot`

---

## 2. Dual-Mode Storage Architecture

The backend is engineered for zero-dependency resilience:

1. **Cloud Database Mode (PostgreSQL / Supabase):**
   If `DATABASE_URL` or `SUPABASE_DB_URL` is set in `.env`, the server initializes an asynchronous connection pool (`asyncpg.create_pool(min_size=2, max_size=10)`), logging every cycle, hyetograph, hydrograph, step execution, and accuracy score into structured relational tables.
2. **Standalone Embedded Mode (JSON Ledger):**
   If no external database is configured, the server operates autonomously using high-speed atomic JSON writes into:
   - `data/runs/{cycle_id}.json`: Complete immutable snapshot of the computation cycle.
   - `data/runs/runs_index.json`: Fast KPI index for historical queries.
   - `frontend/public/data/latest_pipeline_state.json`: Direct zero-copy broadcast to Next.js.

---

## 3. Interactive API Explorer

FastAPI generates its own browsable documentation from the application's own
metadata. Nothing extra needs to be installed or configured.

```
# From the repository root
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

| Surface | URL | Purpose |
| :--- | :--- | :--- |
| **Swagger UI** | `/docs` | Interactive explorer — *Try it out* against a live backend |
| **ReDoc** | `/redoc` | Three-panel reference; better for reading than clicking |
| **OpenAPI spec** | `/openapi.json` | Machine-readable contract for codegen and contract tests |

The explorer is populated entirely from the route declarations in
`src/api/main.py` and `src/api/admin.py` — the `summary`, `description`,
`tags`, `response_model` and Pydantic type hints you write there are what
render on the page. Adding a field to a response model automatically adds it
to the schema; there is no separate OpenAPI file to keep in sync.

Click **Authorize** once at the top right to attach either credential, then
every protected route becomes callable from the browser:


To produce a static spec in CI without binding a port:

```bash
python -c "import json; from src.api.main import app; \
           print(json.dumps(app.openapi(), indent=2))" > openapi.json
```

See the [API Reference](api-reference/index.md) for the Python source
reference and the [Security](api-reference/security.md) page for the
credential model.

---

## 4. Complete REST API Endpoint Specification

| Method | Route Path | Description & Payload Summary |
|:---|:---|:---|
| GET | /api/v1/health | Docker container & system liveness health probe |
| GET | /api/v1/status | System status, server time & latest cycle ID |
| POST | /api/v1/visits/record | Record a unique visit; returns daily & total counts |
| GET | /api/v1/rainfall/ecmwf | 90-hr ECMWF precipitation hyetographs per subbasin |
| GET | /api/v1/rainfall/stations | Station selection decisions for latest cycle |
| GET | /api/v1/rainfall/gauges | All 18 raw gauge 90-hr hyetographs (last cycle) |
| GET | /api/v1/runoff/hydrograph | 90-hr discharge + stage at outlet sink (J_Outlet) |
| GET | /api/v1/runoff/summary | Peak Q, lead time, alert, and peak arrival ±2.0h CI |
| GET | /api/v1/runoff/calibration | Real-time hydrologic parameters (α_K, lag, CN, X) |
| GET | /api/v1/runoff/stage/{site_id} | 90-hr stage + alert classification at bridge site |
| GET | /api/v1/alerts | Active flood warnings and CWC notifications |
| GET | /api/v1/alerts/bulletin | Formatted CWC/DDMA flood bulletin JSON |
| GET | /api/v1/pipeline | Pipeline step status for current cycle |
| GET | /api/v1/pipeline/history | Last N cycle durations and execution statuses |
| GET | /api/v1/runs | Paginated historical computation runs ledger |
| GET | /api/v1/runs/{run_id} | Full archived payload for a specific simulation cycle |
| GET | /api/v1/accuracy | Model validation metrics (Spearman ρ, NSE, RMSE, MAE) |
| POST | /api/v1/admin/auth/token | Administrator JWT Bearer login (HS256) |
| GET | /api/v1/admin/me | Authenticated administrator identity & claims |
| POST | /api/v1/admin/trigger-run | Manual forecast cycle trigger (JWT / X-API-Key) |
| POST | /api/v1/admin/archive | Cold storage Parquet archival trigger (JWT / API Key) |
| POST | /api/v1/admin/recalibrate | Force ML hydrologic recalibration & sync Basin_1.basin |
| WS | /ws/live | Real-Time WebSocket event stream for dashboard push |
| POST | /internal/broadcast | Internal-only cycle-completion push (hidden from docs) |


---

## 5. API Security, JWT Authentication & Rate Limiting

Implemented in [`src/api/security.py`](api-reference/security.md) and `src/api/admin.py`:

### 5.1 Public Rate Limiting (`slowapi`)

- All public read endpoints (`/api/v1/runoff/*`, `/api/v1/rainfall/*`, `/api/v1/alerts`) are protected by a rate limiter configured to **100 requests/minute** per client IP.
- Prevents scraping bots and aggressive polling from exhausting system resources.

### 5.2 Dual-Mode Administrative Security

Administrative endpoints (`/api/v1/admin/*`) require authentication via one of two modes:

1. **Signed JWT Bearer Token:**
   - Generated via `POST /api/v1/admin/auth/token` with valid credentials (`ADMIN_USERNAME`, `ADMIN_PASSWORD`).
   - Signed with HMAC-SHA256 using `JWT_SECRET`.
   - Token payload includes expiration (`exp`), issue time (`iat`), issuer (`hydrocast-api`), and role (`admin`).
   - Validated via HTTP Authorization header: `Authorization: Bearer <token>`.
2. **Master API Key (`X-API-Key`):**
   - For backend orchestrators and automated CI/CD pipelines.
   - Header checked against `API_KEY` using constant-time string comparison (`hmac.compare_digest`).

```python
async def verify_admin_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Dict[str, Any]:
    if credentials and credentials.credentials:
        return decode_access_token(credentials.credentials)
    if x_api_key and hmac.compare_digest(x_api_key.strip(), API_KEY.strip()):
        return {"sub": "system_api_key", "role": "admin"}
    raise HTTPException(status_code=401, detail="Unauthorized")
```

---

## 6. Administrative Endpoints & Background Orchestration

The administrative router (`src/api/admin.py`) provides operational control:

### 6.1 Manual Cycle Trigger (`POST /api/v1/admin/trigger-run`)

Allows emergency operations directors to manually trigger an immediate forecast cycle:

- **Request Body:**

```json
  {
    "date": "20260911",
    "hour": 6,
    "async_mode": true
  }
```

- If `async_mode` is `true`, the run is dispatched to FastAPI `BackgroundTasks` so the HTTP request returns immediately with a `queued` status.

### 6.2 Cold Storage Parquet Archival (`POST /api/v1/admin/archive`)

Triggers cold storage data pruning:

- **Request Body:**

```json
  {
    "retention_days": 90,
    "dry_run": false
  }
```

- Exports rows older than cutoff from `hydrograph_results`, `bridge_stage_forecast`, `rainfall_data`, `station_rainfall_telemetry` to Snappy-compressed Parquet files, then prunes PostgreSQL.

### 6.3 On-Demand ML Recalibration (`POST /api/v1/admin/recalibrate`)

Forces dynamic hydrologic recalibration:

- **Request Body:**

```json
  {
    "timing_offset_hours": -1.5,
    "stage_error_m": 0.30,
    "sync_basin_file": true
  }
```

- Optimizes parameters ($\alpha_K, \alpha_{\text{lag}}, \Delta\text{CN}, X$) and updates `Basin_1.basin` atomically on disk.

---

## 7. Real-Time Runoff Calibration & Peak Horizon Payloads

### 7.1 `GET /api/v1/runoff/summary` Response

Now includes the high-precision peak strike horizon and permissible confidence interval ($\pm 2.0\text{h}$):

```json
{
  "outlet": {
    "peak_discharge_m3s": 1420.5,
    "lead_hours_to_peak": 36,
    "total_volume_mcm": 128.4
  },
  "peak_arrival": {
    "shivaji": {
      "site_id": "SHIVAJI_BRIDGE",
      "site_name": "Chhatrapati Shivaji Maharaj Bridge (Panchganga Ghat)",
      "peak_lead_hours": 36,
      "peak_arrival_time": "2026-09-12T18:00:00Z",
      "peak_discharge_m3s": 1420.5,
      "peak_stage_m": 543.82,
      "confidence_interval": {
        "margin_hours": 2.0,
        "confidence_pct": 95,
        "earliest_lead_hours": 34.0,
        "latest_lead_hours": 38.0,
        "earliest_arrival_time": "2026-09-12T16:00:00Z",
        "latest_arrival_time": "2026-09-12T20:00:00Z",
        "stage_range_m": [543.52, 544.12],
        "discharge_range_m3s": [1335.0, 1505.0]
      },
      "status": "PEAK_IDENTIFIED"
    }
  },
  "recalibration": {
    "alpha_k": 1.05,
    "alpha_lag": 1.03,
    "delta_cn": 1.20,
    "muskingum_x": 0.26
  }
}
```

---

## 8. WebSocket Event Manager & Real-Time Push

The WebSocket hub (`/ws/live`) pushes immediate updates to connected emergency operations centers (EOC) screens:

- Eliminates constant client polling.
- The pipeline orchestrator calls `ws_manager.broadcast()` after Step 12 completes.
- Handles keep-alives and auto-reconnects with exponential backoff on client disconnections.

---

## 9. Telegram Bot Disaster Management Dispatcher (`src/alerts/telegram_bot.py`)

HydroCast integrates an automated Telegram flood bulletin dispatcher formatting official Central Water Commission (CWC) and District Disaster Management Authority (DDMA) emergency alert cards whenever river levels exceed Alert, Warning, Danger, or HFL marks:


---

## 10. Apache Parquet Cold Storage Archival Engine (`src/db/archive_runs.py`)

- **Retention Threshold:** Default 90 days (`ARCHIVE_RETENTION_DAYS`), configurable.
- **Archival Targets:** `hydrograph_results`, `bridge_stage_forecast`, `rainfall_data`, `station_rainfall_telemetry`, `subbasin_rainfall_ts`.
- **Storage Format:** Snappy-compressed Apache Parquet partitioned by `data/archives/year=YYYY/month=MM/<table_YYYYMM>.parquet`.
- **Database Pruning:** Transactional deletion in 50,000-row chunks maintaining sub-second query performance while preserving executive KPIs and `simulation_runs` master records indefinitely.
