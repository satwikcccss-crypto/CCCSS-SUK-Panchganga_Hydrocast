# HEC-HMS 4.13 Basin Model & Hydrological Simulation Engine

```
====================================================================================================
           PANCHGANGA HYDROCAST - HEC-HMS 4.13 HYDROLOGICAL ROUTING ARCHITECTURE
====================================================================================================

      [ Subbasin S6: Gaganbawda ]               [ Subbasin S7: Garivade ]
      Area: 227.72 km2 | CN: 61.78              Area: 195.39 km2 | CN: 61.28
      Lag: 3,318.1 min (55.3h)                  Lag: 3,362.3 min (56.0h)
                  \                                        /
                   \                                      /
                    v                                    v
                 +------------------------------------------+
                 |       Reach R5 (Upper Kumbhi River)      |
                 |      K = 18.338 hr  |  X = 0.250         |
                 +------------------------------------------+
                                       |
  [ Subbasin S9: Radhanagari ]         |  (R5 Outflow)
  Area: 366.97 km2 | CN: 64.31         |
  Lag: 5,199.0 min (86.7h)             |
             |                         |
             v                         |
  +--------------------+               |
  | Reach R4 (Bhogavati)|              |
  | K=8.085h | X=0.250 |               |
  +--------------------+               |
             |                         |
             | (R4 Outflow)            |       [ Subbasin S8: Beed ]
             \                         |       Area: 177.44 km2 | CN: 65.76
              \                        |       Lag: 3,387.1 min (56.5h)
               v                       v                  |
          +------------------------------------------+    |
          |       Reach R2 (Middle Panchganga)       |<---+ (Direct S8 Inflow)
          |        K = 16.500 hr  |  X = 0.250       |
          +------------------------------------------+
                                |
                                | (R2 Outflow)
                                v
      [ Subbasin S4: Karanjphen ]               [ Subbasin S5: Padasali ]
      Area: 262.00 km2 | CN: 61.89              Area: 106.39 km2 | CN: 60.97
      Lag: 3,115.5 min (51.9h)                  Lag: 2,117.1 min (35.3h)
                  \                                        /
                   \                                      /
                    v                                    v
                 +------------------------------------------+
                 |       Reach R3 (Kasari River Main)       |
                 |       K = 9.484 hr  |  X = 0.250         |
                 +------------------------------------------+
                                       |
                                       | (R3 Outflow)
                                       v
          +-------------------------------------------------------------+
          |             Reach R1 (Lower Panchganga Trunk)               |
          |                 K = 4.500 hr  |  X = 0.250                  |<--+ [ Subbasin S3: Kotoli ]
          +-------------------------------------------------------------+   | Area: 261.32 km2 | CN: 64.82
                                       |                                    | Lag: 3,997.7 min (66.6h)
                                       | (R1 Outflow)                       |
                                       v                                    +-- [ Subbasin S2: Sangarul ]
          +=============================================================+   | Area: 153.77 km2 | CN: 65.74
          |          Sink-1: Panchganga Basin Outlet (Rajaram)          |   | Lag: 3,154.3 min (52.6h)
          |                                                             |<--+
          |   + [ Subbasin S1: Karveer Direct ] (Area: 86.213 km2)      |
          |   + [ Exponential Baseflow Recession: Q_bf(t) ]             |
          |   = Total Computed Hydrograph: Q_total(t) [0 .. 89 hrs]     |
          +=============================================================+
                                       |
                                       v
                    [ 2D Surveyed Hydraulic Rating Curve ]
                     - Shivaji Bridge: Chainage 6+257 (Sensor)
                     - Rajaram KT Weir: Chainage 10+115 (Sink)
```

---

## 1. Engineering Overview & Execution Engine

The **HydroCast Hydrological Simulation Engine** implements a dual-mode, headless architecture modeling the entire **1,837.213 km² Panchganga River basin** up to the Rajaram K.T. Weir. The system operates on 6-hourly automated cycles (00z, 06z, 12z, 18z), projecting continuous **90-hour river discharge ($m^3/s$)** and **water surface elevation ($m\text{ MSL}$)**.

### 1.1 Dual Execution Architecture

1. **Primary Execution Mode: Headless USACE HEC-HMS 4.13 Binary**
   - Automatically detected at:
     - Linux/Container: `/opt/hec-hms/hec-hms.sh` or `/usr/local/hec-hms/hec-hms.sh`
     - Windows: `C:\Program Files\HEC\HEC-HMS-4.13\hec-hms.cmd`
   - Triggered via automated Jython/Python scripting (`write_jython_script()`) passing dynamic 90-hour DSS precipitation hyetographs and parameter overrides.

