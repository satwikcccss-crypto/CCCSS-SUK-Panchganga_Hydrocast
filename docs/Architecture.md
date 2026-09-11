# HydroCast System Architecture & The 12-Step Pipeline

```
========================================================================================
         HYDROCAST END-TO-END AUTOMATED FLOOD FORECASTING ARCHITECTURE
========================================================================================

  [ STEP 1: MET INGESTION ]         [ STEP 2: SPATIAL ROUTER ]       [ STEP 3: SOIL RETENTION ]
  Open-Meteo ECMWF IFS HRES 9km ───>  Dynamic Subbasin Station  ───>  90-Day Antecedent Moisture
  Exponential Retry & Jitter        Selector (18 Panchganga)         AMC-I / AMC-II / AMC-III
              │                                 │                                 │
              ▼                                 ▼                                 ▼
  [ STEP 4: DSS / MET GEN ]         [ STEP 5: ML RECALIBRATION ]     [ STEP 6: HMS RUNNER ]
  Precipitation Boundary      ───>  Live Discrepancy Check    ───>  HEC-HMS Headless Java Engine
  DSS Records / Gage Arrays         L-BFGS-B α_K, lag, CN, X         / Pure-Python SCS-CN Fallback
              │                                 │                                 │
              ▼                                 ▼                                 ▼
  [ STEP 7: OUTFLOW ROUTE ]         [ STEP 8: HYDRAULIC RATING ]     [ STEP 9: PEAK HORIZON ]
  Sink Node Routing (J_Outlet)───>  Dual-Regime Monotonic PCHIP ───>  Peak Arrival & ±2.0h CI
  Discharge Hydrograph (90h)        Shivaji & Rajaram Stages         95% Stage & Discharge Bands
              │                                 │                                 │
              ▼                                 ▼                                 ▼
  [ STEP 10: REAL-TIME QC ]         [ STEP 11: DDMA ALERTING ]       [ STEP 12: DB & BROADCAST ]
  ThingSpeak 1h Empirical     ───>  Telegram Bot Broadcast     ───>  Postgres Sync, Parquet Arch
  RMSE, MAE, NSE, Spearman ρ        Disaster Agency Webhooks         & WebSocket /ws/live Push
```

---

## 1. Architectural Principles

HydroCast is designed around four core principles:

1. **Hydrological Conservatism:** Always select governing rainfall stations that represent maximum catchment threat to prevent under-predicting flood peaks during orographic cloudbursts.
2. **Decoupled Zero-Dependency Execution:** The system functions with 100% operational fidelity in standalone mode without requiring external databases, message brokers, or proprietary GIS servers.
3. **Rigorous Physical Monotonicity:** Hydraulic stage-discharge relationships adhere strictly to surveyed bed slopes, wetted perimeter mechanics, and official government field benchmarks ($dQ/dh > 0$).
4. **Closed-Loop Adaptive Self-Healing:** The system detects wave timing and stage discrepancies against live IoT radar telemetry, automatically recalibrating routing parameters and updating model definitions on disk.

---

## 2. The 12-Step Automated Pipeline Cycle

Every operational cycle executes sequentially through 12 distinct transactional steps:

