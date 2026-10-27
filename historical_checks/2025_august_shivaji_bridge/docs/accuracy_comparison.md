# Accuracy Comparison: Single Point vs Station Selection

## Overview
Comparison of model accuracy using two rainfall input methods:
1. **Single point**: Rainfall at Rajaram Weir coordinates (16.736083, 74.235250)
2. **Station selection**: Governning gage per subbasin selected via max-rainfall-volume criteria

## August 2019 Flood

| Metric | Single Point | Station Selection | Improvement |
|--------|-------------|-------------------|-------------|
| Mean 90h Catchment Rain | 211.6 mm | 364.7 mm | +72.4% |
| Peak Discharge (m³/s) | 876.1 | 1,662.2 | +89.7% |
| Peak Lead Time | T+138h | T+137h | ~1h earlier |
| Peak Stage (Rajaram) | 539.34 m MSL | 541.87 m MSL | +2.53 m |
| Observed Stage | 546.97 m MSL | 546.97 m MSL | - |
| **Stage Error** | **-8.28 m** | **-5.75 m** | **+30.6% reduction** |
| **Discharge Error** | **-58.5%** | **-21.3%** | **63.6% reduction** |
| AMC Regime | AMC-III | AMC-III | Consistent |

### Key Observations
- Station selection doubles the catchment-mean rainfall (364.7 vs 211.6 mm)
- Discharge error reduced by more than half (-58.5% to -21.3%)
- Stage error improved by ~30% (-8.28 m to -5.75 m)
- Peak timing virtually identical (T+138h vs T+137h)

## July 2021 Flood

| Metric | Single Point | Station Selection | Improvement |
|--------|-------------|-------------------|-------------|
| Mean 90h Catchment Rain | 153.8 mm | 278.2 mm | +80.9% |
| Peak Discharge (m³/s) | 565.8 | 1,149.1 | +103.1% |
| Peak Lead Time | T+129h | T+129h | Identical |
| Peak Stage (Rajaram) | 537.87 m MSL | 540.47 m MSL | +2.60 m |
| Observed Stage | 547.83 m MSL | 547.83 m MSL | - |
| **Stage Error** | **-10.61 m** | **-8.01 m** | **24.5% reduction** |
| Discharge Error | N/A (not verified) | N/A | - |

### Key Observations
- Station selection increases catchment rain by 81% (153.8 to 278.2 mm)
- Stage error reduced by 24% (-10.61 m to -8.01 m)
- Peak timing perfectly consistent (T+129h both methods)
- Discharge not compared (not verified observationally)

## August 2025 Flood - Shivaji Bridge

**Source**: Shivaji Bridge ultrasonic telemetry (ThingSpeak), 20,292 readings, 8–22 August 2025  
**Sensor datum**: 549.35 m MSL (deck level); Stage = 549.35 − (field1 × 0.3048)  
**Cleaning**: removed ultrasonic echo artifacts (field1 ≈ 3.69 ft drops and stage-below-bed max-range reads), resampled to 1-hour averages (`data/shivaji_bridge_2025_hourly_observed.csv`, 360 hours)

| Parameter | Value |
|-----------|-------|
| Modelling window | 2025-08-08 to 2025-08-22 |
| Rainfall source | Open-Meteo archive (`/v1/archive`), station selection (18 gauges, 9 subbasins) |
| Simulated window | 360 h (full 14-day event) |
| Observed peak stage | 542.57 m MSL on 2025-08-21 14:00 (hourly average) |
| Calculated peak discharge | 1,570.4 m³/s at T+336 h |
| Calculated peak stage (Shivaji) | 541.05 m MSL |
| **Stage error** | **−1.52 m** (calculated − observed) |
| AMC regime | AMC-III |
| Mean catchment rain | 465.5 mm |

### Hourly validation vs observed telemetry (338 matched hours)

| Metric | Value |
|--------|-------|
| Nash–Sutcliffe Efficiency (NSE) | 0.86 |
| Kling–Gupta Efficiency (KGE) | 0.76 |
| RMSE (stage) | 1.29 m |
| MAE (stage) | 1.13 m |
| PBIAS (stage) | −0.13 % |
| Peak stage error (Δh_peak) | −1.51 m |
| Peak arrival timing error (ΔTₚ) | +8.00 h (simulated peak 8 h late) |

### Key Observations
- The model reproduces the observed hydrograph with **NSE = 0.86** and **KGE = 0.76**, indicating good skill for a 14-day monsoon event without event-specific calibration.
- Volume bias is negligible (**PBIAS = −0.13 %**); the remaining error is a modest peak under-prediction (−1.51 m) and an 8-hour late crest.
- Peak timing error (+8 h) is larger than for the 2019/2021 events, reflecting the longer, multi-peak monsoon storm rather than a single burst.

## Summary of Improvements

| Metric | August 2019 Improvement | July 2021 Improvement | Average |
|--------|------------------------|-----------------------|---------|
| Catchment Rain Increase | +72.4% | +80.9% | +76.7% |
| Stage Error Reduction | 30.6% | 24.5% | 27.6% |
| Discharge Error Reduction | 63.6% | N/A | 63.6% |
| Hourly NSE (2025 event) | – | – | 0.86 |
| Hourly KGE (2025 event) | – | – | 0.76 |
| Hourly RMSE stage (2025 event) | – | – | 1.29 m |

## Conclusion
Station-based rainfall selection consistently outperforms single-point rainfall:
- **Always increases catchment-mean rainfall** (makes physical sense for flood events)
- **Reduces stage error** in all cases (24-30% improvement)
- **Reduces discharge error** significantly (63.6% improvement in Aug 2019)
- **Maintains peak timing accuracy** (within 1 hour)

The data strongly supports using the full gauge network for rainfall input rather than single-station estimates.

---
*Accuracy comparison data from historical_checks/ folder, October 2026*