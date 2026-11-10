# 06 — Machine Learning

## Scope

This document covers the physics-informed adaptive calibration system. Audience: **Maintainer**.

## Architecture: Physics-Informed, Not Black-Box

The calibration system is **not** a neural network or black-box ML model. It is a bounded nonlinear least-squares optimizer that fits the physical parameters of the hydrological model against observed telemetry data.

### Key Principles

1. **Primary engine is deterministic optimization**: Bounded Levenberg-Marquardt solver (`scipy.optimize.least_squares`)
2. **ML assistant is gated**: A secondary machine-learning predictor contributes to initial parameter estimates only when trained on 3+ historical monsoon events and verified by explicit backtest
3. **Confidence is observation-fit, not forecast probability**: The `confidence_pct` metric measures how closely calibrated parameters reproduce recent observed telemetry

## Calibration Parameters

The optimizer adjusts four scaling factors within strict physical bounds:

| Parameter | Description | Lower Bound | Upper Bound |
|-----------|-------------|-------------|-------------|
| alpha_K | Muskingum reach travel time scaling (applied to all R1-R5) | 0.50 | 1.80 |
| alpha_lag | Subbasin lag time scaling (applied to all S1-S9) | 0.50 | 1.80 |
| delta_CN | SCS Curve Number additive adjustment (all subbasins) | -8.0 | +8.0 |
| X | Muskingum wedge storage factor | 0.15 | 0.40 |

### Immutable Baseline

Calibration operates relative to a frozen snapshot (`data/telemetry/calibration_baseline.json`), NOT the current `Basin_1.basin` file. This prevents cumulative drift — every calibration starts from the same origin.

## Calibration Trigger

The calibrator activates when the discrepancy between forecast and observed telemetry exceeds configured thresholds:

- **Timing discrepancy**: |delta_t| >= 1.0 hour (peak arrival mismatch)
- **Stage discrepancy**: |delta_h| > 0.25 m (stage level mismatch on rising limb)

Observations come from the ThingSpeak ultrasonic sensor at Shivaji Bridge (Channel #3424513).

## Optimization Objective

The Levenberg-Marquardt solver minimizes a combined hydrologic loss:

```
L(theta) = w_nse * (1 - NSE) + w_time * (delta_t / 2.0)^2
         + w_peak * (delta_Q / Q_obs)^2 + w_reg * ||theta - theta_0||^2
```

The regularization term `||theta - theta_0||^2` penalizes departure from the physics baseline, preventing overfitting to a single event.

## Optimization Procedure

1. **Collect observation window**: Recent validated telemetry from ThingSpeak
2. **Set initial parameters**: From frozen baseline (`calibration_baseline.json`), with optional ML prior if validated
3. **Run Levenberg-Marquardt**: `scipy.optimize.least_squares` with method `trf` (Trust Region Reflective)
4. **Apply physical bounds**: All parameters clamped to their defined ranges
5. **Validate result**: Check observation-fit confidence score
6. **Dual sync**: Update both the Python emulator parameters in `runner.py` AND atomically rewrite `Basin_1.basin` with timestamped `.bak` backup
7. **Persist**: Save state to `data/telemetry/ml_calibration_state.json`

## Validation Metrics

| Metric | Full Name | Good Value | Purpose |
|--------|-----------|------------|---------|
| NSE | Nash-Sutcliffe Efficiency | > 0.5 | Overall model skill |
| RMSE | Root Mean Square Error | < 0.5 m | Stage prediction error |
| Spearman rho | Spearman Rank Correlation | > 0.8 | Hydrograph shape match |
| PBIAS | Percent Bias | < 10% | Volume bias |

## Peak Arrival Window

The `calculate_peak_arrival_window()` function computes:

- **Peak arrival time**: When maximum discharge/stage arrives at each bridge
- **Confidence window**: +/- 2.0 hours (configured via `PEAK_ARRIVAL_CI_HOURS`, not statistically derived)
- **Stage/discharge bands**: Heuristic operational envelopes (not statistical confidence intervals)
- **Status**: `PEAK_IDENTIFIED` or `NO_PEAK` based on forecast analysis

## ML Parameter Predictor (Gated)

The secondary ML predictor (`backend/ml/ml_parameter_predictor.py`) is a `HydrologicParameterPredictor` that learns parameter-rainfall relationships:

- **Current state**: `UNTRAINED` — no validated model exists; the engine uses the physics prior
- **Activation gate**: Requires `mark_validated()` after successful backtest against 3+ events
- **Contribution**: Provides initial parameter estimates only (not final values)
- **Override**: If backtest fails, predictor output is discarded and physics priors are used

## Recalibration via Admin Console

Operators can force a recalibration from the admin console:

```
POST /api/v1/admin/recalibrate
Authorization: Bearer <JWT>
```

This triggers an immediate calibration cycle regardless of the discrepancy threshold.

## Source Files

| File | Purpose |
|------|---------|
| `backend/ml/ml_calibration.py` | Levenberg-Marquardt optimization engine |
| `backend/ml/ml_parameter_predictor.py` | Gated ML parameter predictor |
| `backend/validation/validation_metrics.py` | NSE, RMSE, Spearman, PBIAS computation |
| `backend/validation/realtime_telemetry_validator.py` | Forecast-vs-observed comparison |

## References

- Levenberg, K. (1944). A Method for the Solution of Certain Non-Linear Problems in Least Squares. Quarterly of Applied Mathematics, 2(2).
- Nash, J.E. and Sutcliffe, J.V. (1970). River flow forecasting through conceptual models. Journal of Hydrology, 10(3).
