# HydroCast Panchganga Flood Forecasting System
## Technical Open Items & System Audit (docs/OPEN_ITEMS.md)

**Document Reference:** CCCSS-SUK-HC-DOC-OI-001  
**Project:** Operational Flood Early Warning System for Panchganga River Catchment  
**Organization:** Centre for Climate Change & Water Research (CCCSS), Shivaji University, Kolhapur  
**Sponsor:** DST-SERB, Government of India / Maharashtra Water Resources Department (WRD)  
**Verification Date:** 2026-10-21  
**Standard:** Institutional System Engineering Audit  

---

### Audit Policy & Rules
In accordance with system documentation rules:
1. Every component, pipeline edge, database table, endpoint, and automation schedule must be verified against actual committed code files.
2. Any architectural entity, script, worker, or downstream interface mentioned in operational mandates but not committed in this repository is formally designated as **TO CONFIRM**.
3. No speculative code or synthetic mock datasets are permitted.

---

### Summary of System Audit Findings

| Item ID | Component Description | Current Status | Searched Repository Paths | Action Required for Resolution |
| :--- | :--- | :--- | :--- | :--- |
| **OI-001** | **HydroSim Hydraulic Handoff Engine & HEC-RAS Models** | **TO CONFIRM** (External System) | `src/`, `frontend/`, `calibration/`, `data/`, root directory | Repository contains export endpoints (`/api/v1/runoff/hydrograph`, `/api/v1/runoff/stage/{site_id}`) and 2D cross-section viewer (`frontend/components/CrossSectionViewer.tsx`), but the downstream HEC-RAS geometry files (`.prj`, `.g01`, `.p01`) and HydroSim execution runner are external. Confirm external repository URL, API key binding, and server host for HydroSim. |
| **OI-002** | **RTDAS Live Water Level Web Scraper** | **TO CONFIRM** (Missing Script) | `src/processing/`, `src/sensors/`, `src/hydrology/` | UI in `frontend/components/AccuracyPanel.tsx` (L917) references Live RTDAS telemetry (`आजची पातळी (Live RTDAS)`). Active code in `src/processing/gauge_fetcher.py` and `src/sensors/thingspeak_gauge.py` ingests ThingSpeak and generic IoT REST feeds, but an automated scraper for the Maharashtra WRD RTDAS portal is absent. Confirm if RTDAS scraping is handled by an external AWS Lambda/Cloudflare worker or if `src/sensors/rtdas_scraper.py` is to be deployed. |
| **OI-003** | **Go Telemetry Ingestion Worker** | **TO CONFIRM** (Uncommitted Worker) | Full repo (`Get-ChildItem -Include *.go -Recurse`) | Zero `.go` source files exist in the repository. All operational ingestion is implemented in Python 3.12 (`src/orchestrator.py`, `src/ecmwf/downloader.py`, `src/processing/gauge_fetcher.py`, `src/sensors/thingspeak_gauge.py`). Confirm if a standalone Go ingestion daemon is deployed on a remote field gateway or if Python remains the sole ingestion runtime. |
| **OI-004** | **3D Basin DEM / DTM Digital Elevation Model** | **TO CONFIRM** (Raster Missing; Vectors Present) | `data/`, `data/Shapefiles_Panchganga basin/`, `docs/gis/` | Vector flowpaths and subbasin boundaries are present (`Panchganga_RJKT_Flowpath.geojson`, `Panchganga_RJKT_RB.geojson`), and station locations are present (`data/stations/raingauge_stations.csv`). However, raster elevation files (`.tif`, `.dem`, `.asc`, `.dtm`, `.hgt`) are not in the repository. Per Rule C, 3D terrain visualization is strictly skipped until a verified 30m SRTM / CartoDEM GeoTIFF is deposited into `data/gis/dem/`. |
| **OI-005** | **Windows Deployment Script Schema Target (`schema_v3.sql`)** | **TO CONFIRM** (Path Discrepancy) | `windows/install_postgres.ps1`, `database/` | `windows/install_postgres.ps1` (L197) attempts to execute `..\database\schema_v3.sql`. The committed production schema is `database/supabase_schema.sql` (configured in `docker-compose.yml`). Confirm if `windows/install_postgres.ps1` should be updated to point to `database/supabase_schema.sql`. |
| **OI-006** | **ThingSpeak Secondary Channel & CWC API Endpoint** | **TO CONFIRM** (Production Credentials) | `src/sensors/thingspeak_gauge.py`, `src/processing/gauge_fetcher.py`, `.env.example` | Primary ThingSpeak channel `3424513` is configured for Shivaji Bridge ultrasonic radar. Secondary gauge ingestion endpoints (`IOT_API_BASE` in `src/processing/gauge_fetcher.py:21`) use default placeholder `https://your-iot-api/api/v1/gauges`. Confirm production REST endpoints for CWC / WRD automated rain gauge feeds. |

