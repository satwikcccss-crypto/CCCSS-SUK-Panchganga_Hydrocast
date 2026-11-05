# 🌊 HydroCast — Operational Hydrologic Digital Twin & Flood Intelligence Portal

<div class="hc-hero">
  <div class="hc-hero-badge">OPERATIONAL DIGITAL TWIN · PANCHGANGA BASIN (1,837 KM²)</div>
  <h1 style="color: #ffffff; margin-top: 0.5rem; font-size: 2.2rem; font-weight: 800;">Real-Time Hydrometeorological Forecasting & Early Warning</h1>
  <p style="font-size: 1.05rem; line-height: 1.6; opacity: 0.95; max-width: 820px; margin-top: 0.8rem;">
    HydroCast is the operational flood forecasting digital twin engineered for the 1,837 km² Panchganga River Catchment in Kolhapur District, Maharashtra, India. By coupling ECMWF IFS high-resolution QPF with dual-core hydrologic simulation (USACE HEC-HMS 4.13 + pure-Python vectorized twin), PCHIP hydraulic rating curves, and real-time ultrasonic IoT telemetry, HydroCast provides 90 hours of predictive lead time for disaster management agencies.
  </p>
  <div style="display: flex; gap: 12px; margin-top: 1.4rem; flex-wrap: wrap;">
    <a href="basin-hydrology/" class="md-button md-button--primary" style="background: #ffffff; color: #0284c7; font-weight: 700; border-radius: 8px;">Explore Basin Hydrology →</a>
    <a href="https://cccss-suk-panchganga-hydrocast.vercel.app" target="_blank" class="md-button" style="border: 1px solid rgba(255,255,255,0.7); color: #ffffff; border-radius: 8px;">Live Production Dashboard ↗</a>
    <a href="backend/" class="md-button" style="border: 1px solid rgba(255,255,255,0.7); color: #ffffff; border-radius: 8px;">API Documentation →</a>
  </div>
</div>

---

## ⚡ Navigation & Portal Guide

Explore the comprehensive documentation across four operational domains:

<div class="grid cards" markdown>

- :material-water: __Basin Hydrology & Datums__

    ---

    Detailed hydromorphological characterization of the 9 headwater subcatchments, 5 river routing reaches ($R1 \rightarrow R5$), WRD Rajaram Weir and Shivaji Bridge canonical datums, and historical flood benchmarks (2005, 2019, 2021).

    [:octicons-arrow-right-24: Catchment Hydrology & Datums](basin-hydrology.md)  
    [:octicons-arrow-right-24: Rain Gauge Network Registry](raingauge-network.md)  
    [:octicons-arrow-right-24: GIS Boundaries & GeoJSON](gis-vector-layers.md)

- :material-engine: __Hydrologic & Hydraulic Engines__

    ---

    Dual-core hydrologic simulation architecture: deterministic USACE HEC-HMS 4.13 headless runner, pure-Python vectorized digital twin, SCS-CN infiltration loss, SCS Dimensionless UH transforms, and Muskingum-Cunge channel routing.

    [:octicons-arrow-right-24: Dual-Engine Simulation Strategy](hec-hms-engine.md)  
    [:octicons-arrow-right-24: Pure-Python Vectorized Twin](python-twin-emulator.md)  
    [:octicons-arrow-right-24: Monotonic PCHIP Rating Engine](stage-discharge-conversion.md)

- :material-satellite-uplink: __Telemetry & Meteorology__

    ---

    Automated numerical weather prediction (ECMWF IFS HRES 0.1° / 9 km QPF), real-time ultrasonic water level sensor telemetry (ThingSpeak IoT channel 3424513 @ Shivaji Bridge), and Levenberg-Marquardt adaptive recalibration.

    [:octicons-arrow-right-24: ECMWF Numerical Weather Ingest](open-meteo-ecmwf.md)  
    [:octicons-arrow-right-24: IoT Sensor Telemetry Pipeline](iot-telemetry.md)  
    [:octicons-arrow-right-24: Physics-Informed ML Calibrator](ml-calibration-engine.md)

- :material-server-network: __System Architecture & APIs__

    ---

    FastAPI asynchronous service architecture, JWT security policies, PostgreSQL 15 + PostGIS database schema, Next.js 14 operations dashboard, and automated CWC/DDMA flood bulletins.

    [:octicons-arrow-right-24: System Architecture Specification](architecture.md)  
    [:octicons-arrow-right-24: FastAPI Endpoints & Routing](backend.md)  
    [:octicons-arrow-right-24: Hybrid OS Deployment Runbook](deployment-operations.md)

</div>

---

## 📊 Interactive Architecture & Workflow Consoles

HydroCast features 17 explorable standalone HTML consoles visualizing every layer of the platform:

