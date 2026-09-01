# HydroCast — Rainfall-Runoff Prediction System
## Architecture v2.0

---

## Technology Stack

| Layer | Technology | Reason |
|---|---|---|
| NWP Data | ECMWF IFS (ecmwf-opendata / MARS API) | Free open data at 0.25°; MARS for true 9km |
| Data processing | Python 3.11, NumPy, xarray, cfgrib | GRIB2 decode, array ops, interpolation |
| DSS I/O | pydsstools | Python wrapper for HEC-DSS binary format |
| HMS automation | HEC-HMS 4.11 headless + Jython script | Batch compute, no GUI needed |
| Result extraction | pydsstools | Read HMS output DSS |
| Stage conversion | Python + NumPy (Manning's eq.) | From surveyed cross-section → H vs Q |
| Database | PostgreSQL 16 + TimescaleDB + PostGIS | Time-series + spatial, hypertables |
| API backend | FastAPI + asyncpg + uvicorn | Async, fast, auto OpenAPI docs |
| Dashboard | Next.js 14 (App Router) + Leaflet.js | SSR, fast routing, real-time map |
| Charts | Chart.js or Recharts | Hyetograph, hydrograph, stage plots |
| Real-time | WebSocket (FastAPI + Next.js) | Push on cycle completion |
| CI/CD | GitHub Actions | Free automation, cron triggers |
| Hosting (DB) | Supabase (free) or self-hosted Postgres | PostGIS + TimescaleDB |
| Hosting (API) | Railway.app (~$5/mo) or Fly.io | Always-on FastAPI |
| Hosting (UI) | Vercel (free) | Next.js, global CDN |
| HMS compute | Self-hosted Windows runner | HEC-HMS needs Windows/Linux install |
| Alerts | Telegram Bot + email (smtplib) | Free, instant |

---

## Complete Pipeline (12 steps)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  GITHUB ACTIONS (Ubuntu)                                                 │
│                                                                          │
│  Step 1: ECMWF IFS Download                                             │
│    ecmwf-opendata client → GRIB2 → de-accumulate TP → hourly mm/hr NC  │
│    Bbox crop to catchment | 0.25° or 9km (MARS) | 90 lead hours         │
│                                                                          │
│  Step 2: Gauge Station Fetch                                             │
│    IoT API → 90-hr observed hyetograph per station → Postgres insert     │
│    Sources: CWC network, IMD ARG, own IoT gauges                        │
│                                                                          │
│  Step 3: Data Validation                                                 │
│    Range check | QC flag | lag check | missing-data flag               │
│                                                                          │
│  Step 4: Station Selection (per subbasin, dynamic)                      │
│    For each subbasin (SUB_01..SUB_N):                                   │
│      candidates = {station → 90hr cumulative rainfall}                  │
│      selected  = argmax(cumulative)                                     │
│    Stored in: station_selection_log                                      │
│                                                                          │
│  Step 5: DSS Write                                                       │
│    pydsstools → rainfall_input.dss                                       │
│    Pathname: /GODAVARI/<SUB_ID>/PRECIP-INC/<DATE>/1HOUR/ECMWF-GAUGE/   │
│    One record per subbasin, 90 values                                    │
└──────────────────────┬──────────────────────────────────────────────────┘
                       │ artifact: rainfall_input.dss
                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  GITHUB ACTIONS (Self-Hosted Windows Runner — your Windows Server)       │
│                                                                          │
│  Step 6: HMS Parameter Check                                             │
│    Verify CN, Lag, K, X, Ia present in model_calibration                │
│    Warn if stale (> 365 days)                                            │
│                                                                          │
│  Step 7: HEC-HMS Execute                                                 │
│    Patch .control (start/end time, 60-min step)                         │
│    Patch .met (DSS pathname per subbasin)                               │
│    HEC-HMS.exe -Dstudy=project.hms -Dscript=autorun.jy -headless       │
│    Model: SCS-CN loss | Triangular UH | Muskingum routing               │
│    Output DSS: /GODAVARI/J_OUTLET/FLOW//1HOUR/<RUN>/                    │
└──────────────────────┬──────────────────────────────────────────────────┘
                       │ artifact: GodavariBasin.dss (output)
                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  GITHUB ACTIONS (Ubuntu)                                                 │
│                                                                          │
│  Step 8: Result Extraction                                               │
│    pydsstools reads J_Outlet FLOW time series (90 pts)                  │
│    → Peak Q, Time of Peak, Total Volume                                  │
│    → surface_runoff_m3s = Q_total - baseflow                            │
│                                                                          │
│  Step 9: Stage Conversion at Bridge Sites                               │
│    For each bridge (Shivaji Bridge, Rajaram Bridge):                    │
│      a) Apply travel time offset to outlet hydrograph                   │
│      b) Interpolate Q → H using pre-computed rating curve               │
│         (Manning's eq from surveyed XS: Easting/Northing/Elevation)     │
│      c) Classify per CWC: NORMAL|ALERT|WARNING|DANGER|HFL_EXCEEDED     │
│      d) Compute flood arrival time (first hour H > alert_stage_m)      │
│                                                                          │
│  Step 10: Postgres Write                                                 │
│    hydrograph_results     (90 rows per outlet per run)                  │
│    peak_discharge_events  (1 row per run)                               │
│    bridge_stage_forecast  (90 rows per bridge per run)                  │
│    runoff_summary         (1 row per run)                               │
│                                                                          │
│  Step 11: Alert Evaluation                                               │
│    Compare peak stage at each bridge against CWC thresholds             │
│    Trigger: alert_events INSERT                                          │
│    Notify: Telegram Bot, SMTP email                                     │
│                                                                          │
│  Step 12: Dashboard Broadcast                                            │
│    POST /internal/broadcast → WebSocket push to all connected clients   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Database Tables

