# HydroCast Technical Documentation Library

<p align="center">
  <img src="assets/hydrocast_main_banner.jpg" alt="HydroCast Operational Continuum" width="100%">
</p>

<p align="center">
  <a href="https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/">
    <img src="https://img.shields.io/badge/🌐_Live_Hydraulic_&_Documentation_Portal-GitHub_Pages-06B6D4?style=for-the-badge&logo=github&logoColor=white" alt="Live GitHub Pages Portal">
  </a>
</p>


Welcome to the comprehensive technical documentation for **HydroCast: Real-Time Operational Flood Forecasting & Basin Intelligence** for the Panchganga River Catchment (Kolhapur District, Maharashtra, India).

<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<div id="hydrocast-map" style="height: 450px; width: 100%; border-radius: 8px; margin: 30px 0; border: 1px solid #475569; z-index: 1;"></div>

<script>
document.addEventListener("DOMContentLoaded", function() {
    var map = L.map('hydrocast-map').setView([16.65, 74.15], 10);
    
    L.tileLayer('https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}', {
        maxZoom: 20,
        attribution: '&copy; Google Maps Terrain'
    }).addTo(map);

    fetch('gis/panchganga_subbasins.geojson')
        .then(r => r.json())
        .then(data => {
            L.geoJSON(data, {
                style: {color: "#06B6D4", weight: 2, fillOpacity: 0.1},
                onEachFeature: (f, l) => l.bindPopup("<b>Subbasin:</b> " + (f.properties.name || "Panchganga Catchment"))
            }).addTo(map);
        });

    fetch('gis/panchganga_rivers.geojson')
        .then(r => r.json())
        .then(data => {
            L.geoJSON(data, {
                style: {color: "#3B82F6", weight: 4},
                onEachFeature: (f, l) => l.bindPopup("<b>Reach:</b> " + (f.properties.name || "River Reach"))
            }).addTo(map);
        });
});
</script>

## Technology & Engineering Stack

