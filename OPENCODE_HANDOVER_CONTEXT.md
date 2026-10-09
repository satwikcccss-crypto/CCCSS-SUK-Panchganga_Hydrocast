# OpenCode Session Handover & State Snapshot

**Date:** 2026-10-09  
**Repository:** `E:\hydrocast_complete`  
**Purpose:** Full context restore for OpenCode after session termination/credit exhaustion. Contains current state, completed work, root causes, remaining todos, and the new Telegram Bot RBAC requirements.

---

## 1. Executive Summary & Problem Diagnosis

### Root Cause of the ~2.0–2.15 m Constant Stage Bias
* **Symptom:** Run `CYC_20260929_18z` in `data/openmeteo_dss/latest_pipeline_state.json` reported `mae_stage_m=2.023`, `rmse_stage_m=2.024`, flat forecast at ~532.41–532.42 m MSL vs observed 530.34–530.44 m MSL.
* **Why it's a Datum/Baseflow Anchoring Bias (NOT a CN/lag/K calibration problem):**
  - A constant flat stage error across time cannot stem from SCS Curve Number ($CN$) or Muskingum routing ($K, X$), which affect hydrograph wave shapes and peak magnitudes dynamically.
  - Observed stage at Shivaji Bridge (~530.39 m MSL) sits **1.66 m below the lowest WRD-gauged stage** (532.052 m MSL). In this ungauged low-flow regime, the rating curve is an extrapolated shape where $Q \approx 2.0\text{--}2.6\text{ m}^3/\text{s}$.
  - Two historical bugs fabricated this bias:
    1. **Old 40 m³/s floor:** `runner.py` previously floored baseflow at `WRD_MONSOON_BASEFLOW_FLOOR_M3S = 40.0`, which evaluates to $532.42\text{ m}$ MSL on the Shivaji rating curve ($532.42 - 530.40 \approx 2.02\text{ m}$).
    2. **Hardcoded sensor fallback:** `src/ecmwf/open_meteo.py` (lines ~435-438) previously hardcoded `live_stage = 532.60` whenever ThingSpeak live telemetry failed. Validation then compared this against cached observed stage (~530.40 m), injecting a $+2.2\text{ m}$ artificial error.

---

## 2. Completed Work State

### A. Low-Flow Baseflow Fallback Fix (`src/ecmwf/open_meteo.py`)
- **[COMPLETED]** Added `_latest_cached_observation()` to query `load_telemetry_cache()`.
- **[COMPLETED]** Replaced the hardcoded `live_stage = 532.60` fallback with the most recent cached observation (`stage_m`, `raw_feet`).
- **[COMPLETED]** If no cache exists, set `live_stage = None` and mark `telemetry_source = "NO_OBSERVATION"`, rather than inventing a stage.
- **[COMPLETED]** Recorded `telemetry_source` in `bridge_shivaji`.

### B. Low-Flow Guard & Ungauged Rating Detection
- **[COMPLETED]** In `src/hydrology/stage_converter.py`:
  - Added `MAX_BASEFLOW_STAGE_OFFSET_M = 0.5`.
  - Added `assess_low_flow_guard(predicted_stages, observed_stages, site_id, max_offset_m)` which detects:
    - `constant_bias_detected` (when observed variance $< 0.05\text{ m}$ and $|offset| > 0.5\text{ m}$).
    - `rating_extrapolated` (when observed stage $< \text{WRD\_LOWEST\_GAUGE\_STAGE\_M}$).
    - `ungauged_fraction` and explanatory human notes.
- **[COMPLETED]** In `src/hydrology/validation_metrics.py`:
  - Integrated `low_flow_guard` into `evaluate_forecast_accuracy()`.
  - Labels runs with persistent baseflow offsets as `performance_grade = "BASEFLOW_MISMATCH"` / badge `"rose"` rather than `BASEFLOW_STABLE`.
- **[COMPLETED]** In `src/hydrology/realtime_telemetry_validator.py`:
  - Integrated `low_flow_guard` into `compute_pure_metrics()`.

### C. ML Recalibration Loop & Baseline Hardening
- **[COMPLETED]** In `src/hms/basin_parser.py`: Implemented `load_immutable_baseline()` and `data/telemetry/calibration_baseline.json` to freeze physics priors so recalibration doesn't exponentially compound on itself.
- **[COMPLETED]** In `src/hydrology/ml_calibration.py`: Fixed signed stage error `detect_timing_and_stage_discrepancy()`, added peak flow error `peak_discharge_error_m3s`, dynamic Levenberg–Marquardt confidence %, and set `is_recalibrated = True`.
- **[COMPLETED]** In `frontend/components/AccuracyPanel.tsx` & `SystemPanel.tsx`: Updated dashboard to reflect Levenberg–Marquardt parameters, signed $\Delta h$, peak error $\Delta Q_{\text{peak}}$, and dynamic status.

---

## 3. Tasks Completed & Verified (Handover Resolved)

### Task 1: Stale Artifact Synchronization & Cleanup [COMPLETED]
- Synchronized `data/openmeteo_dss/latest_pipeline_state.json` with `frontend/public/data/latest_pipeline_state.json`. Verified MAE is now `0.029 m` (the old `2.023 m` stale metric has been eradicated).

### Task 2: Regression Tests for Fallback & Guardrail [COMPLETED]
- Added regression tests in `tests/test_low_flow_stage_bias.py`:
  - `TestLowFlowGuard`: verified `constant_bias_detected=True` and `rating_extrapolated=True` on the 2m offset.
  - `TestTelemetryObservationFallback`: verified `_latest_cached_observation()` uses the cache and never produces `532.60`.
- All 44 tests in `test_low_flow_stage_bias.py` pass.

### Task 3: Telegram Bot Tiered RBAC [COMPLETED]
- Updated `src/alerts/telegram_bot.py`:
  - `@public_command` (rate-limited, open to everyone): `/start`, `/help`, `/stage`, `/alerts`, `/bulletin`, `/id`.
  - `@official_only` (allowlisted + rate-limited for CCCSS, SUK, WRD, DDMA): `/status`, `/rainfall`, `/curvenumbers` (alias `/calibration`), `/logs`.
  - Added `load_latest_pipeline_state()` fallback so `/stage`, `/alerts`, and `/bulletin` function even in standalone mode without Postgres.
  - Documented in `docs/frontend.md`.
  - All 15 tests in `tests/test_alerts_dispatcher.py` pass.

### Task 4: Full Validation & Test Suite [COMPLETED]
- Full test suite passed: `pytest tests -q --no-header` (**154 passed**).
- Full TypeScript typecheck passed: `cd frontend && npx tsc --noEmit -p tsconfig.json` (**0 errors**).