| Console | Scope & Functional Description | Direct Console Link |
| :--- | :--- | :--- |
| **01 · Topology** | 6-Layer Enterprise System Architecture & Component Mapping | [Open Console ↗](consoles/01-architecture.md){:target="_blank"} |
| **02 · Dataflow** | Rainfall-to-Alert End-to-End Latency Pipeline | [Open Console ↗](consoles/02-dataflow.md){:target="_blank"} |
| **03 · Workflow** | 12-Step Automated Forecast Cycle State Machine | [Open Console ↗](consoles/03-forecast-workflow.md){:target="_blank"} |
| **04 · Auth Sequence** | Bearer JWT & API Key Ingestion Security Flow | [Open Console ↗](consoles/04-sequence-auth-api.md){:target="_blank"} |
| **05 · Lifecycle** | Forecast Run & Telemetry Residual Lifecycle State Transitions | [Open Console ↗](consoles/05-lifecycle-runs.md){:target="_blank"} |
| **06 · Deployment** | Dual-Target Deployment Architecture (Docker & Windows Subsystem) | [Open Console ↗](consoles/06-deployment-docker-os.md){:target="_blank"} |
| **07 · HydroSim Handoff**| 2D Hydrodynamic Handoff & Boundary Influx Format | [Open Console ↗](consoles/07-workflow-hydrosim-handoff.md){:target="_blank"} |
| **08 · Rating Curves** | WRD Rajaram Weir & Shivaji Bridge Monotonic PCHIP Splines | [Open Console ↗](consoles/08-rating-curve-hydraulics.md){:target="_blank"} |
| **09 · Gauge Selection**| Dynamic Spatial Centroid Rain Gauge Assignment Engine | [Open Console ↗](consoles/09-raingauge-selection-flowchart.md){:target="_blank"} |
| **10 · Hydrology Solver**| Subbasin Runoff Convolution & Muskingum Numerical Solvers | [Open Console ↗](consoles/10-catchment-hydrology-solver.md){:target="_blank"} |
| **11 · Backend API** | FastAPI Route Ingress, Middleware & WebSocket Push Pipeline | [Open Console ↗](consoles/11-backend-api.md){:target="_blank"} |
| **12 · Frontend UI** | Next.js 14 App Router, Telemetry Poller & Geospatial UI Layers | [Open Console ↗](consoles/12-frontend-dashboard.md){:target="_blank"} |
| **13 · Database Schema**| Complete PostgreSQL + PostGIS Entity-Relationship Diagram | [Open Console ↗](consoles/13-database-schema.md){:target="_blank"} |
| **14 · HEC-HMS Engine** | Headless USACE Jython Runner & Vectorized Twin Fallback | [Open Console ↗](consoles/14-hec-hms-engine.md){:target="_blank"} |
| **15 · ML Calibration** | Bounded Levenberg-Marquardt Parameter Recalibration Loop | [Open Console ↗](consoles/15-ml-calibration.md){:target="_blank"} |
| **16 · Repository Tree**| Project Directory Hierarchy & Modular File Registry | [Open Console ↗](consoles/16-repository-tree.md){:target="_blank"} |
| **17 · Cycle Latencies**| Real-Time Execution Waterfall & Subsystem Benchmarking | [Open Console ↗](consoles/17-cycle-waterfall.md){:target="_blank"} |

---

## 🏛️ Research Attribution & Citation

HydroCast is developed at the **Centre for Climate Change and Sustainability Studies (CCCSS)**, **Shivaji University, Kolhapur (SUK)**.

* **Research Grant & Funding:** Supported by the **Department of Science & Technology (DST-SERB)**, Government of India.
* **Institutional Partner:** Water Resources Department (WRD), Government of Maharashtra.
* **Disaster Management Partner:** District Disaster Management Authority (DDMA), Kolhapur.

### Author Citation
> **Satwik K. Udupi, Dr. Sachin S. Panhalkar, Dr. Ganesh S. Nhivekar, Nikhil D. Pawar, Center for Climate Change and Sustainability Studies, Shivaji University, Kolhapur (2026).**  
> *HydroCast: Operational Hydrologic Digital Twin & Real-Time Flood Intelligence Platform for the Panchganga River Catchment.*  
> GitHub Repository: [https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast)

```bibtex
@software{hydrocast2026,
  author       = {Udupi, Satwik K. and Panhalkar, Sachin S. and Nhivekar, Ganesh S. and Pawar, Nikhil D.},
  title        = {HydroCast: Operational Hydrologic Digital Twin & Real-Time Flood Intelligence Platform for the Panchganga River Catchment},
  institution  = {Center for Climate Change and Sustainability Studies, Shivaji University, Kolhapur},
  year         = {2026},
  publisher    = {GitHub},
  version      = {2.0.0},
  url          = {https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast}
}
```
