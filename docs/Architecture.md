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
| 01 | ECMWF Precipitation Fetch   | system/src/ecmwf/open_meteo.py (fetch_point_forecast)     |
| 02 | Dynamic Subbasin Selection  | system/src/ecmwf/station_selector.py (STATION_REGISTRY)   |
| 03 | Antecedent Soil Moisture    | system/src/ecmwf/open_meteo.py (calculate_amc_condition)  |
| 04 | DSS Meteorological Gen      | system/src/hms/runner.py (Met_1.dss precipitation tables) |
| 05 | Hydrologic Runoff Execution | system/src/hms/runner.py (execute_hec_hms / SCS-CN)       |
| 06 | Outlet Hydrograph Routing   | system/src/hms/runner.py (extract_outlet_hydrograph)      |
| 07 | Live IoT Telemetry Polling  | system/src/sensors/thingspeak_gauge.py (fetch_shivaji...) |
| 08 | Hydraulic Rating Conversion | system/src/hydrology/stage_converter.py (PCHIP converter) |
| 09 | Accuracy & Metrics Eval     | system/src/hydrology/validation_metrics.py (Spearman ρ)   |
| 10 | Historical Runs Ledger Arch | system/src/hydrology/runs_tracker.py (save_computation...)|
| 11 | Database Sync & State Dump  | system/src/ecmwf/open_meteo.py (latest_pipeline_state)   |
| 12 | Real-Time Dashboard Push    | system/src/api/main.py (WebSocket broadcast /ws/live)     |
+----+-----------------------------+-----------------------------------------------------------+
```

---

## 3. Data Flow & Inter-Process Communication

```
 External Sources               HydroCast Core                Persistence & UI
 
 [ Open-Meteo ] ──HTTP ──>  [ ecmwf/open_meteo.py ]
                                    │
 [ HEC-HMS 4.x] <──CLI───>  [   hms/runner.py   ]
                                    │
 [ ThingSpeak ] ──REST───>  [ sensors/thingspeak ]
                                    │
                            [ stage_converter   ]
                                    │
                            [ validation_metrics]
                                    │
                            [   runs_tracker    ] ──Disk──> [ data/runs/*.json ]
                                    │
                            [  FastAPI Server   ] ──Sync──> [ Supabase / Postgres ]
                                    │
                                WebSocket / REST
                                    │
                                    ▼
                         [ Next.js 14 Dashboard ]
```

---

## 4. Fault Tolerance & Self-Healing

1. **Network Retries:** All external HTTP calls (Open-Meteo, ThingSpeak) employ exponential backoff with random jitter across 3 retries.
2. **HEC-HMS Headless Fallback:** If HEC-HMS native Java binaries fail or DSS libraries are missing, the system smoothly falls back to an internal pure Python SCS-CN and Clark Unit Hydrograph engine (`system/src/hms/runner.py`), producing identical physical hydrographs.
3. **Sensor Telemetry Safeguards:** If the ultrasonic radar gauge drops offline or reports unphysical spikes, the system filters out outliers and computes baseflow from the latest verified water level.
4. **Zero-Crash Standalone Operation:** If PostgreSQL is unreachable, the API seamlessly serves from `public/data/latest_pipeline_state.json` and `data/runs/`.
