"""External integration feeds for HYDROSIM and the public API."""
from __future__ import annotations

import csv
import io
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response

from backend.api.limits import RATE_LIMIT_PUBLIC, limiter
from backend.api.runtime import (
    PublicDep,
    _load_pipeline_state,
    _row_get,
    get_pool,
    log,
)

_FEED_CACHE: dict[str, Any] = {"payload": None, "cached_at": 0.0}
_FEED_CACHE_TTL_SEC = 20.0

router = APIRouter()

@router.get(
    "/api/v1/water-levels",
    dependencies=[PublicDep],
    tags=["Integration"],
    summary="HydroCast water levels (simplest URL)",
    response_description="Latest forecast stage/discharge series for both bridges (JSON or CSV).",
    responses={404: {"description": "No forecast cycle is available yet."}},
)
@router.get(
    "/api/v1/hydrocast/water-levels",
    dependencies=[PublicDep],
    tags=["Integration"],
    summary="HydroCast-branded water-level URL",
    response_description="Same payload as /api/v1/water-levels.",
    responses={404: {"description": "No forecast cycle is available yet."}},
)
@router.get(
    "/api/v1/hydrosim/water-levels",
    dependencies=[PublicDep],
    tags=["Integration"],
    summary="Hydrosim alias for the water-level feed",
    response_description="Same payload as /api/v1/water-levels.",
    responses={404: {"description": "No forecast cycle is available yet."}},
)
@router.get(
    "/api/v1/integration/hydrosim/stage",
    dependencies=[PublicDep],
    tags=["Integration"],
    summary="Water-level boundary conditions for Hydrosim (HEC-RAS)",
    response_description="90-hour stage series per bridge, with datum/thresholds (JSON or CSV).",
    responses={404: {"description": "No forecast cycle is available yet."}},
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def hydrosim_stage(
    request: Request,
    site_id: Optional[str] = Query(None, max_length=50),
    fmt: str = Query("json", alias="format", pattern="^(json|csv)$"),
):
    """Stage hydrographs shaped for a HEC-RAS unsteady-flow boundary condition.

    **Authentication.** The easiest way is to put the read-only key in the URL
    (Open-Meteo style) and paste it straight into a browser or Python::

        GET /api/v1/hydrocast/water-levels?key=<HYDROCAST_READONLY_KEY>

    The key may also be sent as a header (preferred for production, because
    query strings can appear in access logs)::

        X-API-Key: <HYDROCAST_READONLY_KEY>

    **JSON** (default) returns one object per bridge with metadata, WRD
    thresholds and a hourly ``series``. **CSV** (``?format=csv``) returns the
    long/tidy form that is easy to import as a stage hydrograph::

        site_id,site_name,forecast_time_utc,lead_hours,stage_m,discharge_m3s,alert_level,is_above_danger

    **Datum.** ``stage_m`` is on the WRD gauge datum; ``zero_datum_m`` is the
    site's zero offset. HEC-RAS needs a common vertical datum, so apply
    ``stage_m - zero_datum_m`` (or the datum expected by your geometry) before
    assigning the boundary condition. Do not silently mix datums.

    The series is the *latest* forecast cycle only — never a blend of cycles.
    """
    rows = []
    run = None
    try:
        pool = await get_pool()
        if pool is not None:
            async with pool.acquire() as conn:
                run = await conn.fetchrow(
                    "SELECT run_id, start_time FROM simulation_runs ORDER BY start_time DESC LIMIT 1"
                )
                rows = await conn.fetch(
                    """
                    SELECT f.site_id, b.site_name, b.river_name, b.latitude, b.longitude,
                           b.alert_stage_m, b.warning_stage_m, b.danger_stage_m, b.hfl_m,
                           b.zero_datum_m,
                           f.forecast_time, f.lead_hours, f.stage_m, f.discharge_m3s,
                           f.alert_level, f.is_above_danger
                    FROM bridge_stage_forecast f
                    JOIN bridge_sites b ON b.site_id = f.site_id
                    WHERE f.forecast_run_id = (
                        SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1
                    )
                      AND ($1::text IS NULL OR f.site_id = $1)
                    ORDER BY f.site_id, f.lead_hours
                    """,
                    site_id,
                )
    except Exception as e:
        log.warning("Water levels DB fallback: %s", e)
        state = _load_pipeline_state()
        if state:
            all_forecast = []
            for key in ("bridgeShivaji", "bridgeRajaram"):
                b = state.get(key, {})
                if not b:
                    continue
                s = b.get("site", {})
                sid = s.get("site_id", "")
                if site_id and sid != site_id:
                    continue
                for f in b.get("forecast", []):
                    all_forecast.append({
                        "site_id": sid,
                        "site_name": s.get("site_name", ""),
                        "forecast_time": f.get("forecast_time", ""),
                        "lead_hours": f.get("lead_hours", 0),
                        "stage_m": f.get("stage_m", 0),
                        "discharge_m3s": f.get("discharge_m3s", 0),
                        "alert_level": f.get("alert_level", "NORMAL"),
                        "is_above_danger": f.get("is_above_danger", False),
                    })
            if all_forecast:
                return {"cycle_id": state.get("cycle_id", ""), "issued_at": state.get("run_dt", ""), "sites": all_forecast}

    if not run:
        raise HTTPException(
            status_code=404, detail="No forecast cycle available for Hydrosim yet"
        )

    cycle_id = str(_row_get(run, "run_id", "unknown"))
    start_time = _row_get(run, "start_time")
    issued_at = start_time.isoformat() if hasattr(start_time, "isoformat") else str(start_time)

    if fmt == "csv":
        buf = io.StringIO(newline="")
        writer = csv.writer(buf)
        writer.writerow([
            "site_id", "site_name", "forecast_time_utc", "lead_hours",
            "stage_m", "discharge_m3s", "alert_level", "is_above_danger",
        ])
        for r in rows:
            ft = _row_get(r, "forecast_time")
            writer.writerow([
                _row_get(r, "site_id", ""),
                _row_get(r, "site_name", ""),
                ft.isoformat() if hasattr(ft, "isoformat") else str(ft),
                _row_get(r, "lead_hours", ""),
                _row_get(r, "stage_m", ""),
                _row_get(r, "discharge_m3s", ""),
                _row_get(r, "alert_level", ""),
                bool(_row_get(r, "is_above_danger", False)),
            ])
        safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", cycle_id)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="hydrocast_stage_{safe_id}.csv"'
            },
        )

    sites: dict[str, dict] = {}
    for r in rows:
        sid = str(_row_get(r, "site_id", ""))
        site = sites.setdefault(
            sid,
            {
                "site_id": sid,
                "site_name": _row_get(r, "site_name"),
                "river_name": _row_get(r, "river_name"),
                "latitude": _row_get(r, "latitude"),
                "longitude": _row_get(r, "longitude"),
                "zero_datum_m": _row_get(r, "zero_datum_m"),
                "thresholds": {
                    "alert_m": _row_get(r, "alert_stage_m"),
                    "warning_m": _row_get(r, "warning_stage_m"),
                    "danger_m": _row_get(r, "danger_stage_m"),
                    "hfl_m": _row_get(r, "hfl_m"),
                },
                "series": [],
            },
        )
        ft = _row_get(r, "forecast_time")
        site["series"].append(
            {
                "forecast_time": ft.isoformat() if hasattr(ft, "isoformat") else str(ft),
                "lead_hours": _row_get(r, "lead_hours"),
                "stage_m": _row_get(r, "stage_m"),
                "discharge_m3s": _row_get(r, "discharge_m3s"),
                "alert_level": _row_get(r, "alert_level"),
                "is_above_danger": bool(_row_get(r, "is_above_danger", False)),
            }
        )

    return {
        "schema_version": "1.0",
        "source": "HydroCast",
        "cycle_id": cycle_id,
        "issued_at": issued_at,
        "units": {"stage": "m", "discharge": "m3/s"},
        "vertical_datum": (
            "WRD gauge datum; zero_datum_m is the site zero offset. "
            "Align to your HEC-RAS geometry datum before use."
        ),
        "sites": list(sites.values()),
    }

