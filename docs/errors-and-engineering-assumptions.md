# System Errors, Past Mistakes & Engineering Assumptions

```
========================================================================================
       HYDROCAST SYSTEM AUTOPSY: ERRORS, MISTAKES & ENGINEERING ASSUMPTIONS
========================================================================================

                 [ Physical Reality: Panchganga Monsoon Floods ]
                                       │
        ┌──────────────────────────────┴──────────────────────────────┐
        ▼                                                             ▼
[ Past Model Mistakes & Bugs ]                     [ Engineering Assumptions & Trade-offs ]
- 30.2x Bed Slope Distortion                       - 1D Quasi-Steady Open-Channel Flow
- Compound Wetted Perimeter Collapse               - Subbasin Lumped Hydrology (S1 to S9)
- Spline Polynomial Overshoot (Runge)              - Rigid Non-Erodible Bed Topography
- Gauge Datum Zero Elevation Shift                 - Linear Baseflow Superposition
- Artificial 0.12m Stage Subtraction Hack          - Downstream Confluence Free Discharge
- Arithmetic Mountain Rain Dilution                - Uncontrolled Siphon Spillway Release
```

---

## Part I: Post-Mortem of Past Mistakes & Model Errors

Before achieving current operational fidelity, the HydroCast codebase inherited and uncovered several severe engineering and hydraulic errors. Documenting these failure modes is critical for institutional memory, academic honesty, and preventing regression.

---

### 1. The 30.2× Bed Slope Distortion (The Unsegmented Flood Regression Bug)

#### What Went Wrong:
In the initial uncalibrated system, the stage-discharge converter produced reasonable stage heights ($532.6 - 533.5\text{ m MSL}$), but calculated river discharge collapsed to an absurdly low **$16.6\text{ m}^3/s$** ($586\text{ cusecs}$) at Shivaji Bridge and **$10.4\text{ m}^3/s$** at Rajaram Weir. This resulted in an unacceptable volumetric under-prediction (**PBIAS of $30\% - 40\%$**).

#### Root Cause:
The model previously derived the river channel bed slope $S_0$ using an unsegmented single linear regression against 31 historical extreme flood observations recorded during the catastrophic floods of 2019 and 2021 ($542.0\text{m}$ to $545.62\text{m}$ MSL).

At these extreme flood stages, the Panchganga river is subjected to massive backwater effects, floodplain hydraulic drag, and weir submergence. The regression forced an artificial, catchment-wide energy slope of:
$$S_{0, err} = 0.0001938\text{ m/m} \quad (\text{Shivaji Bridge})$$
$$S_{0, err} = 0.0000767\text{ m/m} \quad (\text{Rajaram Weir})$$

The true, field-surveyed longitudinal bed slopes of the river channel are:
$$S_{0, actual} = 0.005858\text{ m/m} \quad (\text{Shivaji Bridge, } 30.2\times\text{ steeper!})$$
$$S_{0, actual} = 0.002318\text{ m/m} \quad (\text{Rajaram Weir, } 30.2\times\text{ steeper!})$$

According to Manning's equation for open-channel velocity:
$$v = \frac{1}{n} \cdot R^{2/3} \cdot S_0^{1/2}$$

Because velocity scales with $\sqrt{S_0}$, using the artificial flood regression slope suppressed in-bank velocity by a factor of:
$$\text{Suppression Factor} = \sqrt{\frac{0.005858}{0.0001938}} = \sqrt{30.23} \approx \mathbf{5.50\times}$$

A true physical flow velocity of $1.65\text{ m/s}$ was crushed to $0.30\text{ m/s}$, reducing discharge from $\sim 109\text{ m}^3/s$ down to $16.6\text{ m}^3/s$.

#### Resolution:
Re-engineered the rating engine into a **WRD-anchored PCHIP formulation** (`src/hydrology/stage_converter.py`, Sep 2026):
- **Both gauged sites** now PCHIP-interpolate directly through the **official Maharashtra WRD stage-discharge sheet** — no Manning slope fitting is used for the discharge conversion.
- **Rajaram K.T. Weir:** WRD sheet stages verbatim + WRD 2021–23 observed low-flow anchors + bed Q=0 anchor.
- **Shivaji Bridge:** the same sheet shifted **−0.648 m downstream** (surveyed bed datum separation: 528.670 m vs 529.318 m over 3,858 m) + bed Q=0 anchor.
- Guarantees $Q(h)$ and $h(Q)$ both strictly monotonic and equal to the government sheet at every official stage.

---

### 2. Compound Cross-Section Wetted Perimeter Discontinuity

#### What Went Wrong:
At stage elevations between $535.0\text{m}$ and $536.0\text{m}$ MSL, the computed rating curve exhibited an inverted gradient: **as river stage increased, calculated discharge actually decreased ($\frac{dQ}{dh} < 0$)**.

```
 Non-Physical Discharge Dip at Bankfull Spill:
 Discharge Q
    ^
    |             Normal Channel Rise
    |                 . - - .
    |               /         \   <-- CATASTROPHIC DISCHARGE COLLAPSE!
    |              /           ` .     Wetted perimeter P explodes from 68m to 310m
    |             /               \    Hydraulic radius R = A/P crashes from 2.6m to 1.05m
    |            /                 ` - - - - - * True Physical Target
    |   * - - - '
    +--------------------------------------------------------------------> Stage h
       532m            534m            535.5m         538m
```

#### Root Cause:
The cross-section geometry was evaluated using a single continuous boundary polygon. When the water level exceeded bankfull stage ($h \approx 535.2\text{m}$), water began spilling over the main channel banks onto wide horizontal agricultural floodplains.

While flow area ($A$) increased by only $\sim 12\%$, the wetted perimeter ($P$) exploded instantly from **$68\text{ meters}$** to **$310\text{ meters}$**.

Because hydraulic radius is defined as $R = \frac{A}{P}$:
$$R_{\text{in-bank}} = \frac{176.8\text{ m}^2}{68.0\text{ m}} = 2.60\text{ m}$$
$$R_{\text{overbank}} = \frac{325.5\text{ m}^2}{310.0\text{ m}} = 1.05\text{ m}$$

