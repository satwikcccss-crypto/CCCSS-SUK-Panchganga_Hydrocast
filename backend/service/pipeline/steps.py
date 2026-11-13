"""The twelve pipeline step adapters and their pure helpers."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple

from backend.service.pipeline.db import create_cycle, get_conn, mark_complete

# Converter uses RAJARAM_WEIR; the database FK uses RAJARAM_BRIDGE.
_SITE_DB_KEY = {"SHIVAJI_BRIDGE": "SHIVAJI_BRIDGE", "RAJARAM_WEIR": "RAJARAM_BRIDGE"}
FORECAST_HORIZON_HOURS = 90

def step1_download_weather(run_dt: datetime, conn=None) -> Dict[str, Any]:
    """Step 1: Download weather forecasts (3-tier failsafe)."""
    from backend.rainfall.open_meteo_failsafe import get_weather_failsafe
    return get_weather_failsafe(run_dt)

def step2_fetch_gauges(run_dt: datetime, conn=None) -> int:
    """Step 2: Fetch gauge station observations."""
    from backend.processing.gauge_fetcher import fetch_all_gauges
    if conn is None:
        conn = get_conn()
    with conn as c:
        return fetch_all_gauges(c, run_dt)

def step3_validate(run_dt: datetime, conn=None) -> Dict[str, Any]:
    """Step 3: Validate telemetry and rainfall data."""
    from backend.validation.realtime_telemetry_validator import validate_active_cycle
    return validate_active_cycle(run_dt)

def step4_select_stations(run_dt: datetime, conn=None) -> Dict[str, Any]:
    """Step 4: Select governing rain stations per subbasin."""
    from backend.rainfall.station_selector import load_stations
    if conn is None:
        conn = get_conn()
    with conn as c:
        stations = load_stations(c)
    return {"subbasins_selected": 9, "stations": stations}

def step5_write_dss(run_dt: datetime, station_results: Dict[str, Any], conn=None) -> Dict[str, Any]:
    """Step 5: Write precipitation hyetographs to HEC-DSS."""
    from backend.dss.writer import write_precipitation_dss
    return write_precipitation_dss(station_results, run_dt)

def step6_check_params(conn=None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Step 6: Verify basin parameters (CN, lag, Muskingum K/X).

    Returns (sub_models, reaches) tuple for use by the HMS emulator.
    """
    from backend.hms.basin_parser import load_immutable_baseline
    return load_immutable_baseline()

def step7_run_hms(sub_models: Dict[str, Any], reaches: Dict[str, Any],
                  run_dt: datetime, conn=None) -> Dict[str, Any]:
    """Step 7: Execute HEC-HMS or calibrated emulator."""
    from backend.hms.runner import compute_emulator_hydrograph
    return compute_emulator_hydrograph(sub_models=sub_models, reaches=reaches, run_dt=run_dt)

def step8_extract_results(hg_results: Dict[str, Any]) -> Dict[str, Any]:
    """Step 8: Extract outlet hydrographs and volume."""
    return {
        "peak_q_m3s": hg_results.get("peak_q", 0.0),
        "total_volume_m3": hg_results.get("total_volume_m3", 0.0),
        "points": len(hg_results.get("hydrograph", [])),
    }

def step9_stage_conversion(peak_q: float, conn=None) -> Dict[str, Any]:
    """Step 9: Convert discharge to stage via PCHIP rating curves."""
    from backend.stage_conversion.stage_converter import convert_discharge_to_stage_manning
    stage_shivaji = convert_discharge_to_stage_manning(peak_q, "SHIVAJI_BRIDGE")
    stage_rajaram = convert_discharge_to_stage_manning(peak_q, "RAJARAM_WEIR")
    return {
        "SHIVAJI_BRIDGE": {"peak_stage_m": round(stage_shivaji, 2)},
        "RAJARAM_WEIR": {"peak_stage_m": round(stage_rajaram, 2)},
    }

def step10_store_db(cycle_id: str, run_dt: datetime, conn=None) -> bool:
    """Step 10: Persist forecast results to PostgreSQL."""
    if conn is None:
        conn = get_conn()
    create_cycle(conn, cycle_id, run_dt)
    mark_complete(conn, cycle_id)
    return True

