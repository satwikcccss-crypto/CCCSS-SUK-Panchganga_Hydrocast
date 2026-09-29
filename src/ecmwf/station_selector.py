"""
Dynamic Subbasin Station Selector & Spatial Fallback Engine
============================================================
SINGLE CANONICAL station-selector module for HydroCast.

Two ingestion paths share this one file (no more duplicate selectors):

1. REGISTRY PATH (production pipeline, pure-Python, no DB):
   STATION_REGISTRY + select_active_subbasin_gages — evaluates rainfall volume
   across Primary & Alternate stations per Panchganga subbasin (S1 to S9),
   selecting the maximum-rainfall station for conservative flood forecasting.
   Ungauged subbasins use spatial nearest-neighbour assignment.

2. ORCHESTRATOR PATH (Postgres + ECMWF grid):
   load_stations / select_stations / store_selection — used by
   src/orchestrator.py when a live Postgres/PostGIS database is available.
   Heavy DB dependencies (psycopg2, xarray, scipy) are imported lazily inside
   the functions so the production registry path stays dependency-light.

The SubbasinRainfall result container is shared by both paths and by the
canonical DSS writer (src/dss/writer.py).
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


@dataclass
class RainStation:
    station_id: str
    name: str
    subbasin: str
    lon: float
    lat: float
    is_primary: bool = True
    elevation_m: float = 600.0


@dataclass
class SubbasinRainfall:
    """Per-subbasin selection result — 90h hyetograph of the governing station."""
    subbasin_id: str
    selected_station: str
    cumulative_mm: float
    hyetograph: List[float]
    all_stations: Dict[str, float]


# ── Subbasin Catchment Areas (Official GIS Delineation) ──────────────────────
SUBBASIN_AREAS_KM2: Dict[str, float] = {
    "S1": 86.213,   # Karveer Subbasin
    "S2": 153.77,   # Sangarul Subbasin
    "S3": 261.32,   # Kotoli Subbasin
    "S4": 262.00,   # Karanjphen Subbasin
    "S5": 106.39,   # Padasali Subbasin
    "S6": 227.72,   # Gaganbawda Subbasin
    "S7": 195.39,   # Garivade Subbasin
    "S8": 177.44,   # Beed Subbasin
    "S9": 366.97,   # Radhanagari Subbasin
}
TOTAL_GAUGED_AREA_KM2 = sum(SUBBASIN_AREAS_KM2.values())  # 1837.213 km²


# ── Full Primary & Alternate Station Registry ─────────────────────────────────

STATION_REGISTRY: List[RainStation] = [
    # S1 (Area: 86.213 km²)
    RainStation("KARVEER", "Karveer", "S1", 74.2481772, 16.706369, is_primary=True, elevation_m=550.0),
    
    # S2 (Area: 153.77 km²)
    RainStation("SANGARUL", "Sangarul", "S2", 74.0931627, 16.6841962, is_primary=True, elevation_m=572.0),
    RainStation("BALINGA", "Balinga", "S2", 74.17031, 16.6878443, is_primary=False, elevation_m=560.0),
    RainStation("KALE", "Kale", "S2", 74.0564499, 16.7228087, is_primary=False, elevation_m=580.0),
    
    # S3 (Area: 261.32 km²)
    RainStation("KOTOLI", "Kotoli", "S3", 74.0518705, 16.7820174, is_primary=True, elevation_m=585.0),
    RainStation("BAJAR_BHOGAON", "Bajar Bhogaon", "S3", 74.1107824, 16.8086769, is_primary=False, elevation_m=590.0),
    RainStation("PADAL", "Padal", "S3", 74.115187, 16.7446006, is_primary=False, elevation_m=575.0),
    
    # S4 (Area: 262.00 km²)
    RainStation("KARANJPHEN", "Karanjphen", "S4", 73.9036487, 16.7850973, is_primary=True, elevation_m=640.0),
    
    # S5 (Area: 106.39 km²)
    RainStation("PADASALI", "Padasali", "S5", 73.843584, 16.701934, is_primary=True, elevation_m=620.0),
    RainStation("SALWAN", "Salwan", "S5", 73.9735, 16.6712, is_primary=False, elevation_m=595.0),
    
    # S6 (Area: 227.72 km²)
    RainStation("GAGANBAWDA", "Gaganbawda", "S6", 73.8346738, 16.5469926, is_primary=True, elevation_m=680.0),
    
    # S7 (Area: 195.39 km²)
    RainStation("GARIVADE", "Garivade", "S7", 73.918419, 16.520366, is_primary=True, elevation_m=610.0),
    
    # S8 (Area: 177.44 km²)
    RainStation("BEED", "Beed", "S8", 74.1288964, 16.647984, is_primary=True, elevation_m=565.0),
    RainStation("SHIROLI_DHUMALA", "Shiroli-Dhumala", "S8", 74.1062828, 16.6166768, is_primary=False, elevation_m=560.0),
    
    # S9 (Area: 366.97 km²)
    RainStation("RADHANAGARI", "Radhanagari", "S9", 73.9971822, 16.41021, is_primary=True, elevation_m=615.0),
    RainStation("HALADI", "Haladi", "S9", 74.156292, 16.5932632, is_primary=False, elevation_m=555.0),
    RainStation("RASHIWADE_BK", "Rashiwade Bk.", "S9", 74.1019728, 16.5475641, is_primary=False, elevation_m=570.0),
    RainStation("AAVALI_BK", "Aavali Bk.", "S9", 74.0549812, 16.481009, is_primary=False, elevation_m=585.0),
    RainStation("KASABA_TARALE", "Kasaba Tarale", "S9", 74.021589, 16.4478876, is_primary=False, elevation_m=595.0),
    RainStation("KASABA_WALAWE", "Kasaba Walawe", "S9", 73.9971822, 16.41021, is_primary=False, elevation_m=615.0),
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great-Circle distance in km between two lat/lon coordinates."""
    r = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return 2.0 * r * math.asin(math.sqrt(a))


