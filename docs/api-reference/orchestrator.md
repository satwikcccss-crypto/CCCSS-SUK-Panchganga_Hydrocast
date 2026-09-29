---
title: Pipeline Orchestrator Reference
---

# Pipeline Orchestrator Reference

The cycle driver.

---

## The 10-step cycle

```text
  create_cycle(cycle_id, run_dt)
  INSERT INTO simulation_runs (run_id, cycle_date, cycle_time, start_time, status)
            │
            ▼
  ┌───────────────────────────────────────────────────────────────────┐
  │  1  download weather   src.ecmwf.downloader.run(date, time)       │
  │  2  ...                                                            │
  │  3  validate            src.processing.validator                  │
  │  4  select stations     src.ecmwf.station_selector                │
  │  5  write DSS           src.dss.writer                             │
  │  6  check parameters    basin file sanity                         │
  │  7  run HMS             src.hms.runner.run_hms(dt, subs, hyetos)  │
  │  8  extract results     read_outlet_hydrograph(dt, hyetos)        │
  │  9  stage conversion    src.hydrology.stage_converter             │
  │ 10  store to DB / 11 alert / 12 broadcast                          │
  └───────────────────────────────────────────────────────────────────┘
            │
            ▼
  every step wrapped in timed_step(conn, cycle_id, n, name)
    INSERT INTO pipeline_step_log (step_number, step_name, status,
                                   start_time, end_time, duration_seconds,
                                   error_message)
```

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

## `src/orchestrator.py`

::: src.orchestrator