```
+----+-----------------------------+-----------------------------------------------------------+
|Step| Pipeline Phase              | Execution Engine & Source Module                          |
+----+-----------------------------+-----------------------------------------------------------+
| 01 | ECMWF Precipitation Fetch   | src/ecmwf/open_meteo.py (retry_utils.py exponential retry)|
| 02 | Dynamic Subbasin Selection  | src/ecmwf/station_selector.py (STATION_REGISTRY)          |
| 03 | Antecedent Soil Moisture    | src/ecmwf/open_meteo.py (calculate_amc_condition)         |
| 04 | DSS Meteorological Gen      | src/hms/runner.py (Met_1.dss precipitation tables)        |
| 05 | Real-Time ML Recalibration  | src/hydrology/ml_calibration.py (L-BFGS-B α_K, lag, CN, X)|
| 06 | Hydrologic Runoff Execution | src/hms/runner.py (execute_hec_hms / SCS-CN emulator)     |
| 07 | Outlet Hydrograph Routing   | src/hms/runner.py (extract_outlet_hydrograph J_Outlet)   |
| 08 | Hydraulic Rating Conversion | src/hydrology/stage_converter.py (Dual-Regime PCHIP)     |
| 09 | Peak Strike Horizon & ±2.0h | src/hydrology/ml_calibration.py (calculate_peak_arrival) |
| 10 | Real-Time Telemetry Validation| src/hydrology/realtime_telemetry_validator.py (ThingSpeak)|
| 11 | DDMA Multi-Channel Alerting | src/alerts/evaluator.py (telegram_bot.py & agency hooks) |
| 12 | Database Sync & Live Push   | src/api/main.py (/ws/live push & Parquet archival support)|
+----+-----------------------------+-----------------------------------------------------------+
```

---

## 3. Dual-Cadence Data Flow & Process Orchestration

HydroCast operates on two complementary temporal loops:
1. **The 6-Hourly Forecast Generation Cadence (00z, 06z, 12z, 18z):** Ingests new ECMWF weather models, executes hydrologic watershed routing, evaluates ML recalibration, and produces a fresh 90-hour forward hydrograph with peak strike arrival confidence windows.
2. **The 1-Hourly Real-Time Verification Cadence (Every Hour at :00):** Ingests live ThingSpeak ultrasonic radar readings, resamples into hourly means, verifies accuracy against the active forecast, and updates the progressive 90-hour lifecycle ledger.

```
 External Sources               HydroCast Core                Persistence & UI
 
 [ Open-Meteo ] ──HTTP ──>  [ ecmwf/open_meteo.py ]
 (6-Hourly Cadence)                 │ (retry_utils.py)
 [ HEC-HMS 4.x] <──CLI───>  [   hms/runner.py   ]
                                    │
                            [ ml_calibration.py ] ──Disk──> [ Basin_1.basin (.bak) ]
                                    │
                            [ stage_converter   ]
                                    │
 [ ThingSpeak ] ──REST───>  [ realtime_telemetry]
 (1-Hourly Cadence)         [   _validator.py   ]
                                    │
                            [   runs_tracker    ] ──Disk──> [ data/runs/*.json ]
                                    │               Mirrors [ frontend/public/data/runs/ ]
                            [  FastAPI Server   ] ──Sync──> [ Supabase / Postgres ]
                                    │                       [ Parquet Cold Archives ]
                                    │
                            [ telegram_bot.py   ] ──Push──> [ DDMA Telegram & Webhooks ]
                                    │
                                WebSocket / REST
                                    │
                                    ▼
                         [ Next.js 14 Dashboard ] (Vercel Production / Docker SSR)
```

---

## 4. Real-Time Adaptive ML Recalibration Loop