def select_active_subbasin_gages(
    station_rainfall_90hr: Dict[str, float]
) -> Dict[str, dict]:
    """
    Selects the governing rainfall gage for each subbasin (S1–S9).
    
    Parameters:
        station_rainfall_90hr: Dict[station_id, total_cumulative_mm]
        
    Returns:
        Dict[subbasin_id, {
            'selected_station_id': str,
            'station_name': str,
            'cumulative_mm': float,
            'method': 'MAX_RAIN_VOLUME' | 'NEAREST_HIGH_RAIN_FALLBACK',
            'candidates_count': int
        }]
    """
    # Group stations by subbasin
    by_subbasin: Dict[str, List[RainStation]] = {}
    for st in STATION_REGISTRY:
        by_subbasin.setdefault(st.subbasin, []).append(st)

    all_subbasins = [f"S{i}" for i in range(1, 10)]
    selection_results = {}

    for sub_id in all_subbasins:
        candidates = by_subbasin.get(sub_id, [])

        if candidates:
            # Sort candidates by rainfall volume descending
            scored = []
            for c in candidates:
                rf = station_rainfall_90hr.get(c.station_id, 0.0)
                scored.append((rf, c))
            
            scored.sort(key=lambda x: x[0], reverse=True)
            best_rf, best_st = scored[0]

            selection_results[sub_id] = {
                "subbasin_id": sub_id,
                "selected_station_id": best_st.station_id,
                "station_name": best_st.name,
                "lat": best_st.lat,
                "lon": best_st.lon,
                "cumulative_mm": round(best_rf, 2),
                "method": "MAX_RAIN_VOLUME",
                "candidates_count": len(candidates),
                "alternate_stations": [s[1].name for s in scored[1:]],
            }
        else:
            # Ungauged subbasin fallback: Find nearest high-rainfall station
            # Subbasin approximate centroids
            sub_centroids = {
                "S1": (16.706369, 74.2481772),  # Karveer
                "S2": (16.6841962, 74.0931627), # Sangarul
                "S3": (16.7820174, 74.0518705), # Kotoli
                "S4": (16.7850973, 73.9036487), # Karanjphen
                "S5": (16.701934,  73.843584),  # Padasali
                "S6": (16.5469926, 73.8346738), # Gaganbawda
                "S7": (16.520366,  73.918419),  # Garivade
                "S8": (16.647984,  74.1288964), # Beed
                "S9": (16.41021,   73.9971822), # Radhanagari
            }
            c_lat, c_lon = sub_centroids.get(sub_id, (16.65, 74.10))

            # Rank all stations by distance and rainfall
            fallback_scored = []
            for st in STATION_REGISTRY:
                dist = haversine_km(c_lat, c_lon, st.lat, st.lon)
                rf = station_rainfall_90hr.get(st.station_id, 0.0)
                # Score: maximize rainfall while penalizing distant stations
                score = rf / (dist + 1.0)
                fallback_scored.append((score, dist, rf, st))

            fallback_scored.sort(key=lambda x: x[0], reverse=True)
            _, best_dist, best_rf, best_st = fallback_scored[0]

            selection_results[sub_id] = {
                "subbasin_id": sub_id,
                "selected_station_id": best_st.station_id,
                "station_name": best_st.name,
                "lat": best_st.lat,
                "lon": best_st.lon,
                "cumulative_mm": round(best_rf, 2),
                "method": "NEAREST_HIGH_RAIN_FALLBACK",
                "candidates_count": 0,
                "fallback_distance_km": round(best_dist, 1),
            }

    return selection_results


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR PATH — Postgres / PostGIS + ECMWF grid (lazy imports)
# Used by src/orchestrator.py when the automation server has a live database.
# The pure-registry functions above never require these dependencies.
# ─────────────────────────────────────────────────────────────────────────────

