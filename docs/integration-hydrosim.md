# HydroSim 2D Hydraulic Handoff & Water-Level Boundary API

HydroCast exposes a specialized, high-performance **read-only water-level and discharge feed** allowing external 2D hydrodynamic flood models—specifically USACE **HEC-RAS 6.x** and **HydroSim 2D**—to directly ingest 90-hour forward stage hydrographs as unsteady boundary conditions.

---

## Interactive diagram consoles

The console below is the rendered reference for this page: it carries the same structure, tier boundaries and failure branches that the prose describes.

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 07</span>
      <strong>HydroSim 2D Handoff & Boundary Workflow</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/07-workflow-hydrosim-handoff.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/07-workflow-hydrosim-handoff.html?embed=1" title="HydroSim 2D Handoff Console"></iframe>
</div>

---

## 1. Multi-Route REST Interface

The boundary condition engine binds to four equivalent URL routes in `src/api/main.py`:

```http
GET /api/v1/hydrocast/water-levels        (Primary Branded Production Endpoint)
GET /api/v1/water-levels                  (Short Normalized API Path)
GET /api/v1/hydrosim/water-levels         (HydroSim Integration Alias)
GET /api/v1/integration/hydrosim/stage    (Legacy Backward-Compatible Path)
```

### 1.1 Request Parameters

| Query Parameter | Supported Values | Default | Purpose & Semantics |
| :--- | :--- | :--- | :--- |
| `key` | String (`hydrocast_PS_V1_...`) | None | Consumer API key passed in URL query string |
| `site_id` | `SHIVAJI_BRIDGE`, `RAJARAM_BRIDGE` | All | Optional site filter (returns both sites if omitted) |
| `format` | `json`, `csv` | `json` | Response serialization format |

### 1.2 Rate Limiting & Response Codes
- **Rate Limit:** Governed by `RATE_LIMIT_PUBLIC` (100 requests / minute per client IP).
- **HTTP 200 OK:** Successful forecast boundary payload.
- **HTTP 401 Unauthorized:** Missing, malformed, or invalid API key.
- **HTTP 404 Not Found:** No forecast cycles exist in the database (cycle in progress or uninitialized).
- **HTTP 422 Unprocessable Entity:** Unsupported `format` or invalid `site_id`.

---

## 2. Consumer Key Authentication & Security Boundary

External hydraulic models authenticate using dedicated, read-only consumer credentials (`src/api/keys.py`):

```http
# Option A: Header Authentication (Recommended for scripts & production pipelines)
GET /api/v1/hydrocast/water-levels HTTP/1.1
Host: localhost:8000
X-API-Key: hydrocast_PS_V1_abcdef123456...

# Option B: Query String Authentication (Convenient for browser verification)
GET /api/v1/hydrocast/water-levels?key=hydrocast_PS_V1_abcdef123456... HTTP/1.1
```

### Security Boundary Guarantees
1. **Strictly Read-Only:** Consumer keys grant access exclusively to public data routes. They are **strictly rejected** by `/api/v1/admin/*` administrative endpoints. External models cannot trigger runs, modify parameters, or access database tables.
2. **Zero-Downtime Rotation:** The server accepts multiple consumer keys configured in `CONSUMER_API_KEYS` (comma-separated list). Operators can provision a new key, deploy it to HydroSim, and retire the old key without pipeline restarts.
3. **Timing-Attack Resistance:** Key validation executes in constant time via `hmac.compare_digest` across all configured keys without early termination.

---

## 3. Data Exchange Contracts

### 3.1 JSON Specification (Default Format)