2. **Calibrated Physical Emulator: Pure-Python Vectorized Solver**
   - When running in microservice environments or GitHub Actions CI where the bulky Java GUI binary is absent (`HMS_FORCE_EMULATOR=1`), HydroCast executes a 100% physically identical vectorized Python emulator in `src/hms/runner.py`.
   - Executes in **< 15 milliseconds** per 90-hour cycle using NumPy and SciPy.
   - Preserves identical governing equations: **SCS Curve Number Loss**, **SCS Dimensionless Unit Hydrograph Transform**, **Muskingum Channel Reach Routing with Numerical Sub-stepping**, and **Exponential Baseflow Recession**.

---

## 2. Mathematical Formulations

### 2.1 SCS Curve Number Loss Method with Dynamic AMC

The model partitions rainfall into initial abstraction, infiltration, and surface runoff depth using the USDA Soil Conservation Service (SCS) Curve Number method (NEH-4).

#### 2.1.1 Potential Maximum Soil Retention ($S$)
For a given antecedent Curve Number ($CN$):

$$S = \frac{25400}{CN} - 254 \quad [\text{mm}]$$

#### 2.1.2 Dynamic Antecedent Moisture Condition (AMC) Tracking
Soils in the Western Ghats undergo rapid saturation transitions during active monsoon storms. The model dynamically evaluates the catchment-mean 90-hour rainfall forecast:

$$\bar{P}_{90} = \frac{1}{9}\sum_{i=1}^{9} \sum_{t=0}^{89} P_{i}(t) \quad [\text{mm}]$$

- **Normal / Moderate Moisture (AMC-II):** $\bar{P}_{90} < 65\text{ mm}$
  - Curve Number retains baseline: $CN = CN_{\text{II}}$
  - Initial Abstraction: $I_a = 0.15 \cdot S$
- **Saturated Monsoon Condition (AMC-III):** $\bar{P}_{90} \ge 65\text{ mm}$
  - Curve Number scales to saturated condition via the Sobhani empirical transformation:
    $$CN_{\text{III}} = \min\left(98.0, \; \frac{CN_{\text{II}}}{0.427 + 0.00573 \cdot CN_{\text{II}}}\right)$$
  - Initial Abstraction drops due to saturated pore space: $I_a = 0.08 \cdot S$

#### 2.1.3 Cumulative Runoff & Incremental Excess Rainfall
For each hour $h \in [0, 89]$:

$$Q_{\text{cum}}(h) = \begin{cases} 
0.02 \cdot P_{\text{cum}}(h) & \text{if } P_{\text{cum}}(h) \le I_a \\[1ex]
\dfrac{(P_{\text{cum}}(h) - I_a)^2}{P_{\text{cum}}(h) - I_a + S} + 0.02 \cdot P_{\text{cum}}(h) & \text{if } P_{\text{cum}}(h) > I_a
\end{cases}$$

> [!NOTE]
> The term $0.02 \cdot P_{\text{cum}}(h)$ represents the direct impervious surface fraction (river water surface, exposed rock outcrops, urban pavement), preventing artificial hard zero step-functions in early hydrographs.

The incremental hourly excess rainfall hyetograph $\Delta P_{\text{excess}}(h)$ is derived by backward differencing:

$$\Delta P_{\text{excess}}(h) = \max\left(0.0, \; Q_{\text{cum}}(h) - Q_{\text{cum}}(h - 1)\right)$$

---

### 2.2 SCS Dimensionless Unit Hydrograph Transform (SCS-UH)

Excess rainfall depth (mm) is converted into direct runoff discharge ($m^3/s$) via convolution with the SCS Dimensionless Unit Hydrograph.

#### 2.2.1 Time to Peak ($t_p$)
For a standard 1-hour unit duration ($\Delta t = 1.0\text{ hr}$):

$$t_p = \frac{\Delta t}{2} + t_{\text{lag}} = 0.5 + \frac{t_{\text{lag, min}}}{60.0} \quad [\text{hours}]$$

#### 2.2.2 Dimensionless Curvilinear Unit Hydrograph Shape
The curvilinear unit hydrograph ordinate $u(t)$ is defined by the Gamma function approximation (SCS National Engineering Handbook):

$$u(t) = \left(\frac{t}{t_p}\right)^m \exp\left[m \left(1 - \frac{t}{t_p}\right)\right], \quad m = 3.7$$

```
   q / q_p
    1.0 |                    * * *
        |                *           *
    0.8 |              *               *
        |             *                 *
    0.6 |            *                   *
        |           *                     *
    0.4 |          *                       * *
        |         *                            * *
    0.2 |        *                                 * * *
        |       *                                       * * * * * *
    0.0 +-------+--------+--------+--------+--------+--------+--------+---> t / t_p
       0.0     0.5      1.0      1.5      2.0      2.5      3.0      3.5
```

