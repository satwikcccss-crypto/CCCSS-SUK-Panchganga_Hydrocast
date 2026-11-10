# 02 — Hydrology

## Scope

This document covers the rainfall-runoff modelling framework: how precipitation is converted into river discharge at the Panchganga basin outlet. Audience: **Maintainer**.

## Basin Delineation

The Panchganga catchment (approximately 1,837 km²) is divided into 9 hydrologic subbasins (S1–S9), each with its own curve number, area, and governing rain gauge:

| Subbasin | Name | Area (km²) | Curve Number (AMC-III) | Primary Gauge |
|----------|------|------------|----------------------|---------------|
| S1 | Karveer | 86.21 | 82 | KARVIR |
| S2 | Sangarul | 153.77 | 78 | SANGARUL |
| S3 | Kotoli | 261.32 | 80 | KOTOLI |
| S4 | Karanjphen | 262.00 | 76 | KARANJPHEN |
| S5 | Padasali | 106.39 | 79 | PADASALI |
| S6 | Gaganbawda | 227.72 | 74 | GAGANBAWDA |
| S7 | Radhanagari | 263.34 | 77 | RADHANAGARI |
| S8 | Panhala | 148.85 | 81 | PANHALA |
| S9 | Kalamma | 267.40 | 75 | KALAMMA_NKP |

## SCS-CN Rainfall-Runoff Model

The Soil Conservation Service Curve Number method estimates effective rainfall (the portion that becomes direct runoff):

```
S   = (25400 / CN) - 254          (maximum retention, mm)
Ia  = 0.2 * S                     (initial abstraction, mm)
Q   = (P - Ia)^2 / (P - Ia + S)  when P > Ia, else Q = 0
```

Where:
- **P** = gross precipitation (mm) from ECMWF forecast
- **CN** = curve number (adjusted for Antecedent Moisture Condition III — wet season)
- **S** = maximum soil retention (mm)
- **Ia** = initial abstraction (mm) — interception, surface depression storage
- **Q** = effective rainfall / direct runoff depth (mm)

### AMC Classification

| AMC Class | 5-day Antecedent Rainfall | Season |
|-----------|--------------------------|--------|
| AMC-I (dry) | < 36 mm | Growing season |
| AMC-II (normal) | 36-53 mm | Growing season |
| AMC-III (wet) | > 53 mm | Growing season |

During monsoon operations, the system defaults to AMC-III (saturated catchment) for conservative flood prediction.

## SCS Dimensionless Unit Hydrograph

Each subbasin generates a unit hydrograph (UH) using the SCS dimensionless UH method:

1. **Time to peak**: Tp = 0.6 * Tc where Tc is the time of concentration
2. **Peak discharge**: Qp = (2.08 * A) / Tp where A is subbasin area (km²)
3. **Convolution**: The effective rainfall hyetograph is convolved with the unit hydrograph to produce the direct runoff hydrograph

The dimensionless UH ordinates follow the standard SCS tabulation (peak at t/Tp = 1.0, with recession to t/Tp = 5.0).

## Baseflow Separation

A constant baseflow is added to each subbasin's direct runoff hydrograph. The baseflow rate is estimated from dry-season minimum flow observations at the basin outlet.

## Muskingum-Cunge Flood Routing

The routed hydrographs from upstream subbasins are propagated through 5 river reaches (R1-R5) using the Muskingum method:

```
O(t+1) = C1 * I(t+1) + C2 * I(t) + C3 * O(t)
```

Where:
- **I** = inflow hydrograph
- **O** = outflow hydrograph
- **K** = travel time through reach (hours)
- **X** = weighting factor (0-0.5)
- **C1, C2, C3** = routing coefficients derived from K, X, and timestep dt

### Reach Configuration

| Reach | From - To | K (hr) | X |
|-------|-----------|--------|---|
| R1 | S6+S7 junction to S4 confluence | Calibrated | Calibrated |
| R2 | S4 confluence to S3 junction | Calibrated | Calibrated |
| R3 | S3 junction to S2 confluence | Calibrated | Calibrated |
| R4 | S2 confluence to S1 junction | Calibrated | Calibrated |
| R5 | S1 junction to Outlet (Kolhapur) | Calibrated | Calibrated |

The exact K and X values are determined by the Levenberg-Marquardt calibration engine (see [06-machine-learning.md](06-machine-learning.md)).

## Outlet Summation

All routed hydrographs are summed at the outlet junction to produce the composite 90-hour discharge hydrograph. This is then passed to the stage conversion module (see [03-hydraulics.md](03-hydraulics.md)).

## Source Files

| File | Purpose |
|------|---------|
| `backend/service/pipeline_worker.py` | 12-step pipeline including SCS-CN, UH, routing |
| `backend/rainfall/station_selector.py` | Subbasin-to-gauge assignment and rainfall weighting |
| `backend/rainfall/open_meteo.py` | ECMWF rainfall download |
| `backend/hms/runner.py` | HEC-HMS headless execution / Python twin emulator |
| `backend/hms/basin_parser.py` | Basin model parameter parsing |

## References

- USDA-SCS (1986). *Urban Hydrology for Small Watersheds*. Technical Release 55.
- Chow, V.T. (1959). *Open-Channel Hydraulics*. McGraw-Hill.
- Cunge, J.A. (1969). On the Subject of a Flood Propagation Computation Method (Muskingum Method). Journal of Hydraulic Research, 7(2).
