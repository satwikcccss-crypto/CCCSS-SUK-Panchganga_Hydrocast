# 04 — Meteorology & Rainfall Ingestion

## Scope

This document covers how HydroCast acquires quantitative precipitation forecasts (QPF) and distributes them to the 9 Panchganga subbasins for the hydrological model.

## Data Source — ECMWF IFS via Open-Meteo

| Property | Value |
|----------|-------|
| Provider | Open-Meteo (free tier, no API key required) |
| Model | ECMWF IFS (Integrated Forecasting System) |
| Resolution | ~9 km (0.1°) global grid |
| Forecast Horizon | 90 hours (aligned to 4-day IFS runs) |
| Temporal Resolution | Hourly |
| Variable | `precipitation` (mm/hr) |
| Bounding Box | N 17.20°, S 16.20°, E 74.50°, W 73.70° |
| Update Cadence | 4 cycles/day (00, 06, 12, 18 UTC synoptic hours) |

The bounding box is configurable via environment variables (`BBOX_N`, `BBOX_S`, `BBOX_E`, `BBOX_W`).

**Source**: `backend/rainfall/open_meteo.py`, `PANCHGANGA_BBOX`.

## Rainfall Ingestion Pipeline

### Step 1 — Grid Forecast Download

For each of the 18 rain gauge stations (9 primary + 9 alternate across S1–S9), the system requests a 90-hour hourly precipitation forecast from Open-Meteo at the station's geographic coordinates.

```
GET https://api.open-meteo.com/v1/forecast
    ?latitude={lat}&longitude={lon}
    &hourly=precipitation
    &forecast_days=4
    &timezone=UTC
```

The Open-Meteo client is configured with:
- **Session cache**: 1-hour `requests_cache` to avoid duplicate fetches within the same cycle
- **Automatic retry**: 5 retries with 0.2s exponential backoff

### Step 2 — Station Selection (Max-Rainfall Conservative)

For each subbasin, the system selects the rain gauge station with the **highest cumulative 90-hour rainfall** among the primary and alternate stations assigned to that subbasin. This conservative strategy ensures the flood forecast is not underestimated.

See [05 Station Network](05-station-network.md) for the station registry and selection algorithm.

### Step 3 — Areal Rainfall Assignment

Each subbasin receives the 90-hour hourly hyetograph from its selected station as its spatially representative rainfall. This is a nearest-gauge / Thiessen polygon approach (single-station per subbasin) rather than grid interpolation, consistent with the operational station density.

## Soil Moisture (Fetch-and-Log Only)

Each cycle also fetches ERA5-Land soil moisture data (4 layers: 0–7 cm, 7–28 cm, 28–100 cm, 100–255 cm) for future antecedent moisture condition (AMC) refinement. These values are logged with each run but are **not used in runoff decisions** — the AMC classification currently uses the simpler rainfall-threshold method.

**Source**: `backend/rainfall/open_meteo.py`, `SOIL_MOISTURE_LAYERS`.

## Three-Tier Failsafe

The weather download step uses a failsafe strategy (`backend/rainfall/open_meteo_failsafe.py`):

1. **Tier 1 — Live Open-Meteo API**: Primary path. ECMWF IFS hourly QPF.
2. **Tier 2 — Cached Forecast**: If the API is down, the system uses the most recent cached forecast from `data/openmeteo_dss/`.
3. **Tier 3 — Climatological Fallback**: If no cached data is available, the system uses long-term monthly mean rainfall for the Panchganga catchment (conservative high values for monsoon months).

The failsafe ensures the pipeline never stalls waiting for weather data.

## Output

The meteorology module produces:
- **9 subbasin hyetographs** (90-point hourly rainfall in mm/hr)
- **Station selection log** (which gauge governs each subbasin and why)
- **Cumulative rainfall per subbasin** (mm over 90 hours)
- **Soil moisture snapshot** (m³/m³, 4 layers, logged for future use)

These feed directly into the SCS-CN loss model ([02 Hydrology](02-hydrology.md)).

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/rainfall/ecmwf` | 90-hr ECMWF hyetograph per subbasin |
| `GET /api/v1/rainfall/stations` | Station selection log for latest cycle |
| `GET /api/v1/rainfall/gauges` | All raw gauge hyetographs (18 stations) |
