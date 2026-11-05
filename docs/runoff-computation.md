# Mathematical Runoff Computation & Hydrograph Routing


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
      <a class="hydrocast-diagram-btn" href="diagrams/10-catchment-hydrology-solver.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="diagrams/10-catchment-hydrology-solver.html?embed=1" title="Catchment Hydrology Solver Console"></iframe>
</div>

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 01</span>
      <strong>End-to-End System Architecture</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="diagrams/01-architecture.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="diagrams/01-architecture.html?embed=1" title="End-to-End System Architecture Console"></iframe>
</div>

---

## 1. Physical Governing Principles

```
====================================================================================================
                  HOURLY DISCRETE RUNOFF CONVOLUTION & ROUTING PIPELINE
====================================================================================================

      Raw Hourly Rainfall Hyetograph: P(t) [mm]
                        |
                        v
          [ SCS-CN Dynamic Loss Model ]
          - Antecedent Wetness Classes: AMC-I (<25mm) / AMC-II (25-65mm) / AMC-III (>=65mm mean 90h rain)
          - Cumulative Potential Retention: S = (25400 / CN) - 254
          - Initial Abstraction: Ia = 0.20*S (AMC-I) or 0.15*S (AMC-II) or 0.08*S (AMC-III)
                        |
                        v
      Incremental Excess Rainfall: Delta_P_excess(t) [mm]
                        |
                        v
**SCS Dimensionless Unit Hydrograph Transform:**

| Parameter | Formula |
|:---|:---|
| Subbasin Lag Time | t_lag = lag_min / 60.0 |
| Time to Peak | t_p = 0.5 + t_lag |
| Dimensionless Equation | u(t) = (t/tp)^3.7 * exp(3.7 * (1 - t/tp)) |
| Volume Conservation | Sum(UH * 3600) == Area_km2 * 1000 m3 |

**Direct Subbasin Outflow Hydrograph:** Q_dir(t) = Delta_P * UH [m3/s]

**5-Reach Muskingum Channel Network Cascade:**

| Reach | Routes Into | Routes Out Of | K (hr) | X |
|:---|:---|:---|:---:|:---:|
| R5 | S6 + S7 | R2 | 4.619 | 0.200 |
| R4 | S9 | R2 | 1.224 | 0.200 |
| R2 | R5 + R4 + S8 | R1 | 11.827 | 0.200 |
| R3 | S4 + S5 | R1 | 3.829 | 0.200 |
| R1 | R2 + R3 + S3 + S2 | Sink-1 | 2.899 | 0.200 |
| Direct (S1) | S1 | Sink-1 | — | — |

**Combined Surface Outflow:** Q_surface(t) = Outflow(R1) + Direct(S1)

**Exponential Baseflow Recession:**

| Parameter | Value | Notes |
|:---|:---|:---|
| Q_bf(t) | Q_bf0 * exp(-0.002 * t) | — |
| Q_bf0 | Discharge of live sensor (converted once) | No floor |
| Default | 91.1 m3/s | Only if telemetry absent |

**Total Hydrograph at Rajaram K.T. Weir:** Q_total(t) = Q_surface(t) + Q_bf(t)

**WRD-Anchored PCHIP Rating Curve Engine:**

| Property | Implementation |
|:---|:---|
| Both gauged sites | PCHIP interpolation through official Maharashtra WRD stage-discharge sheet (monotone, no overshoot) |
| Shivaji stage relationship | Shivaji stage = Rajaram stage - 0.648 m on WRD sheet control points (cross-checked at 1,800 m3/s) |
| Low-flow behavior (< ~20 m3/s) | Related by WRD 2021-23 observed register; offset is NOT constant — see stage-discharge-conversion.md |
| Wetted area A | Supplied by surveyed cross-section for any stage |
| Non-anchored sites | Fall back to compound-section Manning DCM (main n=0.035, overbank sugarcane/paddy n=0.055)

Runoff calculation transforms an hourly depth series of atmospheric precipitation ($P$ in $mm/hr$) into a volumetric discharge rate ($Q$ in $m^3/s$) passing a river cross-section over time.

This involves two consecutive transformations:

1. **Vertical Mass Balance (Loss Model):** Segregates gross precipitation into **infiltration / soil storage** ($F$) and **surface runoff excess** ($P_e$).
2. **Surface Transform Model (SCS Unit Hydrograph):** Converts excess depth over the subbasin surface into an attenuated time series of discharge at the concentration point.

### 1.1 The three-stage cascade at a glance


**The three-stage runoff cascade:**

| Stage | Process | Formula / Parameter |
|:---|:---|:---|
| P(t) | Hyetograph (precipitation input) | mm/h · 90 hourly values |
| AMC class | Antecedent moisture classification | P̄ < 25 → AMC-I; 25–65 → AMC-II; ≥ 65 → AMC-III |
| ΔP_e(t) | Rainfall excess | S = 25400/CN − 254; Ia = λS, λ = 0.20/0.15/0.08 |
| Q_surf(t) | Direct surface runoff | u(t) = (t/tp)^3.7 · e^(3.7(1−t/tp)); t_p = 0.5 + lag/60 |
| Q_routed(t) | Muskingum reach cascade | R5→R4→R2→R3→R1; C₀+C₁+C₂ ≡ 1 (mass-conserving) |
| Q_bf(t) | Baseflow recession | B₀·e^(−0.002t); B₀ from live sensor reading |
| Q_total(t) | Total hydrograph | m³/s · 352 points; peak = argmax Q_total |
| h(t) | Stage at gauges | PCHIP over 27 WRD anchors; Shivaji = Rajaram − 0.648 m on sheet; low-flow points use WRD register |

> **Runoff cascade console** — see [Console 10: Catchment Hydrology Solver](diagrams/10-catchment-hydrology-solver.html){ target="_blank" } for the interactive transformation chain with equations at every stage.

!!! note "Why PCHIP and not a straight line between anchors"
    Linear interpolation between government rating anchors can *overshoot*: it
    produces a non-monotonic curve, meaning a rising stage could yield a
    falling discharge. PCHIP is shape-preserving, so $Q(h)$ is guaranteed
    monotonically increasing and therefore invertible — a given discharge
    always maps back to exactly one stage.

---

## 2. The Non-Linear SCS-CN Infiltration Equation

The United States Natural Resources Conservation Service (NRCS) empirical formulation states that the ratio of actual surface retention to potential maximum retention equals the ratio of surface runoff to total rainfall minus initial abstraction:

$$\frac{F}{S_{ret}} = \frac{Q_{cum}}{P_{cum} - I_a}$$

Since total available water after initial abstraction is partitioned between storage and runoff:

$$P_{cum} - I_a = F + Q_{cum}$$

Substituting $F$ into the first equation yields the fundamental runoff equation:

$$Q_{cum}(t) = \frac{\left(P_{cum}(t) - I_a\right)^2}{P_{cum}(t) - I_a + S_{ret}} \quad \forall P_{cum} > I_a$$

Where:

- $P_{cum}(t) = \sum_{\tau=0}^{t} P(\tau)$ = Cumulative precipitation depth ($mm$)
- $S_{ret} = \frac{25,400}{CN} - 254$ = Potential maximum retention capacity ($mm$)
- $I_a = 0.2 \cdot S_{ret}$ = Initial abstraction ($mm$)

### 2.1 Incremental Excess Runoff Generation

The volumetric excess depth generated in each 1-hour time slice $[h, h+1]$ is computed by backward difference:

$$\Delta P_e[h] = Q_{cum}[h] - Q_{cum}[h-1]$$

---

## 3. Discrete Unit Hydrograph Convolution

Given an incremental excess hyetograph $\Delta P_e[1], \dots, \Delta P_e[M]$ and a discrete 1-hour Unit Hydrograph $U[1], \dots, U[K]$ representing the subbasin response to $1\text{ mm}$ of uniform excess rain:

The resulting surface runoff hydrograph is the **finite discrete convolution**:

$$Q_{surface}[n] = \sum_{m=1}^{\min(n, M)} \Delta P_e[m] \cdot U[n - m + 1] \cdot \left(\frac{A_{subbasin} \cdot 1,000}{3,600}\right)$$

Where the conversion factor $\frac{A \cdot 10^3}{3,600}$ converts $mm \cdot km^2 / hr$ to $m^3/s$:

$$1\text{ mm} \times 1\text{ km}^2 = 10^{-3}\text{ m} \times 10^6\text{ m}^2 = 1,000\text{ m}^3$$

$$\frac{1,000\text{ m}^3}{3,600\text{ s}} = 0.2778\text{ m}^3/s$$

---

## 4. Muskingum River Reach Wave Routing

As the flood wave travels along the $42.6\text{ km}$ Panchganga main stem between Prayag Chikhali and Kolhapur city, peak discharge is attenuated and delayed by channel storage.

The Muskingum storage equation relates reach storage ($S$) to inflow ($I$) and outflow ($O$):

$$S = K \cdot \left[ X \cdot I + (1 - X) \cdot O \right]$$

Where:

- $K$ = Reach travel time / wave lag ($hours$). These are the **fixed channel-storage constants** declared in `data/hms/HMS_Automation_RJKT/Basin_1.basin` and loaded at run time by `src/hms/basin_parser.py`. They are not re-optimised per cycle and are never written back to the `.basin` file. R5 (Shivaji → Rajaram) is $4.619\text{ h}$, consistent with the observed $\sim 4.2\text{ h}$ wave travel between the two gauges.
- $X$ = Dimensionless weighting parameter ($0 \le X \le 0.5$). Fixed at $0.20$ for all five RJKT reaches — the storage weighting of a natural, meandering lowland channel.

Applying the finite-difference continuity equation $\frac{S_2 - S_1}{\Delta t} = \frac{I_1 + I_2}{2} - \frac{O_1 + O_2}{2}$:

$$O_2 = C_0 \cdot I_2 + C_1 \cdot I_1 + C_2 \cdot O_1$$

Where the routing coefficients are (with $K' = K/\text{steps}$ the sub-divided travel time):

$$C_0 = \frac{\Delta t - 2K'X}{2K'(1-X) + \Delta t}$$

$$C_1 = \frac{\Delta t + 2K'X}{2K'(1-X) + \Delta t}$$

$$C_2 = \frac{2K'(1-X) - \Delta t}{2K'(1-X) + \Delta t}$$

$$\text{Conservation of Mass Check: } C_0 + C_1 + C_2 \equiv 1.000$$

**Stability-band sub-stepping.** Because the RJKT reaches are long relative to the
60-minute control interval, a single Muskingum step can drive $C_2$ negative and
destroy mass (HEC-HMS flags this as *WARNING 41169*). `route_muskingum()` therefore
chooses the smallest sub-step count $n$ such that every sub-step satisfies both

$$\frac{\Delta t}{2(1-X)} \le K' = \frac{K}{n} \le \frac{\Delta t}{2X}$$

which guarantees $C_0, C_1, C_2 \ge 0$ and therefore
$\sum O = \sum I$ to floating-point precision.

### 4.1 The RJKT cascade

Reach order is read from `Basin_1.basin` at run time — it is not hard-coded in
the emulator, so the topology below is a property of the model file rather than
of the code. Authoritative subbasin parameters and Muskingum reach matrices are canonically defined in [Catchment Hydrology: Subbasin Parameters](basin-hydrology.md#subbasin-parameters) and [Catchment Hydrology: Muskingum Reaches](basin-hydrology.md#muskingum-reaches).


**RJKT reach cascade topology:**

| Subbasin | Area (km²) | CN | Lag (min) | Routes To |
|:---|:---:|:---:|:---:|:---|
| S6 Gaganbawda | 227.72 | 61.78 | 3318 | R5 |
| S7 Garivade | 195.39 | 61.28 | 3362 | R5 |
| S9 Radhanagari | 366.97 | 64.31 | 5199 | R4 |
| S8 Beed | 177.44 | 65.76 | 3387 | R2 |
| S4 Karanjphen | 262.00 | 61.89 | 3116 | R3 |
| S5 Padasali | 106.39 | 60.97 | 2117 | R3 |
| S2 Sangarul | 153.77 | 65.74 | 3154 | R1 |
| S3 Kotoli | 261.32 | 64.82 | 3998 | R1 |
| S1 Karveer | 86.21 | 74.85 | 2152 | Sink-1 (direct) |

| Reach | K (hr) | X | Routing Passes | Inputs | Output |
|:---|:---:|:---:|:---:|:---|:---|
| R5 | 4.619 | 0.20 | 2 | S6 + S7 | R2 |
| R4 | 1.224 | 0.20 | 1 | S9 | R2 |
| R2 | 11.827 | 0.20 | 5 | R5 + R4 + S8 | R1 |
| R3 | 3.829 | 0.20 | 2 | S4 + S5 | R1 |
| R1 | 2.899 | 0.20 | 2 | R2 + R3 + S2 + S3 | Sink-1 |

**Sink-1 (Rajaram outlet):** Q_total(t) = routed surface + B₀·e^(−0.002t); basin area 1,837.21 km².

> **Cascade console** — see [Console 10: Catchment Hydrology Solver](diagrams/10-catchment-hydrology-solver.html){ target="_blank" } for the interactive subbasin-to-reach network.

---

## 5. Discharge → Stage: the WRD-Anchored Rating Curve

Discharge is only operationally meaningful once it has been converted to a
**water level** at a named location, because that is what a field officer can
actually read off a gauge.

### 5.1 Two paths, one answer

`build_calibrated_rating_curve()` in `src/hydrology/stage_converter.py`
selects a regime per site:


### 5.2 The two gauged sites

Only two sites on the system have a surveyed rating: the Chhatrapati Shivaji
Maharaj Bridge, where the ultrasonic sensor is mounted, and the Rajaram K.T. weir,
which is the regulatory reference point for Kolhapur city. Every other reach is
routed, not rated. The bridge sits 3,858 m upstream of the weir and its bed is
0.648 m lower, which is the whole of the geometric difference between the two
published stage series.


### 5.3 Threshold classification

A stage is classified against the site's own stored marks — consumers never
hard-code thresholds:


---

## 6. Vectorized Python Implementation (`runner.py`)

In [`runner.py`](hms.md) (`src/hms/runner.py`), the entire runoff continuum executes in $< 15\text{ milliseconds}$ via vectorized NumPy operations:

```
# 1. Potential soil retention
s_ret = (25400.0 / cn) - 254.0
ia = 0.2 * s_ret

