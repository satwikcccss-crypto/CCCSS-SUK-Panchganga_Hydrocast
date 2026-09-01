"""
Stage-Discharge Converter
==========================
Builds rating curves from surveyed cross-section data for bridge gauge sites.
Uses Manning's equation with compound cross-section (main channel + floodplains).

Input  : CSV of surveyed points per cross-section (Easting, Northing, Elevation)
         + Manning's n, bed slope S0, bank-full stage
Output : Rating curve table (H vs Q) stored in Postgres
         Flood stage classification per CWC standards

Cross-section CSV format:
  easting,northing,elevation_m
  (points ordered left bank → right bank by easting)

CWC Alert Levels (set per bridge in bridge_sites table):
  alert   → first threshold above base flow
  warning → moderate flood
  danger  → danger level
  hfl     → Highest Flood Level (historical max)
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

log = logging.getLogger(__name__)


# ── Cross-section data model ──────────────────────────────────────────────────

@dataclass
class CrossSection:
    site_id:    str          # e.g. 'SHIVAJI_BRIDGE'
    name:       str
    latitude:   float
    longitude:  float
    n_main:     float = 0.035    # Manning's n — main channel
    n_flood:    float = 0.070    # Manning's n — floodplain
    slope:      float = 0.0002   # bed slope m/m (measure from DEM or survey)
    datum_m:    float = 0.0      # datum offset (survey elevation of gauge zero)
    # CWC alert levels in metres above datum
    alert_stage_m:   float = 3.0
    warning_stage_m: float = 5.0
    danger_stage_m:  float = 6.5
    hfl_m:           float = 8.2     # Highest Flood Level ever recorded
    # Loaded survey points
    station_m:  np.ndarray = field(default_factory=lambda: np.array([]))  # lateral distance
    elevation_m: np.ndarray = field(default_factory=lambda: np.array([]))


def load_cross_section_from_csv(site_id: str, csv_path: Path, meta: dict) -> CrossSection:
    """
    Load surveyed points from CSV and convert Easting/Northing to lateral station.
    
    meta keys: name, latitude, longitude, n_main, n_flood, slope, datum_m,
               alert_stage_m, warning_stage_m, danger_stage_m, hfl_m
    """
    df = pd.read_csv(csv_path, names=["easting", "northing", "elevation_m"])
    df = df.dropna().sort_values("easting").reset_index(drop=True)

    # Convert (E, N) to lateral station distance from left bank
    dx = np.diff(df.easting.values)
    dy = np.diff(df.northing.values)
    dist = np.concatenate([[0.0], np.cumsum(np.hypot(dx, dy))])

    cs = CrossSection(
        site_id=site_id,
        name=meta.get("name", site_id),
        latitude=meta["latitude"],
        longitude=meta["longitude"],
        n_main=meta.get("n_main", 0.035),
        n_flood=meta.get("n_flood", 0.070),
        slope=meta["slope"],
        datum_m=meta.get("datum_m", 0.0),
        alert_stage_m=meta["alert_stage_m"],
        warning_stage_m=meta["warning_stage_m"],
        danger_stage_m=meta["danger_stage_m"],
        hfl_m=meta["hfl_m"],
    )
    cs.station_m   = dist
    cs.elevation_m = df.elevation_m.values
    return cs


def _wetted_properties(station: np.ndarray, elevation: np.ndarray, wse: float):
    """
    Compute wetted area (A) and wetted perimeter (P) for a given
    Water Surface Elevation (WSE) using the trapezoidal rule.

    Returns (A, P) or (0, 0) if WSE is below the channel bed.
    """
    if wse <= np.min(elevation):
        return 0.0, 0.0

    # Depth at each survey point
    depth = np.maximum(wse - elevation, 0.0)

    A = 0.0
    P = 0.0
    for i in range(len(station) - 1):
        d1, d2 = depth[i], depth[i+1]
        dx = station[i+1] - station[i]
        dz = elevation[i+1] - elevation[i]

        if d1 <= 0 and d2 <= 0:
            continue

        # Trapezoidal area for this panel
        A += 0.5 * (d1 + d2) * dx

        # Wetted perimeter: actual slant length between wet points
        if d1 > 0 and d2 > 0:
            P += np.hypot(dx, dz)
        elif d1 > 0:
            # Interpolate water surface intersection
            frac = d1 / (d1 - d2 + 1e-12)  # fraction where depth = 0
            P += np.hypot(dx * frac, dz * frac)
        else:
            frac = d2 / (d2 - d1 + 1e-12)
            P += np.hypot(dx * (1 - frac), dz * (1 - frac))

    return A, P


def build_rating_curve(
    cs: CrossSection,
    h_min: Optional[float] = None,
    h_max: Optional[float] = None,
    n_points: int = 100,
) -> pd.DataFrame:
    """
    Compute Q (m³/s) for a range of water surface elevations using Manning's equation:
        Q = (1/n) * A * (A/P)^(2/3) * S^(1/2)

    Returns DataFrame columns: [stage_m, elevation_m, area_m2, wp_m, hyd_radius, q_m3s]
    stage_m = elevation above cs.datum_m (gauge height)
    """
    bed_elev = np.min(cs.elevation_m)
    h_min = h_min if h_min is not None else 0.0
    h_max = h_max if h_max is not None else (cs.hfl_m + 1.5)

    # WSE range from bed level
    wse_values = np.linspace(bed_elev + h_min, bed_elev + h_max, n_points)
    rows = []

    for wse in wse_values:
        A, P = _wetted_properties(cs.station_m, cs.elevation_m, wse)
        if A < 1e-4 or P < 1e-4:
            q = 0.0
            R = 0.0
        else:
            R = A / P                                           # hydraulic radius
            q = (1.0 / cs.n_main) * A * (R ** (2/3)) * (cs.slope ** 0.5)

        stage = wse - bed_elev - cs.datum_m                    # gauge height
        rows.append({
            "stage_m":     round(stage, 3),
            "wse_m":       round(wse, 3),
            "area_m2":     round(A, 2),
            "wp_m":        round(P, 2),
            "hyd_radius":  round(R, 4),
            "q_m3s":       round(q, 2),
        })

    df = pd.DataFrame(rows)
    log.info(
        "Rating curve for %s: H=%.2f–%.2f m | Q=0–%.1f m³/s",
        cs.site_id, df.stage_m.min(), df.stage_m.max(), df.q_m3s.max(),
    )
    return df


def discharge_to_stage(q_m3s: float | np.ndarray, rating_df: pd.DataFrame) -> float | np.ndarray:
    """
    Interpolate gauge height (stage) from discharge using the rating curve.
    Clamps extrapolation to curve bounds.
    """
    q_col = rating_df["q_m3s"].values
    h_col = rating_df["stage_m"].values

    # Remove duplicates for monotone interpolation
    _, idx = np.unique(q_col, return_index=True)
    q_u = q_col[idx]
    h_u = h_col[idx]

    f_interp = interp1d(q_u, h_u, kind="linear", bounds_error=False,
                        fill_value=(h_u[0], h_u[-1]))
    return float(f_interp(q_m3s)) if np.isscalar(q_m3s) else f_interp(q_m3s)


def classify_alert(stage_m: float, cs: CrossSection) -> dict:
    """
    Returns flood alert classification per CWC standards.
    """
    if stage_m >= cs.hfl_m:
        level, color, msg = "HFL_EXCEEDED", "purple", f"Above HFL ({cs.hfl_m}m). Extreme flood."
    elif stage_m >= cs.danger_stage_m:
        level, color, msg = "DANGER", "red", f"Above Danger Level ({cs.danger_stage_m}m). Evacuate."
    elif stage_m >= cs.warning_stage_m:
        level, color, msg = "WARNING", "orange", f"Above Warning Level ({cs.warning_stage_m}m). Alert agencies."
    elif stage_m >= cs.alert_stage_m:
        level, color, msg = "ALERT", "yellow", f"Above Alert Level ({cs.alert_stage_m}m). Monitor closely."
    else:
        level, color, msg = "NORMAL", "green", "Below alert level. Normal flow."

    return {
        "level":   level,
        "color":   color,
        "message": msg,
        "stage_m": round(stage_m, 2),
        "alert_m":   cs.alert_stage_m,
        "warning_m": cs.warning_stage_m,
        "danger_m":  cs.danger_stage_m,
        "hfl_m":     cs.hfl_m,
    }


def compute_arrival_time(
    outlet_hydrograph: list[tuple],   # [(datetime, q_m3s), ...]
    rating_df: pd.DataFrame,
    cs: CrossSection,
    threshold_stage: Optional[float] = None,
) -> Optional[dict]:
    """
    Find the earliest time when stage at a bridge crosses the alert threshold.
    This assumes travel time from outlet to bridge is pre-computed and added
    to the timestamps (call this after adding travel_time_hours offset).

    threshold_stage: default = cs.alert_stage_m
    """
    thresh = threshold_stage if threshold_stage is not None else cs.alert_stage_m

    for ts, q in outlet_hydrograph:
        h = discharge_to_stage(q, rating_df)
        if h >= thresh:
            status = classify_alert(h, cs)
            return {
                "site":         cs.site_id,
                "arrival_time": ts.isoformat(),
                "stage_m":      round(h, 2),
                "discharge_m3s": round(q, 1),
                "alert":        status,
            }
    return None    # does not exceed threshold in 90-hr window


def store_rating_curve(conn, cs: CrossSection, rating_df: pd.DataFrame):
    """Persist rating curve to Postgres table rating_curves."""
    with conn.cursor() as cur:
        # Upsert header
        cur.execute("""
            INSERT INTO bridge_sites
                (site_id, site_name, latitude, longitude,
                 alert_stage_m, warning_stage_m, danger_stage_m, hfl_m,
                 manning_n_main, manning_n_flood, bed_slope)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (site_id) DO UPDATE SET
                alert_stage_m   = EXCLUDED.alert_stage_m,
                warning_stage_m = EXCLUDED.warning_stage_m,
                danger_stage_m  = EXCLUDED.danger_stage_m,
                hfl_m           = EXCLUDED.hfl_m,
                updated_at      = NOW()
        """, (cs.site_id, cs.name, cs.latitude, cs.longitude,
              cs.alert_stage_m, cs.warning_stage_m, cs.danger_stage_m, cs.hfl_m,
              cs.n_main, cs.n_flood, cs.slope))

        # Upsert rating curve rows
        cur.execute("DELETE FROM rating_curves WHERE site_id=%s", (cs.site_id,))
        for _, row in rating_df.iterrows():
            cur.execute("""
                INSERT INTO rating_curves (site_id, stage_m, discharge_m3s, area_m2, wp_m, hyd_radius)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (cs.site_id, row.stage_m, row.q_m3s, row.area_m2, row.wp_m, row.hyd_radius))

    conn.commit()
    log.info("Rating curve stored for %s (%d points)", cs.site_id, len(rating_df))


