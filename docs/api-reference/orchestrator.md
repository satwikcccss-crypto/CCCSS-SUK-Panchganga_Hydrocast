---
title: Pipeline Orchestrator Reference
---

# Pipeline Orchestrator Reference

The cycle driver.

---

## The 10-step cycle


`timed_step()` is a context manager: it records `running` on entry, and on exit
records `success` or `failed` together with the elapsed time and any exception
text. That table is exactly what `GET /api/v1/pipeline` renders and what the
`pipeline_ok` boolean on `GET /api/v1/status` is computed from.

!!! note "Hyetographs are passed forward, not re-read"
    Steps 7 and 8 take the `subbasin_hyetographs` mapping as an argument. The
    orchestrator builds it once from the step-4 selection results and threads it
    through, so the simulation and the result extraction provably consume the
    same input rather than two independent lookups that could disagree.

---

## The twelve-step cycle

`create_cycle(cycle_id, run_dt)` inserts the run row, then executes the pipeline.
Every step is wrapped in `timed_step(conn, cycle_id, n, name)`, which writes a
`pipeline_step_log` row with the start time, end time, duration and status.

| # | Step | Call |
|:---:|:---|:---|
| 1 | Download weather | `src.ecmwf.downloader.run(date, time)` |
| 2 | Ingest gauges | WRD + IMD ground stations |
| 3 | Validate | `src.processing.validator` |
| 4 | Select stations | `src.ecmwf.station_selector` |
| 5 | Build hyetographs | per-subbasin 90-hour series |
| 6 | Check parameters | `Basin_1.basin` sanity |
| 7 | Run HMS | `src.hms.runner.run_hms(dt, subs, hyetos)` |
| 8 | Extract results | `read_outlet_hydrograph(dt, hyetos)` |
| 9 | Stage conversion | `src.hydrology.stage_converter` |
| 10 | Store | forecast and stage rows |
| 11 | Alert | threshold evaluation |
| 12 | Broadcast | dashboard refresh and Telegram |

A failure in a step marks the run `FAILED` and stops the pipeline; the step log
identifies which one. The archive is written even for a failed run, so the
duration of the failure is visible in the waterfall.


## `src/orchestrator.py`

::: src.orchestrator