---

### Detailed Audit Notes

The notes below record outstanding verification work: items that are implemented
but not yet independently checked, and inputs that exist only as templates in the
repository.

#### 1. HydroSim Integration (OI-001)
* **Code References in Repository:**
  * `src/api/main.py:347-410`: Declares endpoints `GET /api/v1/runoff/hydrograph` and `GET /api/v1/runoff/stage/{site_id}` protected by `X-API-Key`.
  * `src/api/security.py:34-42, 110-128`: Enforces constant-time `hmac.compare_digest()` for incoming `X-API-Key`.
  * `src/hydrology/stage_converter.py:24-60`: Houses official Manning hydraulic parameters and surveyed cross-sections for Shivaji Bridge and Rajaram Weir.
  * `frontend/components/CrossSectionViewer.tsx`: Renders 2D hydraulic cross-section profiles using surveyed elevation vertices.
* **Missing Components:**
  * No Python/C++ code executes HEC-RAS (`ras.exe` / HEC-RAS Controller API).
  * No 1D/2D unsteady flow boundary condition injection script for HEC-RAS is committed.
* **Interim Architectural Designation:**
  * Marked as **External Consumer System**. The hand-off occurs at the HTTP API boundary using API Key authentication. Downstream HEC-RAS steps are classified as `[TO CONFIRM - External HydroSim Pipeline]`.

#### 2. RTDAS Scraper Pipeline (OI-002)
* **Code References in Repository:**
  * `frontend/components/AccuracyPanel.tsx:917`: UI string indicating `Live RTDAS`.
  * `src/processing/gauge_fetcher.py:20-50`: Implements generic REST query with fallback handling.
* **Missing Components:**
  * Direct web scraping routines (e.g., BeautifulSoup, Playwright, Selenium, or urllib scrapers) targeting the Maharashtra Water Resources Department RTDAS portal (`https://rtdas.maharashtra.gov.in`).
* **Interim Architectural Designation:**
  * Telemetry data is ingested via ThingSpeak IoT API (`src/sensors/thingspeak_gauge.py`). RTDAS direct scraper is tagged `[TO CONFIRM]` in the Data Flow diagram.

#### 3. Ingestion Runtime Language (OI-003)
* **Code References in Repository:**
  * Ingestion is executed via `src/orchestrator.py` (steps 1–4), `src/ecmwf/downloader.py`, and `.github/workflows/pipeline.yml`.
  * Multi-stage container `Dockerfile` compiles Python 3.12 with OpenJDK 17, GDAL, libpq5, and eccodes.
* **Missing Components:**
  * No Go runtime, `go.mod`, or `.go` files exist in the repository.
* **Interim Architectural Designation:**
  * Python 3.12 is documented as the sole in-repo ingestion runtime. Go is logged in the 3D stack slab as `[TO CONFIRM]`.

#### 4. Topographic DEM Dataset (OI-004)
* **Code References in Repository:**
  * Vector geometry: `data/Shapefiles_Panchganga basin/Panchganga_RJKT_Flowpath.geojson`
  * Catchment boundary: `data/Shapefiles_Panchganga basin/Panchganga_RJKT_RB.geojson`
  * Gauge registry: `data/stations/raingauge_stations.csv` (20 verified stations with WGS84 coordinates and elevations)
* **Missing Components:**
  * Raster GeoTIFF / ASCII grid elevation file.
* **Directive Compliance:**
  * Per Rule C, 3D terrain generation is omitted to preserve scientific integrity. Required specifications for external DEM ingestion:
    * Projection: EPSG:4326 or EPSG:32643 (UTM Zone 43N)
    * Resolution: 30-meter (SRTM 1 Arc-Second or CartoDEM V3)
    * Coverage: 16.20°N to 17.20°N, 73.70°E to 74.50°E.

---
*Signed by System Architecture Audit — HydroCast Panchganga Engineering Team*
