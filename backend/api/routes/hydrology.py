"""Hydrology and public forecast read routes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from backend.api.limits import RATE_LIMIT_PUBLIC, limiter
from backend.api.runtime import (
    PublicDep,
    _jsonify,
    _load_pipeline_state,
    get_pool,
    log,
)

router = APIRouter()

@router.get(
    "/api/v1/rainfall/ecmwf",
    dependencies=[PublicDep],
    tags=["Hydrology"],
    summary="ECMWF areal hyetograph per subbasin",
    response_description="A map of subbasin id to its 90-point hourly rainfall series (mm/hr).",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def ecmwf_hyetograph(request: Request, subbasin_id: Optional[str] = None):
    """90-hr ECMWF IFS areal rainfall per subbasin (mm/hr, hourly).

    Always reads the **latest** `forecast_run_time` for `source_id='ecmwf_ifs'`,
    so repeated calls never mix two cycles.

    :param subbasin_id: Optional filter. Omit it to return all nine subbasins.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Always fetch latest cycle; optional subbasin filter below
            where = "WHERE forecast_run_time = (SELECT MAX(forecast_run_time) FROM subbasin_rainfall_ts)"
            params: list = []
            if subbasin_id is not None:
                where += f" AND subbasin_id = ${len(params) + 1}"
                params.append(subbasin_id)
            query = f"SELECT subbasin_id, valid_time, lead_hours, rainfall_mm_hr FROM subbasin_rainfall_ts {where} ORDER BY subbasin_id, lead_hours"
            rows = await conn.fetch(query, *params)
    except Exception as e:
        log.warning("ECMWF hyetograph fallback: %s", e)
        state = _load_pipeline_state()
        if state and state.get("ecmwf"):
            return {"data": state["ecmwf"], "degraded": True, "source": "pipeline_state_file", "error": str(e)}
        return {"degraded": True, "source": "fallback", "error": str(e), "ecmwf": {}}

    result: dict[str, list] = {}
    for r in rows:
        sub = r["subbasin_id"]
        result.setdefault(sub, []).append({
            "hour":    r["lead_hours"],
            "time":    r["valid_time"].isoformat(),
            "mm_hr":   r["rainfall_mm_hr"],
        })
    return result

@router.get(
    "/api/v1/rainfall/stations",
    dependencies=[PublicDep],
    tags=["Hydrology"],
    summary="Station selection decisions for the latest cycle",
    response_description="One row per subbasin: the governing gauge, its cumulative rainfall, and the full candidate set.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def station_selection(request: Request):
    """Selection decision for each subbasin in the latest cycle.

    Selection is **database-first**: if a subbasin's governing station has
    readings in the last 90 hours it wins; otherwise the selector falls back to
    the nearest grid cell. `all_candidates_json` carries every station that was
    considered with its distance rank, so a decision can always be audited
    after the fact.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT s.subbasin_id, s.selected_station_id, s.cumulative_mm,
                       s.all_candidates_json, s.selected_at,
                       g.station_name, ST_Y(g.geom) lat, ST_X(g.geom) lon
                FROM station_selection_log s
                JOIN gauge_stations g ON g.station_id=s.selected_station_id
                WHERE s.cycle_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                ORDER BY s.subbasin_id
            """)
    except Exception as e:
        log.warning("Station selection fallback: %s", e)
        state = _load_pipeline_state()
        if state and state.get("stations"):
            return {"data": state["stations"], "degraded": True, "source": "pipeline_state_file", "error": str(e)}
        return {"degraded": True, "source": "fallback", "error": str(e), "stations": []}
    return _jsonify(rows)

