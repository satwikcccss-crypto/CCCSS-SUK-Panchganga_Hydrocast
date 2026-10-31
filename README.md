<p align="center">
  <img src="docs/assets/hydrocast_main_banner.jpg" alt="HydroCast Operational Flood Forecasting System Banner" width="100%">
</p>

# HydroCast — Real-Time Operational Flood Forecasting & Basin Intelligence

> **Panchganga River Catchment** · Kolhapur District, Maharashtra, India  
> **Physics-Based Rainfall-Runoff · Monotonic Hydraulic Rating · IoT Telemetry · 90-Hour Predictive Flood Intelligence**

---

<p align="center">
  <!-- Operational Status -->
  <a href="https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/">
    <img src="https://img.shields.io/badge/Documentation-GitHub_Pages_Portal-06B6D4?style=for-the-badge&logo=googledocs&logoColor=white" alt="Live Documentation Portal">
  </a>
  <a href="https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/actions/workflows/tests.yml">
    <img src="https://img.shields.io/badge/Unit_%26_Integration_Tests-284_Backend_%2B_3_Postgres-22C55E?style=for-the-badge&logo=pytest&logoColor=white" alt="Tests Status">
  </a>
  <a href="https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/actions/workflows/pipeline.yml">
    <img src="https://img.shields.io/badge/Operational_Pipeline-6--Hour_Cycles-3B82F6?style=for-the-badge&logo=githubactions&logoColor=white" alt="Forecast Pipeline Status">
  </a>
  <a href="https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-Academic_Research-8B5CF6?style=for-the-badge" alt="License">
  </a>
</p>

<p align="center">
  <!-- Technology Stack -->
  <img src="https://img.shields.io/badge/Python-3.10_|_3.11_|_3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Next.js-14_(App_Router)-000000?style=flat-square&logo=nextdotjs&logoColor=white" alt="Next.js 14">
  <img src="https://img.shields.io/badge/PostgreSQL-15_+_PostGIS_3.4-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/HEC--HMS-4.x_Emulation-E02424?style=flat-square" alt="HEC-HMS Engine">
  <img src="https://img.shields.io/badge/NWP-ECMWF_IFS_HRES_(9km)-1E3A8A?style=flat-square" alt="ECMWF IFS">
  <img src="https://img.shields.io/badge/IoT-ThingSpeak_Ultrasonic-FF6B6B?style=flat-square" alt="ThingSpeak IoT">
  <img src="https://img.shields.io/badge/Docker-Multi--Stage-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
</p>

---

## Executive Overview

**HydroCast** is a mission-critical, operational hydrologic and hydraulic flood early-warning platform engineered specifically for the **1,837.213 km² Panchganga River Basin** in Western Maharashtra, India.

During the Southwest Monsoon (June–September), torrential orographic precipitation along the Western Ghats crest (Sahyadri ridge, regularly recording **100–250+ mm/day**) funnels through nine steep basaltic headwater subcatchments directly into the urban river corridor of **Kolhapur City**. Catastrophic inundations in **August 2019** and **July 2021** submerged large sections of the district and demonstrated that civic agencies require **48 to 72 hours of validated predictive lead time** to orchestrate flood defenses, operate reservoir gates, and evacuate floodplains.

HydroCast achieves this by coupling:
1. **High-Resolution NWP Forcing**: 90-hour Quantitative Precipitation Forecasts (QPF) from ECMWF IFS HRES (0.1° / ~9 km) with automated spatial centroid mapping and exponential backoff retry policies.
2. **Deterministic Hydrologic Continuum**: Continuous basin-wide runoff routing using SCS-CN infiltration loss, SCS Dimensionless Unit Hydrograph transforms, and Muskingum-Cunge channel routing ($R1 \rightarrow R5$) across 9 subbasins. Runs seamlessly via HEC-HMS 4.x or an automated zero-dependency vectorized Python engine.
3. **Monotonic Hydraulic Rating Engine**: Government Water Resources Department (WRD) cross-section surveys converted into monotonic piecewise cubic Hermite (PCHIP) rating curves for Rajaram Weir and Shivaji Bridge with precise datum correction.
4. **Adaptive ML Telemetry Recalibration**: Continuous error-residual tracking against live ultrasonic water level sensors (ThingSpeak IoT channel 3424513). Discrepancies automatically trigger bounded L-BFGS-B parameter optimization ($\alpha_K, \alpha_{\text{lag}}, \Delta CN, X$) with atomic write-backs to project basin definitions.
5. **Decisive Multi-Channel Alerting**: Direct generation of Central Water Commission (CWC) compliant flood bulletins pushed via WebSocket to operational dashboards and dispatched directly to District Disaster Management Authority (DDMA) Telegram emergency channels.