#### 2.2.3 Mass Conservation Volume Normalization
To ensure rigorous mass conservation, the unit hydrograph is normalized so that the total integral corresponds to exactly $1.0\text{ mm}$ of excess precipitation distributed over the subbasin catchment area ($A_{\text{sub}}$ in $\text{km}^2$):

$$V_{\text{target}} = A_{\text{sub}} \times 10^6 \text{ m}^2 \times 0.001 \text{ m} = A_{\text{sub}} \times 1000 \quad [\text{m}^3]$$

$$V_{\text{discrete}} = \sum_{t=0}^{89} u(t) \times 3600 \text{ seconds} \quad [\text{m}^3]$$

$$UH(t) = u(t) \times \frac{V_{\text{target}}}{V_{\text{discrete}}} \quad [\text{m}^3/\text{s per mm}]$$

#### 2.2.4 Discrete Time Convolution
The direct surface runoff hydrograph $Q_{\text{direct}}(t)$ for each subbasin is computed via discrete convolution:

$$Q_{\text{direct}}(t) = \sum_{\tau=0}^{t} \Delta P_{\text{excess}}(\tau) \cdot UH(t - \tau), \quad t = 0, 1, \dots, 89$$

---

### 2.3 Muskingum Channel Reach Routing Engine

Flood wave translation and attenuation across the 5 trunk reaches are computed using the **Muskingum storage method** ($S = K [X I + (1 - X) O]$).

#### 2.3.1 Governing Finite-Difference Equations
For each reach with travel time $K$ (hours) and weighting factor $X$ ($0.15 \le X \le 0.40$):

$$O_t = C_0 I_t + C_1 I_{t-1} + C_2 O_{t-1}$$

The routing coefficients are:

$$C_0 = \frac{\Delta t - 2 K X}{2 K (1 - X) + \Delta t}$$

$$C_1 = \frac{\Delta t + 2 K X}{2 K (1 - X) + \Delta t}$$

$$C_2 = \frac{2 K (1 - X) - \Delta t}{2 K (1 - X) + \Delta t}$$

$$\text{Verification Check:} \quad C_0 + C_1 + C_2 = 1.000$$

#### 2.3.2 Internal Numerical Sub-stepping for Stability
Standard 1-hour simulation time steps ($\Delta t = 1.0	ext{ hr}$) can violate the numerical stability criterion ($\Delta t \le 2 K X$), causing numerical oscillations and negative outflows when $K$ is small. HydroCast implements an automated adaptive sub-step division:

$$\text{steps} = \max\left(1, \; \text{round}\left(\frac{K}{\max(0.1, 2 K X)}\right)\right), \quad \Delta t_{\text{sub}} = \frac{K}{\text{steps}}$$

Internal routing iterates through `steps` sub-reaches, guaranteeing unconditional stability and non-negative discharge ($O_t \ge 0$).

---

## 3. Subbasin & Reach Parameter Matrices

### 3.1 Subbasin Catchment Parameters (Official Basin_1.basin)

Total modeled catchment area to Rajaram K.T. Weir: **1,837.213 km²**.

| Subbasin ID | Catchment Name | Area ($km^2$) | Area (%) | Base $CN_{\text{II}}$ | Base Lag $t_{\text{lag}}$ (min) | Lag Time (hr) | Time to Peak $t_p$ (hr) |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **S1** | Karveer (Local) | 86.213 | 4.69% | 74.85 | 2,152.0 | 35.87h | 36.37h |
| **S2** | Sangarul | 153.770 | 8.37% | 65.74 | 3,154.3 | 52.57h | 53.07h |
| **S3** | Kotoli | 261.320 | 14.22% | 64.82 | 3,997.7 | 66.63h | 67.13h |
| **S4** | Karanjphen | 262.000 | 14.26% | 61.89 | 3,115.5 | 51.93h | 52.43h |
| **S5** | Padasali | 106.390 | 5.79% | 60.97 | 2,117.1 | 35.29h | 35.79h |
| **S6** | Gaganbawda | 227.720 | 12.39% | 61.78 | 3,318.1 | 55.30h | 55.80h |
| **S7** | Garivade | 195.390 | 10.64% | 61.28 | 3,362.3 | 56.04h | 56.54h |
| **S8** | Beed | 177.440 | 9.66% | 65.76 | 3,387.1 | 56.45h | 56.95h |
| **S9** | Radhanagari | 366.970 | 19.97% | 64.31 | 5,199.0 | 86.65h | 87.15h |
| **TOTAL** | **Panchganga Basin** | **1,837.213** | **100.0%** | **64.71 (wt)** | — | — | — |

---

### 3.2 Muskingum Reach Routing Connectivity & Parameters

