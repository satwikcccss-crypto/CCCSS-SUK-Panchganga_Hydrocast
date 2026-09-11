# HydroCast Backend API & Orchestration Architecture

```
========================================================================================
             HYDROCAST FASTAPI REST SERVICE & AUTOMATION BACKEND
========================================================================================

                             HTTP Clients (Next.js / Dashboard / GIS)
                                                │
                                                ▼
                                    FastAPI Application Server
                                  (src/api/main.py :8000)
                                                │
      ┌─────────────────────────────────────────┼─────────────────────────────────────────┐
      ▼                                         ▼                                         ▼
[ REST Endpoints Router ]             [ WebSocket Manager ]                  [ Automation & Admin ]
/api/v1/dashboard                      /ws/live broadcast                     12-Step Execution Runner
/api/v1/runs & /runs/{id}              Push to connected clients              Admin Router (/admin/*)
/api/v1/runoff/* & /rainfall/*         Keep-alive ping/pong                   JWT Auth & Rate Limiter
      │                                         │                                         │
      └─────────────────────────────────────────┼─────────────────────────────────────────┘
                                                ▼
                             Dual-Mode Data Storage & Persistence
                                                │
                 ┌──────────────────────────────┴──────────────────────────────┐
                 ▼                                                             ▼
    [ PostgreSQL / Supabase DB ]                                  [ Standalone JSON Ledger ]
    asyncpg async connection pool                                  data/runs/{cycle_id}.json
    Tables: simulation_runs, hydrographs,                          data/runs/runs_index.json
    station_telemetry, pipeline_steps                              frontend/public/data/latest_pipeline_state.json
```

---

## 1. Technology Stack & Framework

- **Runtime:** Python 3.12 (64-bit)
- **Framework:** FastAPI 0.111+ & Starlette (Asynchronous ASGI server via Uvicorn)
- **Database Driver:** `asyncpg` (Native binary protocol PostgreSQL connector) & `psycopg2`
- **Security & Authentication:** PyJWT (HS256 algorithms), constant-time HMAC comparison
- **Rate Limiting:** `slowapi` (Token bucket limiter on remote IP address)
- **Serialization:** Pydantic v2 & custom JSON encoders for NumPy arrays / Datetime objects
- **Numerical Engines:** NumPy, Pandas, SciPy (L-BFGS-B, PCHIP), PyArrow
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

## 3. Complete REST API Endpoint Specification

```
+--------+-------------------------------+-------------------------------------------------------+
| Method | Route Path                    | Description & Payload Summary                         |
+--------+-------------------------------+-------------------------------------------------------+
| GET    | /api/v1/health                | Docker container & system liveness health probe       |
| GET    | /api/v1/status                | System status, server time & latest cycle ID          |
| GET    | /api/v1/dashboard             | Full aggregated state (weather, runoff, gauges, logs) |
| GET    | /api/v1/rainfall/ecmwf        | 90-hr ECMWF precipitation hyetographs per subbasin    |
| GET    | /api/v1/rainfall/stations     | Station selection decisions for latest cycle          |
| GET    | /api/v1/rainfall/gauges       | All 18 raw gauge 90-hr hyetographs (last cycle)       |
| GET    | /api/v1/runoff/hydrograph     | 90-hr discharge + stage at outlet sink (J_Outlet)     |
| GET    | /api/v1/runoff/summary        | Peak Q, lead time, alert, and peak arrival ±2.0h CI   |
| GET    | /api/v1/runoff/calibration    | Real-time hydrologic parameters (α_K, lag, CN, X)     |
| GET    | /api/v1/runoff/stage/{site_id}| 90-hr stage + alert classification at bridge site     |
| GET    | /api/v1/alerts                | Active flood warnings and CWC notifications           |
| GET    | /api/v1/alerts/bulletin       | Formatted CWC/DDMA flood bulletin JSON                |
| GET    | /api/v1/pipeline              | Pipeline step status for current cycle                |
| GET    | /api/v1/pipeline/history      | Last N cycle durations and execution statuses         |
| GET    | /api/v1/runs                  | Paginated historical computation runs ledger          |
| GET    | /api/v1/runs/{run_id}         | Full archived payload for a specific simulation cycle |
| GET    | /api/v1/accuracy              | Model validation metrics (Spearman ρ, NSE, RMSE, MAE) |
| POST   | /api/v1/admin/auth/token      | Administrator JWT Bearer login (HS256)                |
| GET    | /api/v1/admin/me              | Authenticated administrator identity & claims         |
| POST   | /api/v1/admin/trigger-run     | Manual forecast cycle trigger (JWT / X-API-Key)       |
| POST   | /api/v1/admin/archive         | Cold storage Parquet archival trigger (JWT / API Key) |
| POST   | /api/v1/admin/recalibrate     | Force ML hydrologic recalibration & sync Basin_1.basin|
| WS     | /ws/live                      | Real-time WebSocket event stream for dashboard push   |
+--------+-------------------------------+-------------------------------------------------------+
```

---

## 4. API Security, JWT Authentication & Rate Limiting

Implemented in [`src/api/security.py`](file:///e:/hydrocast_complete/src/api/security.py) and [`src/api/admin.py`](file:///e:/hydrocast_complete/src/api/admin.py):

### 4.1 Public Rate Limiting (`slowapi`)
- All public read endpoints (`/api/v1/runoff/*`, `/api/v1/rainfall/*`, `/api/v1/alerts`) are protected by a rate limiter configured to **100 requests/minute** per client IP.
- Prevents scraping bots and aggressive polling from exhausting system resources.

### 4.2 Dual-Mode Administrative Security
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

## 5. Administrative Endpoints & Background Orchestration

The administrative router ([`src/api/admin.py`](file:///e:/hydrocast_complete/src/api/admin.py)) provides operational control:

### 5.1 Manual Cycle Trigger (`POST /api/v1/admin/trigger-run`)
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

### 5.2 Cold Storage Parquet Archival (`POST /api/v1/admin/archive`)
Triggers cold storage data pruning:
- **Request Body:**
  ```json
  {
    "retention_days": 90,
    "dry_run": false
  }
  ```
- Exports rows older than cutoff from `hydrograph_results`, `bridge_stage_forecast`, `rainfall_data`, `station_rainfall_telemetry` to Snappy-compressed Parquet files, then prunes PostgreSQL.

### 5.3 On-Demand ML Recalibration (`POST /api/v1/admin/recalibrate`)
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

## 6. Real-Time Runoff Calibration & Peak Horizon Payloads

### 6.1 `GET /api/v1/runoff/summary` Response
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
      "status": "CALIBRATED_ACCURATE"
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

## 7. WebSocket Event Manager & Real-Time Push

The WebSocket hub (`/ws/live`) pushes immediate updates to connected emergency operations centers (EOC) screens:
- Eliminates constant client polling.
- The pipeline orchestrator calls `ws_manager.broadcast()` after Step 12 completes.
- Handles keep-alives and auto-reconnects with exponential backoff on client disconnections.
