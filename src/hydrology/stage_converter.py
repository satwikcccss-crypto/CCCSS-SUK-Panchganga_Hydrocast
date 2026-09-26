"""
Stage-Discharge Converter
==========================
Builds rating curves from surveyed cross-section data for Panchganga bridge gauge sites.
Uses Manning's equation with compound cross-section geometry.
Stores rating curves and 90-hr forward stage projections into Supabase/Postgres.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d, PchipInterpolator

log = logging.getLogger(__name__)


# ── Cross-section data model ──────────────────────────────────────────────────

@dataclass
class CrossSection:
    site_id:        str          # 'SHIVAJI_BRIDGE' | 'RAJARAM_BRIDGE'
    name:           str
    latitude:       float
    longitude:      float
    n_main:         float = 0.031    # Manning's n — main channel (Krishna Basin Flood 2019 Vol.1)
    n_flood:        float = 0.070    # Manning's n — overbank floodplain: standing sugarcane/crops (Krishna Basin Flood 2019 Vol.1)
    slope:          float = 0.000250 # Calibrated against WRD empirical flood records
    datum_m:        float = 0.0      # datum offset
    alert_stage_m:   float = 542.10
    warning_stage_m: float = 542.70
    danger_stage_m:  float = 543.30
    extreme_stage_m: float = 544.00
    hfl_m:           float = 545.33
    station_m:      np.ndarray = field(default_factory=lambda: np.array([]))
    elevation_m:    np.ndarray = field(default_factory=lambda: np.array([]))


# ── Built-in High Precision Survey Cross-Sections ─────────────────────────────

SHIVAJI_SURVEY = np.array([
    [1847364.935, 416360.5843, 541.634],

    [1847364.328, 416362.0973, 541.801],

    [1847363.804, 416363.4023, 542.084],

    [1847362.669, 416366.2283, 541.992],

    [1847361.772, 416368.4623, 542.005],

    [1847360.795, 416370.8963, 541.943],

    [1847359.765, 416373.4623, 542.038],

    [1847358.727, 416376.0463, 542.005],

    [1847357.808, 416378.3363, 541.855],

    [1847356.859, 416380.6983, 541.912],

    [1847355.845, 416383.2243, 541.805],

    [1847354.833, 416385.7433, 541.933],

    [1847353.836, 416388.2283, 541.853],

    [1847353.044, 416390.2013, 541.731],

    [1847352.112, 416392.5203, 541.799],

    [1847351.231, 416394.7153, 541.73],

    [1847350.335, 416396.9453, 541.792],

    [1847349.14, 416399.9233, 541.766],

    [1847348.149, 416402.3903, 541.695],

    [1847347.279, 416404.5573, 541.654],

    [1847346.384, 416406.7853, 541.684],

    [1847345.424, 416409.1773, 541.594],

    [1847344.415, 416411.6903, 541.616],

    [1847343.415, 416414.1803, 541.545],

    [1847342.407, 416416.6903, 541.639],

    [1847341.489, 416418.9773, 541.407],

    [1847340.589, 416421.2183, 541.417],

    [1847339.267, 416424.5123, 541.671],

    [1847338.302, 416426.9163, 541.549],

    [1847337.392, 416429.1813, 541.504],

    [1847336.786, 416430.6913, 541.387],

    [1847335.837, 416433.0533, 541.44],

    [1847334.789, 416435.6633, 541.543],

    [1847333.773, 416438.1943, 541.5],

    [1847332.751, 416440.7413, 541.484],

    [1847331.747, 416443.2403, 541.495],

    [1847330.758, 416445.7033, 541.512],

    [1847329.782, 416448.1343, 541.553],

    [1847328.843, 416450.4723, 541.311],

    [1847327.854, 416452.9363, 541.26],

    [1847326.877, 416455.3703, 541.219],

    [1847326.026, 416457.4883, 540.968],

    [1847325.238, 416459.4503, 540.493],

    [1847324.47, 416461.3653, 540.867],

    [1847323.487, 416463.8123, 540.811],

    [1847322.523, 416466.2123, 540.921],

    [1847321.713, 416468.2313, 541.527],

    [1847321.138, 416469.6613, 541.996],

    [1847319.631, 416473.4163, 542.034],

    [1847319.12, 416474.6873, 541.75],

    [1847318.934, 416475.1513, 541.716],

    [1847318.625, 416475.9203, 541.337],

    [1847318.29, 416476.7553, 540.831],

    [1847317.843, 416477.8683, 539.859],

    [1847317.462, 416478.8183, 539.094],

    [1847317.462, 416478.8183, 539.094],

    [1847317.062, 416479.8143, 538.519],

    [1847316.621, 416480.9133, 537.774],

    [1847316.052, 416482.3293, 537.181],

    [1847315.375, 416484.0143, 536.605],

    [1847314.573, 416486.0113, 535.88],

    [1847313.844, 416487.8293, 535.58],

    [1847312.729, 416490.6043, 535.25],

    [1847311.887, 416492.7023, 535.192],

    [1847310.553, 416496.0233, 535.249],

    [1847309.174, 416499.4593, 535.349],

    [1847307.722, 416503.0753, 535.364],

    [1847306.657, 416505.7273, 535.534],

    [1847305.904, 416507.6023, 535.669],

    [1847304.48, 416511.1493, 535.507],

    [1847303.637, 416513.2483, 535.538],

    [1847302.783, 416515.3743, 535.477],

    [1847301.95, 416517.4493, 535.424],

    [1847300.723, 416520.5053, 535.561],

    [1847299.991, 416522.3283, 535.621],

    [1847299.738, 416522.9583, 535.582],

    [1847299.303, 416524.0423, 535.487],

    [1847298.699, 416525.5473, 535.1],

    [1847298.372, 416526.3613, 534.843],

    [1847298.229, 416526.7183, 534.589],

    [1847297.868, 416527.6163, 532.636],

    [1847297.867, 416527.6193, 533.86],

    [1847297.755, 416527.8973, 533.574],

    [1847297.684, 416528.0743, 533.561],

    [1847297.146, 416529.4153, 531.493],

    [1847296.487, 416531.0563, 530.45],

    [1847296.148, 416531.8993, 529.884],

    [1847296.128, 416531.9503, 529.881],

    [1847295.967, 416532.3513, 529.678],

    [1847295.621, 416533.2133, 529.528],

    [1847295.124, 416534.4503, 529.355],

    [1847294.514, 416535.9693, 529.266],

    [1847293.784, 416537.7893, 529.368],

    [1847293.004, 416539.7303, 529.423],

    [1847292.22, 416541.6843, 529.492],

    [1847291.436, 416543.6363, 529.472],

    [1847291.436, 416543.6363, 529.485],

    [1847290.653, 416545.5863, 529.43],

    [1847289.876, 416547.5193, 529.351],

    [1847289.114, 416549.4183, 529.25],

    [1847288.384, 416551.2363, 529.091],

    [1847287.674, 416553.0043, 528.873],

    [1847286.923, 416554.8743, 528.709],

    [1847286.145, 416556.8133, 528.67],

    [1847285.356, 416558.7773, 528.904],

    [1847284.594, 416560.6763, 529.179],

    [1847283.851, 416562.5273, 529.556],

    [1847283.125, 416564.3343, 529.84],

    [1847282.427, 416566.0733, 529.965],

    [1847281.765, 416567.7213, 530.2],

    [1847281.135, 416569.2903, 530.32],

    [1847280.524, 416570.8123, 530.501],

    [1847279.932, 416572.2853, 530.628],

    [1847279.362, 416573.7053, 530.72],

    [1847278.814, 416575.0713, 530.961],

    [1847278.292, 416576.3713, 531.074],

    [1847277.793, 416577.6143, 531.22],

    [1847277.316, 416578.8003, 531.287],

    [1847276.863, 416579.9283, 531.333],

    [1847276.441, 416580.9813, 531.451],

    [1847276.028, 416582.0093, 531.483],

    [1847275.617, 416583.0323, 531.681],

    [1847275.201, 416584.0683, 531.873],

    [1847274.785, 416585.1063, 532.093],

    [1847274.369, 416586.1413, 532.274],

    [1847273.999, 416587.0623, 532.456],

    [1847273.67, 416587.8813, 532.597],

    [1847273.41, 416588.5293, 532.802],

    [1847273.22, 416589.0033, 532.897],

    [1847273.086, 416589.3363, 532.94],

    [1847267.439, 416603.4003, 541.839],

    [1847260.848, 416619.8153, 549.944],

    [1847260.448, 416620.8113, 549.97],

    [1847259.974, 416621.9903, 550.01],

    [1847256.385, 416630.9313, 550.146],

    [1847255.929, 416632.0673, 550.244],

    [1847255.027, 416634.3123, 550.63],

    [1847248.068, 416651.6433, 554.83],

    [1847247.987, 416651.8453, 554.905],

    [1847247.198, 416653.8113, 554.974],

    [1847246.701, 416655.0483, 555.22],

    [1847222.13, 416716.2433, 554.765],

    [1847220.974, 416719.1213, 554.452],

    [1847220.226, 416720.9833, 554.359],

    [1847214.943, 416734.1413, 554.92],

    [1847214.266, 416735.8283, 554.966],


])


def load_cross_section_array(site_id: str, pts: np.ndarray, meta: dict) -> CrossSection:
    """Build CrossSection from [Northing, Easting, RL] array."""
    # Convert Northing/Easting to cumulative station distance from left bank
    northings = pts[:, 0]
    eastings  = pts[:, 1]
    elevs     = pts[:, 2]

    dx = np.diff(eastings)
    dy = np.diff(northings)
    dist = np.concatenate([[0.0], np.cumsum(np.hypot(dx, dy))])

    cs = CrossSection(
        site_id=site_id,
        name=meta.get("name", site_id),
        latitude=meta["latitude"],
        longitude=meta["longitude"],
        n_main=meta.get("n_main", 0.031),
        n_flood=meta.get("n_flood", 0.070),
        slope=meta.get("slope", 0.000250),
        datum_m=meta.get("datum_m", 0.0),
        alert_stage_m=meta["alert_stage_m"],
        warning_stage_m=meta["warning_stage_m"],
        danger_stage_m=meta["danger_stage_m"],
        hfl_m=meta["hfl_m"],
    )
    cs.station_m   = dist
    cs.elevation_m = elevs
    return cs


def _wetted_properties(station: np.ndarray, elevation: np.ndarray, wse: float):
    """Compute wetted Area (A) and wetted Perimeter (P) via vectorized trapezoidal integration."""
    if len(station) == 0 or len(elevation) == 0 or wse <= np.min(elevation):
        return 0.0, 0.0

    d = np.maximum(wse - elevation, 0.0)
    dx = np.diff(station)
    dz = np.diff(elevation)
    d1 = d[:-1]
    d2 = d[1:]

    # Wetted Area
    a = float(np.sum(0.5 * (d1 + d2) * dx))

    # Wetted Perimeter
    wet_both = (d1 > 0) & (d2 > 0)
    wet_1 = (d1 > 0) & (d2 <= 0)
    wet_2 = (d1 <= 0) & (d2 > 0)

    hyp = np.hypot(dx, dz)
    p = float(np.sum(hyp[wet_both]))
    if np.any(wet_1):
        frac1 = d1[wet_1] / (d1[wet_1] - d2[wet_1] + 1e-12)
        p += float(np.sum(np.hypot(dx[wet_1] * frac1, dz[wet_1] * frac1)))
    if np.any(wet_2):
        frac2 = d2[wet_2] / (d2[wet_2] - d1[wet_2] + 1e-12)
        p += float(np.sum(np.hypot(dx[wet_2] * (1 - frac2), dz[wet_2] * (1 - frac2))))

    return a, p


# ── Official Maharashtra WRD Government Stage-Discharge Records ──────────────
# Calibrated against field observations at Rajaram K.T. Weir / Shivaji Bridge
# Units: Stage in meters MSL, Discharge in cusecs converted to m³/s (1 cusec = 0.028316847 m³/s)
# 
# Stage (m MSL)   Stage (ft)   Discharge (cusecs)   Discharge (m³/s)
# 533.54          11' 0"       2,825                80.00
# 533.71          11' 7"       3,134                88.74
# 533.99          12' 6"       3,902                110.49
# 535.21          16' 6"       7,684                217.59
# 535.77          18' 4"       9,690                274.39
# 536.41          20' 5"       13,087               370.58
# 538.16          26' 2"       21,650               613.06
# 539.02          29' 0"       28,270               800.52
# 541.50          37' 1"       52,266               1480.00 (Alert Rajaram)
# 542.10          39' 1"       63,567               1800.00 (Alert Shivaji)
# 542.70          41' 1"       77,692               2200.00 (Warning)
# 543.30          43' 0"       94,467               2675.00 (Danger)
# 545.33          49' 8"       135,961              3850.00 (HFL)

# NOTE ON RAJARAM KT WEIR ANCHOR POINTS (Krishna Basin Flood 2019 Vol.1 & survey)
# 529.318 m = actual thalweg/bed from X-Section 29 survey (this is where Q=0 physically)
# 530.18  m = Kolhapur-type (KT) weir crest elevation — flow over weir starts above this
#             In summer the weir pools water to crest level but discharge over weir = 0.
#             In monsoon the weir is fully submerged and acts like a natural reach.
# Therefore both 529.318m and 530.18m correctly have Q=0 as anchors.
RAJARAM_ANCHORS_STAGE = np.array([
    529.318, 530.18,  531.50,  532.70,  533.36,  533.54,  534.15,  535.19,  536.00,
    537.04,  538.29,  539.46,  540.37,  541.51,  542.38,  543.29,  544.39,
    545.38,  546.19,  547.00,  547.33,  549.00
])
RAJARAM_ANCHORS_Q = np.array([
    0.0,     0.0,     3.00,    14.16,   71.25,   80.00,   125.00,  214.25,  305.17,
    448.12,  648.29,  883.87,  965.89,  1219.13, 1690.01, 1776.51, 1857.73,
    1935.00, 2015.31, 2116.14, 2162.93, 2450.00
])


# ── Compound Section Bankfull Constants ──────────────────────────────────────
# Above bankfull, the Panchganga floodplain carries sugarcane & paddy in monsoon.
# Manning's n increases significantly for dense crops on both banks.
# Bankfull levels from survey cross-section geometry inflection points.
SHIVAJI_BANKFULL_RL_M  = 541.60   # m MSL — left bank crest Shivaji (survey inflection)
RAJARAM_BANKFULL_RL_M  = 541.05   # m MSL — right bank top Rajaram (survey inflection)
N_MAIN_CHANNEL   = 0.031   # Main river channel — WRD calibrated (Krishna Basin Flood 2019 Vol.1)
N_FLOODPLAIN     = 0.070   # Overbank floodplain: standing sugarcane/crops — WRD calibrated (Krishna Basin Flood 2019 Vol.1)

# ── Panchganga River Geometry Constants (Krishna Basin Flood 2019 Vol.1) ─────
# Chainage measured from Krishna confluence (increasing upstream).
# X-Section 17: Shivaji Bridge  @ chainage 6+257 m, bed RL 528.670 m MSL
# X-Section 29: Rajaram KT Weir @ chainage 10+115 m, bed RL 529.318 m MSL
SHIVAJI_BED_RL_M    = 528.670   # m MSL (thalweg from survey)
RAJARAM_BED_RL_M    = 529.318   # m MSL (thalweg from survey)
SHIVAJI_LATITUDE    = 16.707274
SHIVAJI_CHAINAGE_M  = 6257.0
RAJARAM_CHAINAGE_M  = 10115.0
SHIVAJI_RAJARAM_DIST_M = RAJARAM_CHAINAGE_M - SHIVAJI_CHAINAGE_M  # 3858 m
RAJARAM_KT_WEIR_CREST_RL_M = 530.18   # m MSL — KT weir crest (anchored from WRD records)
# Bed slope: (529.318 - 528.670) / 3858 = 0.0001680 (survey-measured)
# Report slope for Prayag Chikhali → Rajaram reach: 1:4641 = 0.0002155
# Use survey-measured value as it is computed from the two actual XS bed RLs.
PANCHGANGA_BED_SLOPE = (RAJARAM_BED_RL_M - SHIVAJI_BED_RL_M) / SHIVAJI_RAJARAM_DIST_M  # 1:5954


def build_calibrated_rating_curve(
    cs: CrossSection,
    h_min: Optional[float] = None,
    h_max: Optional[float] = None,
    n_points: int = 200,
) -> pd.DataFrame:
    """
    Builds a strictly monotonic, compound-section hydraulic rating curve.

    Hydraulic regime:
      - Main channel (bed to bankfull):  Manning n = cs.n_main (0.035)
      - Floodplain (above bankfull):     Manning n = cs.n_flood (0.055 sugarcane/paddy)

    Rajaram KT Weir uses PCHIP interpolation on observed WRD gauge anchors for
    high-confidence stage-discharge above the weir crest (530.18 m).  Below the
    weir crest the weir impounds water for irrigation — Q over weir = 0.

    The compound-section Q is calculated via the divided-channel method (DCM):
      Q_total = Q_main + Q_overbank_left + Q_overbank_right
    where each sub-section uses its own n, A, P, R.
    """
    bed_elev = float(np.min(cs.elevation_m)) if len(cs.elevation_m) > 0 else 530.584
    h_min = h_min if h_min is not None else bed_elev
    h_max = h_max if h_max is not None else (cs.hfl_m + 3.0)

    is_rajaram = cs.site_id in ("RAJARAM_BRIDGE", "RAJARAM_WEIR")
    bankfull   = RAJARAM_BANKFULL_RL_M if is_rajaram else SHIVAJI_BANKFULL_RL_M
    n_flood    = cs.n_flood  # Default 0.055 for sugarcane/paddy overbank

    if is_rajaram:
        pchip = PchipInterpolator(RAJARAM_ANCHORS_STAGE, RAJARAM_ANCHORS_Q)
    else:
        pchip = None

    wse_values = np.linspace(h_min, h_max, n_points)
    rows = []

    for wse in wse_values:
        if wse <= bed_elev:
            q = 0.0
            A, P, R = 0.0, 0.0, 0.0
        else:
            A, P = _wetted_properties(cs.station_m, cs.elevation_m, wse)
            R = A / P if P > 1e-4 else 0.0

            if is_rajaram and pchip is not None:
                # PCHIP from WRD anchors — covers full monsoon range accurately
                q = float(np.maximum(0.0, pchip(wse)))
            elif wse > bankfull and len(cs.elevation_m) > 0:
                # Compound section: split at bankfull using Divided Channel Method
                A_main, P_main = _wetted_properties(cs.station_m, cs.elevation_m, bankfull)
                A_over, P_over = _wetted_properties(cs.station_m, cs.elevation_m, wse)
                A_over = max(0.0, A_over - A_main)
                P_over = max(0.0, P_over - P_main)
                # Main channel sub-area (bankfull depth)
                R_main = A_main / P_main if P_main > 1e-4 else 0.0
                q_main = (1.0 / cs.n_main) * A_main * (R_main ** (2/3)) * np.sqrt(cs.slope)
                # Overbank floodplain sub-area (above bankfull — crops, sugarcane)
                R_over = A_over / P_over if P_over > 1e-4 else 0.0
                q_over = (1.0 / n_flood) * A_over * (R_over ** (2/3)) * np.sqrt(cs.slope)
                q = float(q_main + q_over)
            else:
                # Below bankfull: single section Manning
                q = (1.0 / cs.n_main) * A * (R ** (2/3)) * np.sqrt(cs.slope)

        rows.append({
            "stage_m":     round(float(wse), 3),
            "area_m2":     round(float(A), 2),
            "wp_m":        round(float(P), 2),
            "hyd_radius":  round(float(R), 4),
            "q_m3s":       float(q),
        })

    df = pd.DataFrame(rows)
    # Enforce strict monotonicity
    df["q_m3s"] = np.maximum.accumulate(df["q_m3s"].values)
    df["q_m3s"] = df["q_m3s"].round(2)

    return df


def build_rating_curve(
    cs: CrossSection,
    h_min: Optional[float] = None,
    h_max: Optional[float] = None,
    n_points: int = 200,
) -> pd.DataFrame:
    """Wrapper backwards-compatible alias for build_calibrated_rating_curve."""
    return build_calibrated_rating_curve(cs, h_min=h_min, h_max=h_max, n_points=n_points)


def discharge_to_stage(q_m3s: float, rating_df: pd.DataFrame) -> float:
    """Interpolate Water Level Stage (MSL) from discharge Q."""
    q_col = rating_df["q_m3s"].values
    h_col = rating_df["stage_m"].values

    _, idx = np.unique(q_col, return_index=True)
    q_u = q_col[idx]
    h_u = h_col[idx]

    f_interp = interp1d(q_u, h_u, kind="linear", bounds_error=False,
                        fill_value=(h_u[0], h_u[-1]))
    return float(f_interp(max(0.0, float(q_m3s))))


def stage_to_discharge(stage_m: float, rating_df: pd.DataFrame) -> float:
    """Interpolate river discharge Q (m3/s) from water stage elevation (m MSL)."""
    h_col = rating_df["stage_m"].values
    q_col = rating_df["q_m3s"].values

    _, idx = np.unique(h_col, return_index=True)
    h_u = h_col[idx]
    q_u = q_col[idx]

    f_interp = interp1d(h_u, q_u, kind="linear", bounds_error=False,
                        fill_value=(q_u[0], q_u[-1]))
    return float(f_interp(float(stage_m)))


def classify_alert(stage_m: float, site_id: str = "SHIVAJI_BRIDGE") -> str:
    """Classifies CWC alert level based on site thresholds."""
    if site_id in ("RAJARAM_WEIR", "RAJARAM_BRIDGE"):
        if stage_m >= 545.33: return "HFL_EXCEEDED"
        if stage_m >= 544.00: return "EXTREME"
        if stage_m >= 543.30: return "DANGER"
        if stage_m >= 542.07: return "WARNING"
        if stage_m >= 541.50: return "ALERT"
        return "NORMAL"
    else:
        if stage_m >= 545.33: return "HFL_EXCEEDED"
        if stage_m >= 544.00: return "EXTREME"
        if stage_m >= 543.30: return "DANGER"
        if stage_m >= 542.70: return "WARNING"
        if stage_m >= 542.10: return "ALERT"
        return "NORMAL"


def store_rating_curve_db(conn, cs: CrossSection, rating_df: pd.DataFrame):
    """Persist rating curves into Supabase/Postgres."""
    with conn.cursor() as cur:
        # Upsert bridge site
        cur.execute("""
            INSERT INTO bridge_sites
                (site_id, site_name, latitude, longitude,
                 alert_stage_m, warning_stage_m, danger_stage_m, hfl_m,
                 manning_n_main, manning_n_flood, bed_slope, datum_m)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (site_id) DO UPDATE SET
                alert_stage_m   = EXCLUDED.alert_stage_m,
                warning_stage_m = EXCLUDED.warning_stage_m,
                danger_stage_m  = EXCLUDED.danger_stage_m,
                hfl_m           = EXCLUDED.hfl_m,
                updated_at      = NOW();
        """, (cs.site_id, cs.name, cs.latitude, cs.longitude,
              cs.alert_stage_m, cs.warning_stage_m, cs.danger_stage_m, cs.hfl_m,
              cs.n_main, cs.n_flood, cs.slope, cs.datum_m))

        # Clear and insert rating curve points
        cur.execute("DELETE FROM rating_curves WHERE site_id=%s;", (cs.site_id,))
        for _, row in rating_df.iterrows():
            cur.execute("""
                INSERT INTO rating_curves (site_id, stage_m, discharge_m3s, area_m2, wp_m, hyd_radius)
                VALUES (%s,%s,%s,%s,%s,%s);
            """, (cs.site_id, row.stage_m, row.q_m3s, row.area_m2, row.wp_m, row.hyd_radius))

    conn.commit()
    log.info("Rating curve stored in DB for %s (%d points)", cs.site_id, len(rating_df))


_SHIVAJI_RC_CACHE = None
_RAJARAM_RC_CACHE = None

def get_shivaji_rating_curve() -> pd.DataFrame:
    """Build and cache Shivaji Bridge calibrated rating curve.
    Compound section: n_main=0.035 (channel), n_flood=0.055 (sugarcane/paddy overbank).
    Bankfull level: SHIVAJI_BANKFULL_RL_M (541.60 m MSL, survey inflection).
    Slope: 1:4641 from report (Prayag Chikhali → Rajaram reach).
    """
    global _SHIVAJI_RC_CACHE
    if _SHIVAJI_RC_CACHE is None:
        cs = load_cross_section_array("SHIVAJI_BRIDGE", SHIVAJI_SURVEY, {
            "name": "Chhatrapati Shivaji Maharaj Bridge (Panchganga Ghat)",
            "latitude": 16.707274,
            "longitude": 74.217482,
            "slope": 0.00021547,  # 1:4641 (Prayag Chikhali to Rajaram, Krishna Basin 2019 Vol.1)
            "n_main": 0.031,      # Main channel — WRD calibrated (Krishna Basin Flood 2019 Vol.1)
            "n_flood": 0.070,     # Overbank: standing sugarcane/crops — WRD calibrated (Krishna Basin Flood 2019 Vol.1)
            "alert_stage_m": 542.10,
            "warning_stage_m": 542.70,
            "danger_stage_m": 543.30,
            "extreme_stage_m": 544.00,
            "hfl_m": 545.33,
        })
        _SHIVAJI_RC_CACHE = build_calibrated_rating_curve(cs, n_points=300)
    return _SHIVAJI_RC_CACHE


def get_rajaram_rating_curve() -> pd.DataFrame:
    """Build and cache Rajaram K.T. Weir calibrated rating curve.
    Uses PCHIP interpolation on official WRD Maharashtra gauge observations.
    KT Weir crest at 530.18 m MSL — impounds water for irrigation in summer.
    Compound section: n_main=0.035 (channel), n_flood=0.055 (sugarcane overbank).
    Slope: 1:7700 from report (Rajaram to Shirol K.T. Weir reach).
    """
    global _RAJARAM_RC_CACHE
    if _RAJARAM_RC_CACHE is None:
        cs = load_cross_section_array("RAJARAM_BRIDGE", RAJARAM_SURVEY, {
            "name": "Rajaram K.T. Weir (Kasba Bawada)",
            "latitude": 16.736083,
            "longitude": 74.235250,
            "slope": 0.00012987,  # 1:7700 (Rajaram to Shirol, Krishna Basin 2019 Vol.1)
            "n_main": 0.031,      # Main channel — WRD calibrated (Krishna Basin Flood 2019 Vol.1)
            "n_flood": 0.070,     # Overbank: standing sugarcane/crops — WRD calibrated (Krishna Basin Flood 2019 Vol.1)
            "alert_stage_m": 541.50,
            "warning_stage_m": 542.07,
            "danger_stage_m": 543.30,
            "extreme_stage_m": 544.00,
            "hfl_m": 545.33,
        })
        _RAJARAM_RC_CACHE = build_calibrated_rating_curve(cs, n_points=300)
    return _RAJARAM_RC_CACHE


RAJARAM_SURVEY = np.array([
    [1850496.548, 418236.5185, 541.344],
    [1850496.505, 418236.9015, 541.162],
    [1850496.294, 418238.7535, 541.211],
    [1850495.905, 418242.1685, 541.248],
    [1850495.661, 418244.3065, 541.258],
    [1850495.402, 418246.5855, 541.259],
    [1850495.134, 418248.9385, 541.235],
    [1850494.878, 418251.1835, 541.17],
    [1850494.618, 418253.4665, 541.162],
    [1850494.356, 418255.7695, 541.126],
    [1850494.021, 418258.7045, 541.136],
    [1850493.758, 418261.0175, 541.057],
    [1850493.476, 418263.4875, 541.062],
    [1850493.311, 418264.9395, 541.193],
    [1850493.034, 418267.3705, 541.055],
    [1850492.88, 418268.7245, 540.96],
    [1850492.746, 418269.8955, 540.902],
    [1850492.583, 418271.3345, 540.958],
    [1850492.345, 418273.4235, 540.983],
    [1850491.735, 418278.7725, 540.715],
    [1850491.248, 418283.0465, 540.817],
    [1850490.523, 418289.4175, 540.988],
    [1850489.704, 418296.6065, 540.917],
    [1850487.509, 418315.8755, 540.364],
    [1850484.086, 418345.9235, 538.955],
    [1850483.915, 418347.4235, 538.237],
    [1850483.654, 418349.7155, 537.33],
    [1850483.371, 418352.1985, 536.766],
    [1850483.055, 418354.9775, 536.264],
    [1850482.729, 418357.8345, 536.083],
    [1850482.424, 418360.5185, 536.023],
    [1850481.936, 418364.7965, 536.393],
    [1850481.721, 418366.6905, 536.47],
    [1850481.471, 418368.8805, 536.628],
    [1850481.066, 418372.4355, 536.233],
    [1850480.858, 418374.2655, 536.468],
    [1850480.712, 418375.5455, 536.573],
    [1850480.42, 418378.1055, 536.991],
    [1850479.949, 418382.2415, 536.638],
    [1850479.747, 418384.0175, 536.468],
    [1850479.57, 418385.5725, 536.894],
    [1850479.212, 418388.7165, 536.739],
    [1850478.899, 418391.4585, 536.529],
    [1850478.628, 418393.8385, 536.357],
    [1850478.411, 418395.7455, 536.362],
    [1850478.05, 418398.9155, 536.338],
    [1850477.843, 418400.7355, 536.554],
    [1850477.549, 418403.3165, 536.376],
    [1850477.264, 418405.8115, 536.417],
    [1850477.024, 418407.9245, 536.542],
    [1850476.817, 418409.7365, 536.712],
    [1850476.583, 418411.7905, 536.542],
    [1850476.378, 418413.5915, 536.592],
    [1850476.105, 418415.9915, 536.43],
    [1850476.07, 418416.2985, 535.693],
    [1850475.985, 418417.0465, 534.72],
    [1850475.852, 418418.2095, 533.996],
    [1850475.801, 418418.6605, 533.783],
    [1850475.761, 418419.0085, 533.333],
    [1850475.606, 418420.3735, 532.946],
    [1850475.455, 418421.6935, 532.634],
    [1850475.328, 418422.8105, 532.371],
    [1850475.23, 418423.6685, 532.168],
    [1850475.185, 418424.0675, 532.096],
    [1850475.085, 418424.9475, 531.709],
    [1850474.935, 418426.2565, 531.469],
    [1850474.754, 418427.8475, 531.351],
    [1850474.557, 418429.5835, 531.328],
    [1850474.362, 418431.2925, 531.27],
    [1850474.15, 418433.1515, 531.237],
    [1850473.912, 418435.2405, 531.303],
    [1850473.664, 418437.4235, 531.306],
    [1850473.417, 418439.5845, 531.293],
    [1850473.175, 418441.7095, 531.316],
    [1850472.945, 418443.7265, 531.339],
    [1850472.723, 418445.6765, 531.394],
    [1850472.497, 418447.6645, 531.402],
    [1850472.259, 418449.7495, 531.386],
    [1850472.021, 418451.8455, 531.413],
    [1850471.782, 418453.9375, 531.433],
    [1850471.557, 418455.9135, 531.445],
    [1850471.35, 418457.7295, 531.353],
    [1850471.134, 418459.6255, 531.318],
    [1850470.906, 418461.6295, 531.298],
    [1850470.671, 418463.6915, 531.234],
    [1850470.431, 418465.8015, 531.16],
    [1850470.185, 418467.9605, 531.062],
    [1850469.936, 418470.1475, 530.895],
    [1850469.683, 418472.3635, 530.775],
    [1850469.435, 418474.5405, 530.613],
    [1850469.188, 418476.7155, 530.43],
    [1850468.941, 418478.8845, 530.205],
    [1850468.693, 418481.0575, 529.861],
    [1850468.446, 418483.2235, 529.65],
    [1850468.199, 418485.3975, 529.428],
    [1850467.949, 418487.5865, 529.318],
    [1850467.697, 418489.8035, 529.592],
    [1850467.446, 418492.0025, 529.824],
    [1850467.199, 418494.1725, 530.187],
    [1850466.952, 418496.3415, 530.172],
    [1850466.704, 418498.5195, 530.294],
    [1850466.455, 418500.7045, 530.271],
    [1850466.205, 418502.8965, 530.348],
    [1850465.957, 418505.0755, 530.354],
    [1850465.716, 418507.1915, 530.544],
    [1850465.482, 418509.2495, 530.773],
    [1850465.25, 418511.2805, 530.921],
    [1850465.025, 418513.2625, 531.109],
    [1850464.805, 418515.1915, 531.35],
    [1850464.602, 418516.9715, 531.455],
    [1850464.422, 418518.5505, 531.582],
    [1850464.264, 418519.9385, 531.763],
    [1850464.124, 418521.1685, 531.974],
    [1850464.001, 418522.2485, 532.185],
    [1850463.891, 418523.2105, 532.384],
    [1850463.798, 418524.0335, 532.393],
    [1850463.716, 418524.7475, 532.388],
    [1850463.645, 418525.3705, 532.326],
    [1850463.584, 418525.9125, 532.344],
    [1850463.528, 418526.4015, 532.325],
    [1850463.478, 418526.8385, 532.322],
    [1850463.434, 418527.2275, 532.322],
    [1850463.413, 418527.4135, 532.302],
    [1850463.325, 418528.1815, 532.418],
    [1850463.325, 418528.1815, 532.354],
    [1850463.304, 418528.3655, 532.426],
    [1850463.276, 418528.6175, 532.468],
    [1850463.255, 418528.7995, 532.481],
    [1850463.245, 418528.8895, 532.512],
    [1850463.188, 418529.3885, 532.724],
    [1850463.046, 418530.6335, 533.27],
    [1850462.419, 418536.1385, 533.532],
    [1850462.366, 418536.6055, 533.914],
    [1850462.359, 418536.6675, 533.82],
    [1850462.327, 418536.9405, 534.154],
    [1850462.093, 418539.0035, 534.15],
    [1850461.908, 418540.6245, 534.098],
    [1850461.535, 418543.8945, 534.309],
    [1850461.179, 418547.0205, 534.37],
    [1850461.125, 418547.4935, 534.962],
    [1850460.997, 418548.6205, 534.886],
    [1850460.937, 418549.1485, 534.974],
    [1850460.922, 418549.2775, 536.309],
    [1850460.712, 418551.1265, 536.808],
    [1850460.556, 418552.4935, 537.28],
    [1850460.314, 418554.6185, 537.403],
    [1850459.971, 418557.6285, 537.488],
    [1850459.76, 418559.4765, 538.411],
    [1850459.496, 418561.7955, 539.595],
    [1850459.455, 418562.1575, 539.558],
    [1850459.135, 418564.9675, 539.635],
    [1850458.863, 418567.3585, 539.414],
    [1850458.845, 418567.5165, 539.429],
    [1850458.57, 418569.9255, 539.432],
    [1850458.472, 418570.7905, 539.465],
    [1850458.197, 418573.2015, 539.705],
    [1850458.075, 418574.2705, 539.801],
    [1850457.733, 418577.2735, 540.378],
    [1850457.229, 418581.6975, 540.643],
    [1850456.77, 418585.7255, 541.337],
    [1850456.229, 418590.4745, 541.977],
    [1850455.865, 418593.6735, 542.504],
    [1850455.358, 418598.1265, 543.069],
    [1850455.035, 418600.9635, 543.749],
    [1850454.738, 418603.5715, 544.385],
    [1850454.283, 418607.5665, 545.085],
    [1850453.84, 418611.4505, 545.76],
    [1850453.413, 418615.1995, 546.435],
    [1850452.998, 418618.8405, 547.052],
    [1850452.687, 418621.5755, 547.259],
    [1850452.197, 418625.8745, 547.974],
    [1850451.72, 418630.0605, 548.527],
    [1850451.265, 418634.0555, 549.071],
    [1850450.816, 418638.0025, 549.702],
    [1850450.386, 418641.7765, 550.307],
    [1850449.917, 418645.8865, 550.392],
    [1850449.547, 418649.1365, 550.493],
    [1850449.033, 418653.6485, 550.528],
    [1850448.647, 418657.0385, 550.586],
    [1850448.647, 418657.0385, 550.586],
    [1850447.935, 418663.2895, 550.493],
    [1850447.671, 418665.6055, 550.123],
    [1850447.45, 418667.5465, 549.395],
    [1850447.221, 418669.5545, 549.713],
    [1850446.963, 418671.8215, 549.487],
    [1850446.454, 418676.2945, 549.271],
    [1850446.211, 418678.4245, 549.04],
    [1850445.816, 418681.8965, 549.049],
    [1850445.441, 418685.1875, 548.872],
    [1850445.196, 418687.3395, 548.778],
    [1850444.945, 418689.5425, 548.748],
    [1850444.696, 418691.7245, 548.512],
    [1850444.366, 418694.6205, 548.685],

])



def build_all_rating_curves():
    """Builds and returns rating curves for both bridge sites.
    NOTE: This uses the SAME canonical slopes as get_shivaji_rating_curve()
    and get_rajaram_rating_curve() to ensure DB sync produces identical curves
    to what the runtime pipeline uses.
    """
    cs_s = load_cross_section_array("SHIVAJI_BRIDGE", SHIVAJI_SURVEY, {
        "name": "Chhatrapati Shivaji Maharaj Bridge (Panchganga Ghat)",
        "latitude": 16.707274, "longitude": 74.217482,
        "slope": 0.00021547,  # 1:4641 — MUST match get_shivaji_rating_curve()
        "n_main": 0.031, "n_flood": 0.070,  # WRD calibrated — Krishna Basin Flood 2019 Vol.1
        "alert_stage_m": 542.10, "warning_stage_m": 542.70, "danger_stage_m": 543.30,
        "extreme_stage_m": 544.00, "hfl_m": 545.33,
    })
    cs_r = load_cross_section_array("RAJARAM_BRIDGE", RAJARAM_SURVEY, {
        "name": "Rajaram K.T. Weir (Kasba Bawada)",
        "latitude": 16.736083, "longitude": 74.235250,
        "slope": 0.00012987,  # 1:7700 — MUST match get_rajaram_rating_curve()
        "n_main": 0.031, "n_flood": 0.070,  # WRD calibrated — Krishna Basin Flood 2019 Vol.1
        "alert_stage_m": 541.50, "warning_stage_m": 542.07, "danger_stage_m": 543.30,
        "extreme_stage_m": 544.00, "hfl_m": 545.33,
    })
    return {
        "SHIVAJI_BRIDGE": (cs_s, get_shivaji_rating_curve()),
        "RAJARAM_BRIDGE": (cs_r, get_rajaram_rating_curve()),
    }


def convert_discharge_to_stage_manning(q_m3s: float, site_id: str = "SHIVAJI_BRIDGE") -> float:
    """Convert discharge Q (m³/s) → stage (m MSL) using site-specific calibrated rating curve."""
    if site_id in ("RAJARAM_WEIR", "RAJARAM_BRIDGE"):
        df_rc = get_rajaram_rating_curve()
    else:
        df_rc = get_shivaji_rating_curve()
    stage = discharge_to_stage(max(float(q_m3s), 0.0), df_rc)
    return float(round(stage, 2))


def convert_stage_to_discharge_manning(stage_m: float, site_id: str = "SHIVAJI_BRIDGE") -> float:
    """Convert stage (m MSL) → discharge Q (m³/s) using site-specific calibrated rating curve."""
    if site_id in ("RAJARAM_WEIR", "RAJARAM_BRIDGE"):
        df_rc = get_rajaram_rating_curve()
    else:
        df_rc = get_shivaji_rating_curve()
    q = stage_to_discharge(float(stage_m), df_rc)
    return float(round(max(0.0, q), 1))


def infer_rajaram_stage_from_shivaji(shivaji_stage_m: float, q_m3s: Optional[float] = None) -> float:
    """Infer Rajaram K.T. Weir water surface elevation from Shivaji Bridge IoT sensor reading.

    Spatial relationship (from survey & Krishna Basin Flood 2019 Vol.1):
      - Rajaram KT Weir is UPSTREAM of Shivaji Bridge (higher chainage from confluence).
      - Chainage:  Rajaram @ 10+115 m,  Shivaji @ 6+257 m,  Distance = 3858 m.
      - Bed RLs:   Rajaram = 529.318 m MSL,  Shivaji = 528.670 m MSL.
      - Bed gradient: Δbed = 0.648 m over 3858 m (slope ≈ 1:5954 from survey).

    Stage transfer method (Gradually Varied Flow approximation):
      Under uniform/normal flow:
          WSE_Rajaram ≈ WSE_Shivaji + bed_drop_between_sites
      KT Weir backwater correction (summer, low Q):
          The KT weir impounds water above its crest (530.18 m) for irrigation.
          When Q < ~100 m³/s, weir backwater raises Rajaram stage by an additional
          0.3–0.9 m above the uniform-flow estimate.

    Args:
        shivaji_stage_m: Live observed water level at Shivaji Bridge sensor (m MSL)
        q_m3s:           Estimated discharge (m³/s) — used for KT weir correction.
                         If None, no backwater correction applied.

    Returns:
        Estimated water surface elevation at Rajaram KT Weir (m MSL)
    """
    bed_diff = RAJARAM_BED_RL_M - SHIVAJI_BED_RL_M  # = 0.648 m
    rajaram_stage = shivaji_stage_m + bed_diff

    # KT Weir backwater correction: in low-flow / dry season the weir ponds the reach.
    # When stage at Rajaram is near the weir crest (530.18 m) and Q is low,
    # add a physically-calibrated backwater head above uniform-flow estimate.
    if q_m3s is not None:
        weir_crest = RAJARAM_KT_WEIR_CREST_RL_M  # 530.18 m
        if q_m3s < 100.0 and rajaram_stage < weir_crest + 2.0:
            # Backwater correction: decays from 0.8m at zero flow to 0m at 100 m3/s
            backwater_m = 0.8 * max(0.0, 1.0 - q_m3s / 100.0)
            rajaram_stage += backwater_m

    return round(float(rajaram_stage), 3)


def run_pipeline():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    curves = build_all_rating_curves()
    for site_id, (cs, df) in curves.items():
        log.info("%s Rating Curve: Stage %.2f-%.2f m | Q 0-%.1f m3/s",
                 site_id, df.stage_m.min(), df.stage_m.max(), df.q_m3s.max())

    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or os.getenv("SUPABASE_DATABASE_URL")
    if db_url:
        try:
            from src.db.connection import get_db_connection
            conn = get_db_connection(db_url)
            if conn:
                for site_id, (cs, df) in curves.items():
                    store_rating_curve_db(conn, cs, df)
                conn.close()
                log.info("Database sync completed successfully for both bridge sites!")
            else:
                log.warning("No database connection established. Skipping rating curve DB sync.")
        except Exception as e:
            log.error("Database sync failed: %s", e)
    else:
        log.warning("No DATABASE_URL found. Rating curves calculated in-memory.")


if __name__ == "__main__":
    run_pipeline()


