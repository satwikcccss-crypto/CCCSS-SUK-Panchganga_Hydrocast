# System Architecture Specification

> This page is the **specification**: what each layer of the system is, what boundary it exposes, and what parameters it is configured with. The [Architecture Atlas](architecture-atlas.md) is the companion **explanatory** document, with the 17 interactive SVG consoles that trace a cycle end to end.

Where the two disagree, this page follows the source. Several claims in the previous version of this document could not be reproduced in the repository — the basin area, the station count, the reach names, the rainfall bound, and the optimiser family were all wrong. Those corrections are listed in the [Engineering Autopsy](errors-and-engineering-assumptions.md).

---

## Interactive diagram consoles

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 01</span>
      <strong>End-to-End System Architecture</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/01-architecture.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/01-architecture.html?embed=1" title="End-to-End System Architecture Console"></iframe>
</div>

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 02</span>
      <strong>Rainfall-to-Alert Dataflow</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/02-dataflow.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/02-dataflow.html?embed=1" title="Rainfall-to-Alert Dataflow Console"></iframe>
</div>

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 03</span>
      <strong>Forecast Cycle Workflow</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/03-forecast-workflow.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/03-forecast-workflow.html?embed=1" title="Forecast Cycle Workflow Console"></iframe>
</div>

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 16</span>
      <strong>Repository Tree</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/16-repository-tree.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/16-repository-tree.html?embed=1" title="Repository Tree Console"></iframe>
</div>

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 17</span>
      <strong>Forecast Cycle Waterfall</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/17-cycle-waterfall.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/17-cycle-waterfall.html?embed=1" title="Forecast Cycle Waterfall Console"></iframe>
</div>

---

## 1. What the system is

HydroCast is a rainfall-runoff and flood-intelligence platform for the Panchganga basin in Western Maharashtra. It ingests a 90-hour quantitative precipitation forecast, redistributes it across nine gauged subbasins, simulates loss and channel routing, converts outlet discharge into water level at two bridges, evaluates the regulatory alert ladder, and dispatches a bulletin to the district emergency room.

The gauged catchment is **1,837.213 km²**, delineated across nine subbasins and drained through five Muskingum reaches into a single outlet at the Rajaram weir. The system runs on a 6-hourly schedule with an hourly telemetry cycle alongside it.

---

## 2. Layer inventory

The pipeline is organised as seven layers, each with a narrow responsibility and a clear input/output contract. The consoles above show how data flows between them; the text below states what each one owns.

### Layer 1 — Meteorological ingestion

`src/ecmwf/open_meteo.py` queries the Open-Meteo REST interface for ECMWF IFS HRES precipitation on the 9 km grid, lead hours 1 through 90 at hourly resolution, over the catchment bounding box.

`src/ecmwf/retry_utils.py` wraps the request with exponential backoff and full jitter, so that concurrent workers do not retry in lockstep and a transient upstream failure does not cost a cycle.

`src/processing/validator.py` then applies four checks before the data is allowed to influence the forecast:

| Constant | Value | Meaning |
|:---|:---|:---|
| `MAX_VALID_MM_HR` | 500.0 | Physical upper bound on hourly depth |
| coverage floor | 50 % | Minimum share of the 90 expected hourly records |
| `MAX_LAG_MINUTES` | 60 | Latest gauge record must be within one hour |
| `ECMWF_MAX_AGE_HR` | 8 | ECMWF run must be fresher than eight hours |

> **Note:** The previous specification stated a 250 mm/h bound. The physical-range check in `src/processing/validator.py` uses 500 mm/h. Neither value is the official limit — 250 mm/h is a plausible Sahyadri extreme and the code permits values well above it. The bound exists to catch instrument and transmission faults, and should be set from the basin record rather than from a round number.

### Layer 2 — Spatial topology and soil moisture

`src/ecmwf/station_selector.py` holds the registry of **20** stations across nine subbasins — nine primaries and eleven alternates — and implements the maximum-precipitation routing rule. The [Rain Gauge Network](raingauge-network.md) page documents the selection algorithm in full.

