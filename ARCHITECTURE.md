# HydroCast — System Architecture (Archify Reference)

> **Panchganga River Catchment** · Kolhapur District, Maharashtra, India  
> **Real-time rainfall-runoff · Hydraulic rating · IoT telemetry · 90-hour predictive flood intelligence**

```
 ██████╗ ███████╗██████╗ ██╗    ██╗███████╗███╗   ██╗██╗ ██████╗
██╔════╝ ██╔════╝██╔══██╗██║    ██║██╔════╝████╗  ██║██║██╔═══██╗
██║  ███╗█████╗  ██████╔╝██║ █╗ ██║█████╗  ██╔██╗ ██║██║██║   ██║
██║   ██║██╔══╝  ██╔═══╝ ██║███╗██║██╔══╝  ██║╚██╗██║██║██║   ██╗
╚██████╔╝███████╗██║     ╚███╔███╔╝███████╗██║ ╚████║██║╚██████╔╝
 ╚═════╝ ╚══════╝╚═╝      ╚══╝╚══╝ ╚══════╝╚═╝  ╚═══╝╚═╝ ╚═════╝

  Operational Hydrologic Continuum · 90-Hour High-Resolution Predictive Flood Intelligence
```

<p align="center">
  <a href="https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/">
    <img src="https://img.shields.io/badge/🌐_Live_Documentation_Portal-GitHub_Pages-06B6D4?style=for-the-badge&logo=github&logoColor=white" alt="Live GitHub Pages Portal">
  </a>
  <a href="https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/main.yml?style=for-the-badge&logo=githubactions" alt="CI Status">
  </a>
  <a href="https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues">
    <img src="https://img.shields.io/github/issues/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast?style=for-the-badge&logo=github" alt="Open Issues">
  </a>
  <a href="https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast?style=for-the-badge" alt="License">
  </a>
</p>

---

## About HydroCast

**HydroCast** is a production-grade, operational hydrologic and hydraulic flood early-warning system engineered for the **2,140 km² Panchganga River Basin** in Western Maharashtra, India.

During the Southwest Monsoon (June–September), intense orographic rainfall along the Western Ghats crest (Sahyadri mountains, often exceeding 100–250 mm/day) drains rapidly through steep basaltic gorges into the urban bottleneck of **Kolhapur city**. The floods of August 2019 and July 2021 showed that municipal authorities need **48–72 hours of predictive lead time** to deploy barriers, operate sluice gates, and evacuate civilians.

HydroCast closes that gap by coupling:

| Capability | Implementation |
|:---|:---|
| **Numerical Weather Prediction** | ECMWF IFS HRES 9 km / 0.1° — 90-h QPF updated every 6 hours, with exponential backoff & jitter (`src/ecmwf/retry_utils.py`) |
| **Watershed Routing** | SCS-CN loss, SCS unit-hydrograph, Muskingum channel routing (R1–R5) across 9 subbasins — HEC-HMS 4.x + pure-Python emulator |
| **River Hydraulics** | WRD-anchored monotonic PCHIP stage↔discharge rating (Rajaram verbatim; Shivaji shifted −0.648 m) |
| **ML Recalibration** | Bounded L-BFGS-B (α_K, α_lag, ΔCN, X) triggered by ThingSpeak IoT telemetry; atomic write-back to `Basin_1.basin` |
| **Peak Strike Horizon** | Exact peak arrival with ±2.0 h confidence interval (95% CI) at Shivaji Bridge, Rajaram Weir, and basin sink |
| **Emergency Alerting** | CWC-formatted flood bulletins to DDMA Telegram channels and agency webhooks |
| **Cold Storage** | 90-day pruning into Snappy-compressed Apache Parquet (`src/db/archive_runs.py`) |
| **Security** | Dual-mode admin auth (HMAC-SHA256 JWT + Master Key) with `slowapi` 100 req/min rate limiting |
| **Containerization** | Docker & Docker Compose (Python 3.12, OpenJDK 17, GDAL, Next.js 14 SSR, PostGIS) |
| **Dashboard** | Next.js 14 with live SVG cross-sections, 90-h hourly prediction logs, WebSocket push |

---

## End-to-End System Architecture — Archify ASCII

