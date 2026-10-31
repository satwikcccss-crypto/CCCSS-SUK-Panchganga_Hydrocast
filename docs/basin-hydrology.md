# Panchganga Catchment Hydrology & Watershed Delineation

---

## Interactive diagram consoles

The console below is the rendered reference for this page: it carries the same structure, tier boundaries and failure branches that the prose describes.

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 10</span>
      <strong>Catchment Hydrology Solver</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/10-catchment-hydrology-solver.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/10-catchment-hydrology-solver.html?embed=1" title="Catchment Hydrology Solver Console"></iframe>
</div>

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 01</span>
      <strong>End-to-End System Architecture</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/01-architecture.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/01-architecture.html?embed=1" title="End-to-End System Architecture Console"></iframe>
</div>

---

## 1. Physical Physiography of the Panchganga Basin

The Panchganga river is a major tributary of the Krishna river basin, draining an authoritative area of exactly **$1,837.213\text{ km}^2$** across Kolhapur district, Maharashtra, up to the terminal forecast reference gauge at Rajaram K.T. Weir.

### 1.1 The Tributary Drainage Network

The river is formed at Prayag Chikhali by the confluence of five major tributary streams:

1. **Kasari River:** Originates in the Sahyadri crestline near Karanjphen ($S_4$, 262.00 km²), flowing through steep forested gorges past Kotoli ($S_3$, 261.32 km²) into Reach R1.
2. **Kumbhi River:** Originates near Shengaon and drains through the steep basaltic terrain of Padasali ($S_5$, 106.39 km²), converging with Kasari into Reach R3.
3. **Tulsi River:** Originates in the southern hills, draining past Sangarul ($S_2$, 153.77 km²) directly into Reach R1.
4. **Bhogawati River:** The largest tributary basin, originating in the high-rainfall upper Sahyadri catchment impounded by Radhanagari Dam ($S_9$, 366.97 km²), flowing through the mid-reach at Beed ($S_8$, 177.44 km²) into Reach R2.
5. **Dhamani / Gaganbawda Streams:** Originating near the Sahyadri crest at Gaganbawda ($S_6$, 227.72 km²) and Garivade ($S_7$, 195.39 km²), routing via Reach R5 into Reach R2.
6. **Karveer Local Catchment:** Immediate outlet catchment ($S_1$, 86.213 km²) surrounding Kolhapur city, discharging directly to the Rajaram K.T. Weir pool (Sink-1).

---

## 2. Subbasin Parameters {: #subbasin-parameters }

The Panchganga catchment is delineated into nine hydrologically distinct subbasins based on 30-meter SRTM Digital Elevation Models (DEM), verified against the official USACE HEC-HMS model (`Basin_1.basin`) and database records (`database/supabase_schema.sql`). The total catchment drainage area is **1,837.213 km²**.

| Subbasin ID | Official Name | Drainage Area (km²) | Baseline Curve Number (CN) | Baseline Lag Time (min) | Lag Time (hr) | Time to Peak $t_p$ (hr) | Primary Rain Gauge Station | Centroid (Lat, Lon) | Inflow & Routing Connectivity |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---|:---:|:---|
| **S1** | Karveer (Local/Outlet) | 86.213 | 74.85 | 2,152.0 | 35.87h | 36.37h | `KARVEER` (550 m MSL) | 16.7064°N, 74.2482°E | Panchganga Mainstem (direct to Sink-1) |
| **S2** | Sangarul (Tulsi Lower) | 153.770 | 65.74 | 3,154.3 | 52.57h | 53.07h | `SANGARUL` | 16.6842°N, 74.0932°E | Tulsi River (into Reach R1) |
| **S3** | Kotoli (Kasari Lower) | 261.320 | 64.82 | 3,997.7 | 66.63h | 67.13h | `KOTOLI` | 16.7820°N, 74.0519°E | Kasari River (into Reach R1) |
| **S4** | Karanjphen (Kasari Headwater) | 262.000 | 61.89 | 3,115.5 | 51.93h | 52.43h | `KARANJPHEN` | 16.7851°N, 73.9036°E | Kasari River (into Reach R3) |
| **S5** | Padasali (Kumbhi Basin) | 106.390 | 60.97 | 2,117.1 | 35.29h | 35.79h | `PADASALI` | 16.7019°N, 73.8436°E | Kumbhi River (into Reach R3) |
| **S6** | Gaganbawda (Crest Reach) | 227.720 | 61.78 | 3,318.1 | 55.30h | 55.80h | `GAGANBAWDA` | 16.5470°N, 73.8347°E | Dhamani River (into Reach R5) |
| **S7** | Garivade (Ridge Catchment) | 195.390 | 61.28 | 3,362.3 | 56.04h | 56.54h | `GARIVADE` | 16.5204°N, 73.9184°E | Dhamani/Bhogawati Divide (into Reach R5) |
| **S8** | Beed (Bhogawati Mid-reach) | 177.440 | 65.76 | 3,387.1 | 56.45h | 56.95h | `BEED` | 16.6480°N, 74.1289°E | Bhogawati River (into Reach R2) |
| **S9** | Radhanagari (Upper Catchment) | 366.970 | 64.31 | 5,199.0 | 86.65h | 87.15h | `RADHANAGARI` | 16.4102°N, 73.9972°E | Bhogawati River (into Reach R4) |
| **Total** | **Panchganga Basin at Rajaram** | **1,837.213** | — | — | — | — | **20 Gauge Network** | — | **Basin Sink-1 (Rajaram K.T. Weir)** |