# ── Bridge site definitions (fill from survey data) ───────────────────────────
# Replace CSV paths and meta with your actual survey data

BRIDGE_SITES = {
    "SHIVAJI_BRIDGE": {
        "csv": Path("data/surveys/shivaji_bridge_xsection.csv"),
        "meta": {
            "name":            "Shivaji Bridge",
            "latitude":        17.6868,         # fill actual
            "longitude":       74.0183,         # fill actual
            "slope":           0.00025,         # m/m — from survey/DEM
            "n_main":          0.030,
            "n_flood":         0.065,
            "datum_m":         0.0,
            "alert_stage_m":   3.5,             # CWC alert level (m above datum)
            "warning_stage_m": 5.5,
            "danger_stage_m":  6.8,
            "hfl_m":           8.5,
        },
    },
    "RAJARAM_BRIDGE": {
        "csv": Path("data/surveys/rajaram_bridge_xsection.csv"),
        "meta": {
            "name":            "Rajaram Bridge",
            "latitude":        17.6512,
            "longitude":       74.0041,
            "slope":           0.00020,
            "n_main":          0.032,
            "n_flood":         0.070,
            "datum_m":         0.0,
            "alert_stage_m":   4.0,
            "warning_stage_m": 6.0,
            "danger_stage_m":  7.2,
            "hfl_m":           9.1,
        },
    },
}


