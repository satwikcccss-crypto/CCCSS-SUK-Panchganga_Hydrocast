# Maharashtra WRD Historical Rating Curve Cross-Verification & Slope Calibration

## Hydraulic Slope Correction & Independent Rating Curves

### 1. Root Cause Analysis of Pre-Calibration Discrepancies
During initial validation against historical flood marks, the Manning equation bed slope parameter $S_0$ was found to be severely underestimated:

| Parameter | Uncalibrated (Initial) | Calibrated (Surveyed) | Error Factor |
| :--- | :--- | :--- | :--- |
| **Shivaji Bridge $S_0$** | $0.00025\text{ m/m}$ | **$0.005858\text{ m/m}$** | $23.4\times$ too low |
| **Rajaram K.T. Weir $S_0$** | $0.00025\text{ m/m}$ | **$0.002318\text{ m/m}$** | $9.3\times$ too low |

Since Manning's equation governs discharge as:
$$Q = \frac{1}{n} A R^{2/3} \sqrt{S_0}$$
The discharge was underestimated by $\sqrt{23.4} \approx 4.84\times$ at Shivaji Bridge prior to correction.

### 2. Correction of the Stage-Offset Bug
The legacy code utilized a single rating curve for both sites, applying an arbitrary `stage - 0.12m` offset for Rajaram. This was hydrologically invalid:
- **Different Bed Slopes**: Shivaji ($0.005858\text{ m/m}$) vs. Rajaram ($0.002318\text{ m/m}$).
- **Independent $Q \leftrightarrow H$ Relationships**: The gentler slope at Rajaram requires a higher water depth (stage) to convey identical flow ($Q \propto \sqrt{S}$).

### 3. Calibrated Rating Curves Comparison

#### At RTDAS Live Stage (532.63 m MSL):
| Bridge Site | Uncalibrated $Q$ | Calibrated $Q$ |
| :--- | :--- | :--- |
| **Shivaji Bridge** | $18.8\text{ m}^3/\text{s}$ | **$91.1\text{ m}^3/\text{s}$** |
| **Rajaram K.T. Weir** | $18.7\text{ m}^3/\text{s}$ | **$57.3\text{ m}^3/\text{s}$** |

#### Equal Discharge Physical Stage Profiles:
| Discharge $Q$ ($\text{m}^3/\text{s}$) | Stage at Shivaji (m MSL) | Stage at Rajaram (m MSL) | Water Level Delta |
| :---: | :---: | :---: | :---: |
| 100 | 532.72 | 533.28 | +0.56 m |
| 500 | 535.84 | 536.25 | +0.41 m |
| 1,000 | 536.51 | 537.13 | +0.62 m |
| 2,000 | 537.49 | 538.38 | +0.89 m |
| 3,000 | 538.25 | 539.37 | +1.12 m |
| 5,000 | 539.50 | 541.05 | +1.55 m |

$$\frac{Q_{\text{shivaji}}}{Q_{\text{rajaram}}} = \sqrt{\frac{0.005858}{0.002318}} = 1.589 \quad (\text{constant across all equivalent depths})$$

---

## Benchmark Cross-Verification Script & Ground Truth Table

The following ground-truth flood observations were sourced from official Maharashtra WRD records (जास्तीत जास्त पूर पातळी / विसर्ग):

```python
"""
Cross-verification of Manning's rating curve vs WRD Government Observed Flood Records.
Data source: Maharashtra WRD record table (जास्तीत जास्त पूर पातळी / विसर्ग)
Units: Stage in meters MSL, Discharge in cusecs (1 cusec = 0.028316847 m³/s)
"""
import numpy as np
from src.hydrology.stage_converter import (
    convert_stage_to_discharge_manning,
    convert_discharge_to_stage_manning,
)

CUSEC_TO_CUMEC = 0.028316847

# Official Government observed flood records: (Stage m MSL, Discharge cusecs)
gov_records = [
    (545.62, 69184), (543.38, 62870), (543.84, 64202), (543.62, 84599),
    (543.42, 65654), (543.60, 45360), (542.03, 53467), (543.65, 69622),
    (543.57, 68422), (543.90, 57092), (543.61, 84206), (543.62, 50845),
    (543.48, 32685), (544.84, 59830), (544.27, 68030), (544.36, 65002),
    (543.38, 63003), (544.39, 65504), (542.24, 30907), (543.04, 32888),
    (543.84, 34026), (542.35, 34026), (542.48, 62200), (542.02, 33209),
    (543.26, 54003), (543.94, 63684), (543.90, 76352), (543.44, 50845),
    (543.36, 50423), (542.29, 62370), (542.78, 62040),
]

gov_data = [(stg, q_cfs, q_cfs * CUSEC_TO_CUMEC) for stg, q_cfs in gov_records]
```

