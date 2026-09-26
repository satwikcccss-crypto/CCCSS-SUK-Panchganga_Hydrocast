# Panchganga HydroCast: AI-Driven Basin Flood Intelligence System

<div align="center">

```
====================================================================================================
  ██╗  ██╗██╗   ██╗██████╗ ██████╗  ██████╗  ██████╗ █████╗ ███████╗████████╗
  ██║  ██║╚██╗ ██╔╝██╔══██╗██╔══██╗██╔═══██╗██╔════╝██╔══██╗██╔════╝╚══██╔══╝
  ███████║ ╚████╔╝ ██║  ██║██████╔╝██║   ██║██║     ███████║███████╗   ██║   
  ██╔══██║  ╚██╔╝  ██║  ██║██╔══██╗██║   ██║██║     ██╔══██║╚════██║   ██║   
  ██║  ██║   ██║   ██████╔╝██║  ██║╚██████╔╝╚██████╗██║  ██║███████║   ██║   
  ╚═╝  ╚═╝   ╚═╝   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝   ╚═╝   
             PANCHGANGA BASIN OPERATIONAL FLOOD INTELLIGENCE (1,837 km²)
====================================================================================================
```

**An automated hydrological simulation, hydrodynamic rating, and disaster early warning system for the Panchganga River basin in Maharashtra, India.**