Soil moisture is classified by `classify_amc` from the mean 90-hour forecast rainfall: AMC-I below 25 mm (dry), AMC-II between 25 and 65 mm (average), AMC-III at or above 65 mm (wet). The class selects a curve number per subbasin through the TR-55 transforms:

$$CN_{\text{III}} = \frac{23\,CN_{\text{II}}}{10 + 0.13\,CN_{\text{II}}} \qquad CN_{\text{I}} = \frac{4.2\,CN_{\text{II}}}{10 - 0.058\,CN_{\text{II}}}$$

with potential retention $S = 25400/CN - 254$ and initial abstraction $I_a = 0.2 S$.

### Layer 3 — Runoff engine

The engine has two implementations of the same model. The primary path writes a Jython control script and executes HEC-HMS 4.x headless. The fallback path is a vectorised pure-Python implementation of SCS-CN loss, SCS unit hydrograph transform, and Muskingum reach routing, and it is what CI actually runs, since CI installs neither Java nor HEC-HMS.

Both paths read parameters from `data/hms/HMS_Automation_RJKT/Basin_1.basin`, which is the single source of truth for both the emulator and the calibration engine. The emulator produces 352 hourly points before the 90-hour slice is taken for the published forecast.

> **Warning:** `result_source` does not reflect what ran — `src/hms/runner.py` never parses `data/hms/compute/Run_1.dss`. The emulator result is returned with `result_source = EMULATOR_PYTHON` even when the binary reports `COMPLETED_BINARY`, so provenance in the persisted run is not reliable.

### Layer 4 — Hydraulic rating

`src/hydrology/stage_converter.py` interpolates the rating curve with `scipy.interpolate.PchipInterpolator` through 27 WRD anchors spanning 528.67 m to 548.00 m, guaranteeing $dQ/dh > 0$ throughout. Rajaram uses the sheet verbatim; Shivaji uses the same anchors shifted by the surveyed bed difference of 0.648 m.

A Divided Channel Method implementation based on surveyed cross-sections also exists in `src/hydrology/rating_curves.py`. It is not on the execution path for either site.

### Layer 5 — Adaptive calibration

`src/hydrology/realtime_telemetry_validator.py` reads ThingSpeak channel `3424513`, where an ultrasonic sensor on the Shivaji Bridge deck reports water level with sensor datum 549.35 m MSL. `src/hydrology/ml_calibration.py` then compares observed against forecast and, when the discrepancy gate fires ($|\Delta t| \ge 1.0$ h or rising-limb $\Delta h > 0.25$ m), runs a bounded L-BFGS-B optimisation over four parameters and writes the result back to `Basin_1.basin` atomically.

> **Note:** Optimiser family — the previous specification named Levenberg-Marquardt. The implementation calls `scipy.optimize.minimize` with method `L-BFGS-B`.

### Layer 6 — Persistence

`src/db/` writes to PostgreSQL 15 with PostGIS 3.4 over `asyncpg`, trying the Supabase pooler host before the direct host because GitHub Actions runners are frequently IPv6-only. Every cycle also writes an immutable JSON document to `data/runs/{cycle_id}.json`.

`src/db/archive_runs.py` exports series older than `ARCHIVE_RETENTION_DAYS` (default 90) into Snappy-compressed Parquet partitions under `data/archives/`, then prunes the source rows in a transaction.

The schema comprises **15 tables and 7 views** — see [PostgreSQL & PostGIS Database Schema](database.md).

### Layer 7 — Alerting and decision support

`src/alerts/evaluator.py` maps predicted stage onto the six-tier regulatory ladder and dispatches through `src/alerts/telegram_bot.py` to the DDMA. The API publishes `/ws/live` for WebSocket push to the Next.js 14 dashboard, and serves archived run documents when the database is unreachable.

---

## 3. Pipeline sequence

The orchestrator in `src/orchestrator.py` runs twelve steps per cycle. The cycle identifier encodes the run, so `CYC_20260901_06z` is the 06z cycle of 1 September 2026.

