---
title: Hydrology Engine Reference
---

# Hydrology Engine Reference

The physics: turning rainfall and channel geometry into stage.

---

## Pipeline position

```text
   hyetographs (mm/hr)                     cross-section (m)
           │                                       │
           ▼                                       ▼
  ┌──────────────────────┐            ┌──────────────────────────┐
  │ src/hms/runner.py    │            │ src/hydrology/           │
  │  compute_emulator_   │  Q_total   │  stage_converter.py      │
  │  hydrograph()        │───────────►│  convert_discharge_to_   │
  │                      │            │  stage_manning()         │
  │  SCS-CN loss         │            │                          │
  │  SCS-UH transform    │            │  WRD-anchored PCHIP      │
  │  Muskingum routing   │            │  (SHIVAJI / RAJARAM)     │
  │  baseflow recession  │            │  falls back to Manning   │
  └──────────────────────┘            │  divided-channel method  │
                                      └───────────┬──────────────┘
                                                  │
                                          stage_m (m MSL)
                                                  │
                                    ┌─────────────▼──────────────┐
                                    │ classify_alert()            │
                                    │  normal < 542.10 < 542.70   │
                                    │  < 543.30 danger < 545.33   │
                                    └────────────────────────────┘
```

---

## `src/hydrology/stage_converter.py`

Rating-curve construction, Manning's Divided Channel Method, WRD anchor
handling and alert classification.

::: src.hydrology.stage_converter

---

## `src/hydrology/runs_tracker.py`

JSON run archive on disk plus the `runs_index.json` pointer table that backs
`GET /api/v1/runs`.

::: src.hydrology.runs_tracker
