# HydroCast Technical Documentation Library

<p align="center">
  <img src="assets/hydrocast_flow_animation.svg" alt="HydroCast Operational Continuum" width="100%">
</p>

Welcome to the comprehensive technical documentation for **HydroCast: Real-Time Operational Flood Forecasting & Basin Intelligence** for the Panchganga River Catchment (Kolhapur District, Maharashtra, India).

## Technology & Engineering Stack

| Area | Tool |
| :--- | :--- |
| **OS** | ![Linux](https://img.shields.io/badge/OS-Linux-FCC624?style=flat&logo=linux&logoColor=black) ![macOS](https://img.shields.io/badge/OS-macOS-000000?style=flat&logo=apple&logoColor=white) ![Windows](https://img.shields.io/badge/OS-Windows-0078D6?style=flat&logo=windows&logoColor=white) |
| **Languages** | ![Bash](https://img.shields.io/badge/Code-Bash-4EAA25?style=flat&logo=gnubash&logoColor=white) ![Python](https://img.shields.io/badge/Code-Python_3.11-3776AB?style=flat&logo=python&logoColor=white) ![Java](https://img.shields.io/badge/Code-Java_LTS-ED8B00?style=flat&logo=openjdk&logoColor=white) ![Node.js](https://img.shields.io/badge/Code-Node.js-339933?style=flat&logo=nodedotjs&logoColor=white) ![JavaScript](https://img.shields.io/badge/Code-JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black) ![TypeScript](https://img.shields.io/badge/Code-TypeScript-3178C6?style=flat&logo=typescript&logoColor=white) ![SQL](https://img.shields.io/badge/Code-SQL-CC292B?style=flat&logo=postgresql&logoColor=white) |
| **Frameworks** | ![Next.js](https://img.shields.io/badge/Code-Next.js_14-000000?style=flat&logo=nextdotjs&logoColor=white) ![React](https://img.shields.io/badge/Code-React_18-61DAFB?style=flat&logo=react&logoColor=black) ![FastAPI](https://img.shields.io/badge/Code-FastAPI-009688?style=flat&logo=fastapi&logoColor=white) ![Tailwind](https://img.shields.io/badge/Code-Tailwind_CSS-06B6D4?style=flat&logo=tailwindcss&logoColor=white) ![Leaflet](https://img.shields.io/badge/Code-Leaflet-199900?style=flat&logo=leaflet&logoColor=white) |
| **Hydrology & GIS** | ![HEC-HMS](https://img.shields.io/badge/Engine-HEC--HMS_4.12-1D4ED8?style=flat&logo=apache&logoColor=white) ![Jython](https://img.shields.io/badge/Script-Jython_2.7-D97706?style=flat&logo=python&logoColor=white) ![GeoPandas](https://img.shields.io/badge/GIS-GeoPandas-139C5A?style=flat&logo=geopandas&logoColor=white) ![GDAL](https://img.shields.io/badge/GIS-GDAL-499848?style=flat&logo=osgeo&logoColor=white) ![SciPy](https://img.shields.io/badge/Math-SciPy_PCHIP-8CAAE6?style=flat&logo=scipy&logoColor=black) ![NumPy](https://img.shields.io/badge/Math-NumPy-013243?style=flat&logo=numpy&logoColor=white) |
| **Databases** | ![PostgreSQL](https://img.shields.io/badge/DB-PostgreSQL_15-4169E1?style=flat&logo=postgresql&logoColor=white) ![Supabase](https://img.shields.io/badge/DB-Supabase-3ECF8E?style=flat&logo=supabase&logoColor=black) ![SQLite](https://img.shields.io/badge/DB-SQLite-003B57?style=flat&logo=sqlite&logoColor=white) ![PostGIS](https://img.shields.io/badge/DB-PostGIS-336791?style=flat&logo=postgresql&logoColor=white) |
| **IoT & Telemetry** | ![ThingSpeak](https://img.shields.io/badge/IoT-ThingSpeak-005B94?style=flat&logo=mathworks&logoColor=white) ![Sensor](https://img.shields.io/badge/Hardware-Radar%20Altimeter-F59E0B?style=flat&logo=target&logoColor=white) ![ESP32](https://img.shields.io/badge/Hardware-ESP32-E7352C?style=flat&logo=espressif&logoColor=white) ![Open-Meteo](https://img.shields.io/badge/NWP-Open--Meteo-F97316?style=flat&logo=accuweather&logoColor=white) |
| **Infrastructure** | ![Docker](https://img.shields.io/badge/Containers-Docker-2496ED?style=flat&logo=docker&logoColor=white) ![Kubernetes](https://img.shields.io/badge/Containers-Kubernetes-326CE5?style=flat&logo=kubernetes&logoColor=white) ![GitHub Actions](https://img.shields.io/badge/CICD-GitHub_Actions-2088FF?style=flat&logo=githubactions&logoColor=white) ![Vercel](https://img.shields.io/badge/Deploy-Vercel-000000?style=flat&logo=vercel&logoColor=white) ![Datadog](https://img.shields.io/badge/Monitoring-Datadog-632CA6?style=flat&logo=datadog&logoColor=white) |

---

## Technical Modules

| Module | Document | Description |
| :--- | :--- | :--- |
| **System Architecture** | [`Architecture.md`](./Architecture.md) | 12-Step operational prediction pipeline, fault tolerance, and self-healing mechanics. |
| **API & Backend** | [`Backend.md`](./Backend.md) | FastAPI REST services, asyncpg connection pooling, WebSocket broadcasting, and endpoints. |
| **Frontend Dashboard** | [`Frontend.md`](./Frontend.md) | Next.js 14 App Router, Tailwind CSS design system, Chart.js, and Leaflet GIS mapping. |
| **Database Architecture** | [`Database.md`](./Database.md) | PostgreSQL production schema, Supabase cloud sync, views, and JSON multi-run ledger. |
| **Open-Meteo & ECMWF** | [`Openmeteo.md`](./Openmeteo.md) | ECMWF IFS 0.25° quantitative precipitation forecasting pipeline and API integration. |
| **Rain Gauge Network** | [`Raingauge_Station.md`](./Raingauge_Station.md) | 18 primary and alternate stations, geographical topology, and dynamic selection. |
| **Basin Hydrology** | [`Hydrology.md`](./Hydrology.md) | 2,140 km² Panchganga basin physiography, subbasins S1–S9, and SCS Curve Number model. |
| **Runoff Computation** | [`Runoff_Computation.md`](./Runoff_Computation.md) | Mathematical runoff continuum, loss rate, unit hydrograph convolution, and routing. |
| **HEC-HMS Automation** | [`HMS.md`](./HMS.md) | Headless USACE HEC-HMS 4.x batch runner, DSS time series, and Python SCS-CN emulator. |
| **River Hydraulics** | [`Hydraulics.md`](./Hydraulics.md) | Manning open-channel flow, bed slope calibration ($S_0 = 0.005858$), and compound cross-sections. |
| **Rating Curves** | [`Stage_Conversion_Discharge.md`](./Stage_Conversion_Discharge.md) | Bi-directional monotonic PCHIP rating curves ($dQ/dh > 0$) for Shivaji Bridge & Rajaram Weir. |
| **Model Calibration** | [`Calibration_Validation.md`](./Calibration_Validation.md) | Spearman rank $\rho$, Nash-Sutcliffe Efficiency (NSE), PBIAS, RMSE, and WRD benchmarks. |
| **Rainfall Validation** | [`Rainfall_Validation_Pipeline.md`](./Rainfall_Validation_Pipeline.md) | Observed rainfall ingestion, ground truth telemetry verification, and QC checks. |
| **WRD Ground Truth** | [`WRD_Historical_Rating_Curve_CrossCheck.md`](./WRD_Historical_Rating_Curve_CrossCheck.md) | Historical flood marks cross-verification vs Maharashtra WRD government records. |
| **IoT Telemetry** | [`IoT_Telemetry.md`](./IoT_Telemetry.md) | ThingSpeak ultrasonic radar level sensor, 549.35m datum, and live stage polling. |
| **GIS Vector Layers** | [`Shpfiles.md`](./Shpfiles.md) | GeoJSON subbasin delineations, stream network routing, and DEM processing. |
| **Engineering Autopsy** | [`Errors_Mistakes_Engineering_Assumptions.md`](./Errors_Mistakes_Engineering_Assumptions.md) | Historical post-mortem of bed slope distortion, wetted perimeter collapse, and bugs. |
| **System Novelty** | [`Novelty_of_this_System.md`](./Novelty_of_this_System.md) | 10 core scientific and architectural innovations of HydroCast vs traditional warning systems. |
| **PI Research Report** | [`Accuracy_Analysis_PI_Report.md`](./Accuracy_Analysis_PI_Report.md) | Formal research report prepared for the Principal Investigator on model accuracy. |
| **Production Roadmap** | [`ROADMAP.md`](./ROADMAP.md) | 5 Open-source production hardening pillars: Dockerization, alerting, archival, and security. |
| **Operations Manual** | [`Deployment_Operations.md`](./Deployment_Operations.md) | Linux systemd, PM2 process management, automated 6-hourly cron jobs, and NGINX setup. |
