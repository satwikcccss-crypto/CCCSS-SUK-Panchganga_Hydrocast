# HydroCast — Real-Time Operational Flood Forecasting & Basin Intelligence

> **Panchganga River Catchment** · Kolhapur District, Maharashtra, India  
> **Real-time rainfall-runoff · Hydraulic rating · IoT telemetry · 90-hour predictive flood intelligence**

```
 

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

## System Architecture — Archify Overview

The full system topology, process map, 12-step pipeline, hydrologic engine, hydraulic rating, ML recalibration loop, database schema, deployment topology, and security model are documented in **Archify style** (layered ASCII cells, left→right flow):

📖 [`ARCHITECTURE.md`](ARCHITECTURE.md) — master system topology & process map  
📖 [`docs/architecture-atlas.md`](docs/architecture-atlas.md) — annotated engineering diagrams  
📖 [`docs/architecture.md`](docs/architecture.md) — layer contracts, WRD datums, parameters  
📖 [`docs/index.md`](docs/index.md) — documentation library navigation

---

## Quickstart

### Prerequisites

* Python 3.10+ (64-bit)
* Node.js 18+ and npm
* Git
* (Optional) Docker & Docker Compose

### 1. Clone & create environment

```bash
git clone https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast.git
cd CCCSS-SUK-Panchganga_Hydrocast
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env: POSTGRES_PASSWORD, API_KEY, JWT_SECRET, ADMIN_PASSWORD, TELEGRAM_BOT_TOKEN
```

### 3. Run the backend

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Run a forecast cycle

```bash
python -m src.orchestrator          # current UTC 6-hour slot
python -m src.orchestrator --date 20260903 --hour 6
```

### 5. Run the frontend

```bash
cd frontend
npm install
npm run dev                         # http://localhost:3000
```

### 6. Run tests

```bash
pytest tests -q                     # 154 tests
cd frontend && npx tsc --noEmit     # 0 TypeScript errors
```

---

## Production Deployment

```bash
docker compose up -d --build
```

| Service | Port |
|:---|:---|
| `hydrocast-db` (Postgres 15 + PostGIS) | 5432 |
| `hydrocast-backend` (FastAPI) | 8000 |
| `hydrocast-frontend` (Next.js 14) | 3000 |
| `hydrocast-docs` (MkDocs, opt-in) | 8001 |
| `hydrocast-dev` (JupyterLab, opt-in) | 8888 |

---

## Interactive Diagrams

The `docs/diagrams/` directory contains 12 interactive HTML simulators (animated flowcharts, sequence diagrams, ERD, lifecycle state machines) that render in the browser:

| # | Console | Focus |
|:---|:---|:---|
| 01 | End-to-End Architecture | 7-stage system topology & boundaries |
| 02 | Precipitation & Telemetry Flow | NWP grids, radar & ingestion QC |
| 03 | Forecast Cycle Workflow | 12-step automation engine & state transitions |
| 04 | API Gateway & Auth Sequence | Security handshake, JWT & Master Keys |
| 05 | Simulation Run Lifecycle | Run verification horizon & state machine |
| 06 | Hybrid OS Deployment | Linux Docker vs Windows HEC-RAS host |
| 07 | HydroSim 2D Handoff | Boundary conditions & HEC-RAS inflow |
| 08 | Hydraulic Rating Simulator | Rajaram cross-section & PCHIP spline curve |
| 09 | Rain Gauge Network Flowchart | Spatial selection, QC gate & Thiessen weights |
| 10 | Hydrology Catchment Solver | SCS-CN runoff & Muskingum routing engine |
| 11 | Relational Schema ERD | PostgreSQL 15, PostGIS 3.4 & TimescaleDB |
| 12 | Radar Telemetry Pipeline | Ultrasonic sensor ingestion & stage conversion |

---

## License & Attribution

Released for **academic research use**. Funded by **DST-SERB, Government of India**.

Developed by **Er. Satwik Udupi** · Centre for Climate Change and Sustainability Studies, Shivaji University Kolhapur.

See [`LICENSE`](LICENSE) for full terms.
