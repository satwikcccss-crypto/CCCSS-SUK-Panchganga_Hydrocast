---
title: HEC-DSS Writer Reference
---

# HEC-DSS Writer Reference

The single canonical HEC-DSS binary writer.

---

## Pathname convention

Every binary `PRECIP-INC` record in the project — from the operational pipeline
and from the offline CLI alike — is produced by `write_gage_to_dss()`,
guaranteeing one pathname convention:


Worked example — subbasin S3 (Kotoli) forecast issued 29 Sep 2026 00z:

```
  SUBBASIN_TO_GAGE["S3"] → "KOTOLI"
  d_part = "29SEP2026"
  ⇒  //KOTOLI/PRECIP-INC/29SEP2026/1HOUR/GAGE/
```

### Why the A-part is empty

HEC-HMS's Gage Manager reads gage records by scanning the **B-part** (the gage
name) within the basin it was configured against. Grouping records under a
`/PANCHGANGA/...` A-part — as the earlier offline tool did — produced a file the
Gage Manager would not resolve, because it looked for a top-level `KOTOLI`
record and found `PANCHGANGA/KOTOLI` instead. The current scheme is the one
HEC-HMS actually expects.

### One writer, three callers

Three callers write precipitation to DSS — the operational pipeline, the offline
CLI, and the calibration rerun — and all three go through `write_gage_to_dss()`.
That is the guarantee behind the single pathname convention: there is no second
code path that could drift from it.


---

## Conventions

Pathname: `//<GAGE>/PRECIP-INC/<DDMMMYYYY>/1HOUR/GAGE/`. The A-part (watershed) is
empty because HEC-HMS's Gage Manager resolves gage records by the B-part; the
earlier `PANCHGANGA/<GAGE>` form was never found by the Manager.

Callers: the operational pipeline (`open_meteo.py` via
`station_rainfall_to_dss`), the offline CLI, and the calibration rerun under
`HMS_Automation_RJKT`. If the DSS library is unavailable the writer falls back to
the CSV table, and the run log records which path was taken.


## `src/dss/writer.py`

::: src.dss.writer