| Reach ID | River Reach Description | Inflow Sources | Outflow Destination | Travel Time $K$ (hr) | Wedge Weight $X$ | Length (km) | Numerical Sub-steps |
|:---|:---|:---|:---|:---:|:---:|:---:|:---:|
| **R5** | Upper Kumbhi River | $S_6 + S_7$ | Reach R2 | 18.338 | 0.250 | ~24.5 km | 2 steps |
| **R4** | Bhogavati River Trunk | $S_9$ | Reach R2 | 8.085 | 0.250 | ~14.2 km | 1 step |
| **R2** | Middle Panchganga Reach | $O_{R5} + O_{R4} + S_8$ | Reach R1 | 16.500 | 0.250 | ~28.0 km | 2 steps |
| **R3** | Kasari River Main | $S_4 + S_5$ | Reach R1 | 9.484 | 0.250 | ~16.8 km | 1 step |
| **R1** | Lower Panchganga Trunk | $O_{R2} + O_{R3} + S_3 + S_2$ | Sink-1 (Rajaram) | 4.500 | 0.250 | ~11.5 km | 1 step |

---

## 4. Baseflow Dynamics & Ground Truth Sensor Ingestion

### 4.1 Exponential Baseflow Recession Formulation
Natural groundwater discharge from the weathered Deccan Traps basalt aquifer discharges continuously into the riverbed. The baseflow hydrograph decays according to the Barnes exponential recession equation:

$$Q_{\text{bf}}(t) = Q_{\text{bf0}} \cdot \exp(-k_{\text{rec}} \cdot t)$$

- **Decay constant:** $k_{\text{rec}} = 0.002\text{ hr}^{-1}$ (calibrated against non-storm dry season recession logs)
- **Minimum Physical Baseline Floor:** $\ge 15.0\text{ m}^3/\text{s}$ (ensuring the 1,837 km² perennial basin never drops to unphysical zero discharge).

### 4.2 Sensor-to-Sink Spatial Transfer: Shivaji Bridge to Rajaram K.T. Weir

A critical physical nuance of the Panchganga river system:
1. **IoT Water Level Telemetry Sensor:** Located at **Chhatrapati Shivaji Maharaj Bridge** (Chainage 6+257 from Krishna confluence, Thalweg RL = 528.670 m MSL).
2. **HEC-HMS Hydrological Model Sink:** Located at **Rajaram K.T. Weir** (Chainage 10+115 from Krishna confluence, Thalweg RL = 529.318 m MSL).

```
   UPSTREAM                                                    DOWNSTREAM
   Chainage 10+115                                           Chainage 6+257
   Rajaram K.T. Weir                                         Shivaji Bridge
   (HEC-HMS Model Sink-1)                                    (IoT Ultrasonic Sensor)
   ======================                                    ======================
         |                                                            |
         |  Thalweg: 529.318 m MSL                                    |  Thalweg: 528.670 m MSL
         |  Crest RL: 530.18 m MSL                                    |  Sensor Datum: 549.35 m MSL
         |                                                            |
         +------------------- Bed Distance: 3,858 m ------------------+
                             Bed Slope: S_0 = 1:4641 (0.000215)
                             Delta Bed RL: +0.648 m (Rajaram higher)
```

The model applies `infer_rajaram_stage_from_shivaji(shivaji_stage_m, q_m3s)` to back-calculate the initial water surface elevation at the model sink before converting stage to baseflow via the WRD PCHIP rating curve:

$$H_{\text{rajaram}} = H_{\text{shivaji}} + \Delta z_{\text{bed}} + \Delta h_{\text{weir}}$$

- $\Delta z_{\text{bed}} = +0.648\text{ m}$ (surveyed thalweg differential over 3,858 m).
- $\Delta h_{\text{weir}}$: Backwater effect of the Kolhapur Type (K.T.) weir when stage is below or near crest ($530.18\text{ m}$ MSL).

---

## 5. Peak Arrival & Low-Flow Protection Algorithm

During non-monsoon or dry periods, the surface runoff wave is near zero, and the hydrograph is dominated by a flat or decaying baseflow. If an unconstrained `np.argmax(q)` was executed, small numerical noise or flat zeroes would cause the algorithm to report a false peak at $T+89\text{h}$.

HydroCast implements the **Physical Flood Wave Significance Rule**:

```python
# Physical flood wave significance check in src/hms/runner.py
peak_idx = int(np.argmax(q_total))
peak_surface_q = float(q_surface[peak_idx])
initial_baseflow = float(baseflow_array[0])

# Event is significant ONLY if surface runoff peak exceeds 2x baseflow
is_significant_event = peak_surface_q > max(0.5, initial_baseflow * 2.0)
if not is_significant_event:
    peak_idx = 0  # Declare T+0 (flow is receding / baseflow stable)
```

When `is_significant_event == False`:
- Lead hours to peak is declared $T+0\text{h}$
- Lifecycle status is marked `BASEFLOW_STABLE`
- Prevents spurious flood alarms during low-flow periods.