Implemented in [`src/hydrology/ml_calibration.py`](file:///e:/hydrocast_complete/src/hydrology/ml_calibration.py):
1. **Discrepancy Detection:** Compares previous forecast hydrograph against observed ThingSpeak ultrasonic radar telemetry. Detects timing offset $\Delta t = t_{\text{peak, obs}} - t_{\text{peak, fcst}}$ and rising limb stage error $\Delta h$.
2. **Trigger Thresholds:** Automatically fires when $|\Delta t| \ge 1.0\text{ hr}$ or stage error $> 0.25\text{ m}$.
3. **Loss Minimization:** Solves for optimal scaling factors using L-BFGS-B optimization:
   - $\alpha_K \in [0.50, 1.80]$ (Muskingum reach travel time scaling)
   - $\alpha_{\text{lag}} \in [0.50, 1.80]$ (Subbasin lag time scaling)
   - $\Delta\text{CN} \in [-8.0, 8.0]$ (SCS Curve Number adjustment)
   - $X \in [0.15, 0.40]$ (Muskingum wedge storage factor)
4. **Simultaneous Dual Synchronization:**
   - Immediately updates Python emulator parameters in `src/hms/runner.py`.
   - Atomically updates `Basin_1.basin` on disk after generating an automated timestamped `.bak` backup.

---

## 5. Peak Flood Strike Horizon & Permissible Confidence Interval ($\pm 2.0\text{h}$)

For civilian safety and emergency evacuation planning, HydroCast computes an official strike window:
- **Peak Arrival Lead Time ($T_{\text{peak}}$):** Exact projected lead hour of peak water level.
- **Permissible Uncertainty Window (95% CI):**
  $$\text{Earliest Arrival} = T_{\text{peak}} - 2.0\text{ hours}$$
  $$\text{Latest Arrival} = T_{\text{peak}} + 2.0\text{ hours}$$
- **Hydraulic Envelope:** Computes 95% confidence bands for water stage ($\pm 0.12\text{m}$ to $\pm 0.35\text{m}$) and discharge ($\pm 6\%$) based on surveyed river geometry.

---

## 6. Cold Storage & Telemetry Archival Strategy

Implemented in [`src/db/archive_runs.py`](file:///e:/hydrocast_complete/src/db/archive_runs.py):
- Automatically exports granular 15-minute and hourly records older than 90 days (`hydrograph_results`, `bridge_stage_forecast`, `rainfall_data`, `station_rainfall_telemetry`, `subbasin_rainfall_ts`) into Snappy-compressed Apache Parquet partitions (`data/archives/{table}/year=YYYY/month=MM/`).
- Deletes pruned records from PostgreSQL inside a safe transaction, keeping database indexes small and query latencies sub-second.
- Retains executive summary KPIs in `simulation_runs` indefinitely.

---

## 7. Multi-Container Docker Architecture

The platform provides a unified container deployment via [`docker-compose.yml`](file:///e:/hydrocast_complete/docker-compose.yml):
1. **`hydrocast-db`:** PostgreSQL 15 + PostGIS 3.4 container with automated schema bootstrapping.
2. **`hydrocast-backend`:** Multi-stage production container ([`Dockerfile`](file:///e:/hydrocast_complete/Dockerfile)) packaging Python 3.12, OpenJDK 17, GDAL, libeccodes, Uvicorn, and HEC-DSS runtime with `/api/v1/health` container probes.
3. **`hydrocast-frontend`:** Standalone SSR production container ([`frontend/Dockerfile`](file:///e:/hydrocast_complete/frontend/Dockerfile)) based on Node 20 Alpine.

---

## 8. Fault Tolerance & Self-Healing

1. **Network Retries:** All external HTTP calls (Open-Meteo, ThingSpeak) employ exponential backoff with random jitter across 5 retries (`src/ecmwf/retry_utils.py`).
2. **HEC-HMS Headless Fallback:** If native HEC-HMS Java binaries fail or DSS libraries are absent, the system seamlessly falls back to an internal pure-Python SCS-CN and SCS Unit Hydrograph engine (`src/hms/runner.py`), producing identical physical hydrographs in $< 20\text{ ms}$.
3. **Sensor Telemetry Safeguards:** If the ultrasonic radar gauge drops offline or reports unphysical spikes, the system filters out outliers and computes baseflow from the latest verified water level.
4. **Zero-Crash Standalone Operation:** If PostgreSQL is unreachable, the API seamlessly serves from `frontend/public/data/latest_pipeline_state.json` and `data/runs/`.
5. **Vercel Serverless Resilience:** Historical run files are mirrored into `frontend/public/data/runs/` and packaged directly within the Next.js bundle, ensuring `/api/v1/dashboard?run_id=...` never throws 404 or filesystem errors on serverless edge functions.
