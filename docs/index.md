# HydroCast Technical Documentation

<div class="hc-hero">
  <div class="hc-hero-badge-group">
    <span class="hc-hero-badge">DST-SERB Funded</span>
    <span class="hc-hero-badge">Panchganga Basin (1,837.213 km²)</span>
    <span class="hc-hero-badge">Dual-Engine HEC-HMS 4.13 + Python Twin</span>
    <span class="hc-hero-badge">Closed Telemetry Loop</span>
  </div>
  <h1 class="hc-hero-title">Operational Early Warning & Hydrologic Forecasting</h1>
  <p class="hc-hero-subtitle">
    Production-grade rainfall-runoff modeling, real-time ultrasonic radar stage validation, physics-informed Levenberg-Marquardt recalibration, and 2D hydrodynamic flood strike prediction for the Panchganga River Catchment.
  </p>
  <div class="hc-hero-actions">
    <a href="architecture-atlas/" class="hc-btn-primary">
      <span>Explore Architecture Atlas</span> →
    </a>
    <a href="https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/" class="hc-btn-secondary" target="_blank" rel="noopener">
      <span>Live Production Portal</span> ↗
    </a>
  </div>
</div>

<div class="hc-stat-grid">
  <div class="hc-stat-box">
    <div class="hc-stat-val">1,837 km²</div>
    <div class="hc-stat-label">Surveyed Watershed</div>
  </div>
  <div class="hc-stat-box">
    <div class="hc-stat-val">90 Hours</div>
    <div class="hc-stat-label">ECMWF IFS Forecast Horizon</div>
  </div>
  <div class="hc-stat-box">
    <div class="hc-stat-val">&lt; 20 ms</div>
    <div class="hc-stat-label">Python Twin Latency</div>
  </div>
  <div class="hc-stat-box">
    <div class="hc-stat-val">± 2.0 hrs</div>
    <div class="hc-stat-label">Peak Flood Strike Window</div>
  </div>
</div>

## System Architecture Highlights

