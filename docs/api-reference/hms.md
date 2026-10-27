---
title: HEC-HMS Engine Reference
---

# HEC-HMS Engine Reference

The hydrologic engine. HEC-HMS cannot run on the Linux production host, so
this module ships a calibrated pure-Python twin of the `Basin_1.basin` model
that reproduces the same loss / transform / routing continuum.

---

## Execution decision tree

The module prefers the native HEC-HMS binary when it is present and runnable, and
falls back to the Python emulator otherwise. The binary is used to produce the
DSS artefacts and the run log; the numbers written into the forecast always come
from the emulator, because the binary's results are never parsed back. This is a
deliberate choice recorded in the errors register, not an oversight.


---

## Emulator internals

The emulator walks the same three-stage chain as the HEC-HMS project: SCS Curve
Number loss per subbasin, SCS unit hydrograph convolution to a subbasin
hydrograph, and Muskingum routing along each reach. It reads its parameters from
`Basin_1.basin` through the same parser the calibration engine uses, so the two
can never disagree about the model definition.


---

## Execution decision tree

`execute_hec_hms(run_dt, subbasin_hyetographs, live_stage_m, parameter_overrides)`
resolves to one of two engines before any work starts:

| Condition | Engine | Consequence |
|:---|:---|:---|
| `HMS_HOME` set and `hec-hms.cmd` present | Native HEC-HMS 4.13 | DSS artefacts and the run log are produced |
| `HMS_FORCE_EMULATOR=1` | Pure-Python engine | No Java dependency, ~15 ms per run |
| `HMS_HOME` missing | Pure-Python engine | Same as forced |

The native path snapshots `Control_1.control` with `snapshot_control_spec()`,
rewrites the 90-hour simulation window with `patch_control_spec(run_dt)`, emits
`compute.jy` with `write_jython_script()`, and runs it under a 300-second cap.
The original control spec is restored in a `finally` block regardless of outcome.
A non-zero exit code does not abort the cycle — the emulator is used instead.

`subbasin_hyetographs` is the full $\{S_1 \ldots S_9\} \to 90 \times
\text{mm/hr}$ matrix. The emulator's first step is `classify_amc()` on the mean
90-hour catchment rainfall: below 25 mm is AMC-I, 25–65 mm is AMC-II as designed,
and above 65 mm is AMC-III.


## `src/hms/basin_parser.py`

The single loader for `Basin_1.basin`. Consumed by both the emulator and the
calibration engine so the two can never disagree about the model definition.

::: src.hms.basin_parser

---

## `src/hms/runner.py`

::: src.hms.runner
