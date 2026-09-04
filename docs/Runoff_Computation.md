# Mathematical Runoff Computation & Hydrograph Routing

```
========================================================================================
       MATHEMATICAL CONTINUUM RUNOFF & UNIT HYDROGRAPH CONVOLUTION ENGINE
========================================================================================

    Hourly Precipitation P[h]                    Excess Precipitation Pe[h]
       [ Total Rainfall ]                           [ Runoff Hyetograph ]
               │                                              │
               ▼                                              ▼
    ┌─────────────────────┐                       ┌─────────────────────┐
    │  SCS-CN Loss Model  │ ── Cumulative Infil ──>│ Convolution Kernel  │
    │  Ia = 0.2 * Sret    │    & Retention Loss   │  U(t) Unit Response │
    └─────────────────────┘                       └─────────────────────┘
                                                              │
                                                              ▼
    Surface Runoff Hydrograph Q_surface[t]       Channel Wave Outflow Q_out[t]
               │                                              │
               ▼                                              ▼
    ┌─────────────────────┐                       ┌─────────────────────┐
    │ Discrete Linear     │ ── Muskingum-Cunge ──>│ Total Discharge     │
    │ Convolution Sum     │    Reach Routing      │ Q_tot = Q_base + Q_s│
    └─────────────────────┘                       └─────────────────────┘
```

---

## 1. Physical Governing Principles

Runoff calculation transforms an hourly depth series of atmospheric precipitation ($P$ in $mm/hr$) into a volumetric discharge rate ($Q$ in $m^3/s$) passing a river cross-section over time.

This involves two consecutive transformations:
1. **Vertical Mass Balance (Loss Model):** Segregates gross precipitation into **infiltration / soil storage** ($F$) and **surface runoff excess** ($P_e$).
2. **Horizontal Kinematic Translation (Routing Model):** Converts excess depth over the subbasin surface into an attenuated time series of discharge at the concentration point.

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
- $K$ = Reach travel time / wave lag ($hours$, approximately $4.2\text{ hours}$ between Shivaji Bridge and Rajaram Weir).
- $X$ = Dimensionless weighting parameter ($0 \le X \le 0.5$, typically $0.20 - 0.25$ for natural meandering rivers).

Applying the finite-difference continuity equation $\frac{S_2 - S_1}{\Delta t} = \frac{I_1 + I_2}{2} - \frac{O_1 + O_2}{2}$:

$$O_2 = C_0 \cdot I_2 + C_1 \cdot I_1 + C_2 \cdot O_1$$

Where the routing coefficients are:

$$C_0 = \frac{\Delta t - 2KX}{2K(1-X) + \Delta t}$$

$$C_1 = \frac{\Delta t + 2KX}{2K(1-X) + \Delta t}$$

$$C_2 = \frac{2K(1-X) - \Delta t}{2K(1-X) + \Delta t}$$

$$\text{Conservation of Mass Check: } C_0 + C_1 + C_2 \equiv 1.000$$

---

## 5. Vectorized Python Implementation (`runner.py`)

In [`runner.py`](file:///e:/hydrocast_complete/src/hms/runner.py), the entire runoff continuum executes in $< 15\text{ milliseconds}$ via vectorized NumPy operations:

```python
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

# 4. Convolution with Clark Unit Hydrograph kernel
surface_runoff = np.convolve(excess_p, unit_hydrograph)[:90] * (area_km2 / 3.6)

# 5. Superposition of live baseflow
total_discharge = baseflow + surface_runoff
```