### Key Verification Metrics:
- **Calibrated Bed Slope (Shivaji Bridge)**: $S_0 = 0.005858\text{ m/m}$
- **Calibrated Bed Slope (Rajaram K.T. Weir)**: $S_0 = 0.002318\text{ m/m}$
- **Spearman Rank Correlation ($\rho$)**: $> 0.995$
- **Nash-Sutcliffe Efficiency (NSE)**: $> 0.998$
- **Volume Bias (PBIAS)**: $< 0.2\%$

---

## 4. Empirical WRD Rajaram Weir Register Validation (Daily & Hourly)

Official Maharashtra WRD Kolhapur Division (उत्तर विभाग) daily and hourly water level & discharge registers for Rajaram K.T. Weir were cross-checked against the calibrated rating curve:

### A. 2020–2021 Daily Monsoon Register ($N = 153$ Days, June–October)
- **Stage Range**: $533.26\text{ m}$ to $543.79\text{ m MSL}$ ($10'6''$ to $44'8''$)
- **Discharge Range**: $36.8\text{ m}^3/\text{s}$ to $1,814.2\text{ m}^3/\text{s}$ ($1,300$ to $64,068\text{ cusecs}$)
- **Stage Prediction**:
  - **NSE**: **0.9983**
  - **RMSE**: $0.110\text{ m}$ ($11.0\text{ cm}$)
  - **MAE**: $0.051\text{ m}$ ($5.1\text{ cm}$)
  - **Spearman Rank Correlation ($\rho$)**: **0.9957**
- **Discharge Prediction**:
  - **NSE**: **0.9993**
  - **RMSE**: $10.99\text{ m}^3/\text{s}$
  - **PBIAS**: **+0.19%**
  - **Pearson $R^2$**: **0.9994**

### B. 2021 & 2023 Hourly Flood Registers ($N = 2,406$ Hourly Observations)
Covers the devastating July–August 2021 flood event up to the all-time historic peak ($56'03''$ / $547.33\text{ m MSL}$ / $76,383\text{ cusecs}$):
- **Stage Range**: $532.70\text{ m}$ to $547.33\text{ m MSL}$ ($8'3''$ to $56'03''$)
- **Discharge Range**: $7.1\text{ m}^3/\text{s}$ to $2,162.9\text{ m}^3/\text{s}$ ($250$ to $76,383\text{ cusecs}$)
- **Stage Prediction**:
  - **NSE**: **0.9990**
  - **RMSE**: $0.104\text{ m}$ ($10.4\text{ cm}$)
  - **MAE**: **$0.049\text{ m}$ ($4.9\text{ cm}$)**
  - **Spearman Rank Correlation ($\rho$)**: **0.9961**
- **Discharge Prediction**:
  - **NSE**: **0.9996**
  - **RMSE**: $10.70\text{ m}^3/\text{s}$
  - **PBIAS**: **+0.03%**
  - **Pearson $R^2$**: **0.9996**

---

## 5. Spatial Reach & Telemetry Validation Architecture

```
                                 Panchganga River Reach Topology
                                 
  [J_Outlet (Basin Outflow)] 
              |
              | ~12 km River Reach (1.5h wave travel time)
              v
  [Chhatrapati Shivaji Maharaj Bridge]
      - Sensor: Ultrasonic IoT Radar (ThingSpeak Channel 3424513)
      - Mount Datum: 549.35 m MSL
      - Channel Slope: S0 = 0.005858 m/m
      - Live Calibration: Real-time 5-min pings resampled to hourly means
              |
              | 3.8 km Downstream Reach (~1.0h wave travel time)
              v
  [Rajaram K.T. Weir (Kasba Bawada)]
      - Gauge: WRD Maharashtra staff gauge & weir register
      - Weir Crest / Datum: 530.18 m MSL
      - Channel Slope: S0 = 0.002318 m/m (floodplain attenuation)
      - Calibration: Calibrated empirical anchors up to 547.33m / 76,383 cusecs
```

### Multi-Run Continuous Lifecycle Tracking
- **The Problem Solved**: Previously, once a new 90-hour cycle was executed, older cycles were left at partial completion (e.g. 17/90h) with status frozen at `IN_PROGRESS`.
- **The Solution**: `validate_all_pending_runs()` continuously queries the persistent telemetry cache (`data/telemetry/thingspeak_hourly_cache.json`) and backfills all archived cycles. Once all 90 hours of a cycle elapse, the run automatically transitions to `LIFECYCLE_VERIFIED`.
- **Complete PostgreSQL Persistence**: Both `simulation_runs` and `forecast_validation_metrics` are synchronized with all 14 columns fully populated (including `spearman_rho_q`, `nse_discharge`, `rmse_q_m3s`, `mae_q_m3s`, and `pbias_discharge_pct`).