def build_all_rating_curves() -> dict[str, tuple[CrossSection, pd.DataFrame]]:
    """Load all bridge cross-sections and build rating curves."""
    results = {}
    for site_id, cfg in BRIDGE_SITES.items():
        if not cfg["csv"].exists():
            log.warning("Cross-section CSV missing: %s — skipping %s", cfg["csv"], site_id)
            continue
        cs = load_cross_section_from_csv(site_id, cfg["csv"], cfg["meta"])
        df = build_rating_curve(cs)
        results[site_id] = (cs, df)
    return results


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

    # Demo with synthetic cross-section
    station = np.array([0, 10, 25, 40, 80, 120, 150, 165, 175])
    elev    = np.array([8.5, 6.0, 2.5, 1.0, 0.8, 1.2, 2.8, 6.2, 8.8])

    cs_demo = CrossSection(
        site_id="DEMO", name="Demo Section",
        latitude=17.68, longitude=74.02,
        slope=0.00025, n_main=0.030, n_flood=0.065,
        alert_stage_m=3.5, warning_stage_m=5.5, danger_stage_m=6.8, hfl_m=8.5,
    )
    cs_demo.station_m   = station
    cs_demo.elevation_m = elev

    df = build_rating_curve(cs_demo, h_max=9.0)
    print(df.to_string(index=False))

    # Test Q → H conversion
    for q_test in [50, 200, 500, 850, 1200]:
        h = discharge_to_stage(q_test, df)
        alert = classify_alert(h, cs_demo)
        print(f"Q={q_test:5.0f} m³/s → H={h:.2f}m [{alert['level']}]")
