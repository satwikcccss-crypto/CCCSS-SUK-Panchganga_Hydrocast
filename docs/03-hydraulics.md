# 03 — Hydraulics

## Scope

This document covers the stage-discharge conversion: how modelled river discharge (m³/s) is translated into physical water level (metres MSL) at bridge gauging sites. Audience: **Maintainer**.

## The Hydraulic Problem

The hydrological model produces a 90-hour discharge hydrograph at the basin outlet. Emergency responders need **water level**, not discharge. The hydraulic module bridges this gap using government-anchored rating curves and Manning's equation as a physics-based fallback.

## Control Sections

Two gauging sites are used, separated by 3,858 m of river channel:

### Site 1: Chhatrapati Shivaji Maharaj Bridge (Panchganga Ghat)

| Property | Value |
|----------|-------|
| Coordinates | 16.708917 N, 74.219278 E |
| Bed Invert Level | 528.670 m MSL (surveyed bedrock thalweg) |
| WRD Gauge Zero Datum | 530.180 m MSL (0' 0" on official gauge post) |
| Sensor Transducer Face | 549.35 m MSL (ThingSpeak #3424513) |
| Bankfull Level | 541.60 m MSL |
| Alert Stage | 542.10 m MSL (39' 1", ~1800 m³/s) |
| Warning Stage | 542.70 m MSL (41' 1", ~2200 m³/s) |
| Danger Stage | 543.30 m MSL (43' 0", ~2675 m³/s) |
| HFL (Aug 2019) | 545.33 m MSL (49' 8", ~3850 m³/s) |

### Site 2: Rajaram K.T. Weir (Kasba Bawada)

| Property | Value |
|----------|-------|
| Coordinates | 16.736167 N, 74.235889 E |
| Bed Invert Level | 529.318 m MSL (0.648 m higher than Shivaji) |
| WRD Gauge Zero Datum | 530.180 m MSL |
| K.T. Weir Crest RL | 535.77 m MSL |
| Bankfull Level | 541.05 m MSL |
| Alert Stage | 541.50 m MSL (37' 1", ~1480 m³/s) |
| Warning Stage | 542.07 m MSL (39' 0", ~1850 m³/s) |
| Danger Stage | 543.30 m MSL (43' 0", ~2400 m³/s) |
| HFL | 545.33 m MSL (~3850 m³/s) |

### RC Offset Between Sites

The Shivaji Bridge bed lies 0.648 m below the Rajaram bed (`SHIVAJI_RC_OFFSET_M = 0.648`). The WRD official rating sheet is referenced to Rajaram, so Shivaji stage is computed as:

```
H_shivaji = PCHIP(Q) - SHIVAJI_RC_OFFSET_M
```

## PCHIP Rating Curves

The discharge-to-stage conversion uses **PCHIP** (Piecewise Cubic Hermite Interpolating Polynomial) splines fitted to the Water Resources Department (WRD) official stage-discharge relationship.

### Why PCHIP over Cubic Spline

- **Monotonicity**: PCHIP preserves the monotonic nature of the rating curve. Standard cubic splines can oscillate and produce physically impossible negative slopes.
- **Shape preservation**: No overshoot between anchor points.
- **WRD anchored**: 26 anchor points per site (`RAJARAM_ANCHORS_STAGE` / `RAJARAM_ANCHORS_Q`, `SHIVAJI_ANCHORS_STAGE` / `SHIVAJI_ANCHORS_Q`) from the WRD official gauge sheet.

### Stage Conversion Flow

```
Given:   Q (m³/s)  -- modelled discharge at basin outlet
Output:  H (m MSL) -- water level at each bridge gauge

1. build_calibrated_rating_curve()    → PCHIP interpolator from WRD anchors
2. convert_discharge_to_stage_manning(Q, site)  → H via PCHIP first, Manning fallback
3. classify_alert(H, site)            → CWC alert level
```

## Manning's Equation (Compound Section Fallback)

When discharge falls outside the PCHIP anchor range, the **Divided Channel Method** (DCM) is used with surveyed cross-sections:

```
Q_total = Q_main + Q_left_overbank + Q_right_overbank

Q_panel = (1/n) × A × R^(2/3) × S₀^(1/2)
```

### Cross-Section Surveys

Full survey data is embedded in the source code:

| Site | Survey Points | Array |
|------|--------------|-------|
| Shivaji Bridge | 128 points | `SHIVAJI_SURVEY` |
| Rajaram Weir | 135 points | `RAJARAM_SURVEY` |

### Manning's Roughness Coefficients

| Zone | n | Rationale |
|------|---|-----------|
| Main channel (below bankfull) | 0.031 | Clean, straight, natural channel |
| Floodplain (above bankfull) | 0.070 | Dense vegetation, irregular banks |

Bankfull transition levels:
- **Shivaji Bridge**: 541.60 m MSL
- **Rajaram Weir**: 541.05 m MSL

### WRD Monsoon Baseflow Floor

A minimum baseflow of 40.0 m³/s (`WRD_MONSOON_BASEFLOW_FLOOR_M3S`) is enforced during active monsoon to prevent unrealistic zero-flow conditions in the rating curve.

## Low-Flow Guard

The `assess_low_flow_guard()` function detects when the river is in low-flow regime (below baseflow threshold) and flags the forecast accordingly. The `estimate_low_flow_discharge()` function inverts the observed stage to estimate discharge during dry periods.

## Rajaram Stage Inference

When direct Rajaram telemetry is unavailable, the `infer_rajaram_stage_from_shivaji()` function estimates Rajaram stage from Shivaji Bridge observations using the hydraulic gradient and channel geometry.

## Alert Classification

The computed stage at each bridge is classified against CWC/DDMA thresholds:

| Level | Colour | Shivaji Bridge | Rajaram Weir | Action |
|-------|--------|----------------|-------------|--------|
| NORMAL | Green | < 542.10 m | < 541.50 m | No action |
| ALERT | Yellow | 542.10–542.70 m | 541.50–542.07 m | Situation monitoring |
| WARNING | Orange | 542.70–543.30 m | 542.07–543.30 m | Evacuation preparation |
| DANGER | Red | 543.30–545.33 m | 543.30–545.33 m | Immediate evacuation |
| HFL_EXCEEDED | Purple | > 545.33 m | > 545.33 m | Emergency above HFL |

## Source Files

| File | Purpose |
|------|---------|
| `backend/stage_conversion/stage_converter.py` | PCHIP rating curve, Manning's DCM, alert classification, low-flow guard |

## References

- Water Resources Department, Government of Maharashtra -- Official Stage-Discharge Tables
- Central Water Commission -- Flood Warning Threshold Standards
- Chow, V.T. (1959). *Open-Channel Hydraulics*. McGraw-Hill.
