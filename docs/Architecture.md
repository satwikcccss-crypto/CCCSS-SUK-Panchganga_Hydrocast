# HydroCast System Architecture & The 12-Step Pipeline

```
========================================================================================
         HYDROCAST END-TO-END AUTOMATED FLOOD FORECASTING ARCHITECTURE
========================================================================================

  [ STEP 1: MET INGESTION ]         [ STEP 2: SPATIAL ROUTER ]       [ STEP 3: SOIL RETENTION ]
  Open-Meteo ECMWF IFS 0.25°  ───>  Dynamic Subbasin Station  ───>  90-Day Antecedent Moisture
  90-Hour Precipitation (mm)        Selector (18 Panchganga)         AMC-I / AMC-II / AMC-III
              │                                 │                                 │
              ▼                                 ▼                                 ▼
  [ STEP 4: DSS / MET GEN ]         [ STEP 5: HMS RUNNER ]           [ STEP 6: OUTFLOW ROUTE ]
  Precipitation Boundary      ───>  HEC-HMS Headless Java Engine───>  Subbasin Convolution &
  DSS Records / Gage Arrays         / SCS-CN Physical Fallback       Sink Node Routing (J_Outlet)
              │                                 │                                 │
              ▼                                 ▼                                 ▼
  [ STEP 7: LIVE TELEMETRY ]        [ STEP 8: HYDRAULIC RATING ]     [ STEP 9: ACCURACY EVAL ]
  ThingSpeak Ultrasonic       ───>  Calibrated PCHIP Rating   ───>  Spearman Rank Correlation (ρ)
  Water Level Radar Sensor          Curve (Shivaji & Rajaram)        NSE, RMSE, Rainfall Volume
              │                                 │                                 │
              ▼                                 ▼                                 ▼
  [ STEP 10: RUNS LEDGER ]          [ STEP 11: DB & STATE DUMP ]     [ STEP 12: LIVE BROADCAST ]
  Persistent Simulation       ───>  Supabase PostgreSQL Sync   ───>  WebSocket /ws/live Push &
  Archiving (data/runs/)            & latest_pipeline_state.json     Next.js 14 Dashboard Render
```

---

## 1. Architectural Principles

HydroCast is designed around three core principles:

1. **Hydrological Conservatism:** Always select governing rainfall stations that represent maximum catchment threat to prevent under-predicting flood peaks.
2. **Decoupled Zero-Dependency Execution:** The system functions with 100% operational fidelity in standalone mode without requiring cloud databases, external message brokers, or proprietary GIS servers.
3. **Rigorous Physical Monotonicity:** Hydraulic stage-discharge relationships adhere strictly to surveyed bed slopes, wetted perimeter mechanics, and government field benchmarks ($dQ/dh > 0$).

---

## 2. The 12-Step Automated Pipeline Cycle

Every operational cycle executes sequentially through 12 distinct steps:

```
+----+-----------------------------+-----------------------------------------------------------+
|Step| Pipeline Phase              | Execution Engine & Source Module                          |
+----+-----------------------------+-----------------------------------------------------------+
| 01 | ECMWF Precipitation Fetch   | src/ecmwf/open_meteo.py (fetch_point_forecast)     |
| 02 | Dynamic Subbasin Selection  | src/ecmwf/station_selector.py (STATION_REGISTRY)   |
| 03 | Antecedent Soil Moisture    | src/ecmwf/open_meteo.py (calculate_amc_condition)  |
| 04 | DSS Meteorological Gen      | src/hms/runner.py (Met_1.dss precipitation tables) |
| 05 | Hydrologic Runoff Execution | src/hms/runner.py (execute_hec_hms / SCS-CN)       |
| 06 | Outlet Hydrograph Routing   | src/hms/runner.py (extract_outlet_hydrograph)      |
| 07 | Live IoT Telemetry Polling  | src/sensors/thingspeak_gauge.py (fetch_shivaji...) |
| 08 | Hydraulic Rating Conversion | src/hydrology/stage_converter.py (PCHIP converter) |
| 09 | Real-Time Telemetry Validation| src/hydrology/realtime_telemetry_validator.py (ThingSpeak 1h)|
| 10 | Historical Runs Ledger Arch | src/hydrology/runs_tracker.py (save_computation...)|
| 11 | Database Sync & State Dump  | src/ecmwf/open_meteo.py (latest_pipeline_state)   |
| 12 | Real-Time Dashboard Push    | src/api/main.py (WebSocket broadcast /ws/live)     |
+----+-----------------------------+-----------------------------------------------------------+
```