This is the single source of truth for the system topology. Six layers flow left→right, top→bottom. Every process, module, model, script, and database lives in exactly **one** logical cell — no scattered boxes, no redundant flowcharts.

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                              HYDROCAST — END-TO-END SYSTEM TOPOLOGY (v2.0.0)                                           ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║  LAYER 0 · EXTERNAL FORCINGS (read-only)                        │ LAYER 0 · EXTERNAL I/O & TELEMETRY                       │ LAYER 0 · ALERTING              ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║  ECMWF IFS HRES 9 km                                            │ ThingSpeak Ch. 3424513                                  │ DDMA / CWC / SDRF                 ║
║  90-h QPF (mm/hr, 1-h step)                                     │ Ultrasonic stage @ Shivaji Bridge (549.35 m MSL)        │ Telegram bot + webhooks           ║
║  Open-Meteo REST API                                            │                                                           │ HTML flood bulletins                ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
                                  │ precip (mm/hr)                 │ observed stage (m MSL)                    │ alert trigger                       ║
                                  ▼                                ▼                                       ▼                                       ║

╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║  LAYER 1 · INGESTION   scripts: src/ecmwf/, src/processing/, src/dss/, src/sensors/                                    ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║  Open-Meteo SDK Client    ─▶   Station Selector   ─▶   DSS Writer   ─▶   ThingSpeak Gauge Fetcher                        ║
║  (retry_utils.py)              (argmax 90-h vol)    (HEC-DSS path)   (fetch_shivaji_live_telemetry)                      ║
║                                                                                                                         ║
║  ▼ 90-h hyetographs per station    ▼ governing gage per subbasin    ▼ live telemetry JSON                                ║
║  data/openmeteo_dss/*.json           STATION_REGISTRY                  cache (data/telemetry/)                            ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
                                  │                                                              ║
                                  ▼                                                              ║

╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║  LAYER 2 · ORCHESTRATION & CORE ENGINE   scripts: src/orchestrator.py, src/hms/                                        ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║  Orchestrator (12 timed steps)   ─▶   HEC-HMS 4.x / Pure-Python Emulator   ─▶   Outlet Hydrograph                        ║
║  (pipeline_step_log)                (SCS-CN → SCS-UH → Muskingum R1–R5)   (J_Outlet sink)                              ║
║                                                                                                                         ║
║  ▼ deterministic, retry-wrapped      ▼ Q_total, Q_surface, baseflow     ▼ 90-point series                                ║
║  logs/pipeline.log                   src/hms/runner.py                   data/runs/CYC_*.json                              ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
                                  │                                                              ║
                                  ▼                                                              ║

╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║  LAYER 3 · HYDRAULIC RATING   model: src/hydrology/stage_converter.py                                                    ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║  Discharge Q   ─▶   WRD-Anchored PCHIP   ─▶   Stage h (m MSL)   ─▶   Alert Classification                                  ║
║  Rajaram (verbatim)   (dQ/dh > 0)      Shivaji (−0.648 m)     NORMAL / ALERT / WARNING / DANGER                          ║
║  Shivaji (shifted)    monotonic proof   530.18 → 545.33 m    HFL_EXCEEDED / EXTREME                                      ║
║                                                                                                                         ║
║  ▼ rating curve df                    ▼ per-site thresholds            ▼ bridge_stage_forecast (DB table)                 ║
║  build_calibrated_rating_curve()      classify_alert()                                                                     ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
                                  │                                                              ║
                                  ▼                                                              ║

╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║  LAYER 4 · ML RECALIBRATION   model: src/hydrology/ml_calibration.py                                                     ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║  ThingSpeak obs   ─▶   Discrepancy Detection   ─▶   Levenberg–Marquardt   ─▶   Basin_1.basin (atomic)                     ║
║  (Δt ≥ 1.0 h or        (|Δt|, Δh, peak Q err)   (α_K, α_lag, ΔCN, X)      + .bak snapshot                                ║
║   Δh > 0.25 m)                                                          in-memory overrides                              ║
║                                                                                                                         ║
║  ▼ calibrator.state                    ▼ L(θ) minimization              ▼ data/telemetry/                                ║
║  detect_timing_and_stage_discrepancy()   calibrate_parameters()        ml_calibration_state.json                          ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
                                  │                                                              ║
                                  ▼                                                              ║

╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║  LAYER 5 · PERSISTENCE & COLD STORAGE   database: PostgreSQL 15 + PostGIS / Supabase                                    ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║  simulation_runs   │  hydrograph_results   │  bridge_stage_forecast   │  step_log   │  alert_events                       ║
║  pipeline_step_log │  rating_curves       │  subbasin_rainfall_ts    │  gauge_stations│  subbasins                         ║
║                                                                                                                         ║
║  ▼ asyncpg pool   ▶ 90-day Parquet prune   ▶ asyncpg pool (reads)   ▶  data/archives/                                   ║
║  store_results.py   src/db/archive_runs.py                                   Snappy partitions                           ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
                                  │                                                              ║
                                  ▼                                                              ║

╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║  LAYER 6 · DELIVERY & ALERTING   scripts: src/api/, src/alerts/, frontend/                                              ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║  FastAPI REST (:8000)   ─▶   WebSocket /ws/live   ─▶   Next.js 14 Dashboard   ─▶   Telegram Bot                            ║
║  /api/v1/* (rate-limited)   real-time push     Leaflet GIS · Chart.js     /status /alerts                                ║
║  admin JWT + X-API-Key        (broadcast after   2D SVG cross-sections     /bulletin                                     ║
║                               step 12)                                        /rainfall                                                              ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## Process → Module → Script → Model → Database (Artifact Map)

Every artifact appears exactly once. Read across: **what runs → where it lives → entry point → model/data produced → stored in.**

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                              ARCHIFY — PROCESS / MODULE / SCRIPT / MODEL / DATABASE                                      ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

  PROCESS                    MODULE                    SCRIPT / ENTRY              MODEL / DATA                    DATABASE TABLE
  ─────                      ──────                    ─────────────               ─────────                       ─────────
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐          ┌──────────────┐            ┌──────────────┐
  │ NWP Ingest   │─────────▶│ ecmwf          │─────────▶│ open_meteo.py│─────────▶│ ECMWF IFS    │─────────▶│ subbasin_rainfall_ts│
  │ (90-h QPF)   │          │ downloader.py  │          │ retry_utils.py│          │ hyetographs  │            │ gauge_stations      │
  │              │          │ retry_utils.py │          │ station_     │          │ 90-h per     │            └──────────────┘
  └──────────────┘          │ validator.py   │          │ selector.py  │          │ station      │                 │
                            └──────────────┘          │ validator.py   │          │ QC flags     │                 │
                                      │               └──────────────┘          └──────────────┘                 │
                                      │                                                  │                      │
                                      ▼                                                  ▼                      │
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐          ┌──────────────┐            ┌──────────────┐
  │ Runoff       │─────────▶│ hms            │─────────▶│ runner.py    │─────────▶│ SCS-CN ·     │─────────▶│ hydrograph_results│
  │ (S1–S9)      │          │ basin_parser.py│          │ basin_parser.py│          │ SCS-UH ·     │            │ simulation_runs   │
  │              │          └──────────────┘          └──────────────┘          │ Muskingum R1–R5│            └──────────────┘
  └──────────────┘                                                     │          │ Basin_1.basin│                 │
                            │                                          │          └──────────────┘                 │
                            │                                          ▼                                          │
                            │                              ┌──────────────┐                                          │
                            │                              │ read_outlet_hydrograph│                                          │
                            │                              └──────────────┘                                          │
                                      │                                                  │                      │
                                      ▼                                                  ▼                      │
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐          ┌──────────────┐            ┌──────────────┐
  │ Hydraulic    │─────────▶│ hydrology      │─────────▶│ stage_converter.py│─────▶│ PCHIP rating │─────────▶│ rating_curves   │
  │ Rating       │          │ stage_converter│          │ post_process.py   │          │ curves (Q↔h) │            │ bridge_sites    │
  │ (Q ↔ h)      │          └──────────────┘          └──────────────┘          │ Survey XS      │            └──────────────┘
  └──────────────┘                                                     │          └──────────────┘                 │
                            │                                          │                                          │
                            │                                          ▼                                          │
                            │                              ┌──────────────┐                                          │
                            │                              │ classify_alert│                                          │
                            │                              └──────────────┘                                          │
                                      │                                                  │                      │
                                      ▼                                                  ▼                      │
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐          ┌──────────────┐            ┌──────────────┐
  │ ML Recalib   │─────────▶│ hydrology      │─────────▶│ ml_calibration.py│─────▶│ Levenberg–Marq│─────────▶│ ml_calibration_state│
  │ (α_K, lag,   │          │ ml_calibration │          │ basin_parser   │          │ α_K · α_lag  │            │ (JSON sidecar)    │
  │ ΔCN, X)      │          └──────────────┘          └──────────────┘          │ ΔCN · X        │            └──────────────┘
  └──────────────┘                                                     └──────────────┘                                          │
                            │                                          │                                                  │
                            │                                          ▼                                                  │
                            │                              ┌──────────────┐                                          │
                            │                              │ sync_to_hec_hms_basin│                                          │
                            │                              └──────────────┘                                          │
                                      │                                                  │                      │
                                      ▼                                                  ▼                      │
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐          ┌──────────────┐            ┌──────────────┐
  │ Telemetry    │─────────▶│ hydrology      │─────────▶│ realtime_telemetry_validator│─────▶│ ThingSpeak obs│─────────▶│ (cache JSON only)│
  │ Validation   │          │ realtime_...   │          │ thingspeak_gauge.py│          │ NSE · ρ     │            └──────────────┘
  │ (NSE, RMSE)  │          └──────────────┘          └──────────────┘          │ RMSE · MAE    │                 │
  └──────────────┘                                                     │          │ PBIAS · R²   │                                          │
                            │                                          └──────────────┘                                          │
                            │                                                  │                                          │
                            ▼                                                  ▼                                          │
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐          ┌──────────────┐            ┌──────────────┐
  │ Alerting     │─────────▶│ alerts         │─────────▶│ evaluator.py   │─────▶│ CWC thresholds │─────────▶│ alert_events    │
  │ (CWC/DDMA)   │          │ telegram_bot   │          │ telegram_bot.py│          │ Warn 542.70  │            │ step_log        │
  │              │          └──────────────┘          └──────────────┘          │ Danger 543.30  │            └──────────────┘
  └──────────────┘                                                     │          │ HFL 545.33   │                                          │
                            │                                          └──────────────┘                                          │
                            │                                                  │                                          │
                            ▼                                                  ▼                                          │
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐          ┌──────────────┐            ┌──────────────┐
  │ API & UI     │─────────▶│ api            │─────────▶│ main.py      │─────▶│ JSON run ledger│─────────▶│ data/runs/*.json│
  │ (FastAPI+Next│          │ admin.py       │          │ admin.py     │          │ data/runs    │            │ (file ledger)   │
  │  .js + WS)   │          │ notifier.py    │          │ notifier.py  │          │              │            └──────────────┘
  └──────────────┘          └──────────────┘          └──────────────┘          └──────────────┘                                          │
                            │                                                  │                                          │
                            ▼                                                  ▼                                          │
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐          ┌──────────────┐                                          │
  │ Archival     │─────────▶│ db           │─────────▶│ archive_runs.py│─────▶│ Parquet      │                                          │
  │ (90-day)     │          │ store_results│          │ store_results.py│          │ Snappy     │                                          │
  │              │          └──────────────┘          └──────────────┘          │ year/month   │                                          │
  └──────────────┘                                                     └──────────────┘           partitions   │                                          │
                                                                                              └──────────────┘                                          │
```

---

## The 12-Step Pipeline — Archify Process Flow

`src/orchestrator.py` runs twelve steps inside `timed_step()`. Each step writes a `running` then `success`/`failed` row into `pipeline_step_log`.

```
╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║  SCHEDULE: 02:30 · 08:30 · 14:30 · 20:30 UTC   (00z, 06z, 12z, 18z cycles)                                              ║
╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
                                  │
                                  ▼
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║  STEP  NAME                           SOURCE MODULE                            ARTIFACT                                  ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║ 01   Download ECMWF IFS QPF          src/ecmwf/open_meteo.py · retry_utils        90-h hyetographs per station   ║
║ 02   Dynamic Subbasin Selection      src/ecmwf/station_selector.py                 governing gage per subbasin    ║
║ 02b  Soil-Moisture Snapshot          src/ecmwf/open_meteo.py                      IFS 90h VWC + ERA5-Land 5-day  ║
║                                      (log only — never feeds CN, K, x, or routing)                          ║
║ 03   Live Telemetry Fetch            src/sensors/thingspeak_gauge.py               observed stage, raw feet       ║
║ 04   ML Recalibration                src/hydrology/ml_calibration.py               α_K, α_lag, ΔCN, X overrides   ║
║ 05 · DSS Write                       src/dss/writer.py                              DSS boundary write           ║
║ 06 · HMS Param Check                 src/hms/runner.py                              check_basin_parameters()     ║
║ 07 · HEC-HMS / Emulator              src/hms/runner.py                              Q_total, Q_surface, baseflow ║
║ 08 · Stage Conversion                src/hydrology/stage_converter.py               PCHIP stage @ Shivaji + Rajaram║
║ 09 · Peak Strike ±2.0 h CI           src/hydrology/ml_calibration.py               peak arrival window (95% CI)   ║
║ 10 · Telemetry Validation            src/hydrology/realtime_telemetry_validator.py   NSE, ρ, RMSE, MAE, PBIAS      ║
║ 11 · Alert Evaluation & Dispatch     src/alerts/evaluator.py · telegram_bot.py      CWC bulletin + Telegram        ║
║ 12 · DB Sync & WebSocket Broadcast   src/api/main.py · notifier.py                  /ws/live push + JSON ledger    ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

Each step is wrapped in `timed_step()` which writes a `running` then `success`/`failed` row into `pipeline_step_log`.

---

## Hydrologic Network — S1–S9 → R1–R5 → Sink (Archify)

```
╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                              HYDROLOGIC NETWORK — SUBBASINS → REACHES → SINK                                             ║
╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

       S6 Gaganbawda (227.72 km², CN 61.78)          S7 Garivade (195.39 km², CN 61.28)
               │                                               │
               ▼                                               ▼
        ┌─────────────────────────────────────────────────────┐
        │  🟣 Reach R5  ·  Upper Kumbhi River                   │
        │     K = 4.619 h   X = 0.20   ·  2 routing passes      │
        └─────────────────────────┬─────────────────────────────┘
                                  │  R5 outflow
       S9 Radhanagari (366.97 km²)│                                               S8 Beed (177.44 km², CN 65.76)
               │                                                                  │
               ▼                                                                  │
        ┌──────────────────┐                                                     │
        │  🟣 Reach R4     │                                                     │
        │  Bhogawati Trunk │                                                     │
        │  K = 1.224 h     │                                                     │
        │  X = 0.20   1 pass│                                                   │
        └────────┬─────────┘                                                     │
                 │  R4 outflow                                                   │
                 \                                                               │
                  v                                                              │
        ┌─────────────────────────────────────────────────────┐                 │
        │  🟣 Reach R2  ·  Middle Panchganga                    │                 │
        │  K = 11.827 h   X = 0.20   ·  5 routing passes        │                 │
        └─────────────────────────┬─────────────────────────────┘                 │
                                  │  R2 outflow                                   │
       S4 Karanjphen (262.00 km²) │               S5 Padasali (106.39 km²)        │
               \                 │                      /                         │
                \                │                     /                          │
                 v                v                    v                         │
        ┌─────────────────────────────────────────────────────┐                  │
        │  🟣 Reach R3  ·  Kasari River Main                    │                  │
        │  K = 3.829 h   X = 0.20   ·  2 routing passes         │                  │
        └─────────────────────────┬─────────────────────────────┘                  │
                                  │  R3 outflow                                   │
       S2 Sangarul (153.77 km²)   │              S3 Kotoli (261.32 km²)           │
               \                 │                    /                          │
                v                v                   v                         │
        ┌─────────────────────────────────────────────────────┐                  │
        │  🟣 Reach R1  ·  Lower Panchganga Trunk               │◄── S2, S3 direct│
        │  K = 2.899 h   X = 0.20   ·  2 routing passes         │                  │
        └─────────────────────────┬─────────────────────────────┘                  │
                                  │  R1 outflow                                   │
                                  v                                               │
        ┌─────────────────────────────────────────────────────┐                  │
        │  🟡 Sink-1  ·  Panchganga Basin Outlet (Rajaram)     │                  │
        │  + S1 Karveer direct (86.213 km², CN 74.85)          │                  │
        │  + Baseflow Q_bf(t) = B₀·e^(−0.002t)                 │                  │
        │  Q₀ = live sensor discharge (no floor; 91.1 if absent)│                 │
        │  = Q_total(t)  [T+0 … T+89 h]                        │                  │
        └─────────────────────────────────────────────────────┘                  │
```

### Subbasin Table (S1–S9)

```
┌──────┬──────────────────────────────┬─────────────┬──────────┬─────────────┬──────────────────────┐
│Sub   │ Catchment Name               │ Area (km²)  │ CN_II    │ Lag (min)   │ Primary Station      │
├──────┼──────────────────────────────┼─────────────┼──────────┼─────────────┼──────────────────────┤
│ S1   │ Karveer (outlet reach)       │ 86.213      │ 74.85    │ 2,152.0     │ KARVEER              │
│ S2   │ Sangarul (Tulsi lower)       │ 153.770     │ 65.74    │ 3,154.3     │ SANGARUL             │
│ S3   │ Kotoli (Kasari lower)        │ 261.320     │ 64.82    │ 3,997.7     │ KOTOLI               │
│ S4   │ Karanjphen (Kasari headwater)│ 262.000     │ 61.89    │ 3,115.5     │ KARANJPHEN           │
│ S5   │ Padasali (Kumbhi basin)      │ 106.390     │ 60.97    │ 2,117.1     │ PADASALI             │
│ S6   │ Gaganbawda (crest reach)     │ 227.720     │ 61.78    │ 3,318.1     │ GAGANBAWDA           │
│ S7   │ Garivade (ridge catchment)   │ 195.390     │ 61.28    │ 3,362.3     │ GARIVADE             │
│ S8   │ Beed (Bhogawati mid-reach)   │ 177.440     │ 65.76    │ 3,387.1     │ BEED                 │
│ S9   │ Radhanagari (upper catchment)│ 366.970     │ 64.31    │ 5,199.0     │ RADHANAGARI          │
└──────┴──────────────────────────────┴─────────────┴──────────┴─────────────┴──────────────────────┘
```

Total gauged area: **1,837.213 km²**.

### Muskingum Reach Table (R1–R5)

```
┌──────┬──────────────────────┬──────────────────────┬────────────────┬───────────────┬────────────────┐
│Reach │ Upstream Inflow From │ Downstream Outflow To│ Travel K (h)   │ Storage X     │ Routing Passes │
├──────┼──────────────────────┼──────────────────────┼────────────────┼───────────────┼────────────────┤
│ R5   │ S6, S7               │ R2                   │ 4.619          │ 0.20          │ 2              │
│ R4   │ S9                   │ R2                   │ 1.224          │ 0.20          │ 1              │
│ R2   │ R5, R4, S8           │ R1                   │ 11.827         │ 0.20          │ 5              │
│ R3   │ S4, S5               │ R1                   │ 3.829          │ 0.20          │ 2              │
│ R1   │ R2, R3, S2, S3       │ Sink-1 (Rajaram)   │ 2.899          │ 0.20          │ 2              │
└──────┴──────────────────────┴──────────────────────┴────────────────┴───────────────┴────────────────┘
```

Routing order: **R5 → R4 → R2 → R3 → R1 → Sink-1**. S1 drains directly to the sink.

---

## Runoff Continuum — Four Stages (Archify)

```
╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                              RUNOFF CONTINUUM — P(t) → Q_total(t)                                                        ║
╚═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
   │  ①  LOSS     │   │  ② TRANSFORM │   │  ③  ROUTE    │   │  ④  STAGE    │   │  ⑤  DELIVER  │
   │              │   │              │   │              │   │              │   │              │
   │  P(t)        │──►│  ΔP_e(t)     │──►│  Q_surf(t)   │──►│  h(t)        │──►│  Alerts +    │
   │  [mm/hr]     │   │  [mm]        │   │  [m³/s]      │   │  [m MSL]     │   │  Dashboard   │
   │              │   │              │   │              │   │              │   │              │
   │  SCS-CN      │   │  SCS UH      │   │  Muskingum   │   │  PCHIP       │   │  Telegram    │
   │  S = 25400/  │   │  u(t)=       │   │  S=K[X·I +   │   │  rating      │   │  WebSocket   │
   │       CN−254 │   │  (t/tp)^3.7· │   │   (1−X)·O]   │   │  WRD anchors │   │  /ws/live    │
   │  Ia = λ·S    │   │  e^{3.7(1−t/ │   │  5 reaches   │   │  + baseflow  │   │              │
   │  λ=.20/.15/  │   │     tp)}     │   │  R1…R5       │   │  recession   │   │              │
   │     .08      │   │              │   │              │   │              │   │              │
   └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
    per subbasin      per subbasin       channel network     at the gauge      district officers
    (9 subbasins)     (9 kernels)        (cascade order)     and 2 bridges     DDMA control room

   Conservation holds across all stages:
      Σ(P·A)  ──①──►  Σ(P_e·A)  ──②──►  Σ(Q_surf·Δt)  ──③──►  ΣQ  =  ΣI
      volume in = volume out, verified per reach by C₀ + C₁ + C₂ ≡ 1
```

---

## Rating Curve — WRD-Anchored PCHIP (Archify)

```
╔═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                              STAGE–DISCHARGE CONVERSION — WR D-ANCHORED PCHIP                                            ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

   Q_total (m³/s)
           │
           ▼
   ┌─────────────────────────────────────────────────────────────────────────────┐
   │  PCHIP interpolation on WRD-anchored control points                         │
   │  (monotonic, shape-preserving ⇒ dQ/dh > 0, no overshoot, invertible)        │
   ├─────────────────────────────────────────────────────────────────────────────┤
   │                                                                             │
   │  RAJARAM (WRD sheet, direct)                    SHIVAJI (−0.648 m shift)   │
   │  stage  529.318 ─ 530.18 ─ 532.70 ─ … ─ 543.30 ─ 545.33                    │
   │  Q m³/s   0.0     0.0     14.16   ─ … ─ 2675.0   3850.0                    │
   │                                                                             │
   │  stage = Rajaram − 0.648 m (downstream bed datum, reach 3,858 m)           │
   │  stage  528.670 ─ 532.052 ─ 532.712 ─ … ─ 544.682                          │
   │  Q m³/s   0.0     14.16     71.25    ─ … ─  2675.0                          │
   │                                                                             │
   │  Cross-check: WRD recorded Shivaji ALERT stage 542.10 m at 1,800 m³/s —    │
   │  same discharge as Rajaram WARNING stage 542.70 m. 542.70 − 542.10 = 0.600 │
   │  m (official pair); 529.318 − 528.670 = 0.648 m (surveyed bed levels).     │
   └───────────────────────────────┬─────────────────────────────────────────────┘
                                   │  invert (monotonic ⇒ single-valued)
                                   ▼
                    stage_m at Chhatrapati Shivaji Maharaj Bridge
                                   │
                                   ▼
   ┌─────────────────────────────────────────────────────────────────────────────┐
   │  ALERT CLASSIFICATION                                                       │
   │  stage ≥ 545.33 → HFL_EXCEEDED   (3,850 m³/s — historical peak)            │
   │  stage ≥ 543.30 → DANGER         (2,675 m³/s — danger mark)                │
   │  stage ≥ 542.70 → WARNING        (2,200 m³/s — warning mark)               │
   │  stage ≥ 542.10 → ALERT          (1,800 m³/s — Shivaji alert mark)         │
   │  otherwise      → NORMAL                                                         │
   └─────────────────────────────────────────────────────────────────────────────┘
```

### WRD Benchmark Table (subset)

```
┌────┬───────────────┬───────────────┬───────────────┬───────────────┬──────────────────────┬─────────────────┐
│ #  │ Stage (m MSL) │ Gauge (ft-in) │ Q (cusecs)    │ Q (m³/s)      │ Regime               │ CWC Alert       │
├────┼───────────────┼───────────────┼───────────────┼───────────────┼──────────────────────┼─────────────────┤
│ 01 │ 530.18        │ 00′ 00″       │ 0             │ 0.00          │ Zero-gauge datum     │ DRY BED         │
│ 02 │ 533.54        │ 11′ 00″       │ 2,825         │ 80.00         │ In-channel           │ NORMAL          │
│ 10 │ 535.21        │ 16′ 06″       │ 7,684         │ 217.59        │ Main channel         │ NORMAL          │
│ 12 │ 535.77        │ 18′ 04″       │ 9,690         │ 274.39        │ Weir overflow        │ NORMAL          │
│ 16 │ 541.50        │ 37′ 01″       │ 52,266        │ 1,480.00      │ Rajaram alert        │ ALERT           │
│ 17 │ 542.10        │ 39′ 01″       │ 63,567        │ 1,800.00      │ Shivaji alert        │ ALERT           │
│ 18 │ 542.70        │ 41′ 01″       │ 77,692        │ 2,200.00      │ Warning              │ WARNING         │
│ 19 │ 543.30        │ 43′ 00″       │ 94,467        │ 2,675.00      │ Danger               │ DANGER          │
│ 20 │ 545.33        │ 49′ 08″       │ 135,961       │ 3,850.00      │ HFL (2019)           │ EMERGENCY       │
└────┴───────────────┴───────────────┴───────────────┴───────────────┴──────────────────────┴─────────────────┘
```

*Conversion:* `Q (m³/s) = Q (cusecs) × 0.028316846592`

---

## ML Recalibration — Closed Loop (Archify)

```
╔═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                              ML RECALIBRATION — BOUNDED PHYSICS-INFORMED FIT                                               ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

   ThingSpeak obs (stage)  ─▶   detect_timing_and_stage_discrepancy()   ─▶   |Δt| ≥ 1.0 h or Δh > 0.25 m ?
                                                            │ No                                              │
                                                            │ "Baseline stable"                               ▼ Yes
                                                            │                                         calibrate_parameters()
                                                            │                                         (bounded L-BFGS-B)
                                                            │                                         L(θ) = w_nse(1−NSE) + w_time(Δt/2.0)² +
                                                            │                                         w_peak(ΔQ/Q_obs)² + w_reg‖θ−θ₀‖²
                                                            │                                                  │
                                                            │                                         Solve: α_K · α_lag · ΔCN · X
                                                            │                                                  │
                                                            │                                         sync_to_hec_hms_basin()  (atomic, + .bak)
                                                            │                                                  │
                                                            │                                         In-memory overrides applied to emulator
                                                            │                                                  │
                                                            ▼                                                  ▼
                                                    calibrator.state                              data/telemetry/ml_calibration_state.json
```

### Calibration Bounds

```
┌────────────┬──────────────────────────────────────┬──────────────────┐
│ Parameter  │ Meaning                              │ Range            │
├────────────┼──────────────────────────────────────┼──────────────────┤
│ α_K        │ Muskingum reach travel-time scaling  │ 0.50 – 1.80      │
│            │ (R1–R5)                              │                  │
│ α_lag      │ Subbasin lag-time scaling (S1–S9)    │ 0.50 – 1.80      │
│ ΔCN        │ SCS Curve Number adjustment (S1–S9)  │ −8.0 – +8.0      │
│ X          │ Muskingum wedge-storage factor       │ 0.15 – 0.40      │
└────────────┴──────────────────────────────────────┴──────────────────┘
```

Recalibration only fires on a **rising limb** (rise > 0.15 m). Write-back uses a timestamped `.bak` snapshot followed by atomic `os.replace()`.

---

## Deployment Topology (Archify)

```
╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                              DEPLOYMENT — GITHUB ACTIONS vs DOCKER COMPOSE                                               ║
╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

   ┌──────────────────────────────┐
   │      GitHub (main)           │
   │  pipeline.yml · tests.yml    │
   │  telemetry_validation.yml    │
   └───────┬──────────────┬───────┘
           │              │
   cron 4×/day│              │ push / PR
           ▼              ▼
   ┌──────────────────────────────────────┐
   │   Ubuntu GitHub Runner (ephemeral)   │
   │                                      │
   │  1. Open-Meteo ECMWF IFS fetch      │
   │  2. Station selection                │
   │  3. HEC-DSS boundary write           │
   │  4. HEC-HMS / pure-Python emulator   │
   │  5. Rating curve + alerts            │
   │  6. PostgreSQL (Supabase) write      │
   │  7. Telegram bulletin dispatch       │
   │  8. data/runs/*.json  ◄── committed  │
   └──────────────────┬───────────────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
   ┌─────────────┐ ┌──────────────┐ ┌──────────────┐
   │ Supabase    │ │ gh-pages     │ │ Vercel       │
   │ PostgreSQL  │ │ MkDocs site  │ │ Next.js 14   │
   │ + PostGIS   │ │ (this page)  │ │ dashboard    │
   └─────────────┘ └──────────────┘ └──────────────┘

   ┌────────────────────────────────────────────────────────────────────┐
   │  Local development — Docker Compose                                │
   │                                                                    │
   │  hydrocast-db     :5432  ·  Postgres 15 + PostGIS 3.4             │
   │  hydrocast-backend:8000  ·  Python 3.12 + JRE 17 + GDAL + FastAPI │
   │  hydrocast-frontend:3000 · Next.js 14 standalone                   │
   │                                                                    │
   │  HEC-HMS 4.13 does not run on Linux — the calibrated pure-Python   │
   │  emulator in src/hms/runner.py is the production path.             │
   └────────────────────────────────────────────────────────────────────┘
```

Named volumes (per-directory, seeded from image): `hydrocast_runs`, `hydrocast_telemetry`, `hydrocast_forecast`, `hydrocast_raw`, `hydrocast_archives`, `hydrocast_logs`, `postgres_data`.

---

## Revision History

| Version | Date | Change |
|:---|:---|:---|
| v2.0.0 | 2026-10 | Archify topology, 12-step pipeline, WRD-anchored PCHIP rating, ML recalibration loop, cold-storage Parquet, Telegram RBAC, low-flow baseflow fallback fix |
| v1.x | 2026-09 | Initial architecture (Mermaid-based, superseded by Archify ASCII) |

> **Maintainer note:** This document is the single source of truth for the system topology. If a module, script, model, or database table is added, removed, or renamed, update this Archify map first so documentation stays consistent with the code.

---

## Documentation Library Index

All architecture, processes, schema, and engineering detail is maintained in **Archify** style:

| Document | Purpose |
|:---|:---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System topology, process→module→script→model→database map, 12-step pipeline, hydrologic engine, hydraulic rating, ML recalibration, database schema, deployment, security |
| [`README.md`](README.md) | Clean entry point — badges, capabilities, quickstart, Archify overview |