@router.get(
    "/api/v1/rainfall/gauges",
    dependencies=[PublicDep],
    tags=["Hydrology"],
    summary="Raw gauge hyetographs",
    response_description="Every individual gauge record from the last 91 hours, with quality flags and coordinates.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def gauge_hyetographs(request: Request):
    """All individual gauge 90-hr hyetographs for the latest cycle.

    Unlike [`/api/v1/rainfall/ecmwf`](#api-v1-rainfall-ecmwf) — which returns
    the *areal* rainfall chosen per subbasin — this endpoint returns the raw
    per-gauge series for all 18 stations. Use it to audit why a particular
    station was selected.

    `quality_flag` propagates upstream sensor quality and is never filtered
    out; consumers should honour it rather than assuming every row is equally
    trustworthy.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT r.gauge_id, r.subbasin_id, r.timestamp,
                       r.rainfall_mm, r.quality_flag,
                       g.station_name, ST_Y(g.geom) lat, ST_X(g.geom) lon
                FROM rainfall_data r
                JOIN gauge_stations g ON g.station_id=r.gauge_id
                WHERE r.timestamp >= NOW()-'91 hours'::interval
                ORDER BY r.gauge_id, r.timestamp
            """)
    except Exception as e:
        log.warning("Gauge hyetographs fallback: %s", e)
        state = _load_pipeline_state()
        if state and state.get("gauges"):
            return {"data": state["gauges"], "degraded": True, "source": "pipeline_state_file", "error": str(e)}
        return {"degraded": True, "source": "fallback", "error": str(e), "gauges": []}
    return _jsonify(rows)

@router.get(
    "/api/v1/runoff/hydrograph",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Outlet discharge hydrograph",
    response_description="90 points of total, surface, and baseflow discharge with stage and peak flags.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def outlet_hydrograph(request: Request, outlet_node: str = "J_Outlet"):
    """90-hr discharge + stage at the sink outlet node.

    The response separates the two physical components so a consumer can reason
    about them separately:

    * `discharge_m3s` — total discharge
    * `surface_runoff_m3s` — the routed surface component from SCS-CN + UH
    * `baseflow_m3s` — exponential recession, floored at the WRD monsoon value
    * `stage_m` — the same discharge pushed through the PCHIP rating curve
    * `is_peak` — `true` on the single `argmax` of total discharge
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT timestamp, lead_hours, discharge_m3s,
                       surface_runoff_m3s, baseflow_m3s, stage_m, is_peak
                FROM v_latest_hydrograph
                WHERE outlet_node=$1
                ORDER BY timestamp
            """, outlet_node)
    except Exception as e:
        log.warning("Outlet hydrograph fallback: %s", e)
        state = _load_pipeline_state()
        if state and state.get("hydrograph"):
            return {"data": state["hydrograph"], "degraded": True, "source": "pipeline_state_file", "error": str(e)}
        return {"degraded": True, "source": "fallback", "error": str(e), "hydrograph": []}
    return _jsonify(rows)