def load_stations(conn) -> List[RainStation]:
    """Load all active gauge stations from Postgres as canonical RainStations."""
    import psycopg2  # noqa: F401  (kept for explicit dependency documentation)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT station_id, station_name, subbasin_id,
                   ST_Y(geom) AS lat, ST_X(geom) AS lon
            FROM gauge_stations
            WHERE is_active = TRUE
            ORDER BY subbasin_id, station_id
        """)
        return [
            RainStation(station_id=row[0], name=row[1], subbasin=row[2],
                        lat=float(row[3]), lon=float(row[4]), is_primary=True)
            for row in cur.fetchall()
        ]


def interpolate_ecmwf_to_station(ds, station: RainStation) -> "np.ndarray":
    """
    Bilinear interpolation of ECMWF gridded TP to a point station location.
    Returns array shape (90,) in mm/hr.
    """
    import numpy as np
    tp = ds["tp_mm_hr"]   # (valid_time=90, lat, lon)
    point_da = tp.interp(
        latitude=station.lat,
        longitude=station.lon,
        method="linear",
    )
    return np.maximum(point_da.values, 0.0)


def fetch_observed_gauge_ts(
    conn,
    station_id: str,
    start_utc,
    end_utc,
) -> Optional["np.ndarray"]:
    """
    Pull observed 1-hourly gauge data from Postgres for the 90-hr window.
    Returns array (90,) or None if insufficient coverage.
    """
    import numpy as np
    import pandas as pd
    hours = pd.date_range(start=start_utc, periods=90, freq="1h", tz="UTC")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT date_trunc('hour', timestamp) AS hr,
                   AVG(rainfall_mm) AS mm
            FROM rainfall_data
            WHERE gauge_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            GROUP BY hr
            ORDER BY hr
        """, (station_id, start_utc, end_utc))
        rows = cur.fetchall()

    if len(rows) < 45:   # need at least 50% coverage
        return None

    ts_df = pd.DataFrame(rows, columns=["hr", "mm"]).set_index("hr")
    ts_df.index = pd.DatetimeIndex(ts_df.index).tz_localize("UTC")
    ts_full = ts_df.reindex(hours, fill_value=0.0)
    return ts_full["mm"].values.astype(np.float32)


