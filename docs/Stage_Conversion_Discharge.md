# 2D Surveyed Hydraulic Rating Curves & Stage-Discharge Conversion

```
====================================================================================================
                DIVIDED CHANNEL METHOD (DCM) CROSS-SECTIONAL HYDRAULICS
====================================================================================================

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
              |                        /                                 \
        528.67+-----------------------+-------- Thalweg: 528.67m MSL -----+--------------------
              +-----------------------+-----------------------------------+--------------------+
                 Left Overbank                      Main Channel               Right Overbank
```

---

## 1. Physical Survey Integration

HydroCast replaces empirical synthetic rating curves with high-resolution **2D field cross-sectional surveys** conducted by the Maharashtra Water Resources Department (WRD):
1. **Chhatrapati Shivaji Maharaj Bridge:** Chainage 6+257 (108 surveyed coordinates across 550m lateral width).
   - Thalweg Elevation: **528.670 m MSL**
   - Bankfull Elevation: **541.600 m MSL**
2. **Rajaram K.T. Weir (Kasba Bawada):** Chainage 10+115 (108 surveyed coordinates across 550m lateral width).
   - Thalweg Elevation: **529.318 m MSL**
   - Weir Crest Level: **530.180 m MSL**
   - Bankfull Elevation: **541.050 m MSL**

---

## 2. Divided Channel Method (DCM) Formulation

When river water levels exceed the bankfull stage, floodwaters spill onto broad agricultural floodplains dominated by standing sugarcane and paddy crops. Modeling the entire cross-section with a single composite Manning's $n$ severely overpredicts floodplain velocity and underestimates stage.

HydroCast partitions the active flow area into three discrete hydraulic subsections:

$$Q(H) = Q_{\\text{left\\_overbank}}(H) + Q_{\\text{main\\_channel}}(H) + Q_{\\text{right\\_overbank}}(H)$$

For each subsection $k \\in \\{\\text{left}, \\text{main}, \\text{right}\\}$:

$$Q_k(H) = \\frac{1}{n_k} \\cdot A_k(H) \\cdot \\left[R_k(H)\\right]^{2/3} \\cdot S_0^{1/2}$$

Where:
- $A_k(H)$: Wetted cross-sectional area of subsection $k$ ($m^2$).
- $P_k(H)$: Wetted perimeter of subsection $k$ ($m$).
- $R_k(H) = \\frac{A_k(H)}{P_k(H)}$: Hydraulic radius ($m$).
- $S_0$: Energy slope (approximated by longitudinal bed slope).

### 2.1 Calibrated Manning's Roughness ($n$) Coefficients
Per the authoritative **Krishna Basin Flood 2019 Volume 1 Study Report**:
- **Main River Channel:** $n_{\\text{main}} = 0.031$ (clean natural channel, silt/sand/gravel bed, irregular banks).
- **Overbank Floodplains:** $n_{\\text{flood}} = 0.070$ (dense standing crops, primarily sugarcane and paddy, causing heavy flow obstruction).

---

## 3. PCHIP Monotonic Rating Spline

To ensure unconditional numerical stability, the discrete $(H, Q)$ pairs computed via the Divided Channel Method are interpolated using **Piecewise Cubic Hermite Interpolating Polynomials (PCHIP)** (`scipy.interpolate.PchipInterpolator`):

$$\\frac{dQ}{dH} > 0 \\quad \\forall H$$

PCHIP prevents unphysical polynomial overshoot or negative derivatives present in standard natural cubic splines, guaranteeing monotonic stage-discharge relationships.

---

## 4. Sensor-to-Sink Spatial Transfer Function

Because the IoT water level sensor is installed at **Shivaji Bridge (Chainage 6+257)** while the HEC-HMS model outlet is at **Rajaram K.T. Weir (Chainage 10+115)**, water levels between the two sites are linked via `infer_rajaram_stage_from_shivaji()`:

```python
# Upstream stage transfer in src/hydrology/stage_converter.py
def infer_rajaram_stage_from_shivaji(shivaji_stage_m: float, q_m3s: Optional[float] = None) -> float:
    # Physical bed elevation difference: Rajaram is 0.648m higher than Shivaji
    delta_bed_m = 529.318 - 528.670  # +0.648 m

    # In low-flow summer conditions, Rajaram KT weir impounds water behind crest (530.18m MSL)
    if shivaji_stage_m < 530.0:
        return max(530.18, shivaji_stage_m + delta_bed_m)
    
    # In flood regime (open weir / submerged), water surface profile follows bed slope
    return shivaji_stage_m + delta_bed_m
```