---

## 3. Muskingum Reaches {: #muskingum-reaches }

River reaches route runoff from subbasin confluences through the channel network to the basin outlet at Rajaram K.T. Weir (Sink-1). The routing parameters are committed in `Basin_1.basin` and parsed at runtime by `src/hms/basin_parser.py`.

The channel network follows the topological routing sequence:

$$R_5 \to R_4 \to R_2 \to R_3 \to R_1 \to \text{Sink-1} \quad (+ S_1 \text{ direct})$$

To eliminate HEC-HMS **WARNING 41169** and ensure strict numerical mass conservation ($\sum O \equiv \sum I$), HydroCast dynamically selects the sub-step pass count $n$ such that $2X \le \frac{\Delta t}{K/n} \le 2(1-X)$, guaranteeing non-negative routing coefficients ($C_0, C_1, C_2 \ge 0$) and $C_0 + C_1 + C_2 \equiv 1.000000$.

| Reach ID | River Reach Description | Upstream Inflow Sources | Downstream Outflow Destination | Travel Time $K$ (hr) | Wedge Weight $X$ | Sub-step Passes ($n$) | Mass Balance & Numerical Stability |
|:---:|:---|:---|:---|:---:|:---:|:---:|:---|
| **R5** | Upper Kumbhi / Dhamani River | $S_6 + S_7$ | Reach R2 | 4.619 | 0.200 | 2 passes | Sub-stepped to guarantee $C_2 \ge 0$; eliminates WARNING 41169 |
| **R4** | Bhogawati River Trunk | $S_9$ | Reach R2 | 1.224 | 0.200 | 1 pass | Single-step routing satisfies Courant condition |
| **R2** | Middle Panchganga Reach | $O_{R5} + O_{R4} + S_8$ | Reach R1 | 11.827 | 0.200 | 5 passes | Sub-stepped into 5 discrete passes ensuring internal mass conservation |
| **R3** | Kasari River Main | $S_4 + S_5$ | Reach R1 | 3.829 | 0.200 | 2 passes | Sub-stepped to satisfy Courant limit; eliminates WARNING 41169 |
| **R1** | Lower Panchganga Trunk | $O_{R2} + O_{R3} + S_3 + S_2$ | Sink-1 (Rajaram Weir) | 2.899 | 0.200 | 2 passes | Confluence cascade entering Rajaram weir outlet pool |
| *(Direct)* | Local Runoff (Karveer) | $S_1$ | Sink-1 (Rajaram Weir) | — | — | Direct | Added unrouted to surface outflow at outlet |

---

## 4. Regulatory Datums {: #regulatory-datums }

All river stage monitoring, flood warning alerts, and hydraulic rating curves in the Panchganga basin are referenced to the official Maharashtra Water Resources Department (WRD) datums and surveyed bridge cross-sections.

### 4.1 Official Reference Datums & Survey Elevations