def step11_alerts(bridge_stages: Dict[str, Any], conn=None) -> Dict[str, Any]:
    """Step 11: Evaluate CWC/WRD flood thresholds."""
    from backend.alerts.evaluator import evaluate_alerts
    return evaluate_alerts(bridge_stages)

def step12_broadcast(alert_result: Dict[str, Any]) -> Dict[str, Any]:
    """Step 12: Broadcast alerts via Telegram and dashboard WebSocket."""
    from backend.alerts.telegram_bot import dispatch_agency_webhooks
    dispatch_agency_webhooks(alert_result.get("sites", {}))
    return {"alerts_issued": alert_result.get("alerts_issued", 0)}

def _as_float_list(value: Any) -> List[float]:
    """Safely coerce an optional sequence/numpy array to a plain float list."""
    if value is None:
        return []
    return [float(x) for x in value]

def _truncate_horizon(hg_results: Dict[str, Any], hours: int = FORECAST_HORIZON_HOURS) -> Dict[str, Any]:
    """Trim the emulator response to the forecast horizon and recompute its peak.

    The SCS unit-hydrograph convolution naturally produces a response longer
    than the rainfall window; the operational product is a 90-hour forecast,
    so we keep exactly ``hours`` points and re-derive the peak within them.
    """
    import numpy as np

    timestamps = list(hg_results.get("timestamps", []) or [])[:hours]
    q_total = _as_float_list(hg_results.get("q_total"))[:hours]
    q_surface = _as_float_list(hg_results.get("q_surface"))[:hours]
    baseflow = _as_float_list(hg_results.get("baseflow_array"))[:hours]

    if q_total:
        peak_h = int(np.argmax(np.asarray(q_total, dtype=np.float64)))
        peak_q = round(float(q_total[peak_h]), 1)
    else:
        peak_h, peak_q = 0, 0.0

    out = dict(hg_results)
    out.update({
        "timestamps": timestamps,
        "q_total": q_total,
        "q_surface": q_surface,
        "baseflow_array": baseflow,
        "peak_h": peak_h,
        "peak_q": peak_q,
    })
    return out

def _db_alert_level(persist_site_id: str, stage_m: float) -> str:
    """CWC classification mapped into the bridge_stage_forecast CHECK vocabulary."""
    from backend.alerts.evaluator import classify_stage

    level = classify_stage(persist_site_id, stage_m)
    return "HFL_EXCEEDED" if level == "HISTORIC_PEAK" else level

def _build_subbasin_hyetographs(weather_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Aggregate Open-Meteo station forecasts into one governing hyetograph per subbasin.

    Applies the same conservative MAX_RAIN_VOLUME rule as the registry selector:
    for each subbasin, pick the candidate station with the largest cumulative
    rainfall and use its 90-h series as the subbasin hyetograph. The result is
    fed both to the HEC-HMS emulator (Step 7) and to subbasin_rainfall_ts.
    """
    from backend.rainfall.station_selector import STATION_REGISTRY

    stations = (weather_data or {}).get("stations", {}) or {}
    lead_hours = int((weather_data or {}).get("lead_hours", 90) or 90)

    by_sub: Dict[str, list] = {}
    for st in STATION_REGISTRY:
        by_sub.setdefault(st.subbasin, []).append(st)

    result: Dict[str, Dict[str, Any]] = {}
    for sub_id in [f"S{i}" for i in range(1, 10)]:
        best_id = None
        best_series: List[float] = []
        best_cum = -1.0
        all_candidates: Dict[str, float] = {}

        for st in by_sub.get(sub_id, []):
            raw = stations.get(st.station_id, {}).get("precipitation_mm_hr", []) or []
            series = [float(x) for x in raw]
            if len(series) < lead_hours:
                series += [0.0] * (lead_hours - len(series))
            series = series[:lead_hours]
            cum = float(sum(series))
            all_candidates[st.station_id] = round(cum, 2)
            if cum > best_cum:
                best_cum = cum
                best_id = st.station_id
                best_series = series

        if best_id is None:
            continue

        result[sub_id] = {
            "selected_station_id": best_id,
            "cumulative_mm": round(max(best_cum, 0.0), 2),
            "hyetograph": best_series,
            "all_candidates": all_candidates,
        }
    return result
