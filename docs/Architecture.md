# HydroCast Architecture Specification

```
====================================================================================================
                     PANCHGANGA HYDROCAST - END-TO-END SYSTEM TOPOLOGY
====================================================================================================

   [ ECMWF 9km HRES IFS ]                    [ ThingSpeak IoT Channel 3424513 ]
  (18 Station Precipitation)                 (Shivaji Bridge Ultrasonic Level)
              |                                              |
              v                                              v
   +----------------------+                       +----------------------+
   | Open-Meteo SDK Client|                       | Telemetry Validator  |
   | - 90h Hyetographs    |                       | - Quality Control    |
   +----------------------+                       +----------------------+
              |                                              |
              +----------------------+-----------------------+
                                     |
                                     v
                 +---------------------------------------+
                 |  Adaptive Physics-Informed ML Engine  |
                 |  - Discrepancy Detection (Delta_t)    |
                 |  - Scipy L-BFGS-B Loss Minimization   |
                 +---------------------------------------+
                                     |
                                     v
                 +---------------------------------------+
                 |    HEC-HMS 4.13 Hydrological Core     |
                 |  - Loss: SCS Curve Number (AMC-II/III)|
                 |  - Transform: SCS Unit Hydrograph (UH)|
                 |  - Channel Routing: Muskingum (R1–R5) |
                 |  - Baseflow: Exponential Recession    |
                 +---------------------------------------+
                                     |
                                     v
                 +---------------------------------------+
                 |   2D Surveyed Hydraulic Rating Engine |
                 |  - Divided Channel Method (DCM)       |
                 |  - Main: n=0.031 | Overbank: n=0.070  |
                 |  - Bed Gradient & Backwater Transfer  |
                 +---------------------------------------+
                                     |
                   +-----------------+-----------------+
                   |                                   |
                   v                                   v
   +-------------------------------+   +-------------------------------+
   | Supabase PostgreSQL DB        |   | Next.js 14 Dashboard & SWR    |
   | - Single-Tree Relational Store|   | - GIS Leaflet Map             |
   | - Parquet Cold Storage Archival   | - 2D Cross-Section Viewer     |
   |   (src/db/archive_runs.py)    |   | - Adaptive ML Calibration Tab |
   +-------------------------------+   | - Serverless Telegram Webhook |
                   |                   +-------------------------------+
                   v                                   |
   +-------------------------------+                   v
   | DDMA Emergency Alert Engine   |   +-------------------------------+
   | - Telegram Bot Push Bulletins |   | Interactive Telegram Chatbot  |
   | - CWC Threshold Dispatcher    |   | - /status, /stage, /alerts    |
   +-------------------------------+   +-------------------------------+
```

---

## 1. System Technology Stack

| Layer | Technologies & Frameworks | Functionality & Characteristics |
|:---|:---|:---|
| **Meteorological Layer** | ECMWF IFS High-Res (9km / 0.08°), Open-Meteo SDK | Automated ingestion across 18 Panchganga gauging stations |
| **Hydrological Engine** | USACE HEC-HMS 4.13 + Vectorized Python Physical Solver | Loss (SCS-CN), Transform (SCS Dimensionless UH), Channel Routing (Muskingum with Sub-stepping), Baseflow (Exponential Recession) |
| **Hydraulic Rating** | 2D Divided Channel Method (DCM), PCHIP Monotonic Spline | 108 surveyed coordinates at Shivaji Bridge and Rajaram Weir ($n_{\text{main}}=0.031$, $n_{\text{flood}}=0.070$) |
| **Machine Learning** | Adaptive Physics-Informed Calibrator (Scipy L-BFGS-B) | Real-time tuning of $\alpha_K$, $\alpha_{\text{lag}}$, $\Delta CN$, and $X$ |
| **Database & Storage**| PostgreSQL 15+ (Supabase) + Apache Parquet Engine | Unified single-tree relational schema with automated 90-day Parquet cold storage |
| **Alerting & Dispatch**| Telegram Bot API + Next.js Serverless Webhook | Automated CWC/DDMA flood bulletins & interactive chatbot |
| **Frontend UI** | Next.js 14 (App Router), Tailwind CSS, Chart.js, Leaflet | Responsive operational dashboard, CrossSectionViewer, OdometerCounter, System Telemetry |