```json
{
  "schema_version": "1.0",
  "source": "HydroCast",
  "cycle_id": "CYC_20260903_06z",
  "issued_at": "2026-09-03T06:00:00+00:00",
  "units": {
    "stage": "m",
    "discharge": "m3/s"
  },
  "vertical_datum": "WRD gauge datum; zero_datum_m is the site zero offset. Align to your HEC-RAS geometry datum before use.",
  "sites": [
    {
      "site_id": "SHIVAJI_BRIDGE",
      "site_name": "Chhatrapati Shivaji Maharaj Bridge (Panchganga Ghat)",
      "river_name": "Panchganga",
      "latitude": 16.708917,
      "longitude": 74.219278,
      "zero_datum_m": 530.18,
      "thresholds": {
        "alert_m": 542.10,
        "warning_m": 542.70,
        "danger_m": 543.30,
        "hfl_m": 545.33
      },
      "series": [
        {
          "forecast_time": "2026-09-03T07:00:00+00:00",
          "lead_hours": 1,
          "stage_m": 533.45,
          "discharge_m3s": 98.2,
          "alert_level": "NORMAL",
          "is_above_danger": false
        }
      ]
    }
  ]
}
```

### 3.2 CSV Specification (`?format=csv`)

Designed for direct import into the HEC-RAS Unsteady Flow Boundary Conditions editor:

```csv
site_id,site_name,forecast_time_utc,lead_hours,stage_m,discharge_m3s,alert_level,is_above_danger
SHIVAJI_BRIDGE,Chhatrapati Shivaji Maharaj Bridge (Panchganga Ghat),2026-09-03T07:00:00+00:00,1,533.45,98.20,NORMAL,False
RAJARAM_BRIDGE,Rajaram K.T. Weir (Kasba Bawada),2026-09-03T07:00:00+00:00,1,534.10,98.20,NORMAL,False
```

- **Stage Hydrograph Boundary:** Use `stage_m` column.
- **Flow Hydrograph Boundary:** Use `discharge_m3s` column.
- **Time Alignment:** `forecast_time_utc` formatted in ISO-8601 with UTC offset.

---

## 4. Vertical Datum Alignment Warning (WRD vs. MSL)

!!! danger "Mandatory Vertical Datum Reconciliation"
    All stage values (`stage_m`) returned by HydroCast are referenced to the **Maharashtra Water Resources Department (WRD) gauge datum** ($530.18\text{ m MSL}$ at gauge zero $0'\ 0''$).

    Before assigning `stage_m` as an unsteady water surface boundary condition in HEC-RAS 2D or HydroSim:

    1. **Verify Your Mesh Invert Datum:** If your 2D terrain model (DEM / LiDAR mesh) is referenced to absolute Mean Sea Level (MSL), HydroCast's stages are already in absolute MSL ($530.18\text{ m} + \text{depth}$).
    2. **Relative Gauge Inverts:** If your hydraulic mesh uses local channel bed relative elevations ($Z_{local} = 0.0$ at bed), you must apply the datum transformation:
       $$Z_{mesh} = \text{stage\_m} - \text{zero\_datum\_m}$$
    3. **Documented Response Caution:** The `vertical_datum` header field is embedded in every JSON payload to prevent engineers from silently applying mismatched vertical reference frames.

---

## 5. Single-Cycle Forecast Window Isolation

To prevent boundary condition discontinuities that destabilize 2D hydrodynamic solvers:

- **Isolated Query Execution:** The database query fetches records from the single latest completed run:
  ```sql
  SELECT run_id FROM simulation_runs WHERE status = 'completed' ORDER BY start_time DESC LIMIT 1;
  ```
- **Zero Inter-Cycle Blending:** The API never stitches or blends time-series points across consecutive 6-hourly cycles. Each payload represents a coherent, continuous 90-hour physical hydrograph.
- **Client Cache Invalidation:** Clients must key their caching by `cycle_id` (e.g. `CYC_20260903_06z`), never by local operating system wall-clock time.

---

## 6. Python Automation Client Example

```python
import os
import requests

HYDROCAST_URL = os.getenv("HYDROCAST_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("HYDROCAST_READONLY_KEY", "hydrocast_PS_V1_sample_key")

def pull_hydrosim_boundary():
    url = f"{HYDROCAST_URL}/api/v1/hydrocast/water-levels"
    headers = {"X-API-Key": API_KEY}
    params = {"format": "csv"}

    response = requests.get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()

    with open("boundary_unsteady.csv", "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"Successfully retrieved boundary conditions ({len(response.text)} bytes).")

if __name__ == "__main__":
    pull_hydrosim_boundary()
```