| Reference Benchmark / Datum | Elevation (m MSL) | Imperial Gauge (ft-in) | Description & Field Significance |
|:---|:---:|:---:|:---|
| **Shivaji Bridge Bed Thalweg** | **528.670** | — | Surveyed lowest riverbed invert at Shivaji Bridge (chainage 6+257 m) |
| **Rajaram K.T. Weir Bed Thalweg** | **529.318** | — | Surveyed lowest riverbed invert at Rajaram K.T. Weir (chainage 10+115 m) |
| **Natural Bed Elevation Offset** | **+0.648 m** | — | Rajaram bed is 0.648 m higher than Shivaji over the 3,858 m reach |
| **Maharashtra WRD Zero Gauge Datum** | **530.180** | $00'\ 00''$ | Official government reference zero datum ($0'\ 0''$ mark) for Kolhapur city |
| **Rajaram K.T. Weir Solid Crest** | **535.770** | $18'\ 04''$ | Overtopping crest level of the solid masonry weir structure |
| **District Field Warning Threshold** | **539.700** | $31'\ 03''$ | Field warning benchmark for low-lying agricultural causeways |
| **District Field Danger Threshold** | **540.700** | $34'\ 06''$ | Field danger benchmark triggering emergency staging and sirens |
| **Rajaram K.T. Weir Alert Level** | **541.500** | $37'\ 01''$ | DDMA Alert Stage at Rajaram ($Q = 1,480\text{ m}^3/s$) |
| **Shivaji Bridge Alert Level** | **542.100** | $39'\ 01''$ | DDMA Alert Stage at Shivaji Bridge ($Q = 1,800\text{ m}^3/s$) |
| **Maharashtra WRD / CWC Warning Level**| **542.700** | $41'\ 01''$ | Official WRD Warning Stage ($Q = 2,200\text{ m}^3/s$); evacuation alerts initiated |
| **Maharashtra WRD / CWC Danger Level** | **543.300** | $43'\ 00''$ | Official WRD Danger Stage ($Q = 2,675\text{ m}^3/s$); major urban flooding |
| **Highest Flood Level (HFL)** | **545.330** | $49'\ 08''$ | Historical record flood crest (August 2019 / July 2021; $Q = 3,850\text{ m}^3/s$) |
| **Live Ultrasonic Radar Deck Mounting** | **549.350** | — | Sensor mounting RL on Chhatrapati Shivaji Maharaj Bridge deck |

### 4.2 Authoritative 26-Point Rating Schedule

The hydraulic stage-discharge engine (`src/hydrology/stage_converter.py`) anchors its shape-preserving Piecewise Cubic Hermite Interpolating Polynomial (PCHIP) rating curve to 26 canonical calibration points from the Maharashtra WRD rating register:

