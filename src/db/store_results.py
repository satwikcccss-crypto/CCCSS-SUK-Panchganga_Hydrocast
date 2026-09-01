"""
src/db/store_results.py
=======================
Persists all HMS output to PostgreSQL after a completed simulation cycle.
Writes: hydrograph_results, peak_discharge_events, runoff_summary
"""

import logging
from datetime import datetime

log = logging.getLogger(__name__)


def store_all(conn, cycle_id: str, run_dt: datetime, hg: dict, bridge_forecasts: dict) -> dict:
    counts = {}
    counts.update(_store_hydrograph(conn, cycle_id, hg))
    counts.update(_store_peak_event(conn, cycle_id, run_dt, hg))
    counts.update(_store_runoff_summary(conn, cycle_id, run_dt, hg, bridge_forecasts))
    conn.commit()
    log.info("DB write complete for cycle %s: %s", cycle_id, counts)
    return counts


def _store_hydrograph(conn, cycle_id: str, hg: dict) -> dict:
    rows = 0
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM hydrograph_results
            WHERE run_id=%s AND outlet_node='J_Outlet'
        """, (cycle_id,))
        for lead, (ts, q) in enumerate(hg["hydrograph"], start=1):
            is_peak = (ts == hg["time_of_peak"])
            baseflow = 45.0
            surf = max(0.0, q - baseflow)
            cur.execute("""
                INSERT INTO hydrograph_results
                    (run_id, basin_id, outlet_node, timestamp,
                     lead_hours, discharge_m3s, surface_runoff_m3s,
                     baseflow_m3s, is_peak)
                VALUES ('MAIN_BASIN', %s, 'J_Outlet', %s, %s, %s, %s, %s, %s, %s)
            """, (
                cycle_id, ts, lead,
                round(float(q), 2),
                round(surf, 2), baseflow, is_peak,
            ))
            rows += 1
    return {"hydrograph_rows": rows}


def _store_peak_event(conn, cycle_id: str, run_dt: datetime, hg: dict) -> dict:
    peak_idx = next(
        i for i, (ts, _) in enumerate(hg["hydrograph"])
        if ts == hg["time_of_peak"]
    )
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO peak_discharge_events
                (run_id, basin_id, outlet_node,
                 peak_discharge_m3s, time_of_peak, lead_hours_to_peak,
                 total_runoff_volume_m3, forecast_run_time)
            VALUES (%s, 'MAIN_BASIN', 'J_Outlet', %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            cycle_id,
            round(hg["peak_q"], 2),
            hg["time_of_peak"],
            peak_idx + 1,
            round(hg["total_volume_m3"], 0),
            run_dt,
        ))
    return {"peak_events": 1}


def _store_runoff_summary(conn, cycle_id: str, run_dt: datetime, hg: dict, bridge_forecasts: dict) -> dict:
    q_vals = [q for _, q in hg["hydrograph"]]
    hours_watch = sum(1 for q in q_vals if q >= 500)
    hours_warn  = sum(1 for q in q_vals if q >= 750)
    hours_emerg = sum(1 for q in q_vals if q >= 1000)

    peak_q = hg["peak_q"]
    alert = (
        "emergency" if hours_emerg > 0 else
        "warning"   if hours_warn  > 0 else
        "watch"     if hours_watch > 0 else
        "normal"
    )
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO runoff_summary
                (run_id, basin_id, forecast_run_time,
                 peak_discharge_m3s, time_of_peak, lead_hours_to_peak,
                 total_runoff_volume_m3,
                 alert_level, hours_above_watch, hours_above_warning, hours_above_emergency)
            VALUES (%s,'MAIN_BASIN',%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (run_id) DO UPDATE SET
                peak_discharge_m3s = EXCLUDED.peak_discharge_m3s,
                alert_level = EXCLUDED.alert_level
        """, (
            cycle_id, run_dt,
            round(peak_q, 2), hg["time_of_peak"],
            next((i+1 for i,(ts,_) in enumerate(hg["hydrograph"]) if ts==hg["time_of_peak"]), 0),
            round(hg["total_volume_m3"], 0),
            alert, hours_watch, hours_warn, hours_emerg,
        ))
    return {"summary_rows": 1}
