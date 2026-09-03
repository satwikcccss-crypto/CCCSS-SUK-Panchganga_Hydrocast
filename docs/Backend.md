# HydroCast Backend API & Orchestration Architecture

```
========================================================================================
             HYDROCAST FASTAPI REST SERVICE & AUTOMATION BACKEND
========================================================================================

                             HTTP Clients (Next.js / Dashboard / GIS)
                                                │
                                                ▼
                                    FastAPI Application Server
                                  (system/src/api/main.py :8000)
                                                │
      ┌─────────────────────────────────────────┼─────────────────────────────────────────┐
      ▼                                         ▼                                         ▼
[ REST Endpoints Router ]             [ WebSocket Manager ]                  [ Automation Pipeline ]
/api/v1/dashboard                      /ws/live broadcast                     12-Step Execution Runner
/api/v1/runs & /runs/{id}              Push to connected clients              HEC-HMS & Open-Meteo
/api/v1/accuracy & /hydrograph         Keep-alive ping/pong                   Cron: 00z, 06z, 12z, 18z
      │                                         │                                         │
      └─────────────────────────────────────────┼─────────────────────────────────────────┘
                                                ▼
                             Dual-Mode Data Storage & Persistence
                                                │
                 ┌──────────────────────────────┴──────────────────────────────┐
                 ▼                                                             ▼
    [ PostgreSQL / Supabase DB ]                                  [ Standalone JSON Ledger ]
    asyncpg async connection pool                                  system/data/runs/{cycle_id}.json
    Tables: simulation_runs, hydrographs,                          system/data/runs/runs_index.json
    station_telemetry, pipeline_steps                              frontend/public/data/latest_pipeline_state.json
```

---

## 1. Technology Stack & Framework

- **Runtime:** Python 3.12 (64-bit)
- **Framework:** FastAPI 0.111+ & Starlette (Asynchronous ASGI server via Uvicorn)
- **Database Driver:** `asyncpg` (Native binary protocol PostgreSQL connector)
- **Serialization:** Pydantic v2 & custom JSON encoders for NumPy arrays / Datetime objects
- **Numerical Engines:** NumPy, Pandas, SciPy, Scikit-learn
- **Task Orchestration:** Python standard library `subprocess`, `threading`, and file-based state locks

---

## 2. Dual-Mode Storage Architecture

The backend is engineered for zero-dependency resilience:

1. **Cloud Database Mode (PostgreSQL / Supabase):**
   If `DATABASE_URL` or `SUPABASE_DB_URL` is set in `.env`, the server initializes an asynchronous connection pool (`asyncpg.create_pool(min_size=2, max_size=10)`), logging every cycle, hyetograph, hydrograph, and step execution into structured relational tables.
2. **Standalone Embedded Mode (JSON Ledger):**
   If no external database is configured, the server operates autonomously using high-speed atomic JSON writes into:
   - `system/data/runs/{cycle_id}.json`: Complete immutable snapshot of the computation cycle.
   - `system/data/runs/runs_index.json`: Fast KPI index for historical queries.
   - `system/frontend/public/data/latest_pipeline_state.json`: Direct zero-copy broadcast to Next.js.

---

## 3. Complete REST API Endpoint Specification

```
+--------+--------------------------+-------------------------------------------------------+
| Method | Route Path               | Description & Payload Summary                         |
+--------+--------------------------+-------------------------------------------------------+
| GET    | /health                  | Service liveness & database connectivity check        |
| GET    | /api/v1/dashboard        | Full aggregated state (weather, runoff, gauges, logs) |
| GET    | /api/v1/summary          | Quick executive metrics (peak Q, lead hours, alert)   |
| GET    | /api/v1/hydrograph       | 90-hour river runoff hydrograph time series           |
| GET    | /api/v1/alerts           | Active CWC flood alerts for Shivaji and Rajaram       |
| GET    | /api/v1/pipeline/status  | 12-step pipeline component health & latency metrics   |
| GET    | /api/v1/pipeline/history | Last N simulation runs performance summary            |
| GET    | /api/v1/runs             | Paginated historical computation runs ledger          |
| GET    | /api/v1/runs/{run_id}    | Full archived payload for a specific simulation cycle |
| GET    | /api/v1/accuracy         | Model validation metrics (Spearman ρ, NSE, RMSE, MAE) |
| WS     | /ws/live                 | Real-time WebSocket event stream for dashboard push   |
+--------+--------------------------+-------------------------------------------------------+
```

### 3.1 Endpoint Details

#### `GET /api/v1/accuracy`
Returns model validation metrics evaluated against physical ground truth observations:

```json
{
  "cycle_id": "CYC_20260903_06z",
  "run_date": "03 Sep 2026",
  "validation": {
    "status": "VALIDATED",
    "performance_grade": "EXCELLENT",
    "metrics": {
      "spearman_rho": 0.9889,
      "spearman_rho_q": 0.9875,
      "nse_stage": 0.9892,
      "nse_discharge": 0.9879,
      "rmse_stage_m": 0.031,
      "mae_stage_m": 0.024,
      "pbias_stage_pct": -0.08,
      "basin_rainfall_accuracy_pct": 99.4
    },
    "station_volume_accuracy": [
      {
        "station_id": "KARVIR",
        "predicted_volume_mm": 50.0,
        "observed_volume_mm": 53.0,
        "accuracy_pct": 94.3,
        "status": "ACCURATE"
      }
    ]
  }
}
```

#### `GET /api/v1/runs`
Lists all tracked historical computation cycles, allowing frontend operators to compare model runs over time:

```json
[
  {
    "cycle_id": "CYC_20260903_06z",
    "run_date": "03 Sep 2026",
    "cycle_time": "06z",
    "peak_discharge_m3s": 544.4,
    "lead_hours_to_peak": 24,
    "total_volume_mcm": 74.3,
    "total_rainfall_mm": 65.2,
    "shivaji_peak_stage_m": 535.84,
    "alert_level": "NORMAL",
    "spearman_rho": 0.9889,
    "nse": 0.9879
  }
]
```

---

## 4. WebSocket Event Manager & Real-Time Broadcasting

To avoid constant polling from hundreds of emergency operations centers (EOC) screens during a flood event, the backend includes an event-driven WebSocket hub:

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)
```

Whenever a new 90-hour cycle finishes execution, the orchestrator triggers an internal broadcast to all connected WebSocket clients, updating charts, gauge levels, and flood warnings instantly without requiring a page refresh.