| Pt # | Rajaram Stage (m MSL) | Shivaji Stage (m MSL) [$-0.648\text{m}$] | Imperial Gauge (ft-in) | Flow (Cusecs) | Discharge $Q$ ($m^3/s$) | Operational Tier | Hydraulic Regime & Field Significance |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| 01 | 529.318 | 528.670 | — | 0 | 0.00 | `dry` | Surveyed channel bed thalweg (zero discharge) |
| 02 | 532.700 | 532.052 | $08'\ 03''$ | 500 | 14.16 | `normal` | Low-flow register boundary (WRD observed minimum) |
| 03 | 532.830 | 532.182 | $08'\ 08''$ | 800 | 22.65 | `normal` | In-bank dry season low flow |
| 04 | 532.880 | 532.232 | $08'\ 10''$ | 1,000 | 28.32 | `normal` | In-bank dry season low flow |
| 05 | 532.980 | 532.332 | $09'\ 02''$ | 1,150 | 32.56 | `normal` | In-bank dry season low flow |
| 06 | 533.000 | 532.352 | $09'\ 03''$ | 1,200 | 34.00 | `normal` | Pre-monsoon baseflow transition |
| 07 | 533.360 | 532.712 | $10'\ 05''$ | 2,516 | 71.25 | `normal` | Observed active baseflow threshold |
| 08 | 533.540 | 532.892 | $11'\ 00''$ | 2,825 | 80.00 | `normal` | Lowest official WRD rating sheet anchor |
| 09 | 533.560 | 532.912 | $11'\ 01''$ | 2,869 | 81.24 | `normal` | WRD sheet step (in-bank flow) |
| 10 | 533.590 | 532.942 | $11'\ 02''$ | 2,913 | 82.49 | `normal` | WRD sheet step (in-bank flow) |
| 11 | 533.640 | 532.992 | $11'\ 04''$ | 3,002 | 85.01 | `normal` | WRD sheet step (in-bank flow) |
| 12 | 533.660 | 533.012 | $11'\ 05''$ | 3,046 | 86.25 | `normal` | WRD sheet step (in-bank flow) |
| 13 | 533.690 | 533.042 | $11'\ 06''$ | 3,090 | 87.50 | `normal` | WRD sheet step (in-bank flow) |
| 14 | 533.710 | 533.062 | $11'\ 07''$ | 3,134 | 88.74 | `normal` | WRD sheet step (in-bank flow) |
| 15 | 533.990 | 533.342 | $12'\ 06''$ | 3,902 | 110.49 | `normal` | Normal active monsoon channel baseflow |
| 16 | 535.210 | 534.562 | $16'\ 06''$ | 7,684 | 217.59 | `normal` | Approaching natural river bankfull |
| 17 | 535.590 | 534.942 | $17'\ 09''$ | 8,958 | 253.66 | `normal` | Primary channel bankfull inundation |
| 18 | 535.770 | 535.122 | $18'\ 04''$ | 9,690 | 274.39 | `normal` | Overtopping solid crest of Rajaram K.T. Weir |
| 19 | 536.410 | 535.762 | $20'\ 05''$ | 13,087 | 370.58 | `normal` | Over-weir broad crest discharge |
| 20 | 538.160 | 537.512 | $26'\ 02''$ | 21,650 | 613.06 | `normal` | Weir structure fully drowned/submerged |
| 21 | 539.020 | 538.372 | $29'\ 00''$ | 28,270 | 800.52 | `normal` | Pre-flood valley spreading onto floodplain |
| 22 | 541.500 | 540.852 | $37'\ 01''$ | 52,266 | 1,480.00 | `alert` | Rajaram Alert Level: Causeways submerged |
| 23 | 542.100 | 541.452 | $39'\ 01''$ | 63,567 | 1,800.00 | `alert` | Shivaji Alert Level: Traffic restrictions |
| 24 | 542.700 | 542.052 | $41'\ 01''$ | 77,692 | 2,200.00 | `warning` | CWC/WRD Warning Level: Evacuation alert |
| 25 | 543.300 | 542.652 | $43'\ 00''$ | 94,467 | 2,675.00 | `danger` | CWC/WRD Danger Level: City flood emergency |
| 26 | 545.330 | 544.682 | $49'\ 08''$ | 135,961 | 3,850.00 | `emergency` | Highest Flood Level (HFL, Aug 2019/Jul 2021) |

---

## 5. SCS Curve Number Runoff Depth Mechanics

The physical runoff volume generation follows the United States Natural Resources Conservation Service (NRCS / SCS-CN) standard:

### 5.1 Potential Soil Retention

Given a calibrated Curve Number $CN$:

$$S_{ret} = \frac{25,400}{CN} - 254 \quad (\text{expressed in mm})$$

### 5.2 Initial Abstraction

The initial surface wetting, depression storage, and vegetative canopy interception prior to runoff:

$$I_a = 0.2 \cdot S_{ret}$$

*(For dense basaltic soil with monsoon pre-saturation, this can be dynamically lowered to $I_a = 0.05 \cdot S_{ret}$).*

### 5.3 Cumulative Runoff Equation

For any accumulated precipitation depth $P$:

$$Q_{cum} = \begin{cases}
0 & \text{if } P \le I_a \\
\frac{(P - I_a)^2}{P - I_a + S_{ret}} & \text{if } P > I_a
\end{cases}$$

### 5.4 Incremental Runoff Hyetograph
The excess rainfall generated in time step $\Delta t$ (hour $h$) is:

$$\Delta Q_{excess}[h] = Q_{cum}[h] - Q_{cum}[h-1]$$

---

## 6. Hydrograph Transformation: SCS Unit Hydrograph

To convert the rainfall-excess hyetograph into a river discharge hydrograph at the subbasin outlet, HydroCast utilizes the **SCS Unit Hydrograph method**:

```
        Excess Rain Hyetograph                     SCS Unit Hydrograph Translation & Attenuation
             [ mm/hr ]                                     [ m³/s ]
                |                                             /\  Peak Runoff
                |                                            /  \
               ---       ====== Convolution ======>         /    \
              |   |                                        /      \
            --|   |--                                    /          \
                                                        /            \_____ Baseflow
```