| Step | Operation | Module |
|:---|:---|:---|
| 1 | Meteorological forcing ingestion, with retry and QC | `src/ecmwf/open_meteo.py` |
| 2 | Gauge fetching and spatial station routing | `src/ecmwf/station_selector.py` |
| 3 | Antecedent moisture classification | `src/hydrology/` |
| 4 | HEC-DSS boundary condition preparation | `src/hms/runner.py` |
| 5 | Recalibration check against live telemetry | `src/hydrology/ml_calibration.py` |
| 6 | Hydrologic watershed runoff execution | `src/hms/runner.py` |
| 7 | Sink outlet hydrograph extraction | `src/hms/runner.py` |
| 8 | Monotonic hydraulic stage conversion | `src/hydrology/stage_converter.py` |
| 9 | Peak arrival window and uncertainty envelope | `src/hydrology/ml_calibration.py` |
| 10 | Accuracy auditing — Spearman ρ, NSE, RMSE, MAE, PBIAS | `src/hydrology/validation_metrics.py` |
| 11 | Multi-channel emergency alert dispatch | `src/alerts/` |
| 12 | Persistence, archival, and dashboard broadcast | `src/db/` |

> **Warning:** `pipeline_ok` is currently always false — the success predicate checks for **10** successful steps while the step list contains **12** entries, so a cycle that completes cleanly is still reported as failed. Steps 7 and 8 are also executed twice in the orchestrator body, which inflates the step log. Both are described in the [Production Hardening Roadmap](roadmap.md).

### Scheduling

| Workflow | Cadence | Command |
|:---|:---|:---|
| `pipeline.yml` | 02:30, 08:30, 14:30, 20:30 UTC | `python -m src.ecmwf.open_meteo` |
| `telemetry_validation.yml` | Hourly, minute 0 | `python -m src.hydrology.realtime_telemetry_validator --all-pending` |
| `tests.yml` | On push and pull request | `python -m pytest -q` |

> **Note:** The scheduled command is not the orchestrator — `pipeline.yml` invokes `python -m src.ecmwf.open_meteo` and the downstream modules directly. The twelve-step orchestrator is not what runs on the schedule.

---

## 4. Basin parameters

Parameters are read from `data/hms/HMS_Automation_RJKT/Basin_1.basin` by `src/hms/basin_parser.py`.