# 2. Cumulative runoff calculation
cum_p = np.cumsum(p_basin)
cum_q = np.zeros(90, dtype=np.float32)
for h in range(90):
    if cum_p[h] > ia:
        cum_q[h] = ((cum_p[h] - ia) ** 2) / (cum_p[h] + 0.8 * s_ret)

# 3. Incremental excess hyetograph
excess_p = np.diff(np.insert(cum_q, 0, 0.0))

# 4. Convolution with SCS Unit Hydrograph kernel
surface_runoff = np.convolve(excess_p, unit_hydrograph)[:90] * (area_km2 / 3.6)

# 5. Superposition of live baseflow
total_discharge = baseflow + surface_runoff
```

---

## 7. Adaptive Closed-Loop Parameter Scaling Formulation

In production, soil infiltration and watershed lag vary dynamically between antecedent dry spells and saturated torrential downpours. Rather than using fixed parameters, the computation engine scales parameters dynamically via real-time calibration:

$$CN_{\text{effective}} = \min(98.0, \max(50.0, \alpha \cdot CN))$$

$$T_{\text{lag, effective}} = \max(1.0, \beta \cdot T_{\text{lag}})$$

Where $\alpha \in [0.50, 1.80]$ is the Curve Number scaling coefficient and $\beta \in [0.50, 1.80]$ is the SCS Unit Hydrograph lag time scaling coefficient determined by minimizing observed residual error:

$$\mathcal{L}(\alpha, \beta) = \sum_{t=1}^{N} \left[ Q_{\text{sim}}(t; \alpha, \beta) - Q_{\text{obs}}(t) \right]^2 + \lambda \left[ (1 - \alpha)^2 + (1 - \beta)^2 \right]$$

The regularizer term $\lambda \left[ (1 - \alpha)^2 + (1 - \beta)^2 \right]$ penalizes large deviations from physical baseline parameters, preventing overfitting to short-term sensor noise or anomalous telemetry spikes.

---

## 8. Peak Flood Arrival Horizon & Confidence Interval ($\pm 2.0\text{ hours}$)

HydroCast computes the operational peak arrival window directly from the resulting runoff hydrograph $Q_{\text{total}}(t)$:

1. **Peak Index Determination:**

    $$t^* = \arg\max_{t \in [0, 90]} Q_{\text{total}}(t), \quad T_{\text{peak}} = T_{\text{cycle\_start}} + t^* \cdot \Delta t$$

2. **Permissible Confidence Interval Window:**
    Field hydrodynamic validation confirms peak wave arrival follows normal dispersion $\mathcal{N}(0, \sigma^2)$ with $\sigma \approx 1.02\text{ hours}$.
    At the 95% operational confidence interval ($z = 1.96$):

    $$\Delta T_{\text{window}} = \pm 1.96 \cdot \sigma \approx \pm 2.0\text{ hours}$$

    $$T_{\text{earliest}} = T_{\text{peak}} - 2.0\text{ hours}$$

    $$T_{\text{latest}} = T_{\text{peak}} + 2.0\text{ hours}$$

3. **Peak Inundation Warning Trigger:**
   If $Q_{\text{total}}(t^*) \ge 1,200\text{ m}^3/s$ (Shivaji Bridge Alert Level, $542.1\text{m}$ MSL) or $Q_{\text{total}}(t^*) \ge 1,550\text{ m}^3/s$ (Danger Level, $543.3\text{m}$ MSL), this precise operational window $[T_{\text{earliest}}, T_{\text{latest}}]$ is dispatched across the DDMA Telegram Alert Bot and live dashboard overlays.
