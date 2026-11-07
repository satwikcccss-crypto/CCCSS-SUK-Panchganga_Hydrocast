# HYDROCAST PANCHGANGA — ENTERPRISE OPERATOR & ENGINEERING MANUAL
### Production Deployment & Operating Standard for Windows Server Standard
**Centre for Climate Change and Smart Solutions (CCCSS), Shivaji University, Kolhapur (SUK)**  
*Document Version: 2.0-ENTERPRISE | Authored by Senior Technical Lead & Enterprise Systems Architect*

---

## 1. Executive Summary & Architecture Topology

HydroCast Panchganga is an autonomous, on-premises flood intelligence and 90-hour river forecasting platform engineered specifically for **Windows Server Standard** at Shivaji University, Kolhapur.

Unlike legacy prototypes that depended on cloud CI/CD runners (GitHub Actions) or external hosted proxies (Supabase / Vercel), this production release is **100% self-hosted, failsafe, and autonomous**. It operates directly on university infrastructure, backed by local PostgreSQL 16, supervised by a background watchdog daemon, and commanded via an isolated Operator Mission Control console.

```
                      +-------------------------------------------------------+
                      |         SHIVAJI UNIVERSITY WINDOWS SERVER             |
                      +-------------------------------------------------------+
                                                  |
                  +-------------------------------+-------------------------------+
                  |                                                               |
        [ Port 3000: PUBLIC PORTAL ]                                    [ Port 3001: OPERATOR CONSOLE ]
       Accessible to Citizens & Officials                              Campus Intranet / VPN Only (RBAC)
       - 1. Executive Dashboard                                         - 12-Step Pipeline Execution Matrix
       - 2. Meteorological Rainfall                                     - Single-Step Retry & Emergency Abort
       - 3. HEC-HMS Runoff & Bridge Stage                               - Real-Time Telemetry Validation Math
       - 4. System Health Indicator                                     - Physics-Informed ML Calibration
       - 5. Project Information (SUK / DST-SERB)                        - Historical Runs Ledger & Diagnostics
       * Strict Light UI Theme (No Dark Mode)                           - Live WebSocket Terminal Streamer
                  |                                                               |
                  +-------------------------------+-------------------------------+
                                                  |
                                       [ Port 8000: FASTAPI ]
                                REST API & WebSocket Streaming Hub
                                                  |
                         +------------------------+------------------------+
                         |                                                 |
             [ AUTONOMOUS 24/7 SCHEDULER ]                       [ WATCHDOG SUPERVISOR ]
             - 02:30, 08:30, 14:30, 20:30 UTC                    - Heartbeat monitor (15s probe)
             - Hourly Telemetry Sync (:05)                       - Hardware & DB health collector
             - Idempotent Checkpointing Worker                   - Auto-restart crashed processes
                         |                                                 |
                         +------------------------+------------------------+
                                                  |
                               +------------------+------------------+
                               |                                     |
               [ HYDROLOGICAL ENGINE LAYER ]                 [ RESILIENT DATA TIER ]
               - HEC-HMS 4.13 (Modeling System)              - PostgreSQL 16 + PostGIS (:5432)
               - HEC-DSS (Data Storage System)               - E:\pgdata Dedicated Tablespace
               - PCHIP Stage Rating Curves                   - Offline Disk-Backed Staging Buffer
               - 3-Tier Weather & Radar Failsafes            - Automated Daily Compressed Backups
```

### Fundamental Engineering Principle: HEC-HMS vs. HEC-DSS
* **HEC-HMS (Hydrologic Modeling System)**: The numerical watershed simulation engine developed by USACE. It solves the rainfall-runoff physics: SCS Curve Number loss calculations, SCS Unit Hydrographs for 9 subbasins, baseflow recession, and Muskingum channel routing. Located in `backend/hydrology/` and executed headlessly via batch Jython script `compute.jy`.
* **HEC-DSS (Data Storage System)**: The binary record-based database system developed by USACE specifically for water resources time-series data. It is the structured file container (`.dss`) that stores precipitation hyetographs and output hydrograph records. Located in `backend/dss/` and stored in `dss/HMS_Automation_RJKT/`.

---

## 2. Restructured Directory Layout

The codebase has been refactored into clean, single-responsibility enterprise domains:

