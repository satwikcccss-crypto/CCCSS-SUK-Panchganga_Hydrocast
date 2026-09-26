# HydroCast Backend Architecture & Operational Engine

```
====================================================================================================
                  HYDROCAST 12-STAGE ORCHESTRATION PIPELINE (src/orchestrator.py)
====================================================================================================

 [ Stage 01: Environment & Directory Initialization ]
        |
        v
 [ Stage 02: Dynamic Station & Subbasin Selector (18 Stations) ]
        |
        v
 [ Stage 03: ECMWF 9km HRES Precipitation Ingestion via Open-Meteo SDK ]
        |
        v
 [ Stage 04: ThingSpeak Channel 3424513 Ultrasonic Telemetry Ingestion ]
        |
        v
 [ Stage 05: Physics-Informed Adaptive ML Calibrator (L-BFGS-B Loss Minimization) ]
        |
        v
 [ Stage 06: HEC-HMS 4.13 Simulation / Pure-Python Vectorized Physical Solver ]
        |  - SCS-CN Loss Method with Dynamic AMC-II/AMC-III
        |  - SCS Dimensionless Unit Hydrograph (SCS-UH)
        |  - Muskingum Reach Routing Network (R1–R5) with Sub-stepping
        |  - Exponential Baseflow Recession (k=0.002/hr, Min Floor >= 15 m³/s)
        v
 [ Stage 07: 2D Divided Channel Hydraulic Rating Curve Conversion (Shivaji & Rajaram) ]
        |
        v
 [ Stage 08: CWC Flood Alert Evaluation & Government Threshold Breach Detection ]
        |
        v
 [ Stage 09: Automated Telegram Bot Emergency Bulletin Dispatch to DDMA/WRD ]
        |
        v
 [ Stage 10: Relational State Persistence & Supabase PostgreSQL Sync ]
        |
        v
 [ Stage 11: Apache Parquet Cold Storage Archival Engine (90-Day Retention) ]
        |
        v
 [ Stage 12: Pipeline State Emission & WebSocket Live Broadcast ]
```

---

## 1. Directory Structure & Core Modules

```
src/
├── orchestrator.py                 # Master 12-stage automated pipeline coordinator
├── ecmwf/
│   ├── open_meteo.py               # Open-Meteo SDK client for ECMWF 9km IFS models
│   ├── retry_utils.py              # Exponential backoff and jittered retry wrapper
│   └── station_selector.py         # Subbasin spatial mapping for 18 stations
├── dss/
│   └── writer.py                   # HEC-DSSVue binary DSS time-series writer
├── hms/
│   └── runner.py                   # USACE HEC-HMS batch runner & Python physical emulator
├── hydrology/
│   ├── ml_calibration.py           # Real-time adaptive ML calibrator (L-BFGS-B)
│   ├── stage_converter.py          # 2D DCM rating curves, PCHIP splines, stage transfer
│   ├── validation_metrics.py       # Spearman, NSE, Pearson, RMSE, MAE, PBIAS
│   ├── realtime_telemetry_validator.py # ThingSpeak continuous 90h verification
│   └── runs_tracker.py             # Cycle state persistence & historical runs index
├── db/
│   ├── connection.py               # Supabase PostgreSQL connection pool with SSL
│   ├── store_results.py            # Relational database persistence
│   ├── sync_all_to_supabase.py     # Automated bulk synchronization
│   └── archive_runs.py             # Parquet cold storage engine & table pruning
├── alerts/
│   ├── telegram_bot.py             # Disaster dispatcher for DDMA/WRD flood bulletins
│   └── evaluator.py                # CWC threshold evaluator (Alert, Warning, Danger, HFL)
└── api/
    ├── main.py                     # FastAPI REST server & WebSocket live push (/ws/live)
    └── security.py                 # API key authentication & rate limiting
```

---

## 2. Telegram Bot Disaster Management System

### 2.1 Emergency Bulletin Dispatcher (`src/alerts/telegram_bot.py`)
Dispatches automated CWC/DDMA flood bulletin cards when projected stage breaches threshold tiers:

```
🌊 HYDROCAST FLOOD BULLETIN 🌊
Authority: District Disaster Management Authority (DDMA)
Classification: 🔴 [DANGER / FLOOD EMERGENCY]
━━━━━━━━━━━━━━━━━━━━━━
📍 Site: Chhatrapati Shivaji Maharaj Bridge (SHIVAJI_BRIDGE)
📊 Projected Peak Stage: 543.82 m MSL
⏱ Peak Arrival Time: 2026-09-12T06:00:00Z (T+36h)
📏 Current Water Level: 538.16 m MSL
Exceeds Danger by: +0.52 m
━━━━━━━━━━━━━━━━━━━━━━
🏛 Official WRD Reference Datums:
  • Warning Mark: 542.70 m
  • Danger Mark: 543.30 m
  • Historical Peak (HFL): 545.33 m
━━━━━━━━━━━━━━━━━━━━━━
🚨 RECOMMENDED ACTION:
Evacuate low-lying ghat settlements. Deploy NDRF / SDRF units to Panchganga Ghat.
```

### 2.2 Next.js Serverless Interactive Webhook (`frontend/app/api/telegram/webhook/route.ts`)
Responds instantly to disaster officers and citizens with live system status:
- `/start` or `/help`: Command guide
- `/status`: System health, cycle ID, runtime SLA
- `/stage`: Current water level and peak stage forecast for Shivaji Bridge and Rajaram Weir
- `/alerts`: Active warning and danger alerts
- `/bulletin`: Full CWC emergency flood bulletin