```
gauge_stations           Station registry (PostGIS point)
rainfall_data            Observed gauge readings (TimescaleDB hypertable)
subbasin_rainfall_ts     Selected hyetograph per subbasin per cycle
station_selection_log    Audit: which station was selected + why
ecmwf_forecast           Raw ECMWF gridded data (TimescaleDB hypertable)
simulation_runs          HMS run metadata (status, duration)
hydrograph_results       90-hr Q at outlet (TimescaleDB hypertable)
peak_discharge_events    Peak Q, Tp, volume per run
runoff_summary           One-row summary per run
bridge_sites             CWC bridge gauge sites + alert thresholds
rating_curves            H vs Q table per bridge (from Manning's)
bridge_stage_forecast    90-hr stage forecast per bridge (TimescaleDB)
alert_events             Issued flood alerts
pipeline_step_log        Step-level status for each cycle
model_calibration        CN, Lag, K, X, Ia per subbasin
system_logs              Operational logs (TimescaleDB)
```

---

## Stage-Discharge Conversion

**Input**: `data/surveys/shivaji_bridge_xsection.csv`
```
easting,northing,elevation_m
512340.2,1955820.1,412.50
512351.4,1955825.3,409.20
...
```

**Process** (`src/hydrology/stage_converter.py`):
1. Sort by easting → lateral station distance via `hypot(dE, dN)`
2. For WSE = H + bed_elevation:
   - `A, P = wetted_area_and_perimeter(station, elev, WSE)`
   - `R = A / P`
   - `Q = (1/n) * A * R^(2/3) * S^(1/2)` (Manning)
3. Table: H=0.5m..HFL+2m at 0.1m steps → stored in `rating_curves`

**CWC Alert Classification**:
```
H < alert_stage_m    → NORMAL
H ≥ alert_stage_m    → ALERT     (caution, monitor)
H ≥ warning_stage_m  → WARNING   (alert agencies)
H ≥ danger_stage_m   → DANGER    (evacuate low-lying areas)
H ≥ hfl_m            → HFL_EXCEEDED (extreme)
```

Fill in for each bridge site:
| Site | Alert (m) | Warning (m) | Danger (m) | HFL (m) |
|---|---|---|---|---|
| Shivaji Bridge | 3.5 | 5.5 | 6.8 | 8.5 |
| Rajaram Bridge | 4.0 | 6.0 | 7.2 | 9.1 |

---

## Dashboard Sections (Next.js)

### Panel 1 — Rainfall Command Centre
- Leaflet map: subbasin polygons coloured by ECMWF mm/hr
- Rain gauge markers: click → popup hyetograph
- Hyetograph chart: selected station per subbasin (Bar chart, 90 bars, 1-hr)
- Table: station selection log — all candidates + selected + cumulative mm
- Metrics bar: last fetch time | data interval | events fetched | QC status