```
E:\Hydrocast Windows Server\
├── backend/
│   ├── ml/                   # Machine learning calibration & parameter predictor
│   ├── hydrology/            # SCS-CN unit hydrograph, Muskingum routing, basin parser
│   ├── hydraulics/           # Manning equation, bridge rating curves, physics
│   ├── stage_conversion/     # PCHIP bridge stage conversion (Shivaji & Rajaram)
│   ├── rainfall/             # Open-Meteo IFS 90h, 3-tier failsafe, station selector
│   ├── dss/                  # HEC-DSS time-series record generation & catalog reader
│   ├── thingspeak/           # ThingSpeak radar telemetry, spike filtering & cache
│   ├── validation/           # Statistical metrics (RMSE, MAE, NSE, PBIAS, Spearman rho)
│   ├── api/                  # FastAPI endpoints, WebSocket hub, local RBAC auth
│   ├── services/             # 24/7 scheduler daemon, supervisory watchdog, worker
│   └── db/                   # Resilient connection pool, offline staging buffer
├── frontend-public/      # Standalone Next.js app for Port 3000 (Public Disaster Intelligence Portal)
│   ├── app/              # Clean public routes only (Dashboard, Rainfall, Runoff, System, Info)
│   ├── components/       # Public hydrograph and hyetograph charts
│   └── package.json      # "start": "next start -p 3000"
├── frontend-admin/       # Standalone Next.js app for Port 3001 (Operator Mission Control)
│   ├── app/              # Direct passwordless Mission Control on "/" (No login gate)
│   ├── components/       # HEC-RAS 2D cross-section, AccuracyPanel, ratings, dial gauges
│   └── package.json      # "start": "next start -p 3001"
├── database/
│   ├── schema.sql            # Clean PostgreSQL 16 + PostGIS production schema
│   ├── seeds.sql             # Panchganga subbasins (S1-S9), 20 stations, bridge datums
│   └── admin_users.sql       # Approved SUK official accounts & login audit table
├── windows/
│   ├── install_services.ps1  # NSSM Windows Service installer
│   ├── service_control.ps1   # Start / Stop / Restart / Status controller
│   ├── init_database.ps1     # Database and tablespace initializer
│   ├── backup_database.ps1   # Automated daily pg_dump + 30-day retention
│   ├── system_diag.ps1       # Pre-flight diagnostic checker
│   └── run_pipeline_manual.ps1 # Interactive CLI runner
├── dss/
│   └── HMS_Automation_RJKT/  # Official HEC-HMS 4.13 project (for GUI and batch)
├── data/
│   ├── inputs/               # Basin shapefiles, cross-sections, station tables
│   ├── telemetry/            # Radar cache, ML calibration state
│   ├── runs/                 # Output forecast run ledgers & hydrograph JSONs
│   ├── staging/              # Weather cache and pending commits buffer
│   └── logs/                 # Orchestrator, watchdog, and service logs
├── docs/                     # Technical specifications and research documentation
└── tests/                    # Automated pytest suite
```

---

## 3. Server Prerequisites & Specifications

| Resource | Specification | Notes |
| :--- | :--- | :--- |
| **Operating System** | Windows Server Standard (2019 / 2022 / 2025) | 64-bit required |
| **System Memory** | 16 GB RAM minimum (24+ GB recommended) | Memory allocated for GIS and routing |
| **Storage Architecture** | C:\ (OS & Binaries), E:\ (Data & Database) | E:\ stores hypertables and DSS runs |
| **Database Engine** | PostgreSQL 16.x x64 with PostGIS 3.4 | Port 5432, local bound |
| **Python Runtime** | Python 3.12.x 64-bit | In PATH, virtualenv recommended |
| **Node.js Runtime** | Node.js v18.x or v20.x LTS | Powers ports 3000 and 3001 |
| **Hydrologic Engine** | HEC-HMS 4.13 x64 | `C:\Program Files\HEC\HEC-HMS\4.13\HEC-HMS.exe` |

---

## 4. Step-by-Step Clean-Slate Build & Installation Runbook

Execute these steps in an elevated Administrator PowerShell prompt:

### Step 1: Run Pre-Flight Diagnostics
Validate that all system ports, runtimes, dependencies, and file permissions are ready:
```powershell
powershell -ExecutionPolicy Bypass -File .\windows\system_diag.ps1
```
*Verification criteria: Output must report `System status: READY FOR PRODUCTION`.*

