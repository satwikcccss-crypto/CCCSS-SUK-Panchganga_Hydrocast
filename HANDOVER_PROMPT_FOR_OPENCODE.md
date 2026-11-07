# HYDROCAST PANCHGANGA — SYSTEM HANDOVER & ENGINEERING CONTEXT PROMPT
### Senior Technical Lead Handover Specification for OpenCode Developer
**Target Environment**: Windows Server Standard @ Shivaji University Kolhapur (SUK)  
**Catchment**: Panchganga River Basin (1,837.21 km²), Kolhapur, Maharashtra, India  
**Date**: November 2026 | **Engineering Standard**: Enterprise Production Grade

---

## 📋 COPY-PASTE PROMPT FOR THE OPENCODE AGENT / DEVELOPER

```markdown
You are taking over development of **HydroCast Panchganga**, an enterprise flood forecasting and real-time early warning system deployed on **Windows Server Standard** at the Centre for Climate Change and Smart Solutions (CCCSS), **Shivaji University, Kolhapur (SUK)**.

The system has been completely decoupled from GitHub Actions, cloud Supabase, and Vercel. It is now a self-contained, failsafe on-premises production system.

### 🏛️ SYSTEM ARCHITECTURE & DOMAIN LAYOUT
The repository is strictly structured into single-responsibility domains:

1. `backend/`:
   - `ml/`: Physics-informed ML calibration (`ml_calibration.py`, `ml_parameter_predictor.py`) tuning Muskingum K/X and SCS-CN lag.
   - `hydrology/`: Watershed simulation (`runner.py`, `basin_parser.py`) for the 9 Panchganga subbasins (S1 Karveer through S9 Radhanagari).
   - `hydraulics/`: Rating curves and hydraulic physics (`rating_physics.py`).
   - `stage_conversion/`: Converts outlet discharge to water levels at Shivaji Bridge & Rajaram Weir via PCHIP interpolation (`stage_converter.py`).
   - `rainfall/`: Multi-tier weather retrieval engine (`open_meteo_failsafe.py`, `station_selector.py`) for 90-hr ECMWF IFS forecasts.
   - `dss/`: HEC-DSS (Data Storage System) record authoring and time-series extraction (`writer.py`).
   - `thingspeak/`: Ultrasonic radar IoT ingestion from Shivaji Bridge with 3-sigma outlier filtering (`failsafe_telemetry.py`).
   - `validation/`: Statistical accuracy engine (`validation_metrics.py`, `telemetry_metrics.py`) computing RMSE, MAE, NSE, PBIAS, Spearman rho.
   - `api/`: FastAPI REST API (:8000), WebSocket streaming hub (`websocket_hub.py`), rate limiter, and local RBAC JWT auth (`admin.py`, `security.py`).
   - `services/`: Windows daemons: autonomous 24/7 scheduler (`scheduler_daemon.py`), supervisory watchdog (`watchdog.py`), and checkpointed worker (`pipeline_worker.py`).
   - `db/`: Resilient connection pool with offline disk-backed transaction staging (`resilient_pool.py`).

2. `frontend-public/` & `frontend-admin/` (TWO STANDALONE NEXT.JS APPS):
   - **App 1: Public Portal (`frontend-public/` on Port 3000)**: Serves citizens, research scholars, and district authorities. Shows ONLY 5 public sections:
     1. Executive Dashboard (Basin overview, bridge flood status)
     2. Meteorological Rainfall (90h subbasin forecasts S1-S9)
     3. HEC-HMS Runoff & Stage (Hydrographs, peak discharge arrival)
     4. System Health (Operational indicator, sync timestamps)
     5. Project Information (DST-SERB, Shivaji University Kolhapur & team)
     *Completely stripped of admin routes, login pages, and operational controls.*
   - **App 2: Operator Mission Control (`frontend-admin/` on Port 3001)**: Dedicated SCADA command room console for Windows Server operators.
     - **NO LOGIN LOCK**: Direct passwordless access on root `http://localhost:3001/` (no login gate, no password prompt needed on local Windows Server).
     - **Spacious Sidebar-Driven Layout (72px Left Rail)**: Eliminates claustrophobic clutter by dividing operations into 5 dedicated enterprise domain panels:
       * **Panel 1 — Executive Overview**: Top IMP KPIs (ML Operational Status, Current Run Validation ground truth), Stage Gauges (Radial dial & vertical staff gauge for Shivaji Bridge & Rajaram Weir), HEC-RAS 2D Bathymetric Cross-Section with 90h water level simulation slider/playback, and Dual-Axis Hydrograph (Discharge $m^3/s$ + Stage $m$ MSL).
       * **Panel 2 — Meteorological Rainfall**: 20 AWS catchment stations roster with active indicators and manual override toggles, accompanied by an interactive Basin GIS Location Map with zoom/layer/centroid controls.
       * **Panel 3 — ML & Model Accuracy**: LightGBM/XGBoost residual error curve ($\Delta Q$), concordance scatter plot (1:1 regression fit), and official Maharashtra WRD 19-regime rating curve records table.
       * **Panel 4 — Historical Run Ledger**: Searchable HEC-DSS runs database with peak discharge ($m^3/s$), peak stage ($m$ MSL), simulation duration, and binary DSS pathnames.
       * **Panel 5 — System Health & Engine**: 12-step hydrological cycle matrix with individual step retries, Windows Server hardware (8 vCPUs, 24 GB RAM, PostgreSQL 16 resilient pool), 5 NSSM services, and live streaming terminal.
   - **STRICT UI REQUIREMENT**: All screens strictly use an **ENTERPRISE LIGHT THEME** (`bg-slate-50`, pure white card containers, crisp `border-slate-200`, dark slate typography). **NO DARK BACKGROUNDS STRICTLY**.
   - **OWNERSHIP NOTE**: Frontend design and user-interface architecture are managed by Antigravity. OpenCode focuses on backend simulation logic, HEC-DSS integration, ML algorithms, database resilience, and Windows Server administration.