<div class="hc-grid-3">
  <div class="hc-spec-card">
    <div class="hc-spec-icon">⚡</div>
    <div class="hc-spec-title">Dual-Engine Strategy</div>
    <p class="hc-spec-desc">Native USACE HEC-HMS 4.13 headless batch automation seamlessly paired with a Pure-Python vectorized digital twin emulator for millisecond ensemble inference.</p>
  </div>
  <div class="hc-spec-card">
    <div class="hc-spec-icon">🔄</div>
    <div class="hc-spec-title">Physics-Informed Calibrator</div>
    <p class="hc-spec-desc">Levenberg-Marquardt optimizer with asymmetric 3× flood penalty and gated ML predictor lifecycle (UNTRAINED → TRAINED → VALIDATED).</p>
  </div>
  <div class="hc-spec-card">
    <div class="hc-spec-icon">📡</div>
    <div class="hc-spec-title">IoT Radar Ingestion</div>
    <p class="hc-spec-desc">Continuous real-time ultrasonic stage telemetry from Shivaji Bridge deck (#3424513) with automated rate-of-rise anomaly filtering.</p>
  </div>
</div>

## Interactive Engineering Consoles

Every console is an interactive vector architecture map with pan, zoom, layer switching, and export capabilities.

| # | Console | Focus | Open |
|:---:|:---|:---|:---:|
| **01** | End-to-End Architecture | Seven-layer topology, boundaries, external forces | [Launch ↗](diagrams/01-architecture.html) |
| **02** | Rainfall-to-Alert Dataflow | ECMWF, hydrology, DSS, sensors, alerting lanes | [Launch ↗](diagrams/02-dataflow.html) |
| **03** | Forecast Cycle Workflow | Twelve-step orchestration with SLAs | [Launch ↗](diagrams/03-forecast-workflow.html) |
| **04** | API Gateway & Auth Sequence | JWT handshake, API keys, internal broadcast | [Launch ↗](diagrams/04-sequence-auth-api.html) |
| **05** | Simulation Run Lifecycle | Verification state machine for every run | [Launch ↗](diagrams/05-lifecycle-runs.html) |
| **06** | Hybrid OS Deployment | Docker Compose stack vs native Windows PostgreSQL | [Launch ↗](diagrams/06-deployment-docker-os.html) |
| **07** | HydroSim 2D Handoff | Boundary conditions passed to HEC-RAS | [Launch ↗](diagrams/07-workflow-hydrosim-handoff.html) |
| **08** | Rating Curves & Cross-Sections | Divided channel geometry, PCHIP stage-discharge | [Launch ↗](diagrams/08-rating-curve-hydraulics.html) |
| **09** | Rain Gauge Selection | QC gate, argmax selection, Thiessen weights | [Launch ↗](diagrams/09-raingauge-selection-flowchart.html) |
| **10** | Catchment Hydrology Solver | SCS-CN loss, SCS-UH, Muskingum R1–R5 | [Launch ↗](diagrams/10-catchment-hydrology-solver.html) |
| **11** | Backend API Map | Public routes, WebSocket, internal endpoints | [Launch ↗](diagrams/11-backend-api.html) |
| **12** | Frontend Build & Dashboard | Next.js build stages and operations console | [Launch ↗](diagrams/12-frontend-dashboard.html) |
| **13** | Relational Schema ERD | Ten tables across PostgreSQL, PostGIS, TimescaleDB | [Launch ↗](diagrams/13-database-schema.html) |
| **14** | Dual-Engine HEC-HMS | Headless batch automation vs Python twin | [Launch ↗](diagrams/14-hec-hms-engine.html) |
| **15** | ML Calibration Loop | Rising-limb trigger and bounded parameter fit | [Launch ↗](diagrams/15-ml-calibration.html) |
| **16** | Repository Tree | Module layout and ownership | [Launch ↗](diagrams/16-repository-tree.html) |
| **17** | Forecast Cycle Waterfall | Measured step latencies per cycle | [Launch ↗](diagrams/17-cycle-waterfall.html) |

## The Panchganga Catchment & Gauging Geometry

<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<div id="hydrocast-map" style="height: 460px; width: 100%; border-radius: 12px; margin: 24px 0; border: 1px solid var(--hc-card-border-light); z-index: 1; box-shadow: var(--hc-card-shadow-light);"></div>

<script>
document.addEventListener("DOMContentLoaded", function() {
    var map = L.map('hydrocast-map').setView([16.65, 74.15], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    var stations = [
        {name: "Kolhapur (Shivaji Bridge)", lat: 16.7114, lon: 74.2185, type: "Telemetry Radar Deck (549.35 m MSL)"},
        {name: "Rajaram K.T. Weir", lat: 16.7198, lon: 74.2541, type: "Regulatory Basin Outlet (539.00 m Warning)"},
        {name: "Gaganbawda (Upper Ghats)", lat: 16.5417, lon: 73.8267, type: "High-Rainfall Ridge Station"}
    ];

    stations.forEach(function(s) {
        L.marker([s.lat, s.lon]).addTo(map)
            .bindPopup("<b>" + s.name + "</b><br>" + s.type);
    });
});
</script>

## System Architecture Specification

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 01</span>
      <strong>End-to-End System Topology (Panchganga Basin)</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="diagrams/01-architecture.html" target="_blank" rel="noopener">
        <span>Full Screen Console</span> ↗
      </a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="diagrams/01-architecture.html?embed=1" title="End-to-End Architecture Diagram"></iframe>
</div>

## Comprehensive Topic Map

| Section | Topic Reference | Focus Area |
|:---|:---|:---|
| **System Architecture** | [`architecture.md`](architecture.md) · [`architecture-atlas.md`](architecture-atlas.md) | Layer contracts, WRD datums, 12-step pipeline, physical parameters, security model, deployment |
| **Modeling Engines** | [`hec-hms-engine.md`](hec-hms-engine.md) · [`python-twin-emulator.md`](python-twin-emulator.md) | USACE headless automation, Pure-Python twin emulator, sub-stepped Muskingum routing |
| **Hydrology & Runoff** | [`runoff-computation.md`](runoff-computation.md) · [`basin-hydrology.md`](basin-hydrology.md) | SCS-CN continuous loss, SCS dimensionless unit hydrograph, Muskingum R1–R5 routing |
| **Adaptive Calibration** | [`ml-calibration-engine.md`](ml-calibration-engine.md) · [`calibration-validation.md`](calibration-validation.md) | Levenberg-Marquardt optimizer, 3× flood penalty, 3-state gated ML predictor lifecycle |
| **Hydraulics & Rating** | [`stage-discharge-conversion.md`](stage-discharge-conversion.md) · [`hydraulics.md`](hydraulics.md) | Divided Channel Method, 26 WRD empirical pairs, monotonic PCHIP stage-discharge spline |
| **Telemetry & Ingestion** | [`iot-telemetry.md`](iot-telemetry.md) · [`open-meteo-ecmwf.md`](open-meteo-ecmwf.md) | ECMWF 90-hour IFS precipitation, Shivaji Bridge radar sensor (#3424513), outlier filters |
| **API & Operations** | [`backend.md`](backend.md) · [`database.md`](database.md) · [`deployment-operations.md`](deployment-operations.md) | FastAPI REST services, HMAC key security, Supabase 13-table PostGIS schema, Docker runbooks |
| **Hydraulic Integration** | [`integration-hydrosim.md`](integration-hydrosim.md) | HydroSim 2D hydrodynamic boundary handoffs and water-level API |
