---
title: Data Ingestion Reference
---

# Data Ingestion Reference

Where the forecast inputs come from, and how governing gauges are chosen.

---

## Cycle ingestion order


!!! info "Why is the soil-moisture step observational only?"
    Antecedent moisture currently activates through a rainfall-magnitude proxy
    (`classify_amc`), because the automation path has no observed 5-day gauge
    record. ERA5-Land soil moisture is the *physically correct* antecedent
    wetness signal. Capturing it every cycle means the archive is already in
    place the day the AMC classifier is upgraded from proxy to measurement —
    without ever letting an unvalidated field change a forecast.

---

## Request shape and station selection

The forecast request is a single Open-Meteo call —
`GET /v1/forecast?models=ecmwf_ifs&hourly=precipitation` — over the catchment
bounding box. `forecast_days` is computed as
$\lceil (\text{start\_hour} + 90)/24 \rceil$ rather than hard-coded to 4, so a
cycle that starts at 18z still receives a full 90-hour series. Responses are
cached for one hour and retried five times with a 0.2 s exponential backoff.

Station selection is database-first, per subbasin:

1. If the station's latest stored observation is younger than 6 hours, it is
   selected and tagged `source_id = "selected_gauge"`.
2. Otherwise the grid cell covering the subbasin centroid is used and tagged
   `source_id = "grid_fallback"`.

The output is one governing gauge per subbasin, $S_1 \ldots S_9$, expanded to 18
stations across the two sites.

Soil moisture is a fetch-and-log step, not a modelled input: 90 hours across four
ERA5-Land layers plus five antecedent daily values, clipped to
$[0.00, 0.60]\ \text{m}^3/\text{m}^3$. A failed fetch is swallowed and the cycle
continues.


## `src/ecmwf/open_meteo.py`

::: src.ecmwf.open_meteo

---

## `src/ecmwf/station_selector.py`

The canonical station selector (moved here from `src/processing/`).

::: src.ecmwf.station_selector

---

## `src/processing/gauge_fetcher.py`

IoT gauge ingestion into `rainfall_data`.

!!! warning "No silent reanalysis fallback"
    If the IoT fetch for a station fails, the station is **skipped** and the
    failure is logged as an error. It is *not* back-filled from Open-Meteo
    historical reanalysis, because a forecast cycle scored against the same
    reanalysis it was generated from would certify itself.

::: src.processing.gauge_fetcher
