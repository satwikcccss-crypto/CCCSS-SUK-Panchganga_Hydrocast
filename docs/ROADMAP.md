# HydroCast: Production Architecture Roadmap & Hardening Guide

## Executive Architecture Evaluation

HydroCast implements an end-to-end, operational hydrologic and hydraulic intelligence continuum:
1. **Meteorological Ingestion**: ECMWF IFS 0.25° quantitative precipitation forecasts via Open-Meteo API v1.
2. **Dynamic Station Selection**: Multi-gauge maximum-precipitation and centroid routing across 9 Panchganga subbasins.
3. **Hydrologic Watershed Simulation**: Loss modeling, Clark unit hydrograph transform, and Muskingum reach routing via HEC-HMS 4.x (with pure-Python SCS-CN fallback).
4. **Calibrated River Hydraulics**: Bi-directional monotonic PCHIP rating curves anchored to surveyed river bed slopes ($S_0 = 0.005858$ at Shivaji, $S_0 = 0.002318$ at Rajaram) and verified against Maharashtra WRD ground truth.
5. **Persistence & Presentation**: Resilient dual-layer persistence (immutable JSON multi-run ledger + Supabase/PostgreSQL) serving a Next.js 14 executive dashboard with live WebSocket broadcast.

To advance HydroCast from a **Functional Operational System** to an **Enterprise Mission-Critical Production Platform**, five architectural hardening pillars are defined below.

---

## The 5 Production Hardening Pillars (100% Open Source)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                    HYDROCAST ENTERPRISE PRODUCTION PILLARS                       │
├───────────────────┬───────────────────┬──────────────────┬───────────────────────┤
│ 1. Orchestration  │ 2. Real-Time Alert│ 3. Docker        │ 4. Archival & Security│
│    & Scheduling   │    & Telegram Bot │    Containers    │    Rate-Limiting      │
└───────────────────┴───────────────────┴──────────────────┴───────────────────────┘
```

### 1. Robust Orchestration & Fault-Tolerant Scheduling
- **Objective**: Prevent silent cycle skips caused by temporary API timeouts, network partitions, or compute crashes.
- **Implementation Options**:
  - **Option A (GitHub Actions Cron)**: Automated execution at 02:30, 08:30, 14:30, 20:30 UTC via `.github/workflows/pipeline.yml` with automated retry steps and centralized status alerts.
  - **Option B (Airflow / Systemd Timers)**: Deploy systemd timer units on Linux hosts or Apache Airflow DAGs with retry-on-failure (`retries=3, retry_delay=timedelta(minutes=5)`).
- **Milestones**:
  - [x] Implement 12-step transactional pipeline orchestrator (`src/orchestrator.py`).
  - [x] Configure GitHub Actions 6-hourly automated workflow.
  - [ ] Add exponential backoff retry wrappers around external weather ingestion.

### 2. Automated Multi-Channel Emergency Alerting
- **Objective**: Push immediate warning and evacuation bulletins when predicted stages breach Warning or Danger thresholds.
- **Implementation**:
  - **Telegram Bot API**: Free, zero-infrastructure messaging using `python-telegram-bot` (`src/alerts/evaluator.py`).
  - **FastAPI Webhooks**: Broadcast CWC alert events to disaster management agency dispatch endpoints.
- **Milestones**:
  - [x] Threshold evaluation engine (`src/alerts/evaluator.py`) with CWC warning tiers.
  - [x] WebSocket live push stream (`/ws/live`) to dashboard.
  - [ ] Implement production Telegram bot dispatcher for District Disaster Management Authority (DDMA).

### 3. Containerization (Docker & Compose)
- **Objective**: Package Python 3.12, Java JDK 17 (for HEC-DSS / HEC-HMS), GDAL, and Next.js into standardized images to ensure complete reproducibility across any cloud VM or on-premise workstation.
- **Architecture**:
  - `docker-compose.yml` defining:
    1. `hydrocast-backend`: FastAPI + HEC-DSS runtime with Python & Java.
    2. `hydrocast-frontend`: Node.js 18 Next.js production SSR container.
    3. `hydrocast-db`: Local PostgreSQL 15 + PostGIS container (for offline air-gapped deployments).
- **Milestones**:
  - [ ] Author multi-stage `Dockerfile` for backend with OpenJDK 17 + GDAL.
  - [ ] Author standalone `Dockerfile` for Next.js frontend.
  - [ ] Provide unified `docker-compose.yml` for 1-command startup.

### 4. Cold Storage & Telemetry Archival Strategy
- **Objective**: Keep the primary Supabase/PostgreSQL database responsive by pruning high-frequency time-series older than 90 days into compressed parquet archives.
- **Strategy**:
  - Maintain summary KPIs in `simulation_runs` indefinitely.
  - Export granular 15-minute `hydrograph_results` and `rainfall_data` older than 30-90 days into Apache Parquet files stored in MinIO (self-hosted S3) or Cloud Storage.
- **Milestones**:
  - [ ] Build automated weekly archival script (`src/db/archive_runs.py`).
  - [ ] Integrate Apache Parquet columnar compression for historical hydrographs.

### 5. API Security, JWT Authentication & Rate Limiting
- **Objective**: Protect operational endpoints against scrapers, DDoS attacks, and unauthorized database writes.
- **Strategy**:
  - Standardize API key validation via `X-API-Key` headers on administrative endpoints.
  - Implement IP-based rate-limiting using `slowapi` on public FastAPI endpoints.
  - Implement JWT authentication for administrative manual run triggering.
- **Milestones**:
  - [x] Internal authorization header check for broadcast endpoints.
  - [ ] Enforce rate limits (100 req/min) on `/api/v1/runoff/*` endpoints.

---

## Implementation Progress Tracker

| Milestone | Area | Status | Target File |
| :--- | :--- | :---: | :--- |
| Dynamic 18-Station Selection | Hydrology | Completed | `src/ecmwf/station_selector.py` |
| Monotonic PCHIP Rating Curves | Hydraulics | Completed | `src/hydrology/stage_converter.py` |
| WRD Ground Truth Verification | Accuracy | Completed | `docs/WRD_Historical_Rating_Curve_CrossCheck.md` |
| Observed Rainfall Pipeline | QC / Ingestion | Completed | `src/hydrology/observed_rainfall_pipeline.py` |
| Pipeline Orchestrator | Execution | Completed | `src/orchestrator.py` |
| Next.js Operational Dashboard | Presentation | Completed | `frontend/app/dashboard/page.tsx` |
| Docker Multi-Container Compose | Operations | Planned | `docker-compose.yml` |
| Weekly Parquet Data Pruning | Database | Planned | `src/db/archive_runs.py` |
