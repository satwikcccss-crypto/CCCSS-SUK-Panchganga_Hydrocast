---
title: Calibration & Validation Reference
---

# Calibration & Validation Reference

How the model is corrected by live telemetry, and how it is scored without
flattering itself.

---

## Discrepancy detection → recalibration

```text
  previous cycle forecast           ThingSpeak hourly cache
   (bridgeShivaji.forecast)          (observed_stage_m per hour)
            │                                    │
            └──────────────┬─────────────────────┘
                           ▼
        detect_timing_and_stage_discrepancy()
                           │
        ┌──────────────────┴───────────────────┐
        │                                      │
   NOT warranted                        warranted
   |Δt| < 1.0 h  AND                  |Δt| ≥ 1.0 h  OR
   |Δh| ≤ 0.25 m                      |Δh| > 0.25 m
        │                                      │
        ▼                                      ▼
  log "Baseline Stable"          recalibrate_parameters(Δt, Δh, hyetos)
                                         │
                                         ▼
                            ┌────────────────────────────┐
                            │  Levenberg–Marquardt        │
                            │  scipy.optimize             │
                            │    .least_squares(method=lm)│
                            │                            │
                            │  parameters p =            │
                            │   α_K    ∈ [0.50, 1.80]    │
                            │   α_lag  ∈ [0.50, 1.80]    │
                            │   ΔCN    ∈ [−8.0, 8.0]     │
                            │   X      ∈ [0.15, 0.40]    │
                            │                            │
                            │  residuals =               │
                            │   (q_sim − q_target)/scale  │  hydrograph
                            │   (timing error)/2.0        │  physics anchor
                            │   (−ΔCN/4.5 − Δh)/0.25       │  stage anchor
                            │   (X − X_expected)/0.05      │  wave shape
                            │                            │
                            │  max_nfev = 25              │
                            └─────────────┬──────────────┘
                                          ▼
                            sync_to_hec_hms_basin(params)
                            ├─ Basin_1.basin.bak_<ts>
                            └─ os.replace() atomic swap
```

`q_target` is the *baseline* emulator hydrograph, translated by the timing offset
and rescaled by the observed peak-discharge error — so the optimiser is fitting a
real simulated hydrograph to a physically-motivated target, not minimising a
hand-constructed scalar surrogate.

!!! note "Test safety"
    `save_calibration_state()` short-circuits when `PYTEST_CURRENT_TEST` is set,
    so a test run that explores extreme parameter bounds can never overwrite the
    live `data/telemetry/ml_calibration_state.json` that production reads.

---

## Metric reliability gating

```text
              matched (predicted, observed) pairs
                           │
                    n = 0 ────────────────────► status  INSUFFICIENT_DATA
                           │                     grade   ACCUMULATING_TELEMETRY
                    n ≥ 1
                           │
             ┌─────────────┴──────────────┐
             │                            │
     ERROR metrics                   SKILL metrics
     (always defined)                 NSE · Spearman · Pearson
     RMSE · MAE · PBIAS                      │
             │                       needs ALL THREE:
             │                       • n ≥ MIN_CORRELATION_SAMPLES (6)
             │                       • σ(observed) ≥ 0.05 m
             │                       • Σ(O−Ō)² > 1e-4
             │                                │
             │              not met ──► all three reported as None
             │                                │   skill_metrics_reliable = false
             │                                │   grade = BASEFLOW_STABLE (flat
             │                                │            observed) or
             │                                │   ACCUMULATING_TELEMETRY (short)
             │                                ▼
             └────────────────────────────►  grade from the Moriasi ladder
```

```text
   nse_stage is not None
     ├── nse ≥ 0.75 → EXCELLENT
     ├── nse ≥ 0.60 → VERY_GOOD
     ├── nse ≥ 0.40 → SATISFACTORY
     ├── nse > 0.0  → MODERATE_BIAS
     └── nse ≤ 0.0  → CALIBRATION_REQUIRED   (never grades better)
```

!!! warning "Discharge metrics are derived, not measured"
    The sensor measures **stage only**. "Observed discharge" is that stage pushed
    through the same WRD rating curve that produced the forecast, so discharge
    metrics are a monotone transform of the stage errors. Every payload labels
    them `discharge_metrics_source: "RATING_IMPLIED_DERIVED"` and carries an
    explicit `discharge_metrics_note` so they are never mistaken for an
    independent discharge measurement.

---

## `src/hydrology/ml_calibration.py`

::: src.hydrology.ml_calibration

---

## `src/hydrology/realtime_telemetry_validator.py`

ThingSpeak ingestion, hourly resampling, per-run lifecycle state machine and
pure metric computation.

::: src.hydrology.realtime_telemetry_validator

---

## `src/hydrology/validation_metrics.py`

In-process accuracy evaluation over a stored run payload.

::: src.hydrology.validation_metrics