@router.get(
    "/api/SUK_hydrocast_v1",
    tags=["SUK Public API"],
    summary="Shivaji University Kolhapur HydroCast v1 Flood Intelligence Feed (Open Public Access)",
    response_description="All-in-one completely open, read-only, rate-limited flood intelligence feed for SUK. No API key required.",
)
@router.get(
    "/api/v1/SUK_hydrocast_v1",
    tags=["SUK Public API"],
    summary="Shivaji University Kolhapur HydroCast v1 Flood Intelligence Feed (v1 alias, Open Access)",
)
@router.get(
    "/api/v1/hydrocast/complete",
    tags=["Integration"],
    summary="Comprehensive HydroCast Forecast (Open Access)",
    response_description="All-in-one flood intelligence: peak stages, peak discharge, runoff volume, arrival times, station rainfall peaks, and 90-hr hydrographs.",
)
@router.get(
    "/api/v1/forecast/complete",
    tags=["Integration"],
    summary="Alias for comprehensive forecast feed",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def complete_forecast_feed(request: Request, response: Response):
    """
    Open-Meteo style comprehensive flood forecast feed.

    Accessible with ?key=<HYDROCAST_READONLY_KEY> or X-API-Key header.

    Returns:
      1. summary: peak discharge, total volume, arrival times, alert level.
      2. bridges: 90-hr stage & discharge hydrographs and peaks for Shivaji Bridge & Rajaram Weir.
      3. stations_rainfall: station-wise 90-hr cumulative rainfall, peak intensity, and peak timestamp.
      4. outlet_hydrograph_90h: full 90-hr discharge hydrograph.
    """
    global _FEED_CACHE
    now = time.time()
    if _FEED_CACHE["payload"] and (now - _FEED_CACHE["cached_at"] < _FEED_CACHE_TTL_SEC):
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = "public, max-age=20"
        return _FEED_CACHE["payload"]

    state = _load_pipeline_state() or {}
    run = None
    bridge_rows = []
    hydro_rows = []

    try:
        pool = await get_pool()
        if pool is not None:
            async with pool.acquire() as conn:
                run = await conn.fetchrow("""
                    SELECT run_id, peak_discharge_m3s, lead_hours_to_peak,
                           total_volume_mcm, peak_stage_m, alert_level, start_time
                    FROM simulation_runs
                    ORDER BY start_time DESC LIMIT 1
                """)
                if run:
                    run_id = run["run_id"]
                    bridge_rows = await conn.fetch("""
                        SELECT f.site_id, f.forecast_time, f.lead_hours, f.stage_m,
                               f.discharge_m3s, f.alert_level, f.is_above_danger,
                               b.site_name, b.alert_stage_m, b.warning_stage_m, b.danger_stage_m, b.hfl_m
                        FROM bridge_stage_forecast f
                        JOIN bridge_sites b ON b.site_id = f.site_id
                        WHERE f.forecast_run_id = $1
                        ORDER BY f.site_id, f.lead_hours
                    """, run_id)
                    hydro_rows = await conn.fetch("""
                        SELECT lead_hours, discharge_m3s, stage_m, timestamp
                        FROM hydrograph_results
                        WHERE run_id = $1
                        ORDER BY lead_hours ASC
                    """, run_id)
    except Exception as e:
        log.warning("Complete forecast DB query fallback: %s", e)

    # Summary
    summary_data = state.get("summary", {})
    cycle_id = str(_row_get(run, "run_id", summary_data.get("cycle_id", "CYC_LATEST")))
    issued_at = _row_get(run, "start_time", summary_data.get("forecast_date", datetime.now(timezone.utc).isoformat()))
    if hasattr(issued_at, "isoformat"):
        issued_at = issued_at.isoformat()

    peak_q = float(_row_get(run, "peak_discharge_m3s", summary_data.get("peak_discharge_m3s", 0.0)))
    total_vol = float(_row_get(run, "total_volume_mcm", summary_data.get("total_volume_mcm", 0.0)))
    lead_to_peak = int(_row_get(run, "lead_hours_to_peak", summary_data.get("lead_hours_to_peak", 0)))
    alert_lvl = str(_row_get(run, "alert_level", summary_data.get("alert_level", "NORMAL")))
    peak_arrival = summary_data.get("peak_arrival", {})

    # Bridges 90h series
    bridges = {}
    if bridge_rows:
        for r in bridge_rows:
            sid = str(r["site_id"])
            if sid not in bridges:
                bridges[sid] = {
                    "site_id": sid,
                    "site_name": str(r["site_name"]),
                    "alert_stage_m": float(r["alert_stage_m"] or 0),
                    "warning_stage_m": float(r["warning_stage_m"] or 0),
                    "danger_stage_m": float(r["danger_stage_m"] or 0),
                    "hfl_m": float(r["hfl_m"] or 0),
                    "current_stage_m": float(r["stage_m"] or 0),
                    "peak_stage_m": 0.0,
                    "peak_discharge_m3s": 0.0,
                    "series_90h": [],
                }
            ft = r["forecast_time"]
            ft_str = ft.isoformat() if hasattr(ft, "isoformat") else str(ft)
            bridges[sid]["series_90h"].append({
                "lead_hours": int(r["lead_hours"]),
                "forecast_time": ft_str,
                "stage_m": float(r["stage_m"] or 0),
                "discharge_m3s": float(r["discharge_m3s"] or 0),
                "alert_level": str(r["alert_level"]),
                "is_above_danger": bool(r.get("is_above_danger", False)),
            })
        for sid, b in bridges.items():
            if b["series_90h"]:
                b["peak_stage_m"] = max(p["stage_m"] for p in b["series_90h"])
                b["peak_discharge_m3s"] = max(p["discharge_m3s"] for p in b["series_90h"])
                b["current_stage_m"] = b["series_90h"][0]["stage_m"]
    else:
        for key, sid in (("bridgeShivaji", "SHIVAJI_BRIDGE"), ("bridgeRajaram", "RAJARAM_BRIDGE")):
            b_state = state.get(key, {})
            site_info = b_state.get("site", {})
            fc = b_state.get("forecast", [])
            pk_st = max((p.get("stage_m", 0) for p in fc), default=0.0) if fc else 0.0
            pk_q_b = max((p.get("discharge_m3s", 0) for p in fc), default=0.0) if fc else 0.0
            bridges[sid] = {
                "site_id": sid,
                "site_name": site_info.get("site_name", sid),
                "alert_stage_m": float(site_info.get("alert_stage_m", 0)),
                "warning_stage_m": float(site_info.get("warning_stage_m", 0)),
                "danger_stage_m": float(site_info.get("danger_stage_m", 0)),
                "hfl_m": float(site_info.get("hfl_m", 0)),
                "current_stage_m": fc[0].get("stage_m", 0) if fc else 0.0,
                "peak_stage_m": pk_st,
                "peak_discharge_m3s": pk_q_b,
                "series_90h": fc,
            }

    # Station-wise rainfall peaks and totals
    stations_rainfall = []
    gauges = state.get("gauges", {})
    stations_list = {s.get("station_id"): s.get("station_name") for s in state.get("stations", [])}
    for st_id, points in gauges.items():
        if not points:
            continue
        peak_pt = max(points, key=lambda x: x.get("mm_hr", 0.0))
        tot = sum(x.get("mm_hr", 0.0) for x in points)
        stations_rainfall.append({
            "station_id": st_id,
            "station_name": stations_list.get(st_id, st_id),
            "peak_rainfall_mm_hr": round(float(peak_pt.get("mm_hr", 0.0)), 2),
            "peak_time": peak_pt.get("timestamp"),
            "cumulative_90h_mm": round(float(tot), 2),
        })

    # Outlet hydrograph 90h
    if hydro_rows:
        outlet_90h = [
            {
                "lead_hours": int(r["lead_hours"]),
                "discharge_m3s": float(r["discharge_m3s"] or 0),
                "stage_m": float(r["stage_m"] or 0),
                "timestamp": r["timestamp"].isoformat() if hasattr(r["timestamp"], "isoformat") else str(r["timestamp"]),
            }
            for r in hydro_rows
        ]
    else:
        outlet_90h = state.get("hydrograph", [])

    payload = {
        "status": "success",
        "cycle_id": cycle_id,
        "issued_at": issued_at,
        "summary": {
            "peak_discharge_m3s": peak_q,
            "total_volume_mcm": total_vol,
            "lead_hours_to_peak": lead_to_peak,
            "alert_level": alert_lvl,
            "peak_arrival": peak_arrival,
        },
        "bridges": bridges,
        "stations_rainfall": sorted(stations_rainfall, key=lambda x: x["cumulative_90h_mm"], reverse=True),
        "outlet_hydrograph_90h": outlet_90h,
    }

    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = "public, max-age=20"
    _FEED_CACHE["payload"] = payload
    _FEED_CACHE["cached_at"] = now
    return payload
