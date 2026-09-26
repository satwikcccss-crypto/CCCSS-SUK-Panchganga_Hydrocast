# Real-Time Adaptive Machine Learning Hydrologic Calibrator

```
====================================================================================================
               PHYSICS-INFORMED REAL-TIME ML CALIBRATION CONTROL LOOP
====================================================================================================

      ThingSpeak Ultrasonic IoT Sensor Telemetry (Shivaji Bridge)
                               |
                               v
               [ Telemetry Ingestion & Quality Control ]
               - 1-hour rolling median filter
               - Spike removal & missing value interpolation
               - Water Surface Elevation (m MSL)
                               |
                               +-----------------------------------+
                               |                                   |
                               v                                   v
             [ Observed Rising Limb Detector ]   [ Previous Forecast Cycle Evaluator ]
             - Rate of rise > 0.15 m/hr          - Aligns predicted stage vs observed
             - Identifies hydrograph slope       - Computes timing offset: Delta_t (hr)
                                                 - Computes stage discrepancy: Delta_h (m)
                               |                                   |
                               +-----------------+-----------------+
                                                 |
                                                 v
                                 +-------------------------------+
                                 |  Recalibration Trigger Logic  |
                                 +-------------------------------+
                                 |  |Delta_t| >= 1.0 hr          |
                                 |  OR                           |
                                 |  Delta_h > 0.25m AND Rising   |
                                 +-------------------------------+
                                                 |
                     +---------------------------+---------------------------+
                     | (Trigger Condition Met)                               | (Tolerances Satisfied)
                     v                                                       v
     +-----------------------------------------------+       +-------------------------------+
     | Scipy L-BFGS-B Bounded Loss Optimization      |       | Retain Baseline Parameters    |
     | - alpha_K   in [0.50, 1.80] (Reach Travel)    |       | alpha_K = 1.0, alpha_lag = 1.0|
     | - alpha_lag in [0.50, 1.80] (Subbasin Lag)    |       | Delta_CN = 0.0, X = 0.250     |
     | - Delta_CN  in [-8.0, +8.0] (Soil Retention)  |       +-------------------------------+
     | - X         in [0.15, 0.40] (Wedge Storage)   |
     +-----------------------------------------------+
                     |
                     v
     [ Dual System State Synchronization ]
     - Updates src/hms/runner.py runtime parameters
     - Atomically updates Basin_1.basin with timestamped .bak backups
     - Persists data/telemetry/ml_calibration_state.json
```

---

## 1. Engine Purpose & Operational Philosophy

The **Adaptive Hydrologic Calibrator** (`src/hydrology/ml_calibration.py`) functions as an automated real-time machine learning supervisory loop. During major monsoon storms, uncalibrated static hydrological models suffer from two primary errors:
1. **Timing Lead-Time Errors ($\Delta t$):** Flood peaks arrive earlier or later than simulated due to variable channel velocities, antecedent soil moisture, or backwater obstructions.
2. **Volumetric Runoff Errors ($\Delta h, \Delta Q$):** Peak stage is underpredicted or overpredicted due to dynamic infiltration changes and seasonal crop resistance (sugarcane).

The calibrator detects discrepancies between real-time ultrasonic sensor observations and simulated forecasts, solving a **bounded physics-informed loss minimization** problem to dynamically adjust governing parameters.

---

## 2. Discrepancy Detection & Trigger Criteria

The engine continuously evaluates real-time ThingSpeak Channel 3424513 water levels against previous forecast cycles.

### 2.1 Wave Timing Offset ($\Delta t$)
The timing offset represents the phase shift between the observed flood wave and the modeled hydrograph. During rising limb conditions ($dh/dt > 0.15\text{ m/hr}$):

$$\Delta t = -\frac{\bar{e}_{\text{stage}}}{\text{Rate of Rise}} \quad [\text{hours}]$$

- **Early Arrival ($\Delta t < 0$):** Observed stage rises faster than modeled. Wave velocity in river reaches is faster than modeled.
- **Late Arrival ($\Delta t > 0$):** Flood wave is delayed. Channel storage attenuation is higher than modeled.