3. `database/`:
   - `schema.sql`: PostgreSQL 16 + PostGIS production schema (subbasins, stations, bridges, runs, metrics, logs).
   - `seeds.sql`: Official Panchganga subbasins (S1-S9), 20 stations, and 19 WRD field benchmarks.
   - `admin_users.sql`: Approved SUK accounts (`satwikcccss@gmail.com`, `panhalkarsachin@gmail.com`, `gonioelect@gmail.com`, `nikhilpawar6297@gmail.com`) and login audit trail.
   - `storage_setup.sql`: 3512 GB dedicated tablespace configuration for E:\ drive.

4. `windows/`:
   - `install_services.ps1`: Registers Backend, Scheduler, Watchdog, Public Web, and Operator Console as Windows Services via NSSM.
   - `service_control.ps1`: Central controller (`-Action start|stop|restart|status`).
   - `init_database.ps1`: Automated PostgreSQL database and tablespace creator.
   - `backup_database.ps1`: Daily custom compressed `pg_dump` with SHA-256 verification and 30-day retention.
   - `system_diag.ps1`: Pre-flight environment diagnostics (hardware, ports, python libs, write permissions).
   - `run_pipeline_manual.ps1`: Manual CLI forecast runner with step retry support (`-SingleStep <1-12>`).

5. `dss/`:
   - Contains the official HEC-HMS 4.13 project in `dss/HMS_Automation_RJKT/` which can be opened directly in the HEC-HMS Windows GUI or executed headlessly via batch Jython `compute.jy`.

6. `data/`:
   - `inputs/` (GIS layers, station coordinates)
   - `telemetry/` (radar cache, calibration state)
   - `runs/` (forecast hydrographs and runs ledger)
   - `staging/` (weather cache and offline DB pending commits buffer)
   - `logs/` (orchestrator, watchdog, and service logs)

---

### ⚠️ SENIOR TECH LEAD RULES (DOs AND DONTs)
1. **HEC-HMS vs HEC-DSS**: Remember that **HEC-HMS** is the Hydrologic Modeling System (numerical simulation engine), whereas **HEC-DSS** is the Data Storage System (binary record database file container). Never confuse the two in code or docs.
2. **Never Commit State to Git**: The legacy system committed JSON files to GitHub. In this production system, all simulation runs and metrics persist in local **PostgreSQL 16**.
3. **Failsafe Weather**: Weather ingestion must strictly follow the 3 tiers:
   - Tier 1: Live Open-Meteo IFS 90h API with exponential backoff.
   - Tier 2: Cached predecessor forecast cycle shifted 6 hours forward with tail decay.
   - Tier 3: Calibrated IMD historical monsoon climatology baseline.
4. **Resilient DB Buffering**: When PostgreSQL is restarting or unavailable, write operations must buffer to `data/staging/pending_commits/` via `backend.db.resilient_pool.stage_transaction()` and auto-replay upon reconnection.
5. **Idempotent Step Execution**: In `backend.services.pipeline_worker`, always check `pipeline_step_log` before executing a step. If a step succeeded, skip it unless explicitly forced.
6. **Strict Light Theme**: All UI components must use white cards, slate-50 backgrounds, and crisp borders. Never introduce dark backgrounds.
7. **Port Isolation**: Port 3000 is for the Public Portal; Port 3001 is for the internal Operator Console; Port 8000 is FastAPI; Port 5432 is PostgreSQL.
```

---

## 🛠️ Verification Checklist for Developer
- [x] Pre-flight diagnostics passing (`.\windows\system_diag.ps1`) -> 22 Passed, 0 Failed.
- [x] Database schemas and seeds verified (`database/schema.sql`, `seeds.sql`, `admin_users.sql`).
- [x] All failsafe unit tests passing (`python -m pytest tests/test_weather_failsafe.py tests/test_db_resilience.py tests/test_pipeline_worker.py -v`).
- [x] Windows PowerShell administrative suite tested and ready.
- [x] Stale Vercel, Supabase, mkdocs, and GitHub Actions files removed.
- [x] Frontend Public Portal trimmed to 5 items; Operator Console equipped with full mission control.

