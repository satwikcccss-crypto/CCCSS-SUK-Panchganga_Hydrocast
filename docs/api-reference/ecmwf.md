---
title: Data Ingestion Reference
---

# Data Ingestion Reference

Where the forecast inputs come from, and how governing gauges are chosen.

---

## Cycle ingestion order

```text
  ┌──────────────────────────────────────────────────────────────────────┐
  │  01  Open-Meteo / ECMWF IFS                                           │
  │      GET /v1/forecast?models=ecmwf_ifs&hourly=precipitation           │
  │      forecast_days = ceil((start_hour + 90) / 24)   ← computed, not 4│
  │      18 stations → 90 hourly mm/hr hyetographs                       │
  │      requests_cache (1 h TTL) + urllib3 Retry(5, backoff 0.2)        │
  └──────────────────────────────┬───────────────────────────────────────┘
                                 ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  02  Dynamic station selection     src/ecmwf/station_selector.py   │
  │      DB-first:  is the station's latest stored observation < 6 h?    │
  │           yes ─► select it, source_id = "selected_gauge"             │
  │           no  ─► fall back to the grid cell covering the subbasin    │
  │                  centroid, source_id = "grid_fallback"               │
  │      per subbasin S1..S9 → one governing gauge                        │
  └──────────────────────────────┬───────────────────────────────────────┘
                                 ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  02b Soil-moisture snapshot        FETCH-AND-LOG ONLY               │
  │      forecast  90 h × 4 ERA5-Land layers   (archive-api/v1/era5)    │
  │      antecedent 5 d daily VWC         (archive-api/v1/era5)          │
  │      clipped to 0.00 .. 0.60 m³/m³; failures are swallowed           │
  │      ⚠ NEVER feeds Curve Numbers, K, x or routing.                    │
  └──────────────────────────────┬───────────────────────────────────────┘
                                 ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  03  DSS boundary file              src/dss/writer.py                │
  │      //<GAGE>/PRECIP-INC/<DDMMMYYYY>/1HOUR/GAGE/                     │
  │      → data/hms/HMS_Automation_RJKT/HMS_Automation_RJKT.dss           │
  └──────────────────────────────────────────────────────────────────────┘
```

!!! info "Why is the soil-moisture step observational only?"
    Antecedent moisture currently activates through a rainfall-magnitude proxy
    (`classify_amc`), because the automation path has no observed 5-day gauge
    record. ERA5-Land soil moisture is the *physically correct* antecedent
    wetness signal. Capturing it every cycle means the archive is already in
    place the day the AMC classifier is upgraded from proxy to measurement —
    without ever letting an unvalidated field change a forecast.

---

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
