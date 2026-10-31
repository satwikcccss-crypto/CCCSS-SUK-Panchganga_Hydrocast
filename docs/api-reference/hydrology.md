---
title: Hydrology Engine Reference
---

# Hydrology Engine Reference

The physics: turning rainfall and channel geometry into stage.

---

## Interactive diagram consoles

The console below provides interactive visualization of the catchment hydrology core across the 9 subbasins (AMC classification, dynamic initial abstraction, SCS-UH convolution, and 5-reach Muskingum cascade).

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 10</span>
      <strong>Catchment Hydrology Solver (Runoff & Muskingum Routing)</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../../diagrams/10-catchment-hydrology-solver.html" target="_blank" rel="noopener">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../../diagrams/10-catchment-hydrology-solver.html?embed=1" title="Catchment Hydrology Solver Console" loading="lazy"></iframe>
</div>

---

## Pipeline position

`stage_converter` sits between the routing engine and everything that consumes a
water level. It receives discharge per reach from `runner.py`, applies the rating
curve, and returns stage in metres above mean sea level together with the WRD
alert class. `runs_tracker` then persists the result and updates the run index
that backs `GET /api/v1/runs`.


---

## Pipeline position

`stage_converter` receives discharge per reach from `runner.py` and returns stage
in metres above mean sea level with the WRD alert class attached. `runs_tracker`
persists the result and updates the index behind `GET /api/v1/runs`.

The hydrology package does not route or transform rainfall itself — that happens
in `src/hms/runner.py`. What lives here is the conversion and the bookkeeping:
WRD-anchored PCHIP rating curves for the two gauged sections, Manning's equation
as the fallback when a section has no fitted curve, and the run archive.


## `src/hydrology/stage_converter.py`

Rating-curve construction, Manning's Divided Channel Method, WRD anchor
handling and alert classification.

::: src.hydrology.stage_converter

---

## `src/hydrology/runs_tracker.py`

JSON run archive on disk plus the `runs_index.json` pointer table that backs
`GET /api/v1/runs`.

::: src.hydrology.runs_tracker
