---
title: Processing & QC Reference
---

# Processing & QC Reference

Pre-simulation data-quality control and the offline DSS conversion CLI.

---

## Pre-run QC gate

```text
  step 3  validate_cycle(conn, run_dt)          BEFORE any data is written
            │
            ├── _check_ecmwf_freshness  ──►  source_id = 'selected_gauge'
            │       empty table?  ──►  WARN (fresh DB / first cycle is expected)
            │       age > threshold ─►  WARN
            │       else              ──►  OK
            │
            ├── _check_gauge_coverage  ──►  every active station present?
            │
            └── report{critical_failures, warnings, details}
                    │
                    ├── critical_failures > 0 ──► pipeline ABORTS
                    └── warnings only         ──► pipeline CONTINUES
```

!!! note "Why freshness is only a warning"
    The step-3 QC runs *before* step 4 writes the selected-gauge rows. On a fresh
    database the table is legitimately empty, so treating that as a critical
    failure would make the first cycle of every new deployment impossible. It is
    a warning, and the check is now correctly scoped to `selected_gauge` rows
    (the ones the run actually consumed) rather than to raw ECMWF rows.

---

## `src/processing/validator.py`

::: src.processing.validator

---

## `src/processing/station_rainfall_to_dss.py`

Standalone offline CSV → DSS converter. Binary writes are **delegated** to the
canonical `src/dss/writer.py` so the offline tool and the operational pipeline
produce byte-identical pathname conventions:

```text
  //<GAGE>/PRECIP-INC/<DDMMMYYYY>/1HOUR/GAGE/
```

The offline CSV table and the Jython import script use the same scheme, so a
file produced without `pydsstools` installed is still directly loadable by
HEC-DSSVue.

::: src.processing.station_rainfall_to_dss