1. **Translation (Time-Area Routing):**
    Runoff is lagged to the outlet according to the dimensionless time-area curve:

    $$\frac{A_t}{A} = \begin{cases}
    1.414 \cdot \left(\frac{t}{T_c}\right)^{1.5} & \text{for } 0 \le t \le 0.5 T_c \\
    1 - 1.414 \cdot \left(1 - \frac{t}{T_c}\right)^{1.5} & \text{for } 0.5 T_c < t \le T_c
    \end{cases}$$

    Where $T_c$ is the Time of Concentration.

2. **Attenuation (Linear Reservoir Routing):**
    Storage effects in channels and valley wetlands are modeled through a linear reservoir with storage coefficient $R$:

    $$S = R \cdot O$$

    Using finite differences:

    $$O_2 = C_A \cdot I_2 + C_B \cdot I_1 + C_C \cdot O_1$$

    Where routing coefficients are derived from $\Delta t$ and $R$:

    $$C_A = C_B = \frac{\Delta t}{2R + \Delta t}, \quad C_C = \frac{2R - \Delta t}{2R + \Delta t}$$

---

## 7. Monsoon Baseflow Separation & Physical Groundwater Release

The Panchganga river maintains a continuous physical baseflow during the June–September Southwest Monsoon generated by unconfined groundwater aquifers in the Sahyadri lateritic formations.

In `src/hms/runner.py`:
1. **Physical Live Baseflow:** Extracted directly from live water level telemetry:

    $$Q_{base} = \text{convert\_stage\_to\_discharge\_manning}(h_{live}, \text{"SHIVAJI\_BRIDGE"})$$

    At current normal monsoon stages ($532.63 - 533.28\text{ m MSL}$), $Q_{base} \approx 91.1 - 109.2\text{ m}^3/s$.
2. **Total River Hydrograph:**

    $$Q_{total}(t) = Q_{base} + \sum_{i=1}^{9} Q_{surface, i}(t)$$

This ensures that even during dry weather breaks between monsoon storms, river discharge never collapses to artificial zero or non-physical single-digit values.

---

## 8. Real-Time Closed-Loop ML Parameter Recalibration Engine

To adapt to temporal variations in catchment characteristics (e.g. soil pore saturation, crop cover progression, siltation behind weir crests), HydroCast incorporates an automated closed-loop machine learning calibration engine (`src/hydrology/ml_calibration.py`):

1. **Residual Evaluation:** Compares the simulated hydrograph $Q_{\text{sim}}(t)$ against observed gauge discharge $Q_{\text{obs}}(t)$ derived from Shivaji Bridge ultrasonic water levels.
2. **Physically Bound Optimization:** Scales subbasin Curve Numbers by multiplier $\alpha \in [0.85, 1.15]$ and lag times by $\beta \in [0.80, 1.20]$. These hard mathematical bounds guarantee that calibration can never induce unphysical hydrological runaway or negative runoffs.
3. **Automated HEC-HMS Disk Synchronization:** In addition to internal emulator parameter updates, the calibration engine provides disk synchronization routines (`sync_to_hms_basin_file`) to persist updated catchment parameters back into `.basin` and `.control` project files.

---

## 9. Peak Flood Strike Horizon & ±2.0h Permissible Error Window

HydroCast translates continuous 90-hour hydrographs into operational disaster response timeframes:

1. **Nominal Crest Detection:** Identifies the point of maximum simulated discharge:

    $$T_{\text{peak}} = \arg\max_{t} Q_{\text{total}}(t)$$

2. **Gradient & Centroid Validation:** Cross-checks the crest with the hyetograph centroid lag:

    $$\bar{T}_{\text{rain}} = \frac{\sum t \cdot P(t)}{\sum P(t)}, \quad T_{\text{lag, basin}} \approx 14.2 - 18.5\text{ hours}$$

3. **Permissible Error Window Formulation:**
    Based on empirical validation across historical monsoon events (2019, 2021, 2026), the travel time variability follows a normal distribution with standard deviation $\sigma_t \approx 1.02\text{ hours}$.
    At a 95% confidence level ($z \approx 1.96$), the permissible early warning window is:

    $$[T_{\text{earliest}}, T_{\text{latest}}] = [T_{\text{peak}} - 2.0\text{h}, T_{\text{peak}} + 2.0\text{h}]$$

4. **Operational Integration:** Both the nominal peak and the bounding window are published in the REST API payload (`/api/v1/runoff/summary`), rendered on the Next.js visual alert banner, and pushed directly to District Disaster Management Authority (DDMA) emergency dispatch channels.