### Step 2: Initialize PostgreSQL Database
Create the `rainfall_runoff` database, tables, spatial indexes, and approved accounts:
```powershell
powershell -ExecutionPolicy Bypass -File .\windows\init_database.ps1 -PgUser "postgres" -PgPassword "YourAdminPassword"
```
*Verification criteria: `[SUCCESS] PostgreSQL Database initialized and ready for production.`*

### Step 3: Build the Frontend Production Assets
Compile the Next.js production build:
```powershell
cd frontend
npm install
npm run build
cd ..
```

### Step 4: Register Windows Services (NSSM)
Install the backend, scheduler, watchdog, public portal, and operator console as native Windows Services:
```powershell
powershell -ExecutionPolicy Bypass -File .\windows\install_services.ps1
```
*Verification criteria: All 5 services registered with `SERVICE_AUTO_START` and failure restart actions.*

### Step 5: Launch and Verify Services
Start all registered services and inspect their status:
```powershell
powershell -ExecutionPolicy Bypass -File .\windows\service_control.ps1 -Action start
powershell -ExecutionPolicy Bypass -File .\windows\service_control.ps1 -Action status
```

### Step 6: Smoke-Test a Manual Forecast Cycle
Execute a test run directly from PowerShell to verify the entire 12-step pipeline:
```powershell
powershell -ExecutionPolicy Bypass -File .\windows\run_pipeline_manual.ps1
```

---

## 5. Enterprise Senior Tech Lead Guidelines: DOs and DONTs

### The STRICT DOs:
1. **DO rely on Idempotent Checkpointing**: If a forecast run is interrupted at Step 7, use `.\windows\run_pipeline_manual.ps1 -SingleStep 7` or click the step retry button in the Operator Console. The system automatically loads prior step outputs from cache without repeating work.
2. **DO verify Resilient DB Staging**: If PostgreSQL goes down for scheduled Windows maintenance, the backend queues all step outputs to `data/staging/pending_commits/` as JSON. Once PostgreSQL restarts, the scheduler automatically replays and commits all queued records.
3. **DO schedule Daily Backups**: Verify that `.\windows\backup_database.ps1` runs every morning at 03:00 UTC via Windows Task Scheduler. Check `E:\pgbackups\hydrocast\backup_audit.log` for valid SHA-256 hashes.
4. **DO keep the HEC-HMS Project in `dss/` Pristine**: You can open `dss/HMS_Automation_RJKT/HMS_Automation_RJKT.hms` directly in the official HEC-HMS 4.13 GUI at any time. The automation engine restores `Control_1.control` to pristine baseline upon run completion.
5. **DO enforce Strict Light Theme**: Academic, governmental, and engineering control rooms require high legibility under daylight and ambient office conditions. No dark backgrounds are permitted anywhere in the UI.

### The STRICT DONTs:
1. **DON'T commit generated JSON files to Git**: Never commit `data/runs/*.json` or telemetry files to source control. All state belongs strictly in the local PostgreSQL database.
2. **DON'T expose Port 3001 or Port 5432 to the Public Internet**: Port 3000 (Public Portal) can be exposed through the university reverse proxy (IIS / NGINX). Port 3001 (Operator Console) and Port 5432 (PostgreSQL) must remain strictly firewalled to localhost or campus VPN.
3. **DON'T delete or move files while HEC-HMS is computing**: HEC-HMS acquires OS locks on `Run_1.dss`. Bypassing or deleting file locks while `compute.jy` is executing will corrupt the binary DSS index.
4. **DON'T bypass the Resilient Pool**: Always acquire connections through `backend.db.resilient_pool.get_resilient_connection()`. Never open raw unpooled psycopg2 connections in long-running threads.
5. **DON'T edit `Basin_1.basin` with a plain text editor during live cycles**: If updating hydrological parameters manually, use the Machine Learning & Calibration panel in the Operator Console or run `backend.ml.ml_calibration` to ensure atomic `.bak` snapshots.

---

## 6. Multi-Tier Failsafe Architecture & Incident Response Protocols

The system incorporates five defensive layers against unexpected failures:

### Failsafe 1: Multi-Tier Weather Engine (`open_meteo_failsafe.py`)
* **Tier 1 (Live Primary)**: Queries Open-Meteo ECMWF IFS 90-hr hourly precipitation with exponential backoff (3 attempts with jitter).
* **Tier 2 (Predecessor Cache Extrapolation)**: If Tier 1 fails due to campus internet disruption or API downtime, the system retrieves the previous 6-hour forecast cycle from disk, shifts the lead window forward by 6 hours, extrapolates the tail with decay, and marks the cycle as `tier2_predecessor_extrapolated`.
* **Tier 3 (Climatological Monsoon Baseline)**: If both Tier 1 and Tier 2 fail (e.g. cold start in an isolated network), the system applies calibrated historical IMD monsoon curves for subbasins S1-S9, preventing cycle abortion.

