# 08 — Architecture

## Scope

This document describes the overall system architecture: how components connect, what each layer does, and the technology stack. Audience: **Maintainer**.

## Dual-Port Design

The system runs two independent FastAPI applications on separate ports, sharing a single PostgreSQL database:

```
                    ECMWF / Open-Meteo
                    (90-hr QPF)
                         |
                  Pipeline Worker
                  (12-step cycle)
                         |
              +----------+----------+
              |                     |
        Public API (:8000)    Admin API (:8001)
              |                     |
        Public Dashboard      Admin Console
        (:3000)               (:3001)
              |                     |
              +----------+----------+
                         |
                   PostgreSQL 16
                   + PostGIS (:5432)
```

### Why Two Ports

- **Security boundary**: Public API has no write endpoints. Admin API requires JWT on every route.
- **Independent CORS**: Each API has its own origin whitelist. Wildcard (`*`) causes `sys.exit(1)`.
- **Independent rate limits**: Public API is rate-limited per IP. Admin API has login-specific limits.
- **Deployment flexibility**: Can be behind separate reverse proxies or firewall rules.

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend Framework | FastAPI + Uvicorn | 0.115+ |
| Frontend Framework | Next.js (React) | 15.x |
| Language (Backend) | Python | 3.12 |
| Language (Frontend) | TypeScript | 5.x |
| Database | PostgreSQL + PostGIS | 16.x |
| IoT Platform | ThingSpeak (MathWorks) | REST API v2 |
| Weather Data | Open-Meteo ECMWF IFS | Free API |
| Authentication | JWT (HS256) + bcrypt (cost 12) | -- |
| Rate Limiting | slowapi (limits) | -- |
| Process Management | Windows Services (NSSM) | -- |
| OS | Windows Server / Windows 11 | -- |

## Component Map

### Backend Services

| Component | Entry Point | Port | Description |
|-----------|------------|------|-------------|
| Public API | `backend/api/main.py` | 8000 | Read-only forecast data for citizens |
| Admin API | `backend/api/admin_app.py` | 8001 | Operator control plane with JWT auth |
| Pipeline Worker | `backend/service/pipeline_worker.py` | -- | 12-step forecast cycle executor |
| Scheduler Daemon | `backend/service/scheduler_daemon.py` | -- | 6-hourly cycle scheduler |
| Orchestrator | `backend/service/orchestrator.py` | -- | Pipeline entry point and abort control |
| Watchdog | `backend/service/watchdog.py` | -- | Process health monitoring |

### Frontend Applications

| Component | Directory | Port | Description |
|-----------|----------|------|-------------|
| Public Dashboard | `frontend-public/` | 3000 | Citizen-facing flood dashboard |
| Admin Console | `frontend-admin/` | 3001 | Windows 11 Settings-style operator UI |

### Data Stores

| Store | Technology | Location | Description |
|-------|-----------|----------|-------------|
| Primary Database | PostgreSQL 16 + PostGIS | `E:\PostgreSQL\16` | All forecast data, users, audit logs |
| Local Cache | JSON files | `data/cache/` | Last-good rainfall, checkpoint state |
| Run Archive | JSON files | `data/runs/` | Historical cycle results |
| Logs | Text files | `data/logs/` | Orchestrator and pipeline logs |

## Pipeline Architecture (12-Step Cycle)

The forecast pipeline runs every 6 hours (00, 06, 12, 18 UTC):

| Step | Name | Module | Description |
|------|------|--------|-------------|
| 1 | Weather Download | `rainfall/open_meteo_failsafe.py` | 90-hr QPF with 3-tier failsafe |
| 2 | Gauge Station Fetch | `processing/gauge_fetcher.py` | Panchganga catchment network |
| 3 | Data Validation | `validation/` | Quality control and anomaly checks |
| 4 | Station Selection | `rainfall/station_selector.py` | Dynamic precipitation weighting |
| 5 | DSS Time-Series | `dss/writer.py` | HEC-DSS record authoring |
| 6 | HMS Basin Check | `hms/basin_parser.py` | Loss and routing verification |
| 7 | HMS/Twin Execution | `hms/runner.py` | HEC-HMS 4.13 or Python twin emulator |
| 8 | Result Extraction | `hms/runner.py` | Outlet hydrograph at Rajaram weir |
| 9 | Stage Conversion | `stage_conversion/` | PCHIP rating curves at both bridges |
| 10 | DB Persistence | `db/store_results.py` | PostgreSQL master ledger |
| 11 | Alert Evaluation | `alerts/evaluator.py` | CWC/WRD alert classification |
| 12 | Broadcast | `api/websocket_hub.py` | WebSocket push to dashboards |

### Checkpoint and Recovery

- Each step records a checkpoint. If step 7 crashes, re-running the cycle resumes from step 7.
- Single-step retry: operators can re-trigger an individual step from the console.
- Abort signal: safe mid-simulation termination via threading.Event.

## Communication Flows

### Dashboard Data Flow

```
PostgreSQL --> Public API (:8000) --> HTTP/JSON --> Public Dashboard (:3000)
                                 --> WebSocket  --> Live updates
```

### Admin Control Flow

```
Admin Console (:3001) --> HTTP/JWT --> Admin API (:8001) --> Pipeline Worker
                                                        --> PostgreSQL
                                                        --> ML Calibrator
```

### Telemetry Flow

```
IoT Sensor --> ThingSpeak Cloud --> Pipeline Worker (step 10 validation)
                               --> Public API /sensors/live endpoint
                               --> Admin Console gauges panel
```

## Source Files

| File | Purpose |
|------|---------|
| `backend/api/main.py` | Public API app |
| `backend/api/admin_app.py` | Admin API app |
| `backend/service/pipeline_worker.py` | 12-step pipeline |
| `backend/service/orchestrator.py` | Pipeline entry point |
| `backend/service/scheduler_daemon.py` | 6-hourly scheduler |
| `frontend-public/` | Public dashboard (Next.js) |
| `frontend-admin/` | Admin console (Next.js) |
