<p align="center">
  <img src="docs/assets/hydrocast_main_banner.jpg" alt="HydroCast Banner" width="100%" style="border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.15);">
</p>

<h1 align="center">🌊 HydroCast</h1>

<p align="center">
  <strong>The Open-Source Hydrologic Digital Twin & Real-Time Operational Flood Intelligence Platform</strong><br>
  <em>Engineered for the 1,837 km² Panchganga River Basin · Kolhapur, Maharashtra, India</em>
</p>

<p align="center">
  <a href="https://cccss-suk-panchganga-hydrocast.vercel.app"><img src="https://img.shields.io/badge/Live_Dashboard-Vercel_Production-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Live Dashboard"></a>
  <a href="https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/releases/tag/v2.0.0"><img src="https://img.shields.io/badge/Release-v2.0.0-0ea5e9?style=for-the-badge&logo=github&logoColor=white" alt="Release v2.0.0"></a>
  <a href="https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/"><img src="https://img.shields.io/badge/Docs-MkDocs_Material-06B6D4?style=for-the-badge&logo=googledocs&logoColor=white" alt="Documentation"></a>
  <a href="https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/actions/workflows/tests.yml"><img src="https://img.shields.io/badge/Tests-286_Passed-10b981?style=for-the-badge&logo=pytest&logoColor=white" alt="Tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Academic_&_Civil-8b5cf6?style=for-the-badge" alt="License"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11_|_3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Next.js-14_App_Router-black?style=flat-square&logo=next.js&logoColor=white" alt="Next.js">
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-15_+_PostGIS_3.4-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Supabase-Auth_&_Edge-3ECF8E?style=flat-square&logo=supabase&logoColor=white" alt="Supabase">
  <img src="https://img.shields.io/badge/ECMWF-IFS_HRES_(9km)-1E3A8A?style=flat-square" alt="ECMWF">
  <img src="https://img.shields.io/badge/USACE-HEC--HMS_4.13-C53030?style=flat-square" alt="HEC-HMS">
  <img src="https://img.shields.io/badge/IoT-ThingSpeak_Ultrasonic-FF6B6B?style=flat-square" alt="ThingSpeak">
  <img src="https://img.shields.io/badge/Docker-Multi--Stage-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
</p>

---

## ⚡ Why HydroCast?

Every monsoon, torrential orographic rainfall over the Western Ghats (**100–250+ mm/day**) funnels through nine steep subcatchments into the urban bottleneck of **Kolhapur City**. Catastrophic floods in **2005, 2019, and 2021** proved that emergency responders and dam operators need **48 to 72 hours of validated predictive lead time**—not retrospective post-mortems.

Most academic flood models are slow, fragile desktop GUI scripts that run once a week. **HydroCast is built differently:** a production-grade, distributed digital twin that marries heavy hydrodynamic physics with cloud-native edge reliability.

```
                  ┌──────────────────────────────────────────────┐
                  │          HYDROCAST CLOUD ARCHITECTURE        │
                  └──────────────────────────────────────────────┘
                                          │
       ┌──────────────────────────────────┴──────────────────────────────────┐
       ▼                                                                     ▼
[ EDGE DASHBOARD / VERCEL ]                                     [ COMPUTE CORE / RUNNERS ]
 • Next.js 14 App Router UI                                      • 12-Stage Automated Pipeline
 • Global CDN Sub-Second Delivery                                • Vectorized Pure-Python Digital Twin
 • Operations Control Room (/admin)                              • Official USACE HEC-HMS 4.13 Engine
 • Live Mechanical Odometer Counter                              • ECMWF IFS 0.1° High-Res NWP Ingestion
 • Supabase Google OAuth Allowlist                               • ThingSpeak IoT Stage Calibration
 • Serverless Real-Time Telemetry                                • DDMA / CWC Telegram Emergency Alerts
```

---

## ✨ Features at a Glance

| Feature | Description |
| :--- | :--- |
| **⚡ Vectorized Digital Twin** | Pure-Python kinematic wave & Muskingum-Cunge solver (`src/models/vectorized_engine.py`) providing instantaneous, zero-dependency hydrologic modeling on Linux, Mac, or Windows. |
| **🎯 USACE HEC-HMS 4.13 Automation** | Headless boundary scripting with automated DSS (Data Storage System) binary reading, seamlessly falling back to the vectorized digital twin when HEC-HMS binaries are absent. |
| **📈 Calibrated Rating Curves** | Monotonic piecewise cubic Hermite (PCHIP) rating curves for **Shivaji Bridge** & **Rajaram K.T. Weir** guaranteeing $dQ/dh > 0$, calibrated against 2005, 2019, and 2021 flood stages. |
| **🛰️ 90-Hour Predictive Forcing** | Automated ECMWF IFS 0.1° (~9 km) + Open-Meteo Quantitative Precipitation Forecasts (QPF) mapped spatially to subcatchment centroids every 6 hours. |
| **🎛️ Operations Control Room (`/admin`)** | Real-time administrative cockpit providing 12-step pipeline inspection, telemetry health logs, and one-click cloud pipeline dispatch via GitHub Actions. |
| **🔒 Enterprise Dual-Path Auth** | Role-Based Access Control via Supabase Google OAuth (strictly allowlisting authorized research/civil emails) + salted bcrypt operational passkeys for field operators. |
| **📟 Mechanical Odometer Telemetry** | Live, mechanical-style visitor counter backed by atomic PostgreSQL / Supabase synchronization and in-memory serverless ledgers. |
| **🚨 Multi-Channel Alerting** | Automated CWC-standard flood bulletins dispatched directly to **DDMA Kolhapur** and emergency Telegram control channels. |