Since Manning's discharge is proportional to $R^{2/3}$:
$$R^{2/3} \text{ dropped from } (2.60)^{0.667} = 1.89 \implies (1.05)^{0.667} = 1.03 \quad (\mathbf{-45.5\%}\text{ drop!})$$

The mathematical formulation punished the discharge calculation for wetting the floodplain, violating physical conservation of energy and mass.

#### Resolution:
Decomposed the rating curve into composite sub-sections (main channel vs left/right floodplains) and replaced raw single-polygon geometric integration with **Piecewise Cubic Hermite Interpolating Polynomials (PCHIP)** calibrated directly to field observations, enforcing strict monotonicity $\frac{dQ}{dh} > 0$ across all stages.

---

### 3. Spline Runge-Phenomenon Oscillation

#### What Went Wrong:
Using standard natural cubic splines (`scipy.interpolate.CubicSpline`) to interpolate between surveyed cross-section points caused mathematical polynomial overshoot. Between the normal monsoon stage ($533.5\text{m}$) and the Alert level ($542.1\text{m}$), the spline created an artificial hump and trough, causing the model to over-predict water levels at intermediate flows.

#### Resolution:
Replaced natural cubic splines with **Shape-Preserving PCHIP (`scipy.interpolate.PchipInterpolator`)**. Unlike standard cubic splines which enforce continuous second derivatives ($C^2$) at the expense of shape preservation, PCHIP guarantees that the interpolant is strictly monotonic if the data points are monotonic, completely eliminating artificial polynomial oscillations.

---

### 4. Gauge Zero Datum Elevation Misalignment

#### What Went Wrong:
Early scripts defined the riverbed elevation at Shivaji Bridge as $530.584\text{ m MSL}$, while others used $530.00\text{ m MSL}$. This $58.4\text{ cm}$ discrepancy propagated through all depth calculations, throwing off water depth and wetted perimeter integrations.