[![Next.js 14](https://img.shields.io/badge/Next.js-14.2.5-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)](https://python.org/)
[![HEC-HMS 4.13](https://img.shields.io/badge/USACE-HEC--HMS_4.13-005596?style=for-the-badge)](https://www.hec.usace.army.mil/software/hec-hms/)
[![PostgreSQL Supabase](https://img.shields.io/badge/Database-Supabase_PostgreSQL-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com/)
[![Apache Parquet](https://img.shields.io/badge/Cold_Storage-Apache_Parquet-50882C?style=for-the-badge&logo=apache)](https://parquet.apache.org/)
[![Telegram Bot](https://img.shields.io/badge/Alerts-Telegram_Bot-26A5E4?style=for-the-badge&logo=telegram)](https://telegram.org/)

</div>

---

## 1. System Capabilities & Engineering Highlights

- **Catchment Scale:** Models the entire **1,837.213 km² Panchganga River basin** up to the Rajaram K.T. Weir at Kolhapur across 9 delineated subbasins (S1 to S9).
- **Meteorological Ingestion:** Continuous 90-hour precipitation forecast from ECMWF IFS HRES (0.08° / 9km) across 18 geo-referenced gauge stations.
- **Hydrological Core:**
  - **Loss Method:** USDA SCS Curve Number with dynamic AMC-II / AMC-III saturation switching ($65\text{ mm}/90\text{h}$ threshold).
  - **Transform Method:** SCS Dimensionless Curvilinear Unit Hydrograph ($m=3.7$) normalized to $1.0\text{ mm}$ mass conservation.
  - **Channel Routing:** 5-Reach Muskingum channel routing network (R1 to R5) with internal adaptive sub-stepping for unconditional numerical stability.
  - **Baseflow Dynamics:** Barnes exponential baseflow recession ($k=0.002\text{ hr}^{-1}$) with minimum physical floor of $15.0\text{ m}^3/\text{s}$.
- **2D Surveyed Hydraulic Rating Curves:**
  - Integrated 108 surveyed coordinates at **Chhatrapati Shivaji Maharaj Bridge** (Chainage 6+257) and **Rajaram K.T. Weir** (Chainage 10+115).
  - **Divided Channel Method (DCM)**: Main channel $n_{\text{main}}=0.031$, agricultural sugarcane floodplains $n_{\text{flood}}=0.070$ (Krishna Basin Flood 2019 Vol. 1 report).
  - Upstream/downstream stage transfer via `infer_rajaram_stage_from_shivaji()`.
- **Adaptive Machine Learning Recalibration Engine:**
  - Real-time comparison against ThingSpeak Channel 3424513 ultrasonic sensor telemetry.
  - Bounded Scipy L-BFGS-B loss minimization tuning $\alpha_K$ (reach travel time), $\alpha_{\text{lag}}$ (subbasin lag), $\Delta CN$ (Curve Number), and $X$ (wedge storage).
  - Dual atomic synchronization of Python runtime and `Basin_1.basin` project file.
- **Data Storage & Archival Architecture:**
  - Supabase PostgreSQL single-tree schema.
  - Cold storage archival engine (`src/db/archive_runs.py`) migrating records older than 90 days into Snappy-compressed Apache Parquet partitions and pruning database tables.
- **Government Emergency Alerting & Disaster Dispatch:**
  - Interactive Telegram Bot (`/status`, `/stage`, `/alerts`, `/bulletin`) via serverless Next.js webhook.
  - Automated HTML CWC flood bulletin cards pushed to District Disaster Management Authority (DDMA) and WRD officials.

---

## 2. Directory Layout

```
.
├── .github/workflows/          # Continuous 6-hourly automated CI/CD pipeline
├── database/                   # Supabase PostgreSQL schema (schema_v3, migrations)
├── docs/                       # Technical & Engineering-Grade Documentation Suite
│   ├── HMS.md                  # HEC-HMS 4.13 basin model & simulation engine
│   ├── Hydrology.md            # Basin physiography, HRUs, soils, 18-gauge network
│   ├── Runoff_Computation.md   # Excess rainfall derivation, SCS-UH convolution
│   ├── ML_Calibration_Engine.md# Real-time adaptive L-BFGS-B parameter tuning
│   ├── Calibration_Validation.md# Multi-tier validation (Spearman, NSE, RMSE, MAE)
│   ├── Accuracy_Analysis_PI_Report.md # Authoritative PI progress & accuracy report
│   ├── Stage_Conversion_Discharge.md # 2D DCM hydraulics & surveyed cross-sections
│   ├── Hydraulics.md           # Fluvial geomorphology & L-section slope profiles
│   ├── WRD_Historical_Rating_Curve_CrossCheck.md # 19 government benchmark registers
│   ├── Errors_Mistakes_Engineering_Assumptions.md # 10 engineering mistake resolutions
│   ├── Database.md             # Supabase schema & Parquet cold storage engine
│   ├── Frontend.md             # Next.js 14 App Router, design system, components
│   ├── Backend.md              # Python 3.12 architecture, orchestrator, APIs
│   └── IoT_Telemetry.md        # ThingSpeak ultrasonic sensor ingestion & QC
├── frontend/                   # Next.js 14 Enterprise Web Dashboard
│   ├── app/                    # App Router pages and serverless API webhooks
│   └── components/             # React visualizers (Overview, Accuracy, Runoff, System)
├── src/                        # Python Core Operational Engine
│   ├── alerts/                 # Telegram Bot dispatcher & CWC alert evaluator
│   ├── api/                    # FastAPI REST server & WebSocket live stream
│   ├── db/                     # Supabase connector, sync, and Parquet archival engine
│   ├── dss/                    # HEC-DSSVue binary time-series generator
│   ├── ecmwf/                  # Open-Meteo SDK 9km HRES IFS meteorological client
│   ├── hms/                    # Headless HEC-HMS 4.13 batch runner & Python emulator
│   ├── hydrology/              # 2D rating curves, ML calibration, accuracy metrics
│   └── sensors/                # ThingSpeak IoT ultrasonic level sensor client
├── ARCHITECTURE.md             # System-wide architectural topology specification
└── README.md                   # Repository overview and quickstart guide
```

---

## 3. Quick Start & Execution

### 3.1 Running the Hydrological Forecast Cycle
```bash
# Set up Python virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Run complete 12-stage operational forecast cycle
python -m src.orchestrator
```

### 3.2 Running Parquet Cold Storage Archival
```bash
# Archive time-series records older than 90 days to Apache Parquet
python -m src.db.archive_runs --retention-days 90
```

### 3.3 Running the Next.js Frontend
```bash
cd frontend
npm install
npm run dev
# Dashboard launches at http://localhost:3000
```
