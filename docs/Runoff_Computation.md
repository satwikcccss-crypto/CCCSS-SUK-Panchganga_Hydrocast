# Hydrological Runoff Computation & Convolution Pipeline

```
====================================================================================================
                  HOURLY DISCRETE RUNOFF CONVOLUTION & ROUTING PIPELINE
====================================================================================================

      Raw Hourly Rainfall Hyetograph: P(t) [mm]
                        |
                        v
          [ SCS-CN Dynamic Loss Model ]
          - AMC-II / AMC-III Saturated Switching Threshold (65mm / 90h)
          - Cumulative Potential Retention: S = (25400 / CN) - 254
          - Initial Abstraction: Ia = 0.15*S (AMC-II) or 0.08*S (AMC-III)
                        |
                        v
      Incremental Excess Rainfall: Delta_P_excess(t) [mm]
                        |
                        v
          [ SCS Dimensionless Unit Hydrograph Transform ]
          - Subbasin Lag Time: t_lag = lag_min / 60.0
          - Time to Peak: t_p = 0.5 + t_lag
          - Curvilinear Dimensionless Equation: u(t) = (t/tp)^3.7 * exp(3.7 * (1 - t/tp))
          - Volume Conservation Scaling: Sum(UH * 3600) == Area_km2 * 1000 m3
                        |
                        v
      Direct Subbasin Outflow Hydrograph: Q_dir(t) = Delta_P * UH [m3/s]
                        |
                        v
          [ 5-Reach Muskingum Channel Network Cascade ]
          - R5: Routes (S6 + S7) into Reach R2 (K=18.338h, X=0.250)
          - R4: Routes (S9) into Reach R2 (K=8.085h, X=0.250)
          - R2: Routes (R5 + R4 + S8) into Reach R1 (K=16.500h, X=0.250)
          - R3: Routes (S4 + S5) into Reach R1 (K=9.484h, X=0.250)
          - R1: Routes (R2 + R3 + S3 + S2) into Basin Sink-1 (K=4.500h, X=0.250)
                        |
                        v
      Combined Surface Outflow: Q_surface(t) = Outflow(R1) + Direct(S1)
                        |
                        +---> [ Exponential Baseflow Recession ]
                        |     Q_bf(t) = Q_bf0 * exp(-0.002 * t)
                        |     Floor >= 15.0 m3/s (Panchganga Baseline)
                        v
      Total Hydrograph at Rajaram K.T. Weir: Q_total(t) = Q_surface(t) + Q_bf(t)
                        |
                        v
          [ 2D Surveyed Hydraulic Rating Curve Engine ]
          - Divided Channel Method (Main n=0.031, Overbank Sugarcane n=0.070)
          - Backwater Transfer: Shivaji Bridge Sensor <---> Rajaram KT Weir Sink
```

---

## 1. Computation Pipeline Workflow

The runoff computation pipeline executes sequentially in `src/hms/runner.py`, transforming gridded rainfall hyetographs into bridge flood stages across a continuous 90-hour forward window ($T+0\text{h} \to T+89\text{h}$).

### 1.1 Step-by-Step Computational Workflow

```
[ Step 01: Hyetograph Ingestion ]
    Ingests 90 hourly rainfall values for 9 subbasins from ECMWF IFS HRES (0.08° / 9km).

[ Step 02: AMC-II / AMC-III Saturated Regime Determination ]
    Calculates 90-hr basin-wide cumulative mean precipitation:
    If mean_rain_90h >= 65.0 mm: Set AMC-III (Ia = 0.08*S, CN scaled).
    Else: Set AMC-II (Ia = 0.15*S, base CN).

[ Step 03: Cumulative Soil Water Retention & Runoff Excess ]
    Iterates h = 0..89:
    Computes Q_cum(h) = (P_cum - Ia)^2 / (P_cum - Ia + S) + 0.02 * P_cum.
    Derives incremental excess: excess_p[h] = max(0.0, Q_cum[h] - Q_cum[h-1]).

[ Step 04: SCS Dimensionless Unit Hydrograph Generation ]
    Calculates t_p = 0.5 + t_lag.
    Generates curvilinear ordinate: u(t) = (t / tp)^3.7 * exp(3.7 * (1 - t / tp)).
    Normalizes total volume to exactly 1.0 mm over subbasin area: Area_km2 * 1000 m³.

[ Step 05: Discrete Time Convolution ]
    Convolves excess_p with UH: q_direct = np.convolve(excess_p, uh)[:90].

[ Step 06: Muskingum Channel Reach Routing Network ]
    Routes subbasin outflows through 5 sequential reaches with numerical sub-stepping.

[ Step 07: Baseflow Superposition & Recession ]
    Superimposes baseflow decaying at k = 0.002/hr, with minimum physical floor of 15.0 m³/s.

[ Step 08: 2D Hydraulic Rating Curve Conversion ]
    Converts Q_total(t) into stage (m MSL) at Shivaji Bridge and Rajaram KT Weir.
```

---

## 2. Mathematical Detail of Routing Cascade

The reach routing network precisely preserves the spatial topology of the Panchganga drainage system:

```
Reach R5 Inflow:  I_R5(t) = Q_dir,S6(t) + Q_dir,S7(t)
Reach R5 Outflow: O_R5(t) = Muskingum(I_R5, K=18.338h, X=0.250)

Reach R4 Inflow:  I_R4(t) = Q_dir,S9(t)
Reach R4 Outflow: O_R4(t) = Muskingum(I_R4, K=8.085h, X=0.250)

Reach R2 Inflow:  I_R2(t) = O_R5(t) + O_R4(t) + Q_dir,S8(t)
Reach R2 Outflow: O_R2(t) = Muskingum(I_R2, K=16.500h, X=0.250)

Reach R3 Inflow:  I_R3(t) = Q_dir,S4(t) + Q_dir,S5(t)
Reach R3 Outflow: O_R3(t) = Muskingum(I_R3, K=9.484h, X=0.250)

Reach R1 Inflow:  I_R1(t) = O_R2(t) + O_R3(t) + Q_dir,S3(t) + Q_dir,S2(t)
Reach R1 Outflow: O_R1(t) = Muskingum(I_R1, K=4.500h, X=0.250)

Sink-1 Inflow:    Q_total(t) = O_R1(t) + Q_dir,S1(t) + Q_bf(t)
```

---

## 3. Peak Identification & Flat-Flow Protection

The pipeline calculates the exact hour of peak discharge and peak stage:

```python
# Identify peak lead time and discharge
peak_idx = int(np.argmax(q_total))
peak_surface_q = float(q_surface[peak_idx])
initial_baseflow = float(baseflow_array[0])

# Flood wave significance check
is_significant_event = peak_surface_q > max(0.5, initial_baseflow * 2.0)
if not is_significant_event:
    peak_idx = 0  # Low-flow regime: declare T+0 (receding flow)
```
