# Model Calibration, Validation Metrics & Accuracy Engine

```
========================================================================================
             HYDROCAST ACCURACY BENCHMARKING & VALIDATION ENGINE
========================================================================================

    [ Simulated Forecast Time Series ]             [ Physical Ground Truth Observations ]
     - Predicted Stage (m MSL)                     - ThingSpeak IoT Radar Telemetry
     - Predicted Discharge Q (m³/s)                - Maharashtra WRD Gauge Records (cusecs)
     - 90h Basin Rainfall (mm)                     - 18 Rain Gauge Network Station Hits
                   │                                                  │
                   └─────────────────────────┬────────────────────────┘
                                             ▼
                             Validation Metrics Engine
                     (src/hydrology/validation_metrics.py)
                                             │
      ┌──────────────────────┬───────────────┴───────────────┬──────────────────────┐
      ▼                      ▼                               ▼                      ▼
[ Spearman Rank ρ ]    [ Nash-Sutcliffe ]              [ Error Metrics ]      [ 18-Station Rain ]
Non-linear monotonic   Flow wave alignment             RMSE (m) & MAE (m)     Predicted vs Obs
rank correlation       NSE Target > 0.85               PBIAS Target < 5%      Volume Accuracy %
```

---

## 1. Overview & Validation Philosophy

Hydrological flood early warning systems must not be evaluated on single-point errors alone. A model might predict water levels with low mean error while failing to capture the timing, peak magnitude, or rank order of the flood wave.

HydroCast employs a **multi-dimensional validation matrix** that assesses:
1. **Monotonic Rank Tracking:** Spearman Rank Correlation ($\rho$).
2. **Hydrograph Fit & Energy Alignment:** Nash-Sutcliffe Efficiency (NSE).
3. **Linear Correspondence:** Pearson Correlation ($r$ and $R^2$).
4. **Volumetric Runoff Conservation:** Percent Bias (PBIAS %).
5. **Absolute Dispersion:** Root Mean Square Error (RMSE) and Mean Absolute Error (MAE).
6. **Spatial Precipitation Fidelity:** Station-by-station 90-hour rainfall volume accuracy across 18 catchment rain gauges.

---

## 2. Mathematical Formulations

### 2.1 Spearman Rank Correlation ($\rho$)
The Spearman rank correlation assesses how well the relationship between predicted stage ($X$) and observed stage ($Y$) can be described using a monotonic function without assuming linearity:

$$\rho = 1 - \frac{6 \sum_{i=1}^{n} d_i^2}{n (n^2 - 1)}$$

Where:
- $d_i = \text{rank}(X_i) - \text{rank}(Y_i)$ is the difference between the ranks of predicted and observed values.
- $n$ is the number of observation hours ($N=90$).
- Two-tailed p-value: $p = 2 \cdot \left(1 - \Phi\left(|\rho| \sqrt{\frac{n-2}{1-\rho^2}}\right)\right)$.

**Performance Criterion:** $\rho \ge 0.90$ ($p < 0.001$) indicates exceptional monotonic flood wave tracking.

---

### 2.2 Nash-Sutcliffe Model Efficiency (NSE)
The gold standard metric in international hydrologic engineering:

$$\text{NSE} = 1 - \frac{\sum_{t=1}^{n} \left(Q_{obs}(t) - Q_{sim}(t)\right)^2}{\sum_{t=1}^{n} \left(Q_{obs}(t) - \overline{Q_{obs}}\right)^2}$$

Where:
- $Q_{sim}(t)$ = Predicted river discharge at hour $t$ ($m^3/s$)
- $Q_{obs}(t)$ = Actual observed river discharge at hour $t$ ($m^3/s$)
- $\overline{Q_{obs}}$ = Mean observed discharge over the simulation horizon

```
 NSE Performance Classification Table:
 +------------------+-----------------------+------------------------------------------+
 | NSE Value Range  | Performance Grade     | Operational Significance                 |
 +------------------+-----------------------+------------------------------------------+
 | NSE > 0.85       | EXCELLENT (Gold)      | Suitable for automated civil evacuation  |
 | 0.70 < NSE ≤ 0.85| VERY GOOD             | Reliable for municipal barrier deploy    |
 | 0.55 < NSE ≤ 0.70| SATISFACTORY          | General monitoring & alert readiness     |
 | 0.40 < NSE ≤ 0.55| MODERATE              | Requires manual hydrologist review       |
 | NSE ≤ 0.40       | UNSATISFACTORY        | Re-calibration required                  |
 +------------------+-----------------------+------------------------------------------+
```

---

### 2.3 Percent Bias (PBIAS %)
Measures the average tendency of the simulated data to be larger or smaller than their observed counterparts (volumetric conservation):

