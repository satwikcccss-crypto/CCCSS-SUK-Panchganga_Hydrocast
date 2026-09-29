---
title: HEC-HMS Engine Reference
---

# HEC-HMS Engine Reference

The hydrologic engine. HEC-HMS cannot run on the Linux production host, so
this module ships a calibrated pure-Python twin of the `Basin_1.basin` model
that reproduces the same loss / transform / routing continuum.

---

## Execution decision tree

```text
  execute_hec_hms(run_dt, subbasin_hyetographs, live_stage_m, parameter_overrides)
        │
        ├─► snapshot_control_spec()          cache pristine Control_1.control
        ├─► patch_control_spec(run_dt)       rewrite the 90 h simulation window
        ├─► write_jython_script()            emit compute.jy
        │
        ▼
  ┌──────────────────────────────────┐
  │ find_hec_hms()                   │
  │ HMS_HOME + hec-hms.cmd present?  │
  └──────────────┬───────────────────┘
                 │
     HMS_FORCE_EMULATOR=1 ─────────────┐  overrides everything
                 │                      │
                 no                     yes
                 │                      │
                 ▼                      ▼
  ┌────────────────────────┐   ┌────────────────────────────────┐
  │ native HEC-HMS 4.13    │   │  PURE-PYTHON PHYSICAL ENGINE    │
  │ subprocess (300 s cap)  │   │  compute_emulator_hydrograph()  │
  │ returns 0 ──> real DSS │   │  ~15 ms, no Java dependency     │
  └──────────┬─────────────┘   └────────────────┬───────────────┘
             │ non-zero / missing               │
             └──────────────┬───────────────────┘
                            ▼
              restore_control_spec()   put Control_1.control back
                            │
                            ▼
              hydrograph JSON  ──►  stage_converter  ──►  alerts
```

---

## Emulator internals

```text
  subbasin_hyetographs: {S1..S9 → 90 × mm/hr}
            │
            │  ┌─────────────────────────────────────────────────┐
            │  │ STEP 1  classify_amc(mean 90 h catchment rain)  │
            │  │   < 25 mm        → AMC-I   (TR-55 dry)          │
            │  │   25 .. 65 mm    → AMC-II  (as-designed)        │
            │  │   ≥ 65 mm        → AMC-III (TR-55 saturated)    │
            │  └───────────────────────┬─────────────────────────┘
            │                          │  Ia/S = 0.20 / 0.15 / 0.08
            ▼                          ▼
  ┌──────────────────────────────────────────────────────────────┐
  │ STEP 2  SCS Curve Number loss   (per subbasin)               │
  │   S  = 25400/CN − 254                                          │
  │   Qc = (Pc − Ia)² / (Pc − Ia + S) + 0.02·Pc                    │
  │   ΔPexcess = max(0, Qc(h) − Qc(h−1))                          │
  ├──────────────────────────────────────────────────────────────┤
  │ STEP 3  SCS dimensionless UH    (per subbasin)               │
  │   tp = 0.5 + lag_min/60                                        │
  │   u(t) = (t/tp)^3.7 · exp[3.7(1 − t/tp)]                     │
  │   normalised so Σ u·3600 = area_km² × 1000  (1 mm mass)       │
  │   Qdir = ΔPexcess (*) UH                                      │
  ├──────────────────────────────────────────────────────────────┤
  │ STEP 4  Muskingum routing, network order = Basin_1.basin      │
  │                                                              │
  │   S6 ─┐                                                      │
  │   S7 ─┴─► R5 ─┐                                              │
  │              ├─► R2 ─┐                                       │
  │   S9 ────► R4 ─┘    │                                       │
  │   S8 ────────────────┤                                       │
  │                     ├─► R1 ─┬─► q_surface ──┐                │
  │   S4 ─┐             │       │               ├─► q_total     │
  │   S5 ─┴─► R3 ───────┘       │               │                │
  │   S2 ────────────────────────┤   + baseflow ┘                │
  │   S3 ────────────────────────┘   exp(−0.002·t)               │
  │                                                              │
  │   S1 (Karveer) bypasses the network, adds at Sink-1          │
  ├──────────────────────────────────────────────────────────────┤
  │ STEP 5  peak = argmax(q_total)     ← never overridden         │
  │         is_significant_event = (Q_peak − Q_bf) > max(1, 10%Q₀) │
  └──────────────────────────────────────────────────────────────┘
```

---

## `src/hms/basin_parser.py`

The single loader for `Basin_1.basin`. Consumed by both the emulator and the
calibration engine so the two can never disagree about the model definition.

::: src.hms.basin_parser

---

## `src/hms/runner.py`

::: src.hms.runner