def select_stations(
    ds_ecmwf,
    stations: List[RainStation],
    conn,
    run_time,
    prefer_observed: bool = True,
) -> Dict[str, SubbasinRainfall]:
    """
    Core DB-driven selection logic (orchestrator path).
    For each subbasin:
      1. Gather 90-hr hyetograph for every station (observed if available, else ECMWF).
      2. Compute cumulative (sum of 90 values).
      3. Select station with maximum cumulative (same conservative rule as the
         registry path).

    Returns dict: subbasin_id → SubbasinRainfall
    """
    import numpy as np
    from datetime import timedelta
    end_utc = run_time + timedelta(hours=90)

    by_sub: Dict[str, List[RainStation]] = {}
    for st in stations:
        by_sub.setdefault(st.subbasin, []).append(st)

    results: Dict[str, SubbasinRainfall] = {}

    for sub_id, sub_stations in by_sub.items():
        log.info("Subbasin %s: evaluating %d stations", sub_id, len(sub_stations))
        candidates: Dict[str, "np.ndarray"] = {}

        for st in sub_stations:
            obs = None
            if prefer_observed:
                obs = fetch_observed_gauge_ts(conn, st.station_id, run_time, end_utc)
            hyeto = obs if obs is not None else interpolate_ecmwf_to_station(ds_ecmwf, st)
            source = "observed" if obs is not None else "ecmwf_interp"
            cum = float(hyeto.sum())
            log.info("  %s (%s): %.1f mm [%s]", st.station_id, st.name, cum, source)
            candidates[st.station_id] = hyeto

        cumulative = {sid: float(h.sum()) for sid, h in candidates.items()}
        selected_id = max(cumulative, key=lambda k: cumulative[k])

        log.info(
            "  → SELECTED %s for %s (%.1f mm cumulative)",
            selected_id, sub_id, cumulative[selected_id],
        )

        results[sub_id] = SubbasinRainfall(
            subbasin_id=sub_id,
            selected_station=selected_id,
            cumulative_mm=cumulative[selected_id],
            hyetograph=candidates[selected_id].tolist(),
            all_stations=cumulative,
        )

    return results


def store_selection(conn, results: Dict[str, SubbasinRainfall], run_time, cycle_id: str):
    """
    Persist:
    - All raw station hyetographs   → table `rainfall_data`
    - Selection decision            → table `station_selection_log`
    - Selected hyetograph           → table `subbasin_rainfall_ts`
    """
    import json
    from datetime import timedelta

    with conn.cursor() as cur:
        for sub_id, result in results.items():
            cur.execute("""
                INSERT INTO station_selection_log
                    (cycle_id, subbasin_id, selected_station_id,
                     cumulative_mm, all_candidates_json, selected_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (cycle_id, subbasin_id)
                DO UPDATE SET
                    selected_station_id = EXCLUDED.selected_station_id,
                    cumulative_mm       = EXCLUDED.cumulative_mm,
                    all_candidates_json = EXCLUDED.all_candidates_json,
                    selected_at         = NOW()
            """, (
                cycle_id, sub_id, result.selected_station,
                result.cumulative_mm,
                json.dumps(result.all_stations),
            ))

        valid_times = [run_time + timedelta(hours=h + 1) for h in range(90)]
        for sub_id, result in results.items():
            for i, (vt, mm) in enumerate(zip(valid_times, result.hyetograph)):
                cur.execute("""
                    INSERT INTO subbasin_rainfall_ts
                        (basin_id, subbasin_id, source_id, forecast_run_time,
                         valid_time, lead_hours, rainfall_mm_hr, quality_score)
                    VALUES ('MAIN_BASIN', %s, 'selected_gauge', %s, %s, %s, %s, 1.0)
                    ON CONFLICT (subbasin_id, valid_time, source_id)
                    DO UPDATE SET
                        rainfall_mm_hr = EXCLUDED.rainfall_mm_hr,
                        source_id      = EXCLUDED.source_id,
                        forecast_run_time = EXCLUDED.forecast_run_time
                """, (sub_id, run_time, vt, i + 1, mm))

    conn.commit()
    log.info("Stored station selection and hyetographs for cycle %s", cycle_id)
