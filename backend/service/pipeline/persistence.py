"""Transactional persistence of forecasts, alerts and cycle rows."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.service.pipeline.steps import (
    _SITE_DB_KEY,
    _as_float_list,
    _db_alert_level,
)

log = logging.getLogger(__name__)

def _ensure_cycle_row(conn, cycle_id: str, run_dt: datetime) -> None:
    """Create the simulation_runs row early so FK-targeted tables can persist."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO simulation_runs
                (run_id, cycle_date, cycle_time, start_time, status)
            VALUES (%s, %s, %s, NOW(), 'RUNNING')
            ON CONFLICT (run_id) DO UPDATE SET status='RUNNING'
        """, (cycle_id, run_dt.date(), f"{run_dt.hour:02d}z"))
    conn.commit()

def _persist_forecast(
    conn,
    cycle_id: str,
    run_dt: datetime,
    hg_results: Dict[str, Any],
    bridge_stages: Dict[str, Any],
    station_selection: Dict[str, Dict[str, Any]],
    weather_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Persist EVERY forecast time step: discharge, stage, rainfall and peak metadata.

    Writes (idempotently, deleting the same cycle first):
      * hydrograph_results      — 90 hourly outlet discharge + stage + is_peak
      * bridge_stage_forecast   — 90 hourly rows per bridge (stage, Q, alert, arrival)
      * subbasin_rainfall_ts    — 90 hourly rows per subbasin (governing hyetograph)
      * station_selection_log   — 9 rows of governing-gauge decisions
      * peak_discharge_events   — 1 row (peak Q, time of peak, volume)
      * simulation_runs         — peak Q/stage, lead time, volume, rainfall
    """
    from backend.alerts.evaluator import CWC_THRESHOLDS
    from backend.rainfall.station_selector import SUBBASIN_AREAS_KM2
    from backend.stage_conversion.stage_converter import convert_discharge_to_stage_manning

    timestamps = hg_results.get("timestamps", []) or []
    q_total = _as_float_list(hg_results.get("q_total"))
    q_surface = _as_float_list(hg_results.get("q_surface"))
    baseflow = _as_float_list(hg_results.get("baseflow_array"))
    peak_h = int(hg_results.get("peak_h", 0) or 0)
    peak_q = float(hg_results.get("peak_q", 0.0) or 0.0)

    n = min(len(timestamps), len(q_total))
    if n == 0:
        log.warning("No hydrograph points to persist for cycle %s", cycle_id)
        return {"hydrograph_rows": 0, "bridge_rows": 0, "rainfall_rows": 0}

    q_total = q_total[:n]
    q_surface = (q_surface + [0.0] * n)[:n]
    baseflow = (baseflow + [float(q_total[0])] * n)[:n]
    ts_list = [datetime.fromisoformat(str(t)) for t in timestamps[:n]]
    volume_m3 = sum(q_total) * 3600.0

    # Per-site, per-hour stage via PCHIP rating curves.
    stage_series: Dict[str, List[float]] = {
        converter_key: [convert_discharge_to_stage_manning(q, converter_key) for q in q_total]
        for converter_key in _SITE_DB_KEY
    }

    rain_volume_m3 = sum(
        SUBBASIN_AREAS_KM2.get(sub_id, 0.0) * float(info.get("cumulative_mm", 0.0)) * 1000.0
        for sub_id, info in station_selection.items()
    )
    mean_rain_mm = float(hg_results.get("mean_catchment_rain_90h", 0.0) or 0.0)

    with conn.cursor() as cur:
        # 1. Outlet hydrograph (every hour, exactly one is_peak).
        cur.execute(
            "DELETE FROM hydrograph_results WHERE run_id=%s AND outlet_node='J_Outlet'",
            (cycle_id,),
        )
        shivaji_stages = stage_series["SHIVAJI_BRIDGE"]
        for i in range(n):
            cur.execute("""
                INSERT INTO hydrograph_results
                    (run_id, basin_id, outlet_node, timestamp, lead_hours,
                     discharge_m3s, surface_runoff_m3s, baseflow_m3s, is_peak, stage_m)
                VALUES (%s,'PANCHGANGA_BASIN','J_Outlet',%s,%s,%s,%s,%s,%s,%s)
            """, (
                cycle_id, ts_list[i], i,
                round(q_total[i], 2), round(q_surface[i], 2), round(baseflow[i], 2),
                (i == peak_h), round(shivaji_stages[i], 2),
            ))

        # 2. Bridge stage forecasts (every hour, both bridges, with arrival time).
        cur.execute("DELETE FROM bridge_stage_forecast WHERE forecast_run_id=%s", (cycle_id,))
        bridge_rows = 0
        for converter_key, persist_key in _SITE_DB_KEY.items():
            thresholds = CWC_THRESHOLDS.get(persist_key) or CWC_THRESHOLDS.get(converter_key) or {}
            alert_thr = float(thresholds.get("alert", 0.0) or 0.0)
            danger_thr = float(thresholds.get("danger", 9999.0) or 9999.0)

            arrival_time = None
            if alert_thr > 0:
                for i in range(n):
                    if stage_series[converter_key][i] >= alert_thr:
                        arrival_time = ts_list[i]
                        break

            for i in range(n):
                stage = stage_series[converter_key][i]
                cur.execute("""
                    INSERT INTO bridge_stage_forecast
                        (site_id, forecast_run_id, forecast_time, lead_hours,
                         discharge_m3s, stage_m, alert_level, is_above_danger, arrival_time)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    persist_key, cycle_id, ts_list[i], i,
                    round(q_total[i], 2), round(stage, 2),
                    _db_alert_level(persist_key, stage), (stage >= danger_thr),
                    arrival_time,
                ))
                bridge_rows += 1

        # 3. Subbasin rainfall time series (every hour, every subbasin).
        provenance = (weather_data or {}).get("provenance") or {}
        source_id = provenance.get("tier", "selected_gauge")
        cur.execute("DELETE FROM subbasin_rainfall_ts WHERE forecast_run_time=%s", (run_dt,))
        rainfall_rows = 0
        for sub_id, info in station_selection.items():
            for i, mm in enumerate((info.get("hyetograph") or [])[:n]):
                cur.execute("""
                    INSERT INTO subbasin_rainfall_ts
                        (subbasin_id, valid_time, lead_hours, rainfall_mm_hr,
                         source_id, forecast_run_time)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (sub_id, ts_list[i], i, round(float(mm), 2), source_id, run_dt))
                rainfall_rows += 1

        # 4. Station selection decisions.
        cur.execute("DELETE FROM station_selection_log WHERE cycle_id=%s", (cycle_id,))
        for sub_id, info in station_selection.items():
            cur.execute("""
                INSERT INTO station_selection_log
                    (cycle_id, subbasin_id, selected_station_id, cumulative_mm,
                     all_candidates_json, selected_at)
                VALUES (%s,%s,%s,%s,%s,NOW())
            """, (
                cycle_id, sub_id, info.get("selected_station_id"),
                round(float(info.get("cumulative_mm", 0.0)), 2),
                json.dumps(info.get("all_candidates", {})),
            ))

        # 5. Peak discharge event.
        cur.execute("DELETE FROM peak_discharge_events WHERE run_id=%s", (cycle_id,))
        cur.execute("""
            INSERT INTO peak_discharge_events
                (run_id, outlet_node, peak_discharge_m3s, time_of_peak, total_runoff_volume_m3)
            VALUES (%s,'J_Outlet',%s,%s,%s)
        """, (cycle_id, round(peak_q, 2), ts_list[peak_h], round(volume_m3, 2)))

        # 6. Run summary (peak stage = highest Shivaji stage of the series).
        peak_stage_shivaji = max(shivaji_stages) if shivaji_stages else 0.0
        cur.execute("""
            UPDATE simulation_runs SET
                end_time = NOW(),
                status = 'completed',
                peak_discharge_m3s = %s,
                peak_stage_m = %s,
                lead_hours_to_peak = %s,
                total_volume_mcm = %s,
                total_rainfall_mm = %s,
                total_rainfall_volume_mcm = %s,
                duration_seconds = EXTRACT(EPOCH FROM (NOW() - start_time))
            WHERE run_id = %s
        """, (
            round(peak_q, 2), round(peak_stage_shivaji, 2), peak_h,
            round(volume_m3 / 1e6, 2), round(mean_rain_mm, 2),
            round(rain_volume_m3 / 1e6, 2), cycle_id,
        ))
    conn.commit()

    return {
        "hydrograph_rows": n,
        "bridge_rows": bridge_rows,
        "rainfall_rows": rainfall_rows,
        "station_rows": len(station_selection),
        "peak_h": peak_h,
        "peak_q_m3s": round(peak_q, 2),
        "peak_stage_shivaji_m": round(peak_stage_shivaji, 2),
    }

