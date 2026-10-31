---
title: Calibration & Validation Reference
---

# Calibration & Validation Reference

How the model is corrected by live telemetry, and how it is scored without
flattering itself.

---

## Interactive diagram consoles

The console below provides interactive visualization of the physics-informed adaptive parameter recalibrator (bounded Levenberg-Marquardt / L-BFGS-B optimization, rising limb detection, gated ML predictor, and atomic `.basin` syncing).

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 15</span>
      <strong>Real-Time Adaptive ML Recalibration</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../../diagrams/15-ml-calibration.html" target="_blank" rel="noopener">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../../diagrams/15-ml-calibration.html?embed=1" title="Real-Time Adaptive ML Recalibration Console" loading="lazy"></iframe>
</div>

---

## Discrepancy detection → recalibration


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


!!! warning "Discharge metrics are derived, not measured"
    The sensor measures **stage only**. "Observed discharge" is that stage pushed
    through the same WRD rating curve that produced the forecast, so discharge
    metrics are a monotone transform of the stage errors. Every payload labels
    them `discharge_metrics_source: "RATING_IMPLIED_DERIVED"` and carries an
    explicit `discharge_metrics_note` so they are never mistaken for an
    independent discharge measurement.

---

## What the calibrator compares

The engine holds two series over the same window: the previous cycle's forecast
stage at the bridge (`bridgeShivaji.forecast`) and the ThingSpeak hourly cache of
observed stage. `detect_timing_and_stage_discrepancy()` reduces them to two
scalars — a timing error $\Delta t$ in hours and a stage error $\Delta h$ in
metres — which the gate then tests.

When the gate fires, `recalibrate_parameters(Δt, Δh, hyetograph)` runs, with the
hydrograph scaled by $(q_{sim} - q_{target})/scale$ and the timing anchor weighted
at $\Delta t / 2.0$. When it does not fire, the run logs `Baseline Stable` and
nothing is written.

The skill scores are computed only over matched (predicted, observed) pairs. All
three — NSE, Spearman and Pearson — are reported as `None` if the pair set is
empty, and `skill_metrics_reliable = false` is set. An NSE at or below zero is
classified `CALIBRATION_REQUIRED` and is never allowed to grade better than the
baseline.


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

---

## `src/hydrology/ml_parameter_predictor.py`

Gated machine learning parameter predictor with strict 3-state lifecycle (`UNTRAINED`, `TRAINED_UNVALIDATED`, `VALIDATED`) and feature extraction.

::: src.hydrology.ml_parameter_predictor
