# HydroCast Frontend Architecture & Design System

```
====================================================================================================
               HYDROCAST NEXT.JS 14 BASIN INTELLIGENCE DASHBOARD
====================================================================================================

                     Next.js 14 App Router (React 18 Server/Client Model)
                                              |
      +---------------------------------------+---------------------------------------+
      |                                       |                                       |
      v                                       v                                       v
[ SWR State Engine ]             [ WebSocket Live Push ]             [ Tailwind Design System ]
Cached REST revalidation         Event-driven /ws/live listener      Curated HSL Color Tokens
Fallback: Standalone JSON        Auto-reconnect with backoff         Dark & Light Glassmorphic
      |                                       |                                       |
      +---------------------------------------+---------------------------------------+
                                              |
                                              v
                          Dashboard Shell (app/dashboard/page.tsx)
                                              |
      +---------------+---------------+-------+-------+---------------+---------------+
      |               |               |               |               |               |
      v               v               v               v               v               v
[ Overview ]    [ Rainfall ]    [ Runoff/HMS ]  [ Accuracy ]    [ System ]     [ FloodBanner ]
Basin GIS map   18-Station      90h Outflow     Multi-tier KPIs 12-Step flow   CWC Threshold
Live gauges     Hyetographs     Cross-section   ML Calibrator   Latency/Logs   Emergency Push
Odometer Count  Isohyetals      Rating curves   Runs Ledger     Archival/Bot   Flashing Alert
```

---

## 1. Technology Stack & Framework Specifications

- **Framework:** Next.js 14.2.5 (App Router, TypeScript, React 18).
- **Styling Architecture:** Vanilla Tailwind CSS with custom HSL token palette (Slate, Indigo, Sky, Emerald, Amber, Rose).
- **Data Visualization Engine:** Chart.js 4.4.x, `react-chartjs-2`, and `chartjs-plugin-annotation`.
- **Spatial Mapping:** Leaflet 1.9.4 & `react-leaflet` with Panchganga Basin subbasin GeoJSON boundaries.
- **State Management & Caching:** `swr` (Stale-While-Revalidate) with automated 30s background revalidation.
- **Motion & Micro-Interactions:** `framer-motion` and `lucide-react`.

---

## 2. Component Hierarchy & Operational Workspaces

### 2.1 Workspace Overview (`OverviewPanel.tsx`)
- **Interactive GIS Basin Map:** Renders Panchganga subbasins S1–S9, river reach paths R1–R5, and 18 hydro-meteorological stations.
- **Live Engineering Gauges (`EngineeringGauge.tsx`):** Renders calibrated hydraulic column tube gauges for Shivaji Bridge and Rajaram KT Weir with animated water levels and threshold markers.
- **Animated Odometer Counter (`OdometerCounter.tsx`):** Real-time smooth rolling counter tracking cumulative system visits and forecast compute hours.

### 2.2 Rainfall Intelligence Workspace (`RainfallPanel.tsx`)
- **18-Station Hydro-Meteorological Grid:** Real-time 90-hour forward hyetographs from ECMWF IFS HRES (0.08° / 9km).
- **Subbasin Area-Weighted Precipitation:** Catchment-mean hyetographs driving the SCS-CN loss model.

### 2.3 Runoff & Hydraulic Workspace (`RunoffPanel.tsx`)
- **90-Hour Hydrograph Visualizer:** Discrete surface runoff, baseflow recession, and total basin discharge.
- **2D Cross-Section Viewer (`CrossSectionViewer.tsx`):** Native dynamic SVG rendering of the 108 surveyed coordinates at Shivaji Bridge and Rajaram KT Weir, with live water surface elevation and floodplain inundation.

### 2.4 Model Accuracy & Calibration Workspace (`AccuracyPanel.tsx`)
- **Verification Charts:** Dual-axis hydrograph comparison of simulated vs observed ThingSpeak sensor data.
- **Multi-Tier Statistical KPIs:** Live Spearman $\rho$, Nash-Sutcliffe Efficiency (NSE), Pearson $R^2$, RMSE, and PBIAS.
- **Adaptive ML Recalibration Tab:** Interactive dashboard displaying real-time $\alpha_K$, $\alpha_{\text{lag}}$, $\Delta CN$, and $X$ optimization states, wave timing offset $\Delta t$, and subbasin parameter matrices.
- **Government Records Cross-Check:** 19 official WRD staff gauge benchmark levels (11.0 ft to 49.8 ft HFL).
- **Historical Runs Ledger:** Full 15-cycle historical audit ledger.

### 2.5 System Telemetry Workspace (`SystemPanel.tsx`)
- **12-Stage Pipeline Flow:** Real-time monitoring of every pipeline execution step.
- **System Components & Data Sources:** Ingestion health for Open-Meteo, ThingSpeak, HEC-HMS Core, Supabase DB, **Telegram Disaster Bot**, and **Parquet Cold Storage Engine**.

---

## 3. Serverless API Architecture

```
frontend/app/api/
├── telegram/webhook/route.ts   # Serverless Telegram Bot Webhook handler
├── v1/dashboard/route.ts        # Dynamic force-dynamic state provider
├── v1/export/route.ts           # Secure serverless CSV export route
└── v1/history/route.ts          # Historical cycle ledger provider
```