def _persist_alerts(conn, cycle_id: str, alert_result: Dict[str, Any], peak_q: float) -> int:
    """Cancel stale active alerts and persist the current cycle's CWC alerts."""
    sites = (alert_result or {}).get("sites", {}) or {}
    issued = 0
    with conn.cursor() as cur:
        for raw_site_id, info in sites.items():
            site_id = _SITE_DB_KEY.get(raw_site_id, raw_site_id)
            level = info.get("classification", "NORMAL")
            stage = float(info.get("stage_m", 0.0) or 0.0)

            cur.execute("""
                UPDATE alert_events
                SET status='cancelled', cancelled_at=NOW()
                WHERE site_id=%s AND status='active'
            """, (site_id,))

            if level == "NORMAL":
                continue

            db_level = "HFL_EXCEEDED" if level == "HISTORIC_PEAK" else level
            cur.execute("""
                INSERT INTO alert_events
                    (site_id, alert_level, stage_m, discharge_m3s, issued_at, status, message)
                VALUES (%s,%s,%s,%s,NOW(),'active',%s)
            """, (
                site_id, db_level, round(stage, 2), round(float(peak_q), 2),
                f"Forecast peak {stage:.2f} m MSL classified {db_level} at {site_id} (cycle {cycle_id}).",
            ))
            issued += 1

        max_status = str((alert_result or {}).get("status", "normal")).upper()
        cur.execute(
            "UPDATE simulation_runs SET alert_level=%s WHERE run_id=%s",
            (max_status, cycle_id),
        )
    conn.commit()
    return issued
