---
title: Processing & QC Reference
---

# Processing & QC Reference

Pre-simulation data-quality control and the offline DSS conversion CLI.

---

## Pre-run QC gate


!!! note "Why freshness is only a warning"
    The step-3 QC runs *before* step 4 writes the selected-gauge rows. On a fresh
    database the table is legitimately empty, so treating that as a critical
    failure would make the first cycle of every new deployment impossible. It is
    a warning, and the check is now correctly scoped to `selected_gauge` rows
    (the ones the run actually consumed) rather than to raw ECMWF rows.

---

## Validation contract

`validate_cycle(conn, run_dt)` runs at step 3, before any forecast data is
written. It returns `{critical_failures, warnings, details}`.

`_check_ecmwf_freshness` requires a row for the cycle with
`source_id = 'selected_gauge'`; an empty table produces a warning rather than a
failure, because a fresh database on its first cycle is expected to be empty.
`_check_gauge_coverage` requires every active station to be present in the
cycle's gauge set.

The rule is absolute: any critical failure aborts the pipeline before step 4, and
warnings alone let it continue. Nothing is written and nothing is alerted on a
failed validation.


## `src/processing/validator.py`

::: src.processing.validator

---

## `src/processing/station_rainfall_to_dss.py`

Standalone offline CSV → DSS converter. Binary writes are **delegated** to the
canonical `src/dss/writer.py` so the offline tool and the operational pipeline
produce byte-identical pathname conventions:

```python
  //<GAGE>/PRECIP-INC/<DDMMMYYYY>/1HOUR/GAGE/
```

The offline CSV table and the Jython import script use the same scheme, so a
file produced without `pydsstools` installed is still directly loadable by
HEC-DSSVue.

::: src.processing.station_rainfall_to_dss