### 2.2 Auto-Trigger Conditions
Recalibration is automatically triggered when either of the following conditions is met:

$$\left|\Delta t\right| \ge 1.0\text{ hr} \quad \text{OR} \quad \left(\max |e_{\text{stage}}| > 0.25\text{ m} \;\land\; \text{is\_rising}\right)$$

---

## 3. Mathematical Optimization Formulation

The engine solves for optimal scaling vector $\theta = [\alpha_K, \alpha_{\text{lag}}, \Delta CN, X]$ using the **L-BFGS-B** algorithm (Limited-memory Broyden-Fletcher-Goldfarb-Shanno with Box constraints).

### 3.1 Objective Loss Function

$$L(\theta) = w_{\text{nse}} \cdot (1 - \text{NSE}) + w_{\text{time}} \cdot \left(\frac{\Delta t_{\text{modeled}} - \Delta t}{2.0}\right)^2 + w_{\text{stage}} \cdot \left(\frac{\Delta h_{\text{modeled}} - \Delta h}{0.25}\right)^2 + w_{\text{reg}} \cdot \|\theta - \theta_0\|^2$$

Where:
- $\Delta t_{\text{modeled}} = 0.55 \cdot \left(\frac{\alpha_K - 1.0}{0.075}\right) + 0.45 \cdot \left(\frac{\alpha_{\text{lag}} - 1.0}{0.060}\right)$ (55% reach travel time, 45% subbasin lag).
- $\Delta h_{\text{modeled}} = -\frac{\Delta CN}{4.5}$
- Regularization penalty: $w_{\text{reg}} = 0.05$ (prevents wild swings away from baseline).

### 3.2 Parameter Bounding Constraints

| Parameter | Symbol | Baseline | Physical Lower Bound | Physical Upper Bound | Physical Interpretation |
|:---|:---:|:---:|:---:|:---:|:---|
| **Reach Travel Time Multiplier** | $\alpha_K$ | 1.000 | 0.500 | 1.800 | Scales travel time $K$ across reaches R1–R5 |
| **Subbasin Lag Time Multiplier** | $\alpha_{\text{lag}}$ | 1.000 | 0.500 | 1.800 | Scales lag time $t_{\text{lag}}$ across S1–S9 |
| **SCS Curve Number Shift** | $\Delta CN$ | 0.00 | -8.00 | +8.00 | Uniform soil retention adjustment |
| **Muskingum Wedge Weight** | $X$ | 0.250 | 0.150 | 0.400 | Controls flood wave steepness & diffusion |

---

## 4. Deterministic Analytical Kinematic-Wave Fallback

If numerical optimization fails to converge within 50 iterations or library exceptions occur, the engine falls back to a deterministic analytical solution:

$$k_{\text{shift}} = \text{clip}\left(1.0 + \Delta t \cdot 0.075, \; 0.60, \; 1.60\right)$$

$$\text{lag}_{\text{shift}} = \text{clip}\left(1.0 + \Delta t \cdot 0.060, \; 0.60, \; 1.60\right)$$

$$CN_{\text{shift}} = \text{clip}\left(-\Delta h \cdot 4.5, \; -6.0, \; 6.0\right)$$

$$X_{\text{shift}} = \text{clip}\left(0.25 - \Delta t \cdot 0.02, \; 0.16, \; 0.36\right)$$

This guarantees **100% fail-safe execution** in production runtime environments.

---

## 5. Dual Synchronization & State Persistence

Upon successful recalibration, the engine executes simultaneous atomic synchronization:
1. **Python Emulator In-Memory Parameters:** Injected into `execute_hec_hms()` parameter dictionary.
2. **HEC-HMS Project File (`Basin_1.basin`):** Atomically rewritten on disk with updated `Curve Number:` and `Lag:` values, retaining timestamped backups (`Basin_1.basin.bak_<TIMESTAMP>`).
3. **Telemetry State Ledger:** Persisted to `data/telemetry/ml_calibration_state.json`.