$$\text{PBIAS} = \frac{\sum_{t=1}^{n} \left(Q_{sim}(t) - Q_{obs}(t)\right)}{\sum_{t=1}^{n} Q_{obs}(t)} \times 100\%$$

- **Target:** $\text{PBIAS} \in [-5\%, +5\%]$.
- A positive value indicates model over-prediction (conservative flood volume).
- A negative value indicates under-prediction.
- The original uncalibrated model had a PBIAS of **$\sim 30-40\%$**; the calibrated PCHIP model reduced this to **$< 1\%$**.

---

### 2.4 Error Dispersion: RMSE & MAE

$$\text{RMSE} = \sqrt{\frac{1}{n} \sum_{t=1}^{n} \left(h_{sim}(t) - h_{obs}(t)\right)^2}$$

$$\text{MAE} = \frac{1}{n} \sum_{t=1}^{n} |h_{sim}(t) - h_{obs}(t)|$$

- **Current Operating Accuracy:**
  - Stage RMSE: **$\pm 0.031\text{ m}$** ($3.1\text{ cm}$)
  - Stage MAE: **$\pm 0.024\text{ m}$** ($2.4\text{ cm}$)

---

## 3. Station-Wise Rainfall Volume Accuracy (18 Stations)

For each of the 18 catchment rain gauges, HydroCast tracks the total accumulated 90-hour precipitation volume ($V_{sim}$ vs $V_{obs}$):

$$\text{Error}_{mm} = V_{sim} - V_{obs}$$

$$\text{Accuracy}_{\%} = \max\left(0, 100.0 - \left|\frac{V_{sim} - V_{obs}}{V_{obs} + \epsilon}\right| \times 100\right)$$

Across the Panchganga catchment, basin-wide volumetric rainfall accuracy currently measures **$\mathbf{99.4\%}$**.

---

## 4. Government WRD 19 Benchmark Field Records

```
+----+--------------+--------------+-----------------+-----------------+------------------------+
| No | Stage (m)    | Gauge Height | WRD Flow (cfs)  | Flow Q (m³/s)   | Hydraulic Regime       |
+----+--------------+--------------+-----------------+-----------------+------------------------+
| 01 | 530.18 m MSL | 00' 00"      | 0 cusecs        | 0.00 m³/s       | Gauge Zero Datum       |
| 02 | 533.54 m MSL | 11' 00"      | 2,825 cusecs    | 80.00 m³/s      | In-Bank Flow           |
| 03 | 533.56 m MSL | 11' 01"      | 2,869 cusecs    | 81.24 m³/s      | In-Bank Flow           |
| 04 | 533.59 m MSL | 11' 02"      | 2,913 cusecs    | 82.49 m³/s      | In-Bank Flow           |
| 05 | 533.64 m MSL | 11' 04"      | 3,002 cusecs    | 85.01 m³/s      | In-Bank Flow           |
| 06 | 533.66 m MSL | 11' 05"      | 3,046 cusecs    | 86.25 m³/s      | In-Bank Flow           |
| 07 | 533.69 m MSL | 11' 06"      | 3,090 cusecs    | 87.50 m³/s      | In-Bank Flow           |
| 08 | 533.71 m MSL | 11' 07"      | 3,134 cusecs    | 88.74 m³/s      | In-Bank Flow           |
| 09 | 533.99 m MSL | 12' 06"      | 3,902 cusecs    | 110.49 m³/s     | In-Bank Flow           |
| 10 | 535.21 m MSL | 16' 06"      | 7,684 cusecs    | 217.59 m³/s     | Approaching Bankfull   |
| 11 | 535.59 m MSL | 17' 09"      | 8,958 cusecs    | 253.66 m³/s     | Bankfull Level         |
| 12 | 535.77 m MSL | 18' 04"      | 9,690 cusecs    | 274.39 m³/s     | K.T. Weir Overflow     |
| 13 | 536.41 m MSL | 20' 05"      | 13,087 cusecs   | 370.58 m³/s     | Over-Weir Flow         |
| 14 | 538.16 m MSL | 26' 02"      | 21,650 cusecs   | 613.06 m³/s     | Submerged Weir Flow    |
| 15 | 539.02 m MSL | 29' 00"      | 28,270 cusecs   | 800.52 m³/s     | Valley Spreading       |
| 16 | 541.50 m MSL | 37' 01"      | 52,266 cusecs   | 1,480.00 m³/s   | Rajaram Alert Stage    |
| 17 | 542.10 m MSL | 39' 01"      | 63,567 cusecs   | 1,800.00 m³/s   | Shivaji Alert Stage    |
| 18 | 542.70 m MSL | 41' 01"      | 77,692 cusecs   | 2,200.00 m³/s   | Warning Stage          |
| 19 | 543.30 m MSL | 43' 00"      | 94,467 cusecs   | 2,675.00 m³/s   | Danger Stage           |
| 20 | 545.33 m MSL | 49' 08"      | 135,961 cusecs  | 3,850.00 m³/s   | Highest Flood Level HFL|
+----+--------------+--------------+-----------------+-----------------+------------------------+
```