---

## Core System Architecture

HydroCast follows a strict **6-Layer Decoupled Architecture** ensuring that data ingestion, physical computation, state persistence, and web delivery remain isolated and fault-tolerant:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   HYDROCAST OPERATIONAL SYSTEM CONTINUUM                              │
└────────────────────────────────────────────────────────────────────────────────────────┘

  [ LAYER 0: EXTERNAL FORCINGS & TELEMETRY ]
    │  • ECMWF IFS HRES 90-h QPF (Open-Meteo REST API, 0.1° spatial resolution)
    │  • IoT Ultrasonic Stage Telemetry (ThingSpeak Ch. 3424513 @ Shivaji Bridge)
    ▼
  [ LAYER 1: INGESTION, SPATIAL MAPPING & QC ]
    │  • Subbasin spatial station mapping (Argmax volume & Thiessen polygon weighting)
    │  • Missing data imputation, range sanity checks & HEC-DSS rainfall tables
    ▼
  [ LAYER 2: HYDROLOGIC CONTINUUM & CHANNEL ROUTING ]
    │  • SCS-CN Infiltration Loss Engine ($S = 25.4 \times (1000/CN - 10)$)
    │  • SCS Dimensionless Unit Hydrograph runoff transforms across 9 subbasins
    │  • Muskingum-Cunge Reach Routing ($R1 \rightarrow R5$) to Rajaram & Shivaji sinks
    ▼
  [ LAYER 3: HYDRAULIC RATING & WRD DATUM ALIGNMENT ]
    │  • Strictly Monotonic PCHIP Spline Interpolation ($dQ/dh > 0$)
    │  • Exact WRD survey cross-sections (Rajaram Weir datum vs Shivaji Bridge $-0.648$ m shift)
    │  • CWC Alert Categorization: NORMAL · ALERT (542.7m) · WARNING (543.3m) · DANGER (545.3m)
    ▼
  [ LAYER 4: IOT SENSOR QC & ADAPTIVE ML RECALIBRATION ]
    │  • Real-time timing ($\Delta t$) & stage ($\Delta h$) discrepancy detector
    │  • Bounded L-BFGS-B optimization of ($\alpha_K, \alpha_{\text{lag}}, \Delta CN, X$)
    │  • Atomic parameter update to `Basin_1.basin` with baseline snapshot protection
    ▼
  [ LAYER 5: ENTERPRISE PERSISTENCE & COLD STORAGE ]
    │  • Relational Store: PostgreSQL 15 + PostGIS 3.4 (Supabase cloud sync)
    │  • 90-day cold-storage pruning into Snappy-compressed Apache Parquet archives
    ▼
  [ LAYER 6: API GATEWAY, REAL-TIME PUSH & DASHBOARD ]
    │  • FastAPI Enterprise REST Engine (:8000) with HMAC-SHA256 JWT & API-Key Auth
    │  • WebSocket push broadcasting live 90-hour hydrographs to Next.js 14 Dashboard
    │  • Automated CWC/DDMA Emergency Telegram Bulletins