---

## 🗺️ Panchganga Basin Hydrologic Catchment

The platform models **1,837.21 km²** of the Upper Krishna River Basin draining through 9 primary subcatchments and 5 major routing reaches:

```
  [ Sahyadri Crest (Rainfall 150-250mm/day) ]
      │
      ├── S6 Gaganbawda (227.7 km²) ──┐
      ├── S5 Padasali   (106.4 km²) ──┴─► [ Reach R1: Kasari Upper (K=2.9h) ]
      ├── S4 Karanjphen (262.0 km²) ────► [ Reach R2: Kasari Lower (K=11.8h) ] ──┐
      ├── S3 Kotoli     (261.3 km²) ─────────────────────────────────────────────┤
      ├── S2 Sangarul   (153.8 km²) ────► [ Reach R3: Kumbhi Trunk (K=3.8h) ] ───┼─► 🌉 CHHATRAPATI SHIVAJI BRIDGE
      ├── S9 Radhanagari(367.0 km²) ────► [ Reach R4: Bhogawati    (K=1.2h) ] ───┤     (Warning 542.7m · Danger 544.7m)
      ├── S8 Beed       (177.4 km²) ─────────────────────────────────────────────┘                 │
      ├── S7 Garivade   (195.4 km²) ─────────────────────────────────────────────┐                 ▼
      └── S1 Karveer    (86.2 km²)  ─────────────────────────────────────────────┴─► [ Reach R5: Trunk (K=4.6h) ]
                                                                                                   │
                                                                                                   ▼
                                                                                     🌊 RAJARAM K.T. WEIR (Outlet)
                                                                                       (Warning 539.0m · Danger 541.0m)
```

---

## 🚀 Quickstart in 3 Minutes

### Option A: Local Development

```bash
# 1. Clone repository
git clone https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast.git
cd CCCSS-SUK-Panchganga_Hydrocast

# 2. Setup Python environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.lock
pip install -r requirements-dev.txt

# 3. Configure environment
cp .env.example .env

# 4. Run full forecast simulation cycle
python -m src.orchestrator

# 5. Launch FastAPI backend
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Option B: Frontend Dashboard

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000 in your browser
```

### Option C: Docker Multi-Container Stack

```bash
docker compose up -d --build
# Backend API: http://localhost:8000
# Frontend:    http://localhost:3000
# Docs:        http://localhost:8001
```

---

## 🧪 Rigorous Testing & Quality Gates

HydroCast enforces strict CI/CD validation on every commit:

```bash
# Run complete unit, physics, and security test suite
pytest tests -v

# Run MkDocs documentation build with strict warning gating
python -m mkdocs build --strict

# Run Next.js production build check
cd frontend && npm run build
```

* **286+ Passing Tests:** Comprehensive coverage across hydrologic routing, rating conversions, JWT & passkey auth, rate limiting, and IP hashing.
* **Strict Documentation Gate:** Zero broken links, syntax warnings, or missing schemas permitted.

---

## 🏛️ Interactive Architecture Consoles

HydroCast includes **17 self-contained interactive architecture simulators** built with **Archify** (supporting dark/light themes, zoom, and SVG export):

| Console | Topic | Live Web Link |
| :---: | :--- | :---: |
| **01** | End-to-End System Topology | [Launch Console 01 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/01-architecture.html) |
| **03** | 12-Step Forecast State Machine | [Launch Console 03 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/03-forecast-workflow.html) |
| **08** | Hydraulic Rating & PCHIP Splines | [Launch Console 08 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/08-rating-curve-hydraulics.html) |
| **12** | Frontend Emergency Dashboard UI | [Launch Console 12 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/12-frontend-dashboard.html) |
| **14** | HEC-HMS Engine & Python Digital Twin | [Launch Console 14 ↗](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/diagrams/14-hec-hms-engine.html) |

👉 *Explore all 17 consoles in [`docs/diagrams/`](docs/diagrams/) or on the [Documentation Portal](https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/).*

---

## 🔬 Research Attribution & Sponsorship

HydroCast was conceived and engineered at the **Centre for Climate Change and Sustainability Studies (CCCSS)**, **Shivaji University, Kolhapur (SUK)**.

* **Principal Investigator & Lead Engineer:** Er. Satwik Udupi (`satwikcccss@gmail.com`)
* **Research Grant / Sponsorship:** Supported by the **Department of Science & Technology (DST-SERB)**, Government of India.
* **Institutional Partner:** Water Resources Department (WRD), Government of Maharashtra.

### BibTeX Citation
```bibtex
@software{hydrocast2026,
  author = {Udupi, Satwik and CCCSS Research Team},
  title = {HydroCast: Operational Hydrologic Digital Twin and Flood Early-Warning Platform for the Panchganga Basin},
  year = {2026},
  publisher = {GitHub},
  version = {2.0.0},
  url = {https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast}
}
```

---

<p align="center">
  Released under the <strong>Academic & Civil Disaster Resilience License</strong>.<br>
  Built with ❤️ for the safety and resilience of Kolhapur District.
</p>