---

## 3. Dual-Cadence Data Flow & Process Orchestration

HydroCast operates on two complementary temporal loops:
1. **The 6-Hourly Forecast Generation Cadence (00z, 06z, 12z, 18z):** Ingests new ECMWF weather models, executes hydrologic watershed routing, and produces a fresh 90-hour forward hydrograph.
2. **The 1-Hourly Real-Time Verification Cadence (Every Hour at :00):** Ingests live ThingSpeak ultrasonic radar readings, resamples into hourly means, verifies accuracy, and updates the progressive 90-hour lifecycle ledger.

```
 External Sources               HydroCast Core                Persistence & UI
 
 [ Open-Meteo ] ──HTTP ──>  [ ecmwf/open_meteo.py ]
 (6-Hourly Cadence)                 │
 [ HEC-HMS 4.x] <──CLI───>  [   hms/runner.py   ]
                                    │
                            [ stage_converter   ]
                                    │
 [ ThingSpeak ] ──REST───>  [ realtime_telemetry]
 (1-Hourly Cadence)         [   _validator.py   ]
                                    │
                            [   runs_tracker    ] ──Disk──> [ data/runs/*.json ]
                                    │               Mirrors [ frontend/public/data/runs/ ]
                            [  FastAPI Server   ] ──Sync──> [ Supabase / Postgres ]
                                    │
                                WebSocket / REST
                                    │
                                    ▼
                         [ Next.js 14 Dashboard ] (Vercel Production)
```

---

## 4. Fault Tolerance & Self-Healing

1. **Network Retries:** All external HTTP calls (Open-Meteo, ThingSpeak) employ exponential backoff with random jitter across 3 retries.
2. **HEC-HMS Headless Fallback:** If HEC-HMS native Java binaries fail or DSS libraries are missing, the system smoothly falls back to an internal pure Python SCS-CN and Clark Unit Hydrograph engine (`src/hms/runner.py`), producing identical physical hydrographs.
3. **Sensor Telemetry Safeguards:** If the ultrasonic radar gauge drops offline or reports unphysical spikes, the system filters out outliers and computes baseflow from the latest verified water level.
4. **Zero-Crash Standalone Operation:** If PostgreSQL is unreachable, the API seamlessly serves from `public/data/latest_pipeline_state.json` and `data/runs/`.
5. **Vercel Serverless Resilience:** Historical run files are mirrored into `frontend/public/data/runs/` and packaged directly within the Next.js bundle, ensuring `/api/v1/dashboard?run_id=...` never throws 404 or filesystem errors on serverless edge functions.

---

## 5. Continuous 1-Hour Verification Architecture

Implemented via [`.github/workflows/telemetry_validation.yml`](file:///e:/hydrocast_complete/.github/workflows/telemetry_validation.yml):
- Executes automatically on `cron: "0 * * * *"`.
- Pulls 800 recent 5-minute telemetry feeds from ThingSpeak Channel `3424513`.
- Converts raw ultrasonic distance ($d_{\text{air}}$ in feet) to stage ($h$ in meters MSL) using datum $549.35\text{m}$.
- Computes genuine RMSE, MAE, NSE, PBIAS, Spearman $\rho$, and Pearson $R^2$.
- Commits updated telemetry state back to the repository to trigger instant Vercel synchronization.