```

For complete technical specifications, mathematical equations, and layer interfaces, refer to the master architecture document:
👉 **[`ARCHITECTURE.md`](ARCHITECTURE.md)**

---

## Catchment Hydrology & Subbasin Parameters

The Panchganga basin is segmented into **nine primary hydrological subbasins** draining through five interconnected reaches:

| Subbasin Code | Subbasin Name | Drainage Area ($km^2$) | Initial Curve Number ($CN$) | Basin Lag Time ($min$) | Primary Rain Station |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **S1** | Karveer | 86.21 | 74.85 | 2,151.96 | Karveer |
| **S2** | Sangarul | 153.77 | 65.74 | 3,154.25 | Sangarul |
| **S3** | Kotoli | 261.32 | 64.82 | 3,997.70 | Kotoli |
| **S4** | Karanjphen | 262.00 | 61.89 | 3,115.51 | Karanjphen |
| **S5** | Padasali | 106.39 | 60.97 | 2,117.09 | Gaganbawda |
| **S6** | Gaganbawda | 227.72 | 61.78 | 3,318.07 | Gaganbawda |
| **S7** | Garivade | 195.39 | 61.28 | 3,362.27 | Radhanagari |
| **S8** | Beed | 177.44 | 65.76 | 3,387.15 | Beed |
| **S9** | Radhanagari | 366.97 | 64.31 | 5,199.04 | Radhanagari |
| **TOTAL** | **Modeled Catchment** | **1,837.21 $km^2$** | *Weighted Avg* | — | **5 Core Gauges** |

### Channel Reach Routing Network
- **R1** (Kasari Upper): $K = 2.899\text{ h}, X = 0.20$
- **R2** (Kasari Lower to Shivaji): $K = 11.827\text{ h}, X = 0.20$
- **R3** (Kumbhi Reach): $K = 3.829\text{ h}, X = 0.20$
- **R4** (Bhogawati Reach): $K = 1.224\text{ h}, X = 0.20$
- **R5** (Panchganga Trunk to Rajaram): $K = 4.619\text{ h}, X = 0.20$

---

## Key Capabilities & Production Engineering

| Domain | Engineering Implementation |
| :--- | :--- |
| **Numerical Weather Prediction** | Automated ECMWF IFS HRES (0.1° / 9 km) QPF retrieval. Runs every 6 hours with exponential backoff, jitter, and automated station selection based on 90-hour precipitation volume. |
| **Hydrological Emulation** | 100% pure-Python vectorized hydrology solver that precisely mirrors US Army Corps of Engineers HEC-HMS 4.x calculations, enabling headless execution inside lightweight Linux Docker containers without GUI or X11 dependencies. |
| **Hydraulic Precision** | PCHIP monotonic spline rating curves calibrated against official WRD cross-sectional survey tables. Guarantees $dQ/dh > 0$ under all conditions, preventing unphysical oscillation or negative stage derivations. |
| **Closed-Loop Learning** | Bounded L-BFGS-B parameter calibrator continuously audits IoT ultrasonic stage readings. Automatically optimizes basin storage coefficients when sensor lag or stage error thresholds are crossed. |
| **High-Performance Persistence** | PostgreSQL 15 + PostGIS with async connection pooling. Automated 90-day pruning into Snappy-compressed Apache Parquet format ensures zero database degradation over decades of continuous operation. |
| **Robust Security** | Dual-tier authentication: HMAC-SHA256 JWT tokens for interactive frontend sessions, and Master API Key headers for headless cron orchestrators. Integrated IP-based sliding-window rate limiting (100 req/min). |

---

## Interactive Archify Architecture & Engineering Consoles

HydroCast includes **17 self-contained, interactive standalone HTML simulators** engineered with **Archify** (supporting dark/light theme switching, smooth pan/zoom, interactive node inspection, and vector SVG/image export). They are accessible both locally in [`docs/diagrams/`](docs/diagrams/) and live on the GitHub Pages documentation portal:

| # | Archify Interactive Console | Category | Live Web Console (GitHub Pages) | Local Source File |
| :---: | :--- | :---: | :---: | :---: |
| **01** | **End-to-End System Architecture** | Topology | [Launch Console 01 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/01-architecture.html) | [`01-architecture.html`](docs/diagrams/01-architecture.html) |
| **02** | **Precipitation & Telemetry Flow** | Dataflow | [Launch Console 02 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/02-dataflow.html) | [`02-dataflow.html`](docs/diagrams/02-dataflow.html) |
| **03** | **Forecast Cycle Workflow (12 Steps)** | State Machine | [Launch Console 03 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/03-forecast-workflow.html) | [`03-forecast-workflow.html`](docs/diagrams/03-forecast-workflow.html) |
| **04** | **API Gateway & Auth Sequence** | Security | [Launch Console 04 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/04-sequence-auth-api.html) | [`04-sequence-auth-api.html`](docs/diagrams/04-sequence-auth-api.html) |
| **05** | **Simulation Run Lifecycle** | State Machine | [Launch Console 05 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/05-lifecycle-runs.html) | [`05-lifecycle-runs.html`](docs/diagrams/05-lifecycle-runs.html) |
| **06** | **Hybrid OS Deployment (Docker/Win)** | Infrastructure | [Launch Console 06 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/06-deployment-docker-os.html) | [`06-deployment-docker-os.html`](docs/diagrams/06-deployment-docker-os.html) |
| **07** | **HydroSim 2D Handoff & Boundary Inflow**| Hydrodynamics | [Launch Console 07 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/07-workflow-hydrosim-handoff.html) | [`07-workflow-hydrosim-handoff.html`](docs/diagrams/07-workflow-hydrosim-handoff.html) |
| **08** | **Hydraulic Rating & PCHIP Splines** | Hydraulics | [Launch Console 08 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/08-rating-curve-hydraulics.html) | [`08-rating-curve-hydraulics.html`](docs/diagrams/08-rating-curve-hydraulics.html) |
| **09** | **Rain Gauge Network Flowchart** | Spatial QC | [Launch Console 09 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/09-raingauge-selection-flowchart.html) | [`09-raingauge-selection-flowchart.html`](docs/diagrams/09-raingauge-selection-flowchart.html) |
| **10** | **Catchment Hydrology Solver** | Hydrology | [Launch Console 10 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/10-catchment-hydrology-solver.html) | [`10-catchment-hydrology-solver.html`](docs/diagrams/10-catchment-hydrology-solver.html) |
| **11** | **Backend API Architecture & Routes** | Backend | [Launch Console 11 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/11-backend-api.html) | [`11-backend-api.html`](docs/diagrams/11-backend-api.html) |
| **12** | **Frontend Emergency Dashboard UI** | Frontend | [Launch Console 12 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/12-frontend-dashboard.html) | [`12-frontend-dashboard.html`](docs/diagrams/12-frontend-dashboard.html) |
| **13** | **Relational Schema & Database ERD** | Database | [Launch Console 13 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/13-database-schema.html) | [`13-database-schema.html`](docs/diagrams/13-database-schema.html) |
| **14** | **HEC-HMS Engine & Python Emulator** | Hydrology | [Launch Console 14 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/14-hec-hms-engine.html) | [`14-hec-hms-engine.html`](docs/diagrams/14-hec-hms-engine.html) |
| **15** | **Adaptive ML Recalibration Loop** | Machine Learning| [Launch Console 15 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/15-ml-calibration.html) | [`15-ml-calibration.html`](docs/diagrams/15-ml-calibration.html) |
| **16** | **Navigable Repository Tree & Assets** | Codebase | [Launch Console 16 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/16-repository-tree.html) | [`16-repository-tree.html`](docs/diagrams/16-repository-tree.html) |
| **17** | **90-Hour Cycle Waterfall Timeline** | Telemetry | [Launch Console 17 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/17-cycle-waterfall.html) | [`17-cycle-waterfall.html`](docs/diagrams/17-cycle-waterfall.html) |

---

## Clean Repository Structure

```
hydrocast_complete/
├── src/                               # Production source code
│   ├── orchestrator.py                # Master 12-step forecast cycle conductor
│   ├── alerts/                        # CWC alert evaluation & Telegram dispatcher
│   ├── api/                           # FastAPI REST endpoints, auth & WebSockets
│   ├── db/                            # PostgreSQL connection pool & Parquet archival
│   ├── dss/                           # HEC-DSS integration & rainfall formatters
│   ├── ecmwf/                         # ECMWF IFS QPF fetcher & exponential backoff
│   ├── hms/                           # HEC-HMS basin parser & pure-Python emulator
│   ├── hydrology/                     # PCHIP rating curves, ML calibration & metrics
│   ├── processing/                    # Hyetograph generators & spatial aggregators
│   └── sensors/                       # ThingSpeak ultrasonic telemetry ingestion & QC
├── frontend/                          # Next.js 14 web application & dashboard
│   ├── app/                           # App router pages, layouts & API handlers
│   ├── components/                    # Leaflet GIS map, SVG cross-sections, hydrographs
│   └── lib/                           # WebSocket client, API fetchers & alert stores
├── docs/                              # Comprehensive documentation library
│   ├── diagrams/                      # 17 interactive standalone HTML architecture consoles
│   ├── reports/                       # Formal technical and methodology reports
│   └── api-reference/                 # Auto-generated API documentation
├── database/                          # Database definitions & Supabase SQL schemas
├── windows/                           # Native Windows PostgreSQL & storage automation
├── data/                              # Catchment GIS shapefiles, station metadata & HMS models
├── tests/                             # Comprehensive test suite (284 backend + 3 Postgres integration tests in CI)
├── archive/                           # Archived experimental & exploratory scripts
├── Dockerfile                         # Production multi-stage Docker build
├── docker-compose.yml                 # Multi-container orchestration (DB, API, UI, Docs)
├── mkdocs.yml                         # MkDocs Material configuration
└── requirements.txt                   # Production Python dependencies
```

---

## Quickstart Guide

### Prerequisites
- **Python**: 3.10, 3.11, or 3.12 (64-bit)
- **Node.js**: 18.0+ and npm
- **Git**
- *(Optional)* **Docker & Docker Compose** for containerized execution

### 1. Clone & Set Up Python Environment
```bash
git clone https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast.git
cd CCCSS-SUK-Panchganga_Hydrocast

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
# Configure your database credentials, API keys, and Telegram tokens in .env
```

### 3. Run a Forecast Simulation Cycle
```bash
# Execute the automated 12-step pipeline for the current 6-hour cycle
python -m src.orchestrator

