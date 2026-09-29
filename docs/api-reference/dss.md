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

```text
  //<GAGE>/PRECIP-INC/<DDMMMYYYY>/1HOUR/GAGE/
         │      │            │          │   │
         │      │            │          │   └── C-part: the Gage Manager
         │      │            │          │        record type
         │      │            │          └────── E-part: 1HOUR interval
         │      │            └───────────────── D-part: block start date
         │      └────────────────────────────── B-part: the gauge alias
         └───────────────────────────────────── A-part: empty (no basin
                                                  grouping; HEC-HMS Gage
                                                  Manager expects this)
```

Worked example — subbasin S3 (Kotoli) forecast issued 29 Sep 2026 00z:

```text
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

```text
              ┌────────────────────────────────────────────┐
              │        src/dss/writer.py                  │
              │        write_gauge_to_dss()                │
              │        (single implementation)            │
              └───────┬──────────────────┬────────────────┘
                      │                  │
       ┌──────────────▼──────┐  ┌────────▼─────────────────┐
       │ operational cycle   │  │ offline CLI              │
       │ src/ecmwf/          │  │ src/processing/           │
       │   open_meteo.py     │  │   station_rainfall_to_    │
       │ writes into         │  │   dss.py                  │
       │ HMS_Automation_     │  │ falls back to CSV table + │
       │ RJKT.dss            │  │ Jython script using the   │
       └─────────────────────┘  │ SAME pathname scheme      │
                                └──────────────────────────┘
```

---

## `src/dss/writer.py`

::: src.dss.writer