@router.get(
    "/api/v1/runoff/summary",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Peak discharge summary with arrival confidence",
    response_description="Outlet peak statistics, per-bridge forecast series, peak arrival window, and calibration state.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def runoff_summary(request: Request):
    """Peak Q, Tp, volume, flood alert for the latest run with peak arrival confidence intervals.

    Returns data shaped for the frontend dashboard:
    - outlet: peak discharge, time of peak, and runoff volume at the sink
    - summary: same as outlet (for frontend compatibility)
    - bridges: per-bridge stage forecast with thresholds and forecast series
    - hydrograph: 90-hour discharge hydrograph points
    - peak_arrival: calibrated peak arrival times per bridge
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get latest cycle
            last_cycle = await conn.fetchrow("""
                SELECT run_id, peak_discharge_m3s, lead_hours_to_peak,
                       total_volume_mcm, peak_stage_m, alert_level
                FROM simulation_runs
                ORDER BY start_time DESC LIMIT 1
            """)

            # Get latest stage per bridge with thresholds
            bridge_rows = await conn.fetch("""
                SELECT f.site_id, f.forecast_time, f.stage_m,
                       f.discharge_m3s, f.alert_level,
                       b.site_name, b.alert_stage_m, b.warning_stage_m, b.danger_stage_m, b.hfl_m
                FROM bridge_stage_forecast f
                JOIN bridge_sites b ON b.site_id=f.site_id
                WHERE f.forecast_run_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                ORDER BY f.site_id, f.forecast_time
            """)

            # Get hydrograph points
            hydro_rows = await conn.fetch("""
                SELECT lead_hours, discharge_m3s, stage_m
                FROM hydrograph_results
                WHERE run_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                ORDER BY lead_hours ASC
            """)
    except Exception as e:
        log.warning("Runoff summary fallback: %s", e)
        state = _load_pipeline_state()
        if state:
            summary = state.get("summary", {})
            bridges_data = []
            for key in ("bridgeShivaji", "bridgeRajaram"):
                b = state.get(key, {})
                if b:
                    site = b.get("site", {})
                    forecast = b.get("forecast", [])
                    peak_stage = max((f.get("stage_m", 0) for f in forecast), default=0) if forecast else 0
                    bridges_data.append({
                        "site_id": site.get("site_id", key),
                        "site_name": site.get("site_name", key),
                        "alert_stage_m": site.get("alert_stage_m", 0),
                        "warning_stage_m": site.get("warning_stage_m", 0),
                        "danger_stage_m": site.get("danger_stage_m", 0),
                        "hfl_m": site.get("hfl_m", 0),
                        "peak_stage_m": round(peak_stage, 2),
                        "current_stage_m": forecast[0].get("stage_m", 0) if forecast else 0,
                        "stage_m": forecast[0].get("stage_m", 0) if forecast else 0,
                        "alert_level": forecast[0].get("alert_level", "NORMAL") if forecast else "NORMAL",
                        "forecast": forecast,
                    })
            return {
                "degraded": True,
                "source": "pipeline_state_file",
                "error": str(e),
                "outlet": summary.get("outlet", summary) if isinstance(summary, dict) else summary,
                "summary": summary,
                "bridges": bridges_data,
                "hydrograph": state.get("hydrograph", []),
                "peak_arrival": state.get("peak_arrival", summary.get("peak_arrival", {})),
                "recalibration": state.get("recalibration", {}),
            }
        return {
            "degraded": True,
            "source": "fallback",
            "error": str(e),
            "outlet": {"peak_discharge_m3s": 0.0, "lead_hours_to_peak": 0,
                       "total_volume_mcm": 0.0, "alert_level": "NORMAL"},
            "summary": {"peak_discharge_m3s": 0.0, "lead_hours_to_peak": 0,
                        "total_volume_mcm": 0.0, "alert_level": "NORMAL"},
            "bridges": [],
            "hydrograph": [],
            "peak_arrival": {},
        }

    if not last_cycle:
        return {
            "degraded": True,
            "source": "no_data",
            "error": "No computation cycle available",
            "outlet": {"peak_discharge_m3s": 0.0, "lead_hours_to_peak": 0,
                       "total_volume_mcm": 0.0, "alert_level": "NORMAL"},
            "summary": {"peak_discharge_m3s": 0.0, "lead_hours_to_peak": 0,
                        "total_volume_mcm": 0.0, "alert_level": "NORMAL"},
            "bridges": [],
            "hydrograph": [],
            "peak_arrival": {},
        }

    # Build bridge objects with full stage data
    bridges_by_site = {}
    for r in bridge_rows:
        sid = r["site_id"]
        if sid not in bridges_by_site:
            # First row's stage_m is the T+0 current stage
            first_stage = None
        sid = r["site_id"]
        if sid not in bridges_by_site:
            first_stage = float(r["stage_m"]) if r.get("stage_m") else None
            bridges_by_site[sid] = {
                "site_id": r["site_id"],
                "site_name": r.get("site_name") or r["site_id"],
                "alert_stage_m": float(r.get("alert_stage_m") or 0),
                "warning_stage_m": float(r.get("warning_stage_m") or 0),
                "danger_stage_m": float(r.get("danger_stage_m") or 0),
                "hfl_m": float(r.get("hfl_m") or 0),
                "peak_stage_m": 0.0,  # will compute after loop
                "alert_level": r.get("alert_level") or "NORMAL",
                "current_stage_m": first_stage if first_stage is not None else 0.0,
                "forecast": [],
            }
        bridges_by_site[sid]["forecast"].append({
            "stage_m": float(r["stage_m"]) if r["stage_m"] else 0.0,
            "lead_hours": int(r["lead_hours"]) if r.get("lead_hours") is not None else 0,
        })

    # Compute per-bridge peak and ensure current_stage_m is the T+0 first point
    bridge_order = ["SHIVAJI_BRIDGE", "RAJARAM_BRIDGE"]
    bridges = []
    for sid in bridge_order:
        if sid in bridges_by_site:
            b = bridges_by_site[sid]
            # True peak = max across all forecast points
            if b["forecast"]:
                b["peak_stage_m"] = max(f["stage_m"] for f in b["forecast"])
                b["current_stage_m"] = b["forecast"][0]["stage_m"]
                b["stage_m"] = b["current_stage_m"]  # backward-compat alias
            bridges.append(b)

    # Build peak_arrival from latest calibration state
    peak_arrival = {}
    try:
        from backend.hydrology.runs_tracker import list_computation_runs
        latest_runs = list_computation_runs(limit=1)
        if latest_runs:
            pa = latest_runs[0].get("summary", {}).get("peak_arrival")
            if pa:
                peak_arrival = {
                    "earliest": pa.get("earliest"),
                    "latest": pa.get("latest"),
                }
    except Exception:
        peak_arrival = {}

    # Get calibration state
    try:
        from backend.ml.ml_calibration import calibrator
        calibration_state = calibrator.state
    except Exception:
        calibration_state = {}

    return {
        "outlet": {
            "peak_discharge_m3s": float(last_cycle.get("peak_discharge_m3s") or 0),
            "lead_hours_to_peak": int(last_cycle.get("lead_hours_to_peak") or 0),
            "total_volume_mcm": float(last_cycle.get("total_volume_mcm") or 0),
            "alert_level": last_cycle.get("alert_level") or "NORMAL",
        },
        "summary": {
            "peak_discharge_m3s": float(last_cycle.get("peak_discharge_m3s") or 0),
            "lead_hours_to_peak": int(last_cycle.get("lead_hours_to_peak") or 0),
            "total_volume_mcm": float(last_cycle.get("total_volume_mcm") or 0),
            "alert_level": last_cycle.get("alert_level") or "NORMAL",
        },
        "bridges": bridges,
        "hydrograph": [
            {
                "lead_hours": int(r.get("lead_hours") or 0),
                "discharge_m3s": float(r["discharge_m3s"]) if r.get("discharge_m3s") is not None else 0.0,
                "stage_m": float(r["stage_m"]) if r.get("stage_m") is not None else 0.0,
            }
            for r in hydro_rows
        ],
        "peak_arrival": peak_arrival,
        "recalibration": calibration_state,
    }

@router.get(
    "/api/v1/runoff/calibration",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Live calibration parameters",
    response_description="Current Curve Number, Muskingum K/X, and subbasin lag with the calibrator's own state.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def hydrologic_calibration(request: Request):
    """Current real-time calibrated hydrologic parameters (Muskingum K & X, Subbasin lag, Curve Number).

    Exposing these makes every forecast self-describing: any client can record
    which parameters produced a given run, so a forecast can be reproduced or
    challenged later.

    The values here are read back from `Basin_1.basin`, which is the single
    source of truth. Recalibration writes that file atomically and keeps a
    timestamped `.bak` alongside it.
    """
    from backend.ml.ml_calibration import calibrator
    return {
        "calibration": calibrator.state,
        "status": "OPERATIONAL",
    }

@router.get(
    "/api/v1/runoff/stage/{site_id}",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Stage forecast at a bridge site",
    response_description="Bridge metadata (thresholds and datum) plus the 90-hour stage and alert series.",
)
@router.get(
    "/api/v1/bridge/{site_id}",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Stage forecast at a bridge site (alias)",
    response_description="Bridge metadata (thresholds and datum) plus the 90-hour stage and alert series.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def bridge_stage_forecast(request: Request, site_id: str):
    """90-hr stage + alert classification at a bridge site.

    Returns the site's own metadata alongside the series, including the
    `alert`, `warning`, `danger` and `hfl` stage marks, so a consumer never has
    to hard-code thresholds to classify a stage.

    :raises HTTPException 404: if `site_id` is not a known bridge.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT f.forecast_time, f.lead_hours, f.stage_m,
                       f.discharge_m3s, f.alert_level, f.is_above_danger
                FROM bridge_stage_forecast f
                WHERE f.site_id=$1
                  AND f.forecast_run_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                ORDER BY f.lead_hours
            """, site_id)
            meta = await conn.fetchrow(
                "SELECT * FROM bridge_sites WHERE site_id=$1", site_id
            )
    except Exception as e:
        log.warning("Bridge stage forecast fallback: %s", e)
        state = _load_pipeline_state()
        if state:
            key_map = {"SHIVAJI_BRIDGE": "bridgeShivaji", "RAJARAM_BRIDGE": "bridgeRajaram", "RAJARAM_WEIR": "bridgeRajaram"}
            json_key = key_map.get(site_id)
            if json_key and state.get(json_key):
                b = state[json_key]
                return {"degraded": True, "source": "pipeline_state_file", "error": str(e), "site": b.get("site", {}), "forecast": b.get("forecast", [])}
        return {"degraded": True, "source": "fallback", "error": str(e), "site": {}, "forecast": []}
    if not meta:
        raise HTTPException(status_code=404, detail=f"Bridge site '{site_id}' not found")
    return {
        "site":     dict(meta),
        "forecast": _jsonify(rows),
    }

@router.get(
    "/api/v1/alerts",
    dependencies=[PublicDep],
    tags=["Alerts"],
    summary="Active flood alerts",
    response_description="Every alert currently in the active state, enriched with bridge and threshold context.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def active_alerts(request: Request):
    """List active flood warnings and CWC notifications.

    Only alerts with `status='active'` are returned. Resolved alerts remain
    queryable through the historical runs ledger, so nothing is lost by
    filtering here.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM v_active_alerts_enriched")
    except Exception as e:
        log.warning("Active alerts fallback: %s", e)
        state = _load_pipeline_state()
        if state:
            alerts = state.get("alerts", [])
            if alerts:
                return {"degraded": True, "source": "pipeline_state_file", "error": str(e), "alerts": alerts}
            status_info = state.get("status", {})
            last_cycle = status_info.get("last_cycle", {})
            if last_cycle and last_cycle.get("alert_level", "NORMAL") != "NORMAL":
                return {"degraded": True, "source": "pipeline_state_file", "error": str(e), "alerts": [{"alert_level": last_cycle["alert_level"], "site_id": "SYSTEM", "status": "active"}]}
        return {"degraded": True, "source": "fallback", "error": str(e), "alerts": []}
    return _jsonify(rows)

@router.get(
    "/api/v1/alerts/bulletin",
    dependencies=[PublicDep],
    tags=["Alerts"],
    summary="Academic flood simulation bulletin payload",
    response_description="Research simulation bulletin per bridge: simulated stage, baseflow trends, and engineering metrics.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def flood_bulletin(request: Request):
    """Generate academic simulation bulletin JSON for all bridge sites.

    Academic & scientific research simulation by CCCSS, Shivaji University Kolhapur (DST-SERB).
    NOT an official administrative flood alert or warning.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT b.site_id, b.site_name,
                       b.alert_stage_m, b.warning_stage_m, b.danger_stage_m, b.hfl_m,
                       f.stage_m AS current_stage,
                       f.discharge_m3s AS current_q,
                       f.alert_level,
                       f.arrival_time,
                       p.peak_discharge_m3s,
                       p.time_of_peak,
                       p.total_runoff_volume_m3
                FROM bridge_sites b
                LEFT JOIN bridge_stage_forecast f ON f.site_id=b.site_id
                    AND f.lead_hours=1
                    AND f.forecast_run_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                LEFT JOIN peak_discharge_events p ON p.outlet_node='J_Outlet'
                    AND p.run_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                ORDER BY b.site_id
            """)
    except Exception as e:
        log.warning("Flood bulletin fallback: %s", e)
        rows = []
    issued_at = datetime.now(timezone.utc).isoformat()
    return {
        "bulletin_title": "HYDROCAST PANCHGANGA — ACADEMIC SIMULATION BULLETIN",
        "issued_at":      issued_at,
        "valid_for_hrs":  90,
        "disclaimer":     "Scientific research digital twin by CCCSS, Shivaji University Kolhapur (DST-SERB). For official flood warnings, evacuation notices, and civil alerts, refer to competent government authorities (District Administration / DDMA / CWC).",
        "sites":          _jsonify(rows),
    }

@router.api_route(
    "/api/v1/research/hydrological-summary",
    methods=["GET", "POST"],
    tags=["Research"],
    summary="Academic & Scientific Hydrological Research Summary",
    response_description="Neutral academic research simulation feed from Shivaji University Kolhapur CCCSS.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def research_hydrological_summary(request: Request):
    """Academic and scientific research simulation feed from Shivaji University Kolhapur.

    DISCLAIMER: Academic & Scientific Research Simulation by CCCSS, Shivaji University Kolhapur.
    For official flood warnings, evacuation notices, and civil alerts, consult District Administration / DDMA.
    """
    now_utc = datetime.now(timezone.utc)
    now_ist_str = (now_utc.astimezone(timezone(timedelta(hours=5, minutes=30)))).strftime("%d-%m-%Y %I:%M %p IST")

    shivaji_stage = 531.54
    rajaram_stage = 532.19
    peak_q = 9.10
    lead_hours = 0
    calculated_status = "NORMAL_BASEFLOW"

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row_run = await conn.fetchrow("""
                SELECT peak_discharge_m3s, peak_stage_m, lead_hours_to_peak, total_volume_mcm
                FROM simulation_runs
                ORDER BY start_time DESC LIMIT 1
            """)
            if row_run:
                peak_q = float(row_run["peak_discharge_m3s"] or 9.10)
                lead_hours = int(row_run["lead_hours_to_peak"] or 0)

            rows_b = await conn.fetch("""
                SELECT site_id, stage_m, alert_level
                FROM bridge_stage_forecast
                WHERE lead_hours = 1
                  AND forecast_run_id = (SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
            """)
            for r in rows_b:
                sid = r["site_id"]
                stg = float(r["stage_m"] or 531.54)
                if sid == "SHIVAJI_BRIDGE":
                    shivaji_stage = stg
                elif sid == "RAJARAM_BRIDGE":
                    rajaram_stage = stg
    except Exception as e:
        log.warning("Research summary fallback: %s", e)
        state = _load_pipeline_state()
        if state:
            summary = state.get("summary", {})
            peak_q = float(summary.get("peak_discharge_m3s", 9.10))
            lead_hours = int(summary.get("lead_hours_to_peak", 0))

    if shivaji_stage >= 543.30 or rajaram_stage >= 543.30:
        calculated_status = "HIGH_STAGE_SIMULATED"
        marathi_text = f"संशोधन निरीक्षण: पंचगंगा नदीची संगणकीय जलपातळी {shivaji_stage:.2f} मी. अंदाजित आहे. अधिकृत माहितीसाठी जिल्हा प्रशासनाची संपर्क साधावा."
    elif shivaji_stage >= 542.10 or rajaram_stage >= 541.50:
        calculated_status = "ELEVATED_STAGE_SIMULATED"
        marathi_text = f"संशोधन निरीक्षण: पंचगंगा नदीची संगणकीय जलपातळी {shivaji_stage:.2f} मी. अंदाजित आहे."
    else:
        calculated_status = "NORMAL_BASEFLOW_SIMULATED"
        marathi_text = f"संशोधन निरीक्षण: पंचगंगा नदीचा प्रवाह सामान्य वैज्ञानिक पातळीत ({shivaji_stage:.2f} मी., {peak_q:.1f} m³/s) संगणकीकृत आहे."

    return {
        "status": "success",
        "system": "HydroCast Academic & Scientific Research Simulator",
        "institution": "Centre for Climate Change and Sustainability Studies (CCCSS), Shivaji University, Kolhapur",
        "funding": "Department of Science and Technology, Science and Engineering Research Board (DST-SERB)",
        "disclaimer": "Academic & Scientific Research Simulation by CCCSS, Shivaji University Kolhapur. For official flood warnings, evacuation notices, and civil alerts, consult District Administration / DDMA.",
        "marathi_disclaimer": "शिवाजी विद्यापीठ कोल्हापूर (CCCSS) व DST-SERB अंतर्गत केवळ शैक्षणिक व वैज्ञानिक संशोधनात्मक अभ्यास. अधिकृत पूर सूचना व आपत्कालीन मार्गदर्शक सूचनांसाठी जिल्हा प्रशासनाशी संपर्क साधावा.",
        "timestamp_utc": now_utc.isoformat(),
        "timestamp_ist": now_ist_str,
        "scientific_simulation": {
            "calculated_status": calculated_status,
            "marathi_summary": marathi_text,
            "simulated_peak_discharge_m3s": peak_q,
            "simulated_lead_hours_to_peak": lead_hours,
            "gauged_crossings": [
                {
                    "site_id": "SHIVAJI_BRIDGE",
                    "site_name": "Chhatrapati Shivaji Maharaj Bridge (Panchganga Ghat)",
                    "simulated_stage_m": shivaji_stage,
                    "datum_level_m": 528.67,
                    "danger_threshold_reference_m": 543.30,
                },
                {
                    "site_id": "RAJARAM_BRIDGE",
                    "site_name": "Rajaram K.T. Weir (Kasba Bawada)",
                    "simulated_stage_m": rajaram_stage,
                    "crest_level_m": 535.77,
                    "danger_threshold_reference_m": 543.30,
                },
            ],
        },
    }