# Or run for a specific historical monsoon event
python -m src.orchestrator --date 20260903 --hour 6
```

### 4. Launch the Backend API Server
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
# Interactive Swagger documentation: http://localhost:8000/docs
```

### 5. Launch the Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
# Access the live operational dashboard: http://localhost:3000
```

### 6. Run the Test Suite
```bash
# Execute all 284 backend tests (the 3 Postgres integration tests run in CI)
pytest tests -q

# Run TypeScript validation on the frontend
cd frontend && npx tsc --noEmit
```

---

## Production Containerized Deployment

Deploy the entire stack with a single command via Docker Compose:

```bash
docker compose up -d --build
```

### Service Map
| Container Service | Internal Port | Host Port | Purpose |
| :--- | :---: | :---: | :--- |
| `hydrocast-db` | 5432 | 5432 | PostgreSQL 15 + PostGIS 3.4 spatial database |
| `hydrocast-backend` | 8000 | 8000 | FastAPI REST engine & WebSocket broadcaster |
| `hydrocast-frontend` | 3000 | 3000 | Next.js 14 operational emergency dashboard |
| `hydrocast-docs` *(profile: docs)* | 8000 | 8001 | MkDocs Material live technical documentation |
| `hydrocast-dev` *(profile: dev)* | 8888 | 8888 | JupyterLab analytical environment |

---

## Research Attribution & Governance

HydroCast was developed at the **Centre for Climate Change and Sustainability Studies (CCCSS)**, **Shivaji University, Kolhapur (SUK)**.

- **Principal Investigator / Lead Engineer**: Er. Satwik Udupi
- **Research Sponsorship**: Supported by the **Department of Science & Technology (DST-SERB)**, Government of India.
- **Institutional Partner**: Irrigation Department / Water Resources Department (WRD), Government of Maharashtra.

### Terms of Use
Released for **academic research, disaster resilience, and civic governance**. See [`LICENSE`](LICENSE) for complete terms.
