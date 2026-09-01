"""
Post-Processing: Stage Conversion + Bridge Forecasts
=====================================================
After HEC-HMS runs:
  1. Reads outlet hydrograph from HMS DSS output
  2. Applies travel-time offset to get hydrograph at each bridge
  3. Converts Q → H using rating curves (Manning's from cross-section data)
  4. Classifies CWC alert levels
  5. Computes flood arrival time at each bridge
  6. Stores to bridge_stage_forecast
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import psycopg2

from src.hydrology.stage_converter import (
    CrossSection, discharge_to_stage, classify_alert, build_all_rating_curves
)

log = logging.getLogger(__name__)

# Travel time from HMS outlet (J_Outlet) to each bridge (hours)
# Estimate from channel velocity and reach length; refine after calibration
TRAVEL_TIMES = {
    "SHIVAJI_BRIDGE": float(os.getenv("TT_SHIVAJI", "1.5")),
    "RAJARAM_BRIDGE": float(os.getenv("TT_RAJARAM", "3.0")),
}


def load_rating_curves_from_db(conn) -> dict:
    """
    Load pre-computed rating curves from Postgres.
    Returns dict: site_id → (CrossSection metadata dict, list of (H, Q) pairs)
    """
    curves = {}
    with conn.cursor() as cur:
        cur.execute("SELECT site_id, alert_stage_m, warning_stage_m, danger_stage_m, hfl_m FROM bridge_sites")
        sites = {r["site_id"]: dict(r) for r in cur.fetchall()}

        for site_id, meta in sites.items():
            cur.execute("""
                SELECT stage_m, discharge_m3s
                FROM rating_curves WHERE site_id=%s ORDER BY stage_m
            """, (site_id,))
            rows = cur.fetchall()
            if rows:
                curves[site_id] = {
                    "meta": meta,
                    "stage":  np.array([r["stage_m"]      for r in rows]),
                    "discharge": np.array([r["discharge_m3s"] for r in rows]),
                }
    return curves


def q_to_h(q: float, curve: dict) -> float:
    """Interpolate stage from discharge using rating curve arrays."""
    return float(np.interp(q, curve["discharge"], curve["stage"],
                           left=curve["stage"][0], right=curve["stage"][-1]))


def cwc_level(h: float, meta: dict) -> str:
    if h >= meta["hfl_m"]:           return "HFL_EXCEEDED"
    if h >= meta["danger_stage_m"]:  return "DANGER"
    if h >= meta["warning_stage_m"]: return "WARNING"
    if h >= meta["alert_stage_m"]:   return "ALERT"
    return "NORMAL"


def apply_travel_time(
    hydrograph: list[tuple[datetime, float]],
    travel_hours: float,
) -> list[tuple[datetime, float]]:
    """
    Shift hydrograph timestamps by travel_hours.
    Values stay the same (simple lag, not full hydraulic routing).
    """
    lag = timedelta(hours=travel_hours)
    return [(ts + lag, q) for ts, q in hydrograph]


def convert_and_store_stages(
    conn,
    hg: dict,
    cycle_id: str,
    run_dt: datetime,
) -> dict:
    """
    Main entry point called by orchestrator step 9.

    hg: result from hms.runner.read_outlet_hydrograph()
        {
          'hydrograph': [(datetime, q_m3s), ...],
          'peak_q': float,
          'time_of_peak': datetime,
          ...
        }

    Returns dict: site_id → {
        'arrival_time': datetime|None,
        'peak_stage': float,
        'peak_level': str,
        'forecast': [(ts, q, h, level), ...]
    }
    """
    curves = load_rating_curves_from_db(conn)
    if not curves:
        # Fallback: build from CSV survey files
        log.warning("No rating curves in DB — building from cross-section CSVs")
        built = build_all_rating_curves()
        curves = {}
        for site_id, (cs, df) in built.items():
            curves[site_id] = {
                "meta": {
                    "alert_stage_m":   cs.alert_stage_m,
                    "warning_stage_m": cs.warning_stage_m,
                    "danger_stage_m":  cs.danger_stage_m,
                    "hfl_m":           cs.hfl_m,
                },
                "stage":     df["stage_m"].values,
                "discharge": df["q_m3s"].values,
            }

    outlet_hg = hg["hydrograph"]   # [(datetime, q_m3s), ...]
    results = {}

    for site_id, curve in curves.items():
        travel = TRAVEL_TIMES.get(site_id, 0.0)
        bridge_hg = apply_travel_time(outlet_hg, travel)

        forecast_rows = []
        arrival_time  = None
        peak_stage    = 0.0
        meta          = curve["meta"]

        for i, (ts, q) in enumerate(bridge_hg):
            h     = q_to_h(q, curve)
            level = cwc_level(h, meta)

            if arrival_time is None and level != "NORMAL":
                arrival_time = ts

            peak_stage = max(peak_stage, h)
            forecast_rows.append((ts, q, h, level, i + 1))

        peak_level = cwc_level(peak_stage, meta)
        results[site_id] = {
            "arrival_time": arrival_time,
            "peak_stage":   peak_stage,
            "peak_level":   peak_level,
            "forecast":     forecast_rows,
        }

        log.info(
            "%s → peak stage=%.2fm [%s] | arrival=%s",
            site_id, peak_stage, peak_level,
            arrival_time.isoformat() if arrival_time else "None",
        )

    # Persist to bridge_stage_forecast
    _store_bridge_forecasts(conn, results, cycle_id)
    return results


def _store_bridge_forecasts(conn, results: dict, cycle_id: str):
    with conn.cursor() as cur:
        for site_id, res in results.items():
            for ts, q, h, level, lead in res["forecast"]:
                cur.execute("""
                    INSERT INTO bridge_stage_forecast
                        (site_id, forecast_run_id, forecast_time, lead_hours,
                         discharge_m3s, stage_m, alert_level, arrival_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    site_id, cycle_id, ts, lead,
                    round(q, 2), round(h, 3), level,
                    res["arrival_time"],
                ))
    conn.commit()
    log.info("Stored bridge stage forecasts for %d sites", len(results))
