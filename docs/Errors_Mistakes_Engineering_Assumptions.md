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
Re-engineered the rating engine into a **dual-regime hydraulic formulation**:
- **In-Bank Regime ($h \le 535.0\text{m}$):** Strictly governed by surveyed channel slope ($S_0 = 0.005858$).
- **Overbank Flood Regime ($h \ge 541.0\text{m}$):** Calibrated to official Maharashtra WRD flood telemetry.

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

This was an empirical hack that completely ignored physical channel hydraulics. Rajaram Weir is $3.8\text{ km}$ downstream and has a significantly gentler bed slope ($S_0 = 0.002318$ vs $0.005858$). Hydraulically, a gentler slope requires a **greater cross-sectional depth** to convey the same discharge. During rising limbs and weir drowning, the stage difference between the two sites varies non-linearly from $+0.40\text{m}$ to $-0.80\text{m}$.

#### Resolution:
Built distinct, independently calibrated PCHIP hydraulic curves for both Chhatrapati Shivaji Maharaj Bridge and Rajaram K.T. Weir.

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
| (SCS-CN & Clark Unit Hydrograph)  | micro-topography within subbasins is spatially aggregated.|
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

## Part III: Operational Summary

By identifying past mistakes, replacing unsegmented regressions with dual-regime PCHIP interpolators, and establishing clear physical boundaries for engineering assumptions, HydroCast operates with high technical transparency. It delivers robust early warning projections while clearly defining the limits of its predictive certainty.
