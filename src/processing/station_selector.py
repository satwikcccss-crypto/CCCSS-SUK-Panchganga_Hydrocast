"""
Rain Gauge Station Selector
==============================
Problem: Each subbasin has 1-4 IoT gauge stations.
         HEC-HMS requires exactly ONE hyetograph per subbasin.
Rule:    Select the station with the HIGHEST cumulative 90-hour rainfall (mm).
         Re-run every cycle so the selection is dynamic.

Station registry is loaded from Postgres.
Output: Dict[subbasin_id → selected_station_id] + per-subbasin 90-hr hyetograph.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import psycopg2
import xarray as xr
from scipy.spatial import cKDTree

log = logging.getLogger(__name__)


@dataclass
class Station:
    station_id:  str
    station_name: str
    subbasin_id: str
    latitude:    float
    longitude:   float
    is_active:   bool = True


@dataclass
class SubbasinRainfall:
    subbasin_id:      str
    selected_station: str
    cumulative_mm:    float                    # 90-hr total of selected station
    hyetograph:       list[float]             # length-90 list, mm/hr per hour
    all_stations:     dict[str, float]        # station_id → 90hr cumulative for audit


def load_stations(conn) -> list[Station]:
    """Load all active gauge stations from Postgres."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT station_id, station_name, subbasin_id,
                   ST_Y(geom) AS lat, ST_X(geom) AS lon
            FROM gauge_stations
            WHERE is_active = TRUE
            ORDER BY subbasin_id, station_id
        """)
        return [Station(*row) for row in cur.fetchall()]


def interpolate_ecmwf_to_station(ds: xr.Dataset, station: Station) -> np.ndarray:
    """
    Bilinear interpolation of ECMWF gridded TP to a point station location.
    Returns array shape (90,) in mm/hr.
    """
    tp = ds["tp_mm_hr"]   # (valid_time=90, lat, lon)
    # xarray nearest-neighbour then bilinear via interp
    point_da = tp.interp(
        latitude=station.latitude,
        longitude=station.longitude,
        method="linear",
    )
    vals = point_da.values
    return np.maximum(vals, 0.0)


def fetch_observed_gauge_ts(
    conn,
    station_id: str,
    start_utc: datetime,
    end_utc: datetime,
) -> Optional[np.ndarray]:
    """
    Pull observed 1-hourly gauge data from Postgres for the 90-hr window.
    Returns array (90,) or None if insufficient coverage.
    """
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
    ds_ecmwf: xr.Dataset,
    stations: list[Station],
    conn,
    run_time: datetime,
    prefer_observed: bool = True,
) -> dict[str, SubbasinRainfall]:
    """
    Core selection logic.
    For each subbasin:
      1. Gather 90-hr hyetograph for every station (observed if available, else ECMWF).
      2. Compute cumulative (sum of 90 values).
      3. Select station with maximum cumulative.

    Returns dict: subbasin_id → SubbasinRainfall
    """
    end_utc = run_time + timedelta(hours=90)

    # Group stations by subbasin
    by_sub: dict[str, list[Station]] = {}
    for st in stations:
        by_sub.setdefault(st.subbasin_id, []).append(st)

    results: dict[str, SubbasinRainfall] = {}

    for sub_id, sub_stations in by_sub.items():
        log.info("Subbasin %s: evaluating %d stations", sub_id, len(sub_stations))

        # Build hyetographs and cumulative sums for each candidate
        candidates: dict[str, np.ndarray] = {}

        for st in sub_stations:
            # Try observed gauge data first
            obs = None
            if prefer_observed:
                obs = fetch_observed_gauge_ts(conn, st.station_id, run_time, end_utc)

            if obs is not None:
                hyeto = obs
                source = "observed"
            else:
                # Fallback: ECMWF interpolated to station location
                hyeto = interpolate_ecmwf_to_station(ds_ecmwf, st)
                source = "ecmwf_interp"

            cum = float(hyeto.sum())
            log.info("  %s (%s): %.1f mm [%s]", st.station_id, st.station_name, cum, source)
            candidates[st.station_id] = hyeto

        # Select maximum-cumulative station
        cumulative = {sid: float(h.sum()) for sid, h in candidates.items()}
        selected_id = max(cumulative, key=lambda k: cumulative[k])
        selected_hyeto = candidates[selected_id]

        log.info(
            "  → SELECTED %s for %s (%.1f mm cumulative)",
            selected_id, sub_id, cumulative[selected_id],
        )

        results[sub_id] = SubbasinRainfall(
            subbasin_id=sub_id,
            selected_station=selected_id,
            cumulative_mm=cumulative[selected_id],
            hyetograph=selected_hyeto.tolist(),
            all_stations=cumulative,
        )

    return results


def store_selection(conn, results: dict[str, SubbasinRainfall], run_time: datetime, cycle_id: str):
    """
    Persist:
    - All raw station hyetographs → table `rainfall_data` (gauge_id, timestamp, rainfall_mm)
    - Selection decision        → table `station_selection_log`
    - Selected hyetograph       → table `subbasin_rainfall_ts`
    """
    with conn.cursor() as cur:

        # 1. Log selection decision per subbasin
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
                str(result.all_stations),   # JSON-serialise in production
            ))

        # 2. Store selected hyetograph in subbasin_rainfall_ts
        valid_times = [run_time + timedelta(hours=h+1) for h in range(90)]
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
                        source_id      = EXCLUDED.source_id
                """, (sub_id, run_time, vt, i+1, mm))

    conn.commit()
    log.info("Stored station selection and hyetographs for cycle %s", cycle_id)
