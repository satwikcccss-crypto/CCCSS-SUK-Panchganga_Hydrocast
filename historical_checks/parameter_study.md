# Parameter Study: Subbasin and Reach Parameters Analysis

## Overview
Analysis of model parameters affecting flood prediction accuracy for historical events.

## 5.1 Subbasin Parameters (from Basin_1.basin / calibration_baseline.json)

### Current Immutable Baseline Values

| Subbasin | Lag (min) | CN | Area (km²) |
|----------|-----------|----|------------|
| S1 | 2,152 | 74.85 | 86.213 |
| S2 | 3,154 | 65.74 | 153.77 |
| S3 | 3,998 | 64.82 | 261.32 |
| S4 | 3,116 | 61.89 | 262.0 |
| S5 | 2,117 | 60.97 | 106.39 |
| S6 | 3,318 | 61.78 | 227.72 |
| S7 | 3,362 | 61.28 | 195.39 |
| S8 | 3,387 | 65.76 | 177.44 |
| S9 | 5,199 | 64.31 | 366.97 |

**Key Observations**:
- S9 has the longest lag (5,199 min ≈ 87 hrs) and largest area (367 km²)
- S1 has the shortest lag (2,152 min ≈ 36 hrs) and smallest area (86 km²)
- All subbasins have CN between 60-75 (typical for monsoon conditions)
- Current baseline CN values are **immutable** - calibration offsets applied on top

### Subbasin Parameter Sensitivity

From `src/hms/runner.py` `compute_emulator_hydrograph()`:
- **Lag (lag_min)**: Controls unit hydrograph peak timing
  - Longer lag → later peak
  - S9's 5,199 min lag contributes to basin-scale routing delay
  
- **CN (Curve Number)**: Controls runoff generation
  - Higher CN → more runoff for same rainfall
  - CN range 60-75 maps to actual retention S = (25400/CN) - 254
  - CN 74.85 (S1) → S ≈ 13.4 mm
  - CN 60.97 (S5) → S ≈ 40.3 mm

- **Area (km²)**: Scales runoff volume proportionally
  - Total basin area: 1,837.213 km²
  - S9 contributes 20% of total area

### Recommendation
Subbasin CN values may need event-specific adjustment:
- Current baseline CN values are fixed
- Historical events show systematic stage under-prediction
- Consider calibration-adjusted CN offsets (as done in `ml_calibration.py`)

---

## 5.2 Reach Parameters (from Basin_1.basin)

### Current Immutable Reach Parameters

| Reach | K (hrs) | X (storage weight) |
|-------|---------|-------------------|
| R1 | 2.899 | 0.2 |
| R2 | 11.827 | 0.2 |
| R3 | 3.829 | 0.2 |
| R4 | 1.224 | 0.2 |
| R5 | 4.619 | 0.2 |

**Key Observations**:
- All reaches have **constant X = 0.2** (storage weighting)
- K values range from 1.224 hr (R4) to 11.827 hr (R2)
- R2 has the longest travel time (11.827 hr ≈ 50% of 90-hr simulation)
- R1 and R4 have shortest travel times

### Reach Parameter Sensitivity

From `src/hms/runner.py` `route_muskingum()`:
- **K (travel time)**: Controls flood wave attenuation
  - Larger K → more attenuation, later peak
  - R2's K=11.827 hr is significant for basin routing
  
- **X (storage weight)**: Controls coefficient distribution
  - X=0.2 used consistently (stable mass-conserving scheme)
  - Affects C0/C1/C2 coefficients in routing

- **Musket impact on peak**:
  - Longer K → greater attenuation → lower peak
  - Shorter K → less attenuation → higher peak

### Recommendation
Reach parameters may need event-specific tuning:
- Current values from immutable baseline (never modified)
- R2's long K (11.827 hr) significantly routes flood through basin
- Consider reach-specific calibration for flood timing adjustments

---

## 5.3 Calibration-Offet Mechanics

### How Calibration Works (`src/hydrology/ml_calibration.py`)

The `AdaptiveHydrologicCalibrator` applies offsets on top of the immutable baseline:

1. **Physics-based estimates** from discrepancy detection:
   - `k_shift` → α_K (Muskingum coefficient)
   - `lag_shift` → α_lag (Subbasin lag)
   - `cn_shift` → ΔCN (Curve Number adjustment)
   - `x_shift` → Muskingum x parameter

2. **ML-informed blending** (new in ml_calibration.py revision):
   - ML predictor gives initial guess `ml_guess`
   - Blended: `physics_prior * 0.70 + ML_correction * 0.30`
   - Parameters bounded within physical limits

3. **Application sequence**:
   - Baseline values from `calibration_baseline.json`
   - Offsets added/subtracted
   - Results bounded within physical limits
   - Basin_1.basin rewritten atomically with .bak backups

### Calibration Trigger Conditions
From `detect_timing_and_stage_discrepancy()`:
- `|Δt| >= 1.0 hr` timing offset OR
- Stage discrepancy > 0.25 m on rising limb

When triggered, `recalibrate_parameters()` blends physics and ML predictions.

---

## 5.4 Parameter Study Findings

### 5.3.1 Subbasin CN Impact

| Scenario | Mean CN | Expected Effect |
|----------|---------|-----------------|
| Baseline (immutable) | ~66.5 | Standard runoff generation |
| +5 CN offset | ~71.5 | More runoff → higher peaks |
| -5 CN offset | ~61.5 | Less runoff → lower peaks |

**Observed Effect in Historical Runs**:
- All runs used baseline CN (no calibration offsets applied in standalone mode)
- Stage under-prediction consistent across all runs
- Suggests CN may be too low for these flood events

### 5.3.2 Reach K Impact

| Scenario | R2 K (hrs) | Expected Peak Effect |
|----------|-----------|---------------------|
| Baseline | 11.827 | Standard attenuation |
| +20% K | 14.19 | More attenuation → lower peak |
| -20% K | 9.46 | Less attenuation → higher peak |

**Observed Effect**:
- Peak timing sensitive to K values
- T+137h vs T+138h observed in Aug 2019 runs
- Small K adjustments can shift peak timing

### 5.3.3 Optimal Parameter Adjustment Strategy

Based on the accuracy improvements observed:

1. **Apply CN offsets** (likely positive, +3 to +5)
   - Would increase runoff → raise calculated peaks
   - Would reduce stage under-prediction

2. **Consider reach K adjustments** (possibly -10% to R2)
   - Would increase peak timing slightly
   - Could improve arrival time match

3. **Use ML-informed blending** (from ml_calibration.py)
   - 70% physics prior + 30% ML correction
   - Would automatically adjust parameters based on historical patterns

### 5.4 Recommended Next Steps

1. **Run calibration** with `AdaptiveHydrologicCalibrator` against
   - August 2019 and July 2021 events
   - Capture optimal parameter offsets

2. **Apply calibrated offsets** to baseline and re-run historical events
   - Compare accuracy before/after calibration

3. **Investigate stage under-prediction pattern**
   - All events under-predict by similar magnitude
   - Suggests systematic parameter issue rather than random error

4. **Test ML parameter predictor** with historical training data
   - Use `ml_parameter_predictor.py` to predict parameters from stage series
   - Compare predicted vs calibrated values

---
*Parameter study data from HydroCast codebase analysis, October 2026*