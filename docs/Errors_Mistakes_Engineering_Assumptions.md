# Comprehensive Engineering Assumptions, Historical Mistakes & Resolutions

```
====================================================================================================
           PANCHGANGA HYDROCAST - ENGINEERING AUDIT & RESOLUTION MATRIX
====================================================================================================
```

---

## 1. Ten Core Hydrological & Hydraulic Corrections

### Issue 1: Uniform Manning's Roughness vs Divided Channel Method (DCM)
- **Initial Flaw:** A single composite Manning's $n = 0.035$ was initially applied across the full cross-section. Above bankfull stage ($>541.6\\text{ m}$), this severely overpredicted floodplain discharge and caused stage underprediction during high flood events.
- **Resolution:** Implemented the **Divided Channel Method (DCM)** in `src/hydrology/stage_converter.py`, partitioning main channel ($n_{\\text{main}} = 0.031$) from overbank agricultural floodplains ($n_{\\text{flood}} = 0.070$).

### Issue 2: Agricultural Sugarcane Obstruction on Floodplains
- **Initial Flaw:** Floodplains were modeled with standard pasture roughness ($n = 0.040$).
- **Resolution:** Adopted $n_{\\text{flood}} = 0.070$ per the **Krishna Basin Flood 2019 Volume 1 Study Report**, accurately reflecting dense standing sugarcane and paddy crops that impede flood flow.

### Issue 3: Spatial Transposition of Sensor vs Model Sink Node
- **Initial Flaw:** IoT water level readings from **Shivaji Bridge** were directly applied as the boundary stage at **Rajaram K.T. Weir**, ignoring the 3,858m river reach separation.
- **Resolution:** Developed `infer_rajaram_stage_from_shivaji()`, integrating surveyed thalweg bed elevations (Shivaji: 528.670m MSL, Rajaram: 529.318m MSL, difference: $+0.648\\text{ m}$) and KT weir crest impoundment backwater dynamics.

### Issue 4: Spurious Flat-Flow Peak at T+89h
- **Initial Flaw:** During non-storm low-flow periods, `np.argmax(q)` on flat surface runoff arrays returned index 89 ($T+89\\text{h}$) as the peak arrival time.
- **Resolution:** Added the **Physical Flood Wave Significance Rule** in `src/hms/runner.py`. If peak surface runoff does not exceed $\\max(0.5, 2.0 \\times Q_{\\text{baseflow}})$, the system declares $T+0\\text{h}$ (baseflow stable / receding).

### Issue 5: Regional Bed Slope Delineation
- **Initial Flaw:** A uniform slope of 0.005858 was assigned across the entire river basin.
- **Resolution:** Aligned reach slopes with surveyed government profiles:
  - Radhanagari to Prayag Chikhali: $1:2529$
  - Prayag Chikhali to Rajaram KT Weir: $1:4641$
  - Rajaram KT Weir to Shirol KT Weir: $1:7700$
  - Shivaji Bridge site calibrated to $S_0 = 0.000201$ to incorporate Jayanti Nalla backwater effects.

### Issue 6: Non-Zero Minimum Baseflow Floor
- **Initial Flaw:** Unconstrained simulations allowed dry-season river flow to drop toward $0\\text{ m}^3/\\text{s}$.
- **Resolution:** Enforced an absolute minimum physical baseflow floor of **$15.0\\text{ m}^3/\\text{s}$** reflecting perennial groundwater recharge across the 1,837 km² catchment.

### Issue 7: Dynamic Antecedent Moisture Condition (AMC-II to AMC-III)
- **Initial Flaw:** Static AMC-II Curve Numbers failed to capture rapid saturation in the Western Ghats during heavy continuous monsoon downpours.
- **Resolution:** Added automatic switching to **AMC-III** ($CN$ scaled via Sobhani transform, $I_a = 0.08 S$) whenever 90-hour catchment rainfall forecast $\\ge 65.0\\text{ mm}$.

### Issue 8: Muskingum Numerical Sub-stepping Stability Criterion
- **Initial Flaw:** When reach travel time $K$ was small relative to $\\Delta t = 1\\text{h}$, the stability condition $\\Delta t \\le 2 K X$ was breached, causing numerical oscillations.
- **Resolution:** Added adaptive internal sub-stepping ($\\text{steps} = \\max(1, \\text{round}(K / 2KX))$), guaranteeing non-negative discharge and numerical stability.

### Issue 9: Jayanti Nalla Urban Stormwater Confluence
- **Initial Flaw:** Neglected local urban stormwater and sewage inflow merging between Shivaji Bridge and Rajaram Weir via Jayanti Nalla.
- **Resolution:** Calibrated the local Shivaji energy slope ($S_0 = 0.000201$) to account for the local hydraulic headloss and backwater from the Jayanti Nalla confluence.

### Issue 10: Flat-Flow Baseflow Variance Guard for Validation
- **Initial Flaw:** Applying NSE and Spearman correlation during flat baseflow generated false numerical errors ($-\\infty$).
- **Resolution:** Added `obs_std < 0.05` variance guard in `src/hydrology/validation_metrics.py`, reporting `BASEFLOW_STABLE` with physical RMSE ($\le \\pm 0.025\\text{ m}$) instead.