| Area | Tool |
| :--- | :--- |
| **OS** | ![Linux](https://img.shields.io/badge/OS-Linux-FCC624?style=flat&logo=linux&logoColor=black) ![macOS](https://img.shields.io/badge/OS-macOS-000000?style=flat&logo=apple&logoColor=white) ![Windows](https://img.shields.io/badge/OS-Windows-0078D6?style=flat&logo=windows&logoColor=white) |
| **Languages** | ![Bash](https://img.shields.io/badge/Code-Bash-4EAA25?style=flat&logo=gnubash&logoColor=white) ![Python](https://img.shields.io/badge/Code-Python_3.11-3776AB?style=flat&logo=python&logoColor=white) ![Java](https://img.shields.io/badge/Code-Java_LTS-ED8B00?style=flat&logo=openjdk&logoColor=white) ![Node.js](https://img.shields.io/badge/Code-Node.js-339933?style=flat&logo=nodedotjs&logoColor=white) ![JavaScript](https://img.shields.io/badge/Code-JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black) ![TypeScript](https://img.shields.io/badge/Code-TypeScript-3178C6?style=flat&logo=typescript&logoColor=white) ![SQL](https://img.shields.io/badge/Code-SQL-CC292B?style=flat&logo=postgresql&logoColor=white) |
| **Frameworks** | ![Next.js](https://img.shields.io/badge/Code-Next.js_14-000000?style=flat&logo=nextdotjs&logoColor=white) ![React](https://img.shields.io/badge/Code-React_18-61DAFB?style=flat&logo=react&logoColor=black) ![FastAPI](https://img.shields.io/badge/Code-FastAPI-009688?style=flat&logo=fastapi&logoColor=white) ![Tailwind](https://img.shields.io/badge/Code-Tailwind_CSS-06B6D4?style=flat&logo=tailwindcss&logoColor=white) ![Leaflet](https://img.shields.io/badge/Code-Leaflet-199900?style=flat&logo=leaflet&logoColor=white) |
| **Hydrology & ML** | ![HEC-HMS](https://img.shields.io/badge/Engine-HEC--HMS_4.12-1D4ED8?style=flat&logo=apache&logoColor=white) ![Jython](https://img.shields.io/badge/Script-Jython_2.7-D97706?style=flat&logo=python&logoColor=white) ![GeoPandas](https://img.shields.io/badge/GIS-GeoPandas-139C5A?style=flat&logo=geopandas&logoColor=white) ![GDAL](https://img.shields.io/badge/GIS-GDAL-499848?style=flat&logo=osgeo&logoColor=white) ![SciPy](https://img.shields.io/badge/Math-SciPy_PCHIP-8CAAE6?style=flat&logo=scipy&logoColor=black) ![NumPy](https://img.shields.io/badge/Math-NumPy-013243?style=flat&logo=numpy&logoColor=white) |
| **Databases & Archival** | ![PostgreSQL](https://img.shields.io/badge/DB-PostgreSQL_15-4169E1?style=flat&logo=postgresql&logoColor=white) ![Supabase](https://img.shields.io/badge/DB-Supabase-3ECF8E?style=flat&logo=supabase&logoColor=black) ![Parquet](https://img.shields.io/badge/Storage-Apache_Parquet-4B67A1?style=flat&logo=apache&logoColor=white) ![PostGIS](https://img.shields.io/badge/DB-PostGIS-336791?style=flat&logo=postgresql&logoColor=white) |
| **IoT & Alerting** | ![ThingSpeak](https://img.shields.io/badge/IoT-ThingSpeak-005B94?style=flat&logo=mathworks&logoColor=white) ![Telegram](https://img.shields.io/badge/Alerts-Telegram_Bot-26A5E4?style=flat&logo=telegram&logoColor=white) ![Radar](https://img.shields.io/badge/Hardware-Radar%20Altimeter-F59E0B?style=flat&logo=target&logoColor=white) ![Open-Meteo](https://img.shields.io/badge/NWP-Open--Meteo-F97316?style=flat&logo=accuweather&logoColor=white) |
| **Infrastructure** | ![Docker](https://img.shields.io/badge/Containers-Docker-2496ED?style=flat&logo=docker&logoColor=white) ![Compose](https://img.shields.io/badge/Containers-Docker_Compose-2496ED?style=flat&logo=docker&logoColor=white) ![GitHub Actions](https://img.shields.io/badge/CICD-GitHub_Actions-2088FF?style=flat&logo=githubactions&logoColor=white) ![Vercel](https://img.shields.io/badge/Deploy-Vercel-000000?style=flat&logo=vercel&logoColor=white) |

---

## Technical Modules

| Module | Document | Description |
| :--- | :--- | :--- |
| **System Architecture** | [`architecture.md`](./architecture.md) | 12-Step operational prediction pipeline, ML recalibration loop, multi-container Docker, and cold storage. |
| **API & Backend** | [`backend.md`](./backend.md) | FastAPI REST services, SlowAPI rate limiting, admin JWT tokens, manual triggers, and WebSockets. |
| **Frontend Dashboard** | [`frontend.md`](./frontend.md) | Next.js 14 App Router, Peak Flood Strike Horizon (±2.0h CI), 2D SVG Cross-Section, and Docker runtime. |
| **Database Architecture** | [`database.md`](./database.md) | PostgreSQL production schema, `pipeline_step_log`, Supabase cloud sync, and Parquet cold storage. |
| **Open-Meteo & ECMWF** | [`open-meteo-ecmwf.md`](./open-meteo-ecmwf.md) | ECMWF IFS HRES 9km QPF ingestion, enterprise exponential backoff retry wrappers, and station routing. |
| **Rain Gauge Network** | [`raingauge-network.md`](./raingauge-network.md) | 18 primary and alternate stations, geographical topology, and dynamic selection. |
| **Basin Hydrology** | [`basin-hydrology.md`](./basin-hydrology.md) | 1,837.2 km² Panchganga basin physiography, subbasins S1–S9, SCS-CN, SCS Dimensionless UH, and closed-loop ML recalibration. |
| **Runoff Computation** | [`runoff-computation.md`](./runoff-computation.md) | Mathematical runoff continuum, SCS-CN loss, SCS unit hydrograph convolution, and Muskingum reach routing. |
| **HEC-HMS Automation** | [`hec-hms-engine.md`](./hec-hms-engine.md) | Headless USACE HEC-HMS 4.13 batch runner, `Basin_1.basin` parser, pure-Python emulator with AMC-I/II/III antecedent moisture, SCS-CN loss, SCS-UH, Muskingum routing, and baseflow recession. |
| **River Hydraulics** | [`hydraulics.md`](./hydraulics.md) | Divided Channel Method ($n_{\text{main}}=0.031, n_{\text{flood}}=0.070$), surveyed bed slopes ($1:2529, 1:4641, 1:7700$), and K.T. weir hydraulics. |
| **Rating Curves** | [`stage-discharge-conversion.md`](./stage-discharge-conversion.md) | Bi-directional monotonic PCHIP rating curves ($dQ/dh > 0$) for Shivaji Bridge & Rajaram Weir. |
| **Model Calibration** | [`calibration-validation.md`](./calibration-validation.md) | Spearman rank $\rho$, NSE, PBIAS, real-time ML optimization, and WRD benchmark calibration. |
| **ML Calibration Engine** | [`ml-calibration-engine.md`](./ml-calibration-engine.md) | Details the Physics-Informed Machine Learning engine that fits Levenberg–Marquardt parameters in-memory against the emulator, using the HEC-HMS basin file as the immutable physical ground truth. |
| **Rainfall Validation** | [`rainfall-validation-pipeline.md`](./rainfall-validation-pipeline.md) | Observed rainfall ingestion, ground truth telemetry verification, and QC checks. |
| **WRD Ground Truth** | [`wrd-rating-curve-cross-check.md`](./wrd-rating-curve-cross-check.md) | Historical flood marks cross-verification vs Maharashtra WRD government records. |
| **IoT Telemetry** | [`iot-telemetry.md`](./iot-telemetry.md) | ThingSpeak ultrasonic radar level sensor, 549.35m datum, live stage polling, observation-gap lifecycle states, and ML recalibration integration. |
| **GIS Vector Layers** | [`gis-vector-layers.md`](./gis-vector-layers.md) | GeoJSON subbasin delineations, stream network routing, and DEM processing. |
| **Engineering Autopsy** | [`errors-and-engineering-assumptions.md`](./errors-and-engineering-assumptions.md) | Historical post-mortem of bed slope distortion, wetted perimeter collapse, and v3.0 edge-case mitigations. |
| **System Novelty** | [`novelty-of-this-system.md`](./novelty-of-this-system.md) | 12 core scientific and architectural innovations of HydroCast vs traditional warning systems. |
| **PI Research Report** | [`accuracy-analysis-pi-report.md`](./accuracy-analysis-pi-report.md) | Formal research report prepared for the Principal Investigator on model accuracy. |
| **Production Roadmap** | [`roadmap.md`](./roadmap.md) | 5 Open-source production hardening pillars: Dockerization, alerting, archival, security, and retries. |
| **Operations Manual** | [`deployment-operations.md`](./deployment-operations.md) | Docker Compose multi-container, DDMA Telegram bot dispatch, scheduled Parquet pruning, and NGINX setup. |