#### Resolution:
Audited against the Maharashtra Water Resources Department (WRD) historical benchmark records:
$$\text{Official Zero Gauge Datum } (0'\ 0'') \equiv \mathbf{530.18\text{ m MSL}}$$
$$\text{Sensor Mounting Elevation} \equiv \mathbf{549.35\text{ m MSL}}$$
Water depth above datum is now rigorously calculated as $y = h - 530.18\text{ meters}$.

---

### 5. The "Stage - 0.12m" Artificial Subtraction Hack

#### What Went Wrong:
In previous revisions of `stage_converter.py`, Rajaram K.T. Weir stage was computed by taking the Shivaji Bridge stage and applying a hardcoded subtraction:
$$\text{Stage}_{\text{rajaram}} = \text{Stage}_{\text{shivaji}} - 0.12\text{ m}$$

This was an empirical hack that completely ignored physical channel hydraulics. Rajaram Weir is $3.8\text{ km}$ upstream of Shivaji Bridge, with surveyed bed RL $529.318\text{ m}$ vs Shivaji $528.670\text{ m}$ (datum separation $+0.648\text{ m}$).

#### Resolution:
Built distinct, independently WRD-anchored PCHIP hydraulic curves for both Chhatrapati Shivaji Maharaj Bridge and Rajaram K.T. Weir. The Shivaji curve is the official WRD sheet shifted **−0.648 m** (its lower bed datum); the Rajaram curve is the sheet verbatim. At equal discharge the stage separation is exactly the surveyed datum **0.648 m** (verified in `tests/test_hydrology.py`), replacing the arbitrary 0.12 m hack.

---

### 6. Arithmetic Rainfall Dilution in Mountain Catchments

#### What Went Wrong:
In subbasins with multiple rain gauges (e.g., Subbasin $S_6$ containing Karanjphen at $640\text{m}$ and Gaganbawda at $680\text{m}$), the system initially computed the simple arithmetic mean of rainfall:
$$\bar{P} = \frac{P_{\text{karanjphen}} + P_{\text{gaganbawda}}}{2}$$

During monsoonal cloudbursts along the Western Ghats crest, Gaganbawda often recorded $160\text{ mm/day}$ while Karanjphen in the valley recorded $50\text{ mm/day}$. Taking the arithmetic average ($105\text{ mm}$) diluted the severe headwater runoff peak, delaying the simulated flood wave arrival by up to 6 hours.

#### Resolution:
Implemented the **Dynamic Conservative Selection Engine** (`station_selector.py`), which identifies the maximum-precipitation station within multi-gauge subbasins and uses it as the governing hyetograph for hydrologic modeling.

---

## Part II: Engineering Assumptions & Physical Approximations

Every numerical model is a simplified representation of nature. The following are the core engineering assumptions underpinning HydroCast:

```
+-----------------------------------+-----------------------------------------------------------+
| Engineering Assumption            | Justification & Known Operational Limits                  |
+-----------------------------------+-----------------------------------------------------------+
| 1D Quasi-Steady Uniform Flow      | Backwater effects during rising limbs are captured via    |
| (Manning-Strickler formulation)   | PCHIP rating anchors rather than 2D dynamic Saint-Venant. |
+-----------------------------------+-----------------------------------------------------------+
| Spatially Lumped Subbasins        | Subbasins S1-S9 are discretized at ~80-510 km² scale;    |
| (SCS-CN & SCS Unit Hydrograph)  | micro-topography within subbasins is spatially aggregated.|
+-----------------------------------+-----------------------------------------------------------+
| Linear Baseflow Superposition     | Monsoon baseflow is assumed superimposable upon surface   |
| (Q_total = Q_base + Q_surface)    | runoff without dynamic pressure coupling to groundwater.  |
+-----------------------------------+-----------------------------------------------------------+
| Rigid Non-Erodible Channel Bed    | Cross-section geometry is assumed constant; monsoon bed   |
| (Zero aggradation / degradation)  | scour or post-flood silt deposition is not dynamically    |
|                                   | morphed during a simulation cycle.                        |
+-----------------------------------+-----------------------------------------------------------+
| Uncontrolled Spillway Operation   | Upstream Radhanagari Dam siphon spillways are assumed to   |
| (Radhanagari Dam Siphons)         | discharge naturally once FRL (615.0m) is breached.        |
+-----------------------------------+-----------------------------------------------------------+
| Downstream Free Drainage          | Assumes no severe backwater choke from Krishna River at   |
| (No Krishna River Backwater Choke)| Shirol/Narsobawadi unless manually parameterized.         |
+-----------------------------------+-----------------------------------------------------------+
```

---

### 1. The 1D Quasi-Steady Flow Assumption
HydroCast computes stage from discharge using steady-state hydraulic rating curves on a 1-hour discrete time step. 

**Limitation:** It does not solve the full 2D unsteady shallow water equations (Saint-Venant momentum equations):
$$\frac{\partial Q}{\partial t} + \frac{\partial}{\partial x}\left(\frac{\beta Q^2}{A}\right) + gA \left(\frac{\partial h}{\partial x} + S_f - S_0\right) = 0$$

During extremely rapid flash flood events ($\frac{\partial Q}{\partial t} > 500\text{ m}^3/s\text{ per hour}$), the water surface slope during the rising limb is steeper than the steady-state slope, causing a looped rating curve (hysteresis). HydroCast's rating curve represents the steady-state mean, which may slightly underestimate stage on the extreme rising limb and slightly overestimate stage on the falling limb ($\pm 15 - 25\text{ cm}$ hysteresis envelope).

---

### 2. Lumped Hydrologic Parameters (S1 to S9)
The $2,140\text{ km}^2$ catchment is discretized into 9 subbasins ranging from $80.1\text{ km}^2$ ($S_9$) to $510.5\text{ km}^2$ ($S_7$). Within each subbasin, soil infiltration capacity ($CN$), Time of Concentration ($T_c$), and Storage Coefficient ($R$) are spatially lumped.

**Justification:** While fully distributed grid-cell models (e.g., $100\text{m} \times 100\text{m}$ raster cells) provide higher spatial resolution, they require extensive distributed soil data that does not exist for the upper Western Ghats and increase compute time from **$< 20\text{ milliseconds}$** to over **$45\text{ minutes}$**, making real-time automated 6-hourly operational execution impractical.

---

### 3. Rigid Bed Invert Assumption
River cross-sections at Shivaji Bridge and Rajaram Weir are treated as rigid and non-erodible.

**Known Reality:** The Panchganga riverbed consists of basaltic rock overlaid with silt, sand, and gravel deposits. During extreme floods ($Q > 2,000\text{ m}^3/s$), high shear stresses scour loose bed material, temporarily deepening the channel by $0.3 - 0.6\text{ meters}$. During the falling limb, sediment settles back. HydroCast's rigid bed assumption represents the post-monsoon surveyed datum.

---

### 4. Upstream Dam Discharges (Radhanagari Dam)
Subbasin $S_7$ is controlled by Radhanagari Dam (gross storage capacity $236.8\text{ MCM} / 8.36\text{ TMC}$). The dam features unique automated siphon spillways (8 siphons) that open progressively when the reservoir reaches Full Reservoir Level (FRL $615.0\text{ m MSL}$).

**Assumption:** HydroCast assumes that during pre-monsoon and early monsoon periods, the dam absorbs runoff. Once soil saturation reaches AMC-III and antecedent storage is full, inflow equals outflow through the siphons. If dam authorities execute emergency manual sluice gate operations outside automated siphon mechanics, that volume must be integrated via the baseflow offset parameter.

---

### 5. Downstream Confluence Hydraulic Boundary (Krishna River Backwater)
The Panchganga river discharges into the Krishna river at Shirol / Narsobawadi, approximately $42\text{ km}$ downstream of Kolhapur.

**Assumption:** HydroCast assumes free hydraulic outfall at the basin outlet.
**Exception Condition:** In 2005 and 2019, the Krishna River was concurrently in extreme flood due to heavy discharge from Almatti Dam backwater in Karnataka. This created a massive downstream hydraulic dam that slowed Panchganga drainage and artificially elevated Kolhapur water levels for several days. Capturing this requires coupling a regional Krishna basin hydrodynamic model, which is outside the single-catchment boundary of HydroCast.

---


## Part III: Recent Hydraulic Inconsistencies & Edge-Case Bug Resolutions (v3.1)

```
====================================================================================================
           PART III: RECENT HYDRAULIC INCONSISTENCIES & EDGE-CASE BUG RESOLUTIONS
====================================================================================================

  1. Compound Roughness Bug            2. Sensor-Sink Transposition          3. False T+89h Flat Peak
  =========================            ===========================          =========================
  Floodplain Sugarcane: n=0.070        Shivaji Bridge (Chainage 6+257)      Non-storm flat baseflow:
  Main Channel:        n=0.031        Rajaram KT Weir (Chainage 10+115)     np.argmax() returned T+89
  DCM partitions cross-section.        Delta bed invert: +0.648 m higher.   Fixed: Wave Significance Rule.
```

### 7. Uniform Manning Roughness on Overbank Sugarcane Floodplains
#### What Went Wrong:
The model previously applied a uniform Manning roughness coefficient ($n = 0.035$) across the entire cross-section at both Shivaji Bridge and Rajaram Weir. During high-flow stages when floodwaters spilled over the natural riverbanks (Shivaji bankfull: $541.60\text{ m}$ MSL, Rajaram bankfull: $541.05\text{ m}$ MSL), this uniform roughness severely overpredicted floodplain discharge capacity. Consequently, the modeled stage for high discharges was underestimated by up to $1.2\text{ m}$, failing to match WRD flood registers.

#### Root Cause:
The Panchganga river corridor in Kolhapur district is surrounded by intense perennial sugarcane and paddy cultivation. Standing sugarcane crops ($2.5\text{ m}$ to $3.5\text{ m}$ height) present immense hydraulic flow resistance, drastically impeding overbank flood velocity. A single composite Manning $n$ cannot account for the hydraulic discontinuity between a deep silt/gravel main channel and heavily vegetated overbank floodplains.

#### Resolution:
Implemented the **Divided Channel Method (DCM)** in `src/hydrology/stage_converter.py`. The cross-section is hydraulically partitioned into main channel and overbank floodplains, adopting authoritative roughness values from the **Krishna Basin Flood 2019 Volume 1 Study Report**:
- **Main River Channel:** $n_{\text{main}} = 0.031$ (clean natural channel, silt/sand/gravel bed, irregular natural banks).
- **Overbank Sugarcane Floodplains:** $n_{\text{flood}} = 0.070$ (dense standing sugarcane crops and paddy bunds).

```
   Elevation
    (m MSL)
     546.0 +                                                    2019 HFL (545.33 m)
           |                                                   ~~~~~~~~~~~~~~~~~~~~
     544.0 |   Left Floodplain              Main River Channel          Right Floodplain
           |   (Sugarcane / Paddy)          (Gravel / Silt Bed)         (Sugarcane / Crops)
     542.0 |   n_flood = 0.070              n_main = 0.031              n_flood = 0.070
           |  +--------------------+                                   +--------------------+
     540.0 |  |                    |       +-------------------+       |                    |
           |  |                    |      /                     \      |                    |
     536.0 |  |                    |     /                       \     |                    |
           |  |                    |    /                         \    |                    |
     532.0 |  |                    |   /                           \   |                    |
           |  |                    |  /                             \  |                    |
     528.0 |  +--------------------+ /                               \ +--------------------+
           |                        /                                      528.67+-----------------------+-------- Thalweg: 528.67m MSL -----+--------------------
           +-----------------------+-----------------------------------+--------------------+
              Left Overbank                      Main Channel               Right Overbank
```

$$Q(H) = \frac{1}{n_{\text{main}}} A_{\text{main}} R_{\text{main}}^{2/3} S_0^{1/2} + \sum_{\text{flood}} \frac{1}{n_{\text{flood}}} A_{\text{flood}} R_{\text{flood}}^{2/3} S_0^{1/2}$$

---

### 8. Sensor-to-Sink Spatial Transposition Discrepancy
#### What Went Wrong:
The IoT ultrasonic radar sensor is physically mounted on the girder of **Chhatrapati Shivaji Maharaj Bridge** (Chainage 6+257 from Krishna confluence). However, the HEC-HMS hydrological basin model has its catchment sink at **Rajaram K.T. Weir** (Chainage 10+115). Previously, the baseflow and stage conversion pipelines directly applied the Shivaji Bridge sensor reading to the Rajaram rating curve, ignoring the $3,858\text{ m}$ longitudinal distance separating the two facilities.

#### Root Cause:
Rajaram Weir is located **upstream** of Shivaji Bridge (higher chainage along the river course). The surveyed thalweg bed invert at Rajaram Weir is **$529.318\text{ m}$ MSL**, whereas at Shivaji Bridge it is **$528.670\text{ m}$ MSL**—a bed elevation differential of **$+0.648\text{ m}$**. Furthermore, during low-flow periods (summer and non-monsoon), the Rajaram K.T. Weir retains water up to its solid masonry crest level (**$530.18\text{ m}$ MSL**) for municipal and agricultural irrigation pumping, establishing an artificial upstream impoundment pool.

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

#### Resolution:
Engineered `infer_rajaram_stage_from_shivaji(shivaji_stage_m, q_m3s)` in `src/hydrology/stage_converter.py`. The function dynamically evaluates the hydraulic flow regime:
1. **Low-Flow / Pool Regime ($H_{\text{shivaji}} < 530.0\text{ m}$):** Rajaram water surface elevation is governed by the weir crest impoundment:
   $$H_{\text{rajaram}} = \max\left(530.18, \; H_{\text{shivaji}} + 0.648\right)$$
2. **Open Flood Regime ($H_{\text{shivaji}} \ge 530.0\text{ m}$):** Water surface profile follows the surveyed longitudinal bed gradient:
   $$H_{\text{rajaram}} = H_{\text{shivaji}} + 0.648\text{ m}$$

---

### 9. False T+89h Flat Baseflow Peak Detection Bug
#### What Went Wrong:
During non-storm periods when rainfall was negligible and river discharge was dominated by a flat or slowly receding baseflow, the automated pipeline reported a peak arrival time at the very end of the 90-hour forecast window ($T+89\text{h}$), triggering false alarm indicators on user dashboards.

#### Root Cause:
`execute_hec_hms()` originally evaluated `peak_idx = int(np.argmax(q_surface))`. When surface runoff was zero across all 90 hours, `np.argmax()` returned index 89 due to minor floating-point rounding artifacts or tie-breaking at the end of the array. Even when evaluated on total discharge ($Q_{\text{total}}$), minor baseflow recession curves produced a maximum at index 0 or index 89 arbitrarily.

#### Resolution (v1 — first fix, later superseded):
Added a **Physical Flood Wave Significance Rule** that forced the peak to $T+0$ when surface runoff did not exceed $2\times$ the antecedent baseflow:

```python
# Superseded heuristic (removed in v2 — see below)
is_significant_event = peak_surface_q > max(0.5, initial_baseflow * 2.0)
if not is_significant_event:
    peak_idx = 0  # Declare T+0 (flow is receding / baseflow stable)
```

#### Resolution (v2 — accurate hydrology, current):
The $2\times$ heuristic was itself physically wrong: a genuine storm lifting total discharge by e.g. $+168\%$ over a high monsoon baseflow was mislabelled "receding" and its true crest erased to $T+0$, corrupting peak-discharge and lead-time forecasts. The corrected physics:

```python
# src/hms/runner.py — physically accurate peak detection
peak_idx = int(np.argmax(q_total))          # true crest of total discharge, NEVER overridden
initial_baseflow = float(baseflow_array[0])
storm_rise = q_total[peak_idx] - baseflow_array[peak_idx]   # storm imprint above receding baseflow
is_significant_event = storm_rise > max(1.0, 0.10 * initial_baseflow)
```

- `np.argmax(q_total)` — where $Q_{\text{total}} = Q_{\text{surface}} + Q_{\text{baseflow}}$ — is the hydrologically correct peak location. On a pure recessing basin the exponential baseflow decay naturally yields $T+0$ **without any override**; on a flood it yields the true crest.
- `is_significant_event` only **labels** whether the storm visibly lifts the hydrograph above its concurrent recessing baseflow (≥10%); it never relocates the peak.
- Verified by `tests/test_runner_emulator.py::test_shape_peak_not_overridden_by_high_baseflow` and `test_baseflow_only_basin_naturally_peaks_at_t0`.

---

### 10. Regional Bed Slope Gradient Mismatch
#### What Went Wrong:
Previous models assumed a uniform longitudinal bed slope ($S_0 = 0.005858$) throughout the entire Panchganga river basin. This steep gradient caused open-channel flow velocities to be vastly overpredicted in the middle and lower reaches, distorting stage conversions.

#### Corrected Approach (Sep 2026):
The discharge conversion no longer depends on any regional bed slope. Both gauged rating curves are PCHIP-anchored on the **official WRD stage-discharge sheet** (Rajaram verbatim; Shivaji shifted −0.648 m for its lower bed datum). The true surveyed bed is only used for the Q=0 anchors (528.670 m Shivaji, 529.318 m Rajaram) and for wetted-area geometry from the embedded XS surveys.

#### Root Cause:
Detailed river survey data from the **Krishna Basin Flood 2019 Volume 1 Report** reveals that the bed slope flattens dramatically as the river progresses from the Western Ghats to the Krishna confluence:
- **Radhanagari to Prayag Chikhali:** $1:2529$ ($S_0 = 0.000395\text{ m/m}$)
- **Prayag Chikhali to Rajaram K.T. Weir:** $1:4641$ ($S_0 = 0.000215\text{ m/m}$)
- **Rajaram K.T. Weir to Shirol K.T. Weir:** $1:7700$ ($S_0 = 0.000130\text{ m/m}$)

```
 Elevation
  (m MSL)
   560 +   [Radhanagari Dam: 553.90m MSL]
       |    \
   550 |     \  Bhogavati River Bed Slope = 1:2529 (0.000395 m/m)
       |      \  Length: ~40 km (Radhanagari to Prayag Chikhali)
   540 |       \
       |        +-- [Prayag Chikhali Confluence (Sacred Sangam): ~536.0m MSL]
   535 |            \
       |             \  Upper Panchganga Bed Slope = 1:4641 (0.000215 m/m)
   530 |              \  Length: ~18 km (Prayag Chikhali to Rajaram KT Weir)
       |               +-- [Rajaram KT Weir: Crest 530.18m | Bed 529.318m MSL]
   525 |                   \
       |                    \  Lower Panchganga Bed Slope = 1:7700 (0.000130 m/m)
   520 |                     \  Length: ~42 km (Rajaram KT Weir to Shirol KT Weir)
       +----------------------+---------------------------------------------------> Distance (km)
       0                     40                      58                          100 km
```

#### Resolution:
Updated canonical slopes in `src/hydrology/stage_converter.py`:
- **Shivaji Bridge Site:** Calibrated to $S_0 = 0.000201$ to incorporate the local hydraulic headloss and backwater from the Jayanti Nalla stormwater confluence.
- **Rajaram K.T. Weir Site:** Calibrated to $S_0 = 0.000250$.

## Part IV: Operational Hardening & Edge-Case Failure Mitigations (v3.0)

During the v3.0 operational production hardening, several systemic risks were diagnosed and engineered against:

```
+-----------------------------------+---------------------------------------+-------------------------------------------+
| Vulnerability / Edge Case         | Previous Failure Mode                 | Engineered Mitigation (v3.0)              |
+-----------------------------------+---------------------------------------+-------------------------------------------+
| Weather API Socket Timeouts / 429 | Pipeline aborted on transient errors  | Exponential backoff with random jitter &  |
|                                   | during Open-Meteo queries             | nearest-neighbor fallback (retry_utils.py)|
+-----------------------------------+---------------------------------------+-------------------------------------------+
| Unconstrained ML Parameter Drift  | Calibration against noisy sensor data | Hard bounded parameter scaling            |
|                                   | could explode CN or collapse Tlag     | (α ∈ [0.50, 1.80], β ∈ [0.50, 1.80],    |
|                                   |                                       | ΔCN ∈ [−8, +8], X ∈ [0.15, 0.40])        |
+-----------------------------------+---------------------------------------+-------------------------------------------+
| PostgreSQL Time-Series Bloat      | Accumulation of millions of 15-min    | Scheduled weekly pruning to compressed    |
|                                   | hydrograph rows degrading DB queries  | Apache Parquet cold storage (archive_runs)|
+-----------------------------------+---------------------------------------+-------------------------------------------+
| API Scraping & DoS Exhaustion     | Heavy public scraping threatening     | SlowAPI token-bucket rate limits & JWT    |
|                                   | forecast cycle execution              | authentication on administrative triggers |
+-----------------------------------+---------------------------------------+-------------------------------------------+
| Peak Arrival Scalar Fallacy       | Publishing single-minute peak time    | Statistically bounded ±2.0h operational   |
|                                   | creating false precision in EOCs      | window @ 95% confidence interval          |
+-----------------------------------+---------------------------------------+-------------------------------------------+
```

### 1. The Fallacy of Scalar Peak Flood Prediction
In early releases, the system reported peak flood arrival as a single scalar timestamp (e.g. `2026-09-11T16:30:00Z`). In real-world Western Ghats hydrology, variations in spatial rainfall distribution, soil heterogeneity, and tributary confluence backwaters introduce non-deterministic travel lags. Reporting a single minute led emergency personnel to expect mathematical precision that nature does not exhibit. In v3.0, the system reports peak arrival as a **±2.0 h operational window** $[T_{\text{peak}} - 2\text{h}, T_{\text{peak}} + 2\text{h}]$, read from `PEAK_ARRIVAL_CI_HOURS` with a default of 2.0.

!!! note "The window is an assumption, not a computed confidence interval"
    The margin is a constant applied symmetrically around the argmax of the
    discharge series. No forecast-error distribution is estimated, so the
    "95% confidence" label used in earlier revisions of this page is not
    supported by the implementation. It is a defensible default and should be
    described as such. The corresponding stage margin *is* stage-dependent:
    `0.12 + 0.03·(h_peak − 535)` metres, with discharge bounded to ±6 %.

### 2. Guardrails Against ML Parameter Runaway
When calibrating against live ultrasonic radar telemetry, acoustic echoes from debris or transient sensor dropout can produce artificial stage spikes. If an unconstrained optimizer attempts to fit these anomalies, it might calculate an unphysical Curve Number ($CN > 98$) or an impossible lag time ($T_{\text{lag}} \to 0$), corrupting subsequent cycles. HydroCast enforces:
- Hard physical clipping bounds: $\alpha \in [0.50, 1.80]$, $\beta \in [0.50, 1.80]$, $\Delta CN \in [-8, +8]$, and $X \in [0.15, 0.40]$.
- Regularized cost functions that penalize deviations from baseline parameters.
- Discrepancy gating: recalibration runs only when $|\Delta t| \geq 1.0$ h or the rising-limb stage error exceeds $0.25$ m, and only when at least two validated observations above 520.0 m exist.

!!! note "The gate is stricter than a volume test, and is currently unreachable"
    An earlier revision of this page described the trigger as "volumetric
    divergence exceeds 10 % or NSE drops below 0.85". The implemented gate is a
    *timing and stage* test, not a volume test. It also requires observations
    with `status = 'validated'`, while the pipeline writes `fresh` and nothing
    promotes between the two — so in a live deployment the optimiser does not
    run at all. See Part VI, item 2.

---

## Part V: Operational Summary

By identifying past mistakes, replacing unsegmented regressions and pure-Manning stage conversion with WRD-anchored PCHIP rating curves, and establishing clear physical boundaries for engineering assumptions, HydroCast operates with high technical transparency. It delivers robust early warning projections while clearly defining the limits of its predictive certainty.

---

## Part VI: Open Defects Found in Source Review

Parts I–IV record modelling mistakes that have been diagnosed and, in most
cases, fixed. The items below are different: they were found by reading the
repository rather than by observing a failure, and they are still open. Each is
stated as *what the code does* versus *what the documentation or an adjacent
component expects*, because in every case the documentation was the thing that
was wrong.

These are the register referenced by the [Architecture Atlas](architecture-atlas.md).

### 1. `pipeline_ok` can never be true

`src/orchestrator.py` writes twelve entries to `pipeline_step_log` per cycle,
but the success predicate checks for **ten**. A cycle that completes every
step without error is therefore reported as failed, which propagates to
`/api/v1/health` as `last_run_ok: false` and to the Telegram status message.

*Fix:* assert against the length of the step list rather than a literal, so the
next added feature cannot reintroduce the mismatch.

### 2. The recalibration gate is unreachable

`src/hydrology/ml_calibration.py` requires at least two observations with
`status = 'validated'` and stage above 520.0 m. The pipeline writes telemetry
with `status = 'fresh'`, and no code path promotes it. The count is always
zero, so the bounded optimiser never executes outside of tests.

### 3. Discrepancy is measured circularly

To decide whether the model needs recalibrating, observed *stage* is converted
to discharge through the forecast rating curve and compared against forecast
discharge. This asks the rating curve whether the rating curve is correct, so
a systematic rating bias will never be detected — the loop would converge to
"no discrepancy" precisely when it matters most.

*Fix:* compare in the stage domain against forecast stage, or use an
independent discharge measurement.

### 4. Result provenance is reported incorrectly

`src/hms/runner.py` never parses `data/hms/compute/Run_1.dss`. When HEC-HMS
reports `COMPLETED_BINARY`, the runner still returns the Python emulator output
with `result_source = EMULATOR_PYTHON`. Two consequences: the native solver is
never validated against anything, and persisted runs misstate how they were
produced.

### 5. HMS steps 07 and 08 execute twice

The orchestrator body invokes the sink-extraction and stage-conversion steps a
second time outside the step-list loop, which both wastes work and inflates the
step log that item 1 depends on.

### 6. Imperviousness deduction contradicts the basin model

`src/hms/runner.py` adds `0.02 · P_cum` to every increment regardless of
imperviousness. For S2 and S5 the basin file declares an imperviousness of
**zero**, so adding to it is both physically wrong and inconsistent with the
declared catchment. The classical form is a deduction from potential retention,
which vanishes at zero imperviousness by construction.

### 7. Initial Muskingum X overwrites the basin value

`src/hms/basin_model.py` defaults reach X to `0.25`, while `Basin_1.basin`
declares `0.20` for all five reaches. Depending on which path populates the
model, the routing parameter differs from the configured value.

### 8. `check_basin_parameters` is a stub

The parameter-validation entry point returns without asserting anything, so a
malformed basin file passes silently.

### 9. Simulation length contradicts the product horizon

The emulator produces 352 hourly points while the forecast is a 90-hour
product. Volume and baseflow computations over the full series do not
correspond to the published window, and the baseflow floor is applied across
all 352 steps rather than the 90 published ones.

### 10. Static gauge assignments are dead configuration

`Met_1.met` declares a fixed primary gauge per subbasin. The runtime does not
read it — selection is driven entirely by `STATION_REGISTRY` in
`src/ecmwf/station_selector.py`. Anyone reading the HMS model configuration to
understand station routing is reading something inert.

### 11. Station identifiers are spelled three ways

The outlet subbasin is `KARVEER` in the registry, `KARVIR` in the orchestrator's
fallback path, and `Karvir` in `Met_1.met` and the `.gage` file. The fallback
therefore misses and `station_time_series.get("KARVIR", np.zeros(90))`
substitutes **90 zero-valued hours** for S1 — 45 mm of rainfall invented at the
outlet, with no error raised.

### 12. `EXTREME` is not mapped to an alert tier

`classify_alert` has no branch for `EXTREME`, so the most severe modelled state
falls through and is reported as `watch`. The condition is reachable, since the
HFL threshold is 545.33 m and the rating curve extends to 548.00 m.

### 13. Two tables are written but never created

`src/db/store_results.py` inserts into `peak_discharge_events` and
`runoff_summary`. Neither appears in `database/supabase_schema.sql`, which
defines ten tables and three views, nor in the `sync_all_to_supabase` bootstrap.
Those two inserts fail against a database initialised from the shipped schema.

### 14. Archival is not scheduled

`src/db/archive_runs.py` is complete and runnable, but no GitHub Actions
workflow invokes it. Documentation describing "scheduled weekly pruning" is
not true of the repository; the script is run manually.

### 15. The scheduled command is not the orchestrator

`.github/workflows/pipeline.yml` invokes `python -m src.ecmwf.open_meteo` and
the downstream modules directly. The twelve-step orchestrator described
throughout the documentation is not what runs on the 6-hourly schedule, which
also means items 1, 5 and 9 above do not currently affect the scheduled
production path — only manual and API-triggered runs.

### 16. Duplicate station coordinates in S9

`RADHANAGARI` and `KASABA_WALAWE` are registered at identical coordinates
(73.9971822° E, 16.41021° N). S9's six-candidate maximum comparison therefore
contains one duplicated observation.

### 17. A documented fallback is unreachable

`src/hydrology/rating_curves.py` implements the Divided Channel Method for
deriving a rating from surveyed cross-sections. `compute_stage_from_discharge`
takes the PCHIP path for both sites unconditionally, so the DCM branch is never
reached. Documentation describing a dual-regime PCHIP-with-Manning-fallback
configuration does not match the call graph.

### 18. Peak detection across the full series

The published 90-hour window is a slice of a 352-point series. Where the peak
is located relative to the slice boundary affects which discharge is reported as
the forecast peak, and the baseflow recession is applied to all 352 steps before
slicing.

### 19. A hard baseflow floor overrode a live sensor measurement

*(Found 2026-09-30 and fixed.)* `src/hms/runner.py` applied
`baseflow = max(sensor_baseflow, WRD_MONSOON_BASEFLOW_FLOOR_M3S)` unconditionally,
so a 40 m³/s floor overrode the ultrasonic reading whenever the river was below
that. The floor's own comment justified it as *"WRD 2021-23 observed July-Oct min
~71 m³/s"* and *"unphysical for 2140 km²"*, reasoning that predates the telemetry
link.

Field verification confirmed the sensor: the Panchganga genuinely runs at
2.8 m³/s at 530.44 m MSL in the dry season, which is 0.26 m above gauge zero.
The floor produced a **+1.98 m stage bias across the entire 90-hour window**,
because the rating curve is roughly 150× steeper at low flow than at flood peak
(0.63 m per m³/s below 2.8 m³/s against 0.004 m per m³/s above 1 480 m³/s).

*Fix:* the floor now applies only when no telemetry is available. A live reading
is treated as ground truth.

### 20. Stage was transferred across a reach in order to derive discharge

*(Found 2026-09-30 and fixed.)* Baseflow was derived by shifting the observed
Shivaji stage by the surveyed 0.648 m bed drop and inverting the result at
Rajaram — that is, transferring a *stage* in order to obtain a *discharge*.

Two things were wrong with this. First, the KT weir ponding term was included,
and impoundment raises the water surface without adding conveyance, so
inverting an artificially raised surface double-counted the ponding. Second, and
more seriously, the two rating curves are a constant 0.648 m datum shift **only
from about 20 m³/s upward**. Below that, each curve is pinned to its own surveyed
bed level and the offset widens to 1.02 m at Q = 2.8 m³/s, contradicting the
documented claim that the offset holds at every anchor.

*Fix:* discharge is conserved along a reach whereas stage is not, so the
observed stage is now converted to discharge once, at the site where it was
measured, and no cross-site transfer is performed. `infer_rajaram_stage_from_shivaji`
gained an explicit `apply_backwater` flag, defaulting to the previous behaviour
so callers that genuinely want a stage are unaffected.

Combined effect on the reported case: mean absolute stage error **1.019 m →
0.003 m** across a low-flow sample, with flood-period output unchanged to within
0.5 m³/s. Covered by `tests/test_low_flow_stage_bias.py`.

### 21. The weir crest constant was the gauge zero datum

*(Found 2026-09-30 and fixed.)* `RAJARAM_KT_WEIR_CREST_RL_M` was set to 530.18 m,
which is the WRD gauge zero datum, not the weir crest. The documented weir
overflow level is 535.77 m. Because the value only appeared in one comparison,
the bug was silent. `RAJARAM_GAUGE_ZERO_M` and `RAJARAM_KT_WEIR_CREST_RL_M` are
now separate constants with distinct values.

### 22. The embedded cross-sections were unverified against the ground survey

*(Verified 2026-09-30.)* `stage_converter.py` embeds the two surveyed
cross-sections as literal coordinate arrays, with no runtime dependency on the
survey files. Because they were literals, nothing checked them against the
official WRD ground survey, so a transcription edit could drift silently.

Both sections were checked point-by-point against the surveyed data:

| Site | X-Section | Embedded points | Survey points | Bed RL | Match |
| :--- | :--- | ---: | ---: | ---: | :--- |
| Shivaji Bridge | 17, chainage 6+257 | 146 | 146 | 528.670 m | exact |
| Rajaram K.T. Weir | 29, chainage 10+115 | 193 | 193 | 529.318 m | exact |

No coordinate differed, so nothing needed replacing — the embedded geometry was
already the surveyed section. The survey has since been promoted to a tracked
location (`data/wrd_cross_sections/`) and `tests/test_cross_section_survey.py`
(17 cases) now asserts exact equality, the bed levels, the section widths, and
that discharge is zero at the surveyed bed and grows monotonically with the
wetted area and perimeter.

The same test initially recorded that the wetted geometry "cannot set the
discharge magnitude", citing Manning with $n = 0.031$ and $S = 1{:}4641$
returning ~210 m³/s against a government-gauged 80 m³/s at 533.54 m. **That
comparison was wrong and has been withdrawn** — see item 24.

### 23. The baseflow rule was untested in the runner and only mirrored in tests

*(Fixed 2026-09-30.)* The corrected baseflow derivation lived inline inside
`_execute_hec_hms_core`, and `tests/test_low_flow_stage_bias.py` exercised a
hand-written *copy* of it. A later edit to the runner would not have failed any
test. The rule is now the module-level function
`src.hms.runner.derive_baseflow_m3s(live_stage_m)`, called by the runner and by
the tests, so the tested path is the shipped path.

Its documented consequences, all asserted: discharge is exactly 0 at the
surveyed bed level; it rises monotonically with the wetted area and perimeter;
and 40 m³/s is a legitimate baseflow at 532.42 m MSL (533.06 m at Rajaram) but
never a floor to apply at every level.


### 24. The reach bed slope was used as the friction slope

*(Found 2026-09-30. The conclusion it supported has been withdrawn.)*

The Shivaji→Rajaram reach was checked by applying Manning with $n = 0.031$ and
the **survey bed slope** $1{:}4641$ to the surveyed sections. That returned
~21 m³/s at the live stage against ~2.8 m³/s from the WRD rating curve, and the
project concluded that the wetted geometry over-predicted by a factor of ~7.6.

That comparison is invalid. The bed slope is not the friction slope. The single
matched pair in the official record — $Q = 1800$ m³/s at Shivaji 542.10 m and
Rajaram 542.70 m — gives a **water-surface drop of 0.600 m** over a 0.648 m bed
drop, i.e. the reach is in backwater and the surface gradient is flatter than the
bed gradient. The effective conveyance measured from the lowest WRD gauge is
$K = 0.0539$, an effective $n\sqrt{S}$ of 18.5, against 2197 implied by the bed
slope.

Redone with measured quantities only, the surveyed wetted area and the WRD
record agree:

| Closure | Basis | Q at Shivaji 530.44 m |
| :--- | :--- | ---: |
| Velocity $v\cdot A$ | $v = 0.0767$ m/s measured at the lowest WRD gauge | 3.36 m³/s |
| Conveyance $K\cdot A\cdot R^{2/3}$ | $K = 0.0539$ measured at the same gauge | 2.42 m³/s |
| Production PCHIP | WRD anchors with the −0.648 m transfer | 2.80 m³/s |

The production value lies inside the geometry bracket, and the operator's
independent estimate of 2.90 m³/s does too.

Two further defects found and fixed in the same pass:

- **The `530.18 → Q = 0` rating anchor was fabricated.** 530.18 m is the WRD
  zero-gauge *datum*, not a crest and not a level at which flow ceases. Anchoring
  $Q = 0$ there created a 2.52 m linear ramp whose slope was set by the next
  anchor rather than by any observation. Removed; only the surveyed bed
  (529.318 m) now carries $Q = 0$.
- **The site transfer was documented as WRD-attested.** It is not. The measured
  surface drop is 0.600 m, not 0.648 m. The 0.648 m bed drop is retained as the
  uniform-flow transfer, and the measured value is now recorded separately in
  `SHIVAJI_MEASURED_SURFACE_DROP_M`.

Removing the fabricated anchor also revealed that two tests
(`test_offset_widens_below_20_m3s`, `test_shifting_low_stage_understates_discharge`)
were asserting an artefact of it: the two curves are exact translates, so the
offset is a uniform 0.648 m at every discharge and the stage round trip is an
identity. Both were replaced with tests of the corrected invariant.

### 25. The WRD register contains transcription errors

*(Found and corrected 2026-09-30.)* The hourly register is a wide multi-day
sheet; `stage_m` is derived from the staff-gauge reading, not measured
independently. Recomputing `ft_dec × 0.3048 + 530.18` for every row keeps
**2350 of 2406** rows and exposes **56** that disagree by more than 0.03 m,
including one 2023-07-08 column that is off by exactly 1.00 m. Those rows
produced duplicate stages carrying wildly different discharges and made the
roughness back-calculation meaningless (193 % coefficient of variation).

After the filter the register reproduces the official WRD sheet to within
**±0.3 %** across 533.54–539.02 m, which confirms the sheet anchors. Above
541.50 m the two diverge by up to **−50 %**, so the sheet's upper limb is a
published extension rather than a measurement.

The official sheet is also a clean compound rating:

$$Q = 1.5\,(H - 529.318)^{2.778}, \qquad R^2 = 0.99858$$

fitted on 15 sheet points over 533.54–541.50 m with a maximum residual of
7.3 %. It is **valid only inside that band and must not be extrapolated below
533.54 m**.

### 26. The lowest-flow discharge is an extrapolation, not an observation

*(Open constraint, recorded 2026-09-30.)* After cleaning, the WRD record
contains **no observation below 532.70 m** — the lowest reading in three years is
532.70 m at 14.16 m³/s. The live Shivaji reading of 530.44 m sits 2.26 m below
it, and the rating exponent in the observed low band is $b \approx 10$, so the
curve is extremely steep there and a multi-metre downward extrapolation is not
benign.

The production PCHIP value at the live stage is therefore a shape extrapolation,
and the ~0.648 m site transfer is the survey bed drop rather than a measured low-
flow surface drop. `estimate_low_flow_discharge()` and `is_ungauged_stage()` now
return the geometry bracket (2.42–3.36 m³/s at 530.44 m) and an explicit
`is_ungauged` flag so the uncertainty travels with the number.

Of the 60 archived cycles replayed from 2026-09-10, **35 are anchored on an
un-gauged stage** and must be re-run if official WRD low-flow data below
532.70 m is obtained.

### 27. Replay guardrails

*(Added 2026-09-30.)* `scratch/resim_and_revalidate_all.py` rewrites every
archived cycle in place and rebuilds the ledger. It had no date filter, no
backup, and no record of which rating basis produced a run. It now accepts
`--since`, `--dry-run` and `--no-backup`, writes a timestamped
`data/runs/_backup_<stamp>/` snapshot before any overwrite, carries forward
ledger entries for out-of-scope cycles so a narrow replay cannot truncate the
history, and stamps each replayed run with a `rating_curve_fingerprint` and a
`low_flow_basis` provenance block.