### Failsafe 2: Telemetry Outlier Filter & Radar Degradation (`failsafe_telemetry.py`)
* Raw ultrasonic sensor pings from Shivaji Bridge (ThingSpeak Channel 3424513) are passed through rate-of-change and physical elevation filters (530m to 565m MSL).
* If the sensor is offline, submerged, or reporting noise, the validator switches to `degraded_fallback`, synthesizing stage from the Manning rating curve and alerting the operator without halting the pipeline.

### Failsafe 3: Database Resilience Buffer (`resilient_pool.py`)
* In the event of PostgreSQL service failure, connection drops, or disk full conditions, the pipeline steps serialize output tables to `data/staging/pending_commits/staged_*.json`.
* As soon as PostgreSQL connectivity is restored, `replay_staged_transactions()` automatically executes idempotent `INSERT ... ON CONFLICT DO NOTHING` statements.

### Failsafe 4: Supervisory Watchdog (`watchdog.py`)
* A dedicated supervisory daemon checks `data/health/scheduler_heartbeat.json` every 15 seconds. If the heartbeat is older than 45 seconds, the watchdog records a crash dump and restarts the scheduler process.

---

## 7. Operator Mission Control Runbook (Port 3001 — Direct Operator Access)

The dedicated Operator Console app (`frontend-admin/`) provides immediate, passwordless mission control on Port 3001 for Shivaji University operators across dedicated views (no login required on internal Windows Server):

1. **Control Room**:
   - Live 12-Step Hydrological Simulation Matrix.
   - Immediate actions: *Trigger Forecast Now*, *Emergency Abort*, *Backup DB*.
   - Individual *Retry Step* buttons for targeted re-computation.
   - Embedded real-time terminal streaming logs over WebSocket (`/ws/admin/logs`).
2. **Realtime Telemetry Validation**:
   - ThingSpeak ultrasonic radar ground truth comparison.
   - Mathematical accuracy metrics: Stage RMSE, Discharge RMSE, NSE, PBIAS, Spearman rho, and Pearson $R^2$.
3. **Machine Learning & Calibration**:
   - Dynamic parameter multipliers: $\alpha_K$, $\alpha_{\text{lag}}$, $\Delta CN$, and Muskingum $X$.
   - Automatic agreement synchronization with `Basin_1.basin`.
4. **Historical Run Ledger**:
   - Full computation run history table with peak discharge, stage, and accuracy metrics.
5. **Hardware & Engine Health**:
   - Live meters for CPU%, RAM%, Disk `E:\` capacity, DB connection pool health, and HEC-HMS 4.13 engine discovery.
6. **Station & Gauge Overrides**:
   - Operational toggles to enable or disable physical rain gauges during field outages.
7. **Security & Login Audit**:
   - Active SUK accounts and real-time login audit log (`admin_login_log`).

---

## 8. Disaster Recovery & Emergency SOP

### Scenario A: Scheduled Windows Server Maintenance / Reboot
No manual action required. All 5 services are registered with `SERVICE_AUTO_START` in NSSM. Upon server boot, the Watchdog, Scheduler, Backend, and Web Portals launch automatically within 30 seconds.

### Scenario B: Database Restoration from Backup
To restore the `rainfall_runoff` database from a compressed dump:
```powershell
$Psql = "C:\Program Files\PostgreSQL\16\bin\pg_restore.exe"
& $Psql -h 127.0.0.1 -p 5432 -U postgres -d rainfall_runoff --clean --if-exists "E:\pgbackups\hydrocast\hydrocast_rainfall_runoff_YYYYMMDD.dump"
```

### Scenario C: Emergency Pipeline Abort
If an errant forecast cycle was triggered with incorrect manual parameters:
1. Click **Emergency Abort** in the Operator Console, OR
2. In PowerShell, run:
```powershell
python -c "from backend.service.pipeline_worker import trigger_abort; trigger_abort()"
```

---
*Centre for Climate Change and Smart Solutions (CCCSS)*  
*Shivaji University, Kolhapur (SUK), Maharashtra, India*