### Panel 2 — Runoff / Discharge / Flood Stage
- Area chart: 90-hr discharge hydrograph at J_Outlet
- Reference lines: WATCH 500 | WARNING 750 | EMERGENCY 1000 m³/s
- Stage gauge (animated SVG) + 90-hr stage line chart per bridge
- Bridge cards: Shivaji Bridge + Rajaram Bridge
  - Current stage | Alert level (colour-coded)
  - HFL margin
  - Flood arrival time
  - **FLOOD WARNING BANNER** when stage ≥ warning_stage_m

### Panel 3 — System / Pipeline Monitor
- 12-step pipeline grid with status badges
- Data source health: ECMWF | G001..G012 | GPM IMERG
- Cycle history bar chart (last 48 cycles, duration + fail/pass)
- Activity log (system_logs table, last 50 rows)
- Next cycle countdown timer

---

## Deployment (Free / Low-Cost)

### Now (no server)
```
GitHub Actions     → pipeline automation (free for public repos)
Supabase           → PostgreSQL + PostGIS (free 500MB)
                     TimescaleDB: use TimescaleDB Cloud free trial
                     OR self-host on Railway
Vercel             → Next.js dashboard (free)
Railway.app        → FastAPI backend ($5/mo hobby plan)
Self-hosted runner → install on any Windows machine with HMS
                     (even a VM, WSL2, or your laptop temporarily)
```

### Windows Server (future)
```
HMS                → runs natively on Windows Server
Self-hosted runner → GitHub Actions runner service on same machine
PostgreSQL         → install locally on Windows Server
FastAPI            → run as Windows service (NSSM)
Nginx              → reverse proxy for FastAPI + serve Next.js static build
```

### Quick start (Supabase + Vercel + Railway)
```bash
# 1. Database
# Sign up at supabase.com → new project → SQL Editor → paste schema_v3.sql
# Get connection string → set DATABASE_URL secret in GitHub

# 2. API
# railway.app → New Project → Deploy from GitHub → select /src/api
# Set env vars: DATABASE_URL, API_KEY, INTERNAL_KEY
# Get URL → set NEXT_PUBLIC_API_URL in Vercel

# 3. Dashboard
# vercel.com → Import GitHub repo → framework: Next.js
# Set NEXT_PUBLIC_API_URL, NEXT_PUBLIC_WS_URL

# 4. Self-hosted runner (Windows, for HMS)
# GitHub repo → Settings → Actions → Runners → New self-hosted runner
# Follow Windows install steps → installs as a service
# Set runner label: windows-hms
```

---

## Python Dependencies

```
# requirements.txt
ecmwf-opendata>=0.3
cfgrib>=0.9
xarray>=2024.1
numpy>=1.26
scipy>=1.12
pandas>=2.2
pydsstools>=0.3        # pip install pydsstools (requires Java JDK)
asyncpg>=0.29
fastapi>=0.111
uvicorn[standard]>=0.29
psycopg2-binary>=2.9
python-telegram-bot>=21
```

---

## HMS Project Files to Patch Each Cycle

```
GodavariBasin.hms       # main project file (do not edit)
GodavariBasin.control   # patch: start/end date, timestep
GodavariBasin.met       # patch: DSS pathname per subbasin gage
GodavariBasin.basin     # read-only: CN, Lag, K, X per subbasin
GodavariBasin.dss       # HMS writes output here → extract results
rainfall_input.dss      # you write: 90-hr hyetograph per subbasin
```

---

## Cross-Section Survey Format

Provide your survey data in this CSV format (one file per bridge):

```csv
easting,northing,elevation_m
512340.20,1955820.10,412.50
512351.40,1955825.30,409.20
512370.00,1955830.00,405.80
512400.00,1955832.00,403.10
512440.00,1955831.50,402.40
512480.00,1955831.00,402.50
512510.00,1955829.80,404.90
512530.00,1955826.50,408.70
512542.00,1955822.10,412.10
```

Points must be ordered left bank → right bank (ascending easting).
UTM Zone 43N (EPSG:32643) for Maharashtra.
The script converts E/N to lateral station distance, then applies Manning's.