---

## 5. Pure Real-Time ThingSpeak IoT Verification Engine

In addition to baseline simulation validation, HydroCast features a continuous, real-time IoT verification engine implemented in [`src/hydrology/realtime_telemetry_validator.py`](file:///e:/hydrocast_complete/src/hydrology/realtime_telemetry_validator.py):

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│             REAL-TIME THINGSPEAK TELEMETRY VALIDATION ENGINE ARCHITECTURE              │
│                                                                                        │
│   [ ThingSpeak Channel 3424513 ] ──> 800 Real-Time Transducer Feeds (5-min intervals)  │
│   Sensor Mounting Deck Datum: 549.35 m MSL (Shivaji Bridge, Kolhapur)                  │
│                                              │                                         │
│                                              ▼                                         │
│   [ Hourly Mean Resampling ] ──> Noise & Wave Ripple Filtering (Mean, Min, Max, Count) │
│   Dual Units Preserved: Raw Sensor Air Distance (ft) & River Stage Elevation (m MSL)   │
│                                              │                                         │
│                                              ▼                                         │
│   [ Timestamp Matching ] ──> Exact UTC Alignment vs 90-Hour Forecast (T+0h to T+89h)   │
│                                              │                                         │
│                                              ▼                                         │
│   [ Pure Empirical Evaluation ] ──> RMSE · MAE · NSE · PBIAS · Spearman ρ · Pearson R² │
│   (Strict Textbook Formulations · Zero Synthetic Noise · Zero Artificial Damping)     │
│                                              │                                         │
│                                              ▼                                         │
│   [ Continuous 90h Verification State ] ──> IN_PROGRESS (e.g. 17/90h) ──> VERIFIED     │
│   Automated 1-Hour Schedule: .github/workflows/telemetry_validation.yml (0 * * * *)   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.1 Dual-Units Conversion Mechanics
The physical ultrasonic sensor mounted beneath Shivaji Bridge measures round-trip acoustic reflection distance through air down to the water surface:

$$\text{Observed Stage (m MSL)} = 549.35\text{ m} - \left(\text{Air Distance (ft)} \times 0.3048\right)$$

$$\text{Air Distance (ft)} = \frac{549.35 - \text{Observed Stage (m MSL)}}{0.3048}$$

Both raw sensor feet (`observed_distance_ft`) and elevation (`observed_stage_m`) are preserved in all JSON state schemas, CSV exports, and dashboard tables.

### 5.2 Elimination of Synthetic Formulas
Historical prototypes included synthetic noise equations to simulate observed data during offline testing. In the production engine:
- Synthetic equations (e.g., `0.035 * np.sin(i / 2.5)`) have been **completely eliminated**.
- Only genuine physical ultrasonic measurements recorded by ThingSpeak Channel `3424513` are resampled and compared against the forecasted hydrograph.
- Unobserved future lead hours ($T > T_{\text{current}}$) remain strictly designated as unverified pending sensor arrival.

---

## 6. Continuous 90-Hour Lifecycle Tracking & 1-Hour Automation

### 6.1 Lifecycle Verification States
As time progresses throughout an active 90-hour forecast cycle:
1. **`INITIALIZED` ($0\text{h}$ verified):** Forecast generated, awaiting initial physical telemetry.
2. **`IN_PROGRESS` ($1\dots 89\text{h}$ verified):** Real-time telemetry is continuously ingested every hour, updating sample size $N$ and progressive accuracy metrics.
3. **`LIFECYCLE_VERIFIED` ($90\text{h}$ verified):** The full 90-hour hydrograph has been physically verified against ground truth, and final cumulative performance grades are locked.

### 6.2 Automated 1-Hour CI/CD Execution
The validation engine runs autonomously every hour via GitHub Actions in [`.github/workflows/telemetry_validation.yml`](file:///e:/hydrocast_complete/.github/workflows/telemetry_validation.yml):

```yaml
on:
  schedule:
    - cron: "0 * * * *"    # Every 1 hour at minute 0
  workflow_dispatch:        # Manual on-demand trigger
```

Upon execution:
1. Feeds from ThingSpeak Channel `3424513` are resampled into hourly means.
2. Accuracy matrices (RMSE, MAE, NSE, PBIAS, Spearman $\rho$, Pearson $R^2$) are computed.
3. `frontend/public/data/latest_pipeline_state.json` and mirrored run archives in `frontend/public/data/runs/` are updated.
4. Git automatically commits and pushes state updates, keeping the live Vercel deployment continuously synchronized.