For the authoritative catchment parameters across all nine subbasins (totaling 1,837.213 km²), see [Catchment Hydrology: Subbasin Parameters](basin-hydrology.md#subbasin-parameters).

Channel routing through the 5 Muskingum reaches (R5, R4, R2, R3, R1) connects subbasin outflows to the terminal sink at Rajaram K.T. Weir. For complete routing parameters, travel times $K$, wedge weights $X$, and numerical sub-stepping passes, see [Catchment Hydrology: Muskingum Reaches](basin-hydrology.md#muskingum-reaches).

> **Basin network console** — see [Console 10: Catchment Hydrology Solver](diagrams/10-catchment-hydrology-solver.html){ target="_blank" } for the interactive subbasin-to-reach network with parameters.

Subbasin S1 drains directly to the sink with no reach routing, which is consistent with its position at the outlet. Every other subbasin reaches the sink through at least one Muskingum reach.

---

## 5. Official reference datums

All regulatory levels are expressed against the official Maharashtra Water Resources Department (WRD) zero gauge datum of **530.18 m MSL** and surveyed bridge cross-section thalwegs.

For the complete regulatory datum schedule, elevation benchmarks, and official 26-point rating schedule, see [Catchment Hydrology: Official Regulatory Datums](basin-hydrology.md#regulatory-datums).

| Elevation (m MSL) | Benchmark |
|:---|:---|
| 545.33 | HFL (2019 / 2021) — record flood crest |
| 543.30 | Danger Level (WRD / CWC) |
| 542.70 | Warning Level (WRD / CWC) |
| 542.10 | Shivaji Bridge Alert Level |
| 541.50 | Rajaram Weir Alert Level |
| 535.77 | Rajaram Weir Solid Crest |
| 533.28 | Normal Monsoon Stage (Q ≈ 109 m³/s) |
| 530.18 | River Bed Zero Datum (WRD 0′ 0″ Gauge Mark) |
| 529.318 | Rajaram Bridge Bed Thalweg |
| 528.670 | Shivaji Bridge Bed Thalweg |

The uncertainty envelope reported with each peak is computed as

$$\text{stage margin} = 0.12 + 0.03\,(\,h_{\text{peak}} - 535\,)$$

metres either side of the peak, with discharge bounded to ±6 % of the rating value. The arrival window is $T_{\text{peak}} \pm 2.0$ h, from `PEAK_ARRIVAL_CI_HOURS` with a default of 2.0.

---

## 6. Technology stack

| Layer | Technology | Function |
|:---|:---|:---|
| NWP data | ECMWF IFS HRES 9 km via Open-Meteo REST | 90-hour QPF forecast |
| Ingestion | `requests`, `openmeteo-requests`, SQLite cache | Backoff, jitter, QC bounds |
| Hydrology | HEC-HMS 4.x + Python emulator | SCS-CN loss, UH transform, Muskingum routing |
| Hydraulics | `scipy.interpolate.PchipInterpolator` | Monotone rating curves |
| Calibration | `scipy.optimize.minimize` (L-BFGS-B), NumPy | Bounded optimiser + gated ML |
| Telemetry | ThingSpeak channel `3424513` | Ultrasonic level at Shivaji Bridge |
| Database | PostgreSQL 15 + PostGIS 3.4, Supabase pooler | Cycles, hydrographs, step logs (15 tables, 7 views) |
| Archival | PyArrow, Apache Parquet | Columnar retention export |
| API | FastAPI, Uvicorn, asyncpg | REST endpoints and WebSocket push |
| Security | PyJWT (HS256), `slowapi`, `hmac.compare_digest` | Scoped API keys, JWT, rate limiting |
| Alerting | Telegram Bot API, HTTP webhooks | DDMA bulletins |
| Frontend | Next.js 14 App Router, React 18, Tailwind | Operations dashboard |
| Deployment | Docker, Docker Compose | Three-service reproducible stack |
| CI/CD & QA | GitHub Actions, pytest | Automated test suite |

---

## 7. Deployment

```yaml
services:
  hydrocast-db:        # postgis/postgis:15-3.4
  hydrocast-backend:   # Python 3.12 + FastAPI
  hydrocast-frontend:  # Next.js 14 standalone
  hydrocast-net:       # private bridge
```

The backend `Dockerfile` builds wheels in a stage that carries OpenJDK 17, `libgdal-dev` and `libeccodes-dev`, and runs a minimal runtime image as a non-root user with a health probe against `/api/v1/health`. The frontend `Dockerfile` produces a Node 20 Alpine standalone server. Schema initialisation comes from `database/supabase_schema.sql`.

---

## 8. API surface

Public reads are rate-limited to `RATE_LIMIT_PUBLIC` (default 100/minute, keyed on remote address) and gated by `verify_public_or_key`. Administrative routes under `/api/v1/admin` require either an HMAC-SHA256 JWT bearer token from `POST /api/v1/admin/auth/token` — compared with `hmac.compare_digest`, valid 24 hours — or an `X-API-Key` header matching `API_KEY`.

| Route | Purpose |
|:---|:---|
| `GET /api/v1/health` | Service and last-run status |
| `GET /api/v1/status` | Current cycle state |
| `GET /api/v1/rainfall/*` | Gauge and subbasin rainfall series |
| `GET /api/v1/runoff/*` | Hydrographs, subbasins, reaches |
| `GET /api/v1/stage` | Bridge stage forecast and peak window |
| `GET /api/v1/calibration` | Calibration state and bounds |
| `GET /api/v1/dss` | Run file listing |
| `POST /api/v1/admin/trigger-run` | Manual cycle trigger |
| `POST /api/v1/admin/archive` | Trigger Parquet archival |
| `POST /api/v1/admin/recalibrate` | Force recalibration |
| `WS /ws/live` | Live cycle and threshold push |

For the generated reference of every endpoint, see the API reference section in the navigation.
