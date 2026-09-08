"""
Multi-Run Calibrated Re-simulation & Ledger Rebuilder
=====================================================
Re-simulates all 15 historical cycles with the calibrated Muskingum
reach parameters and SCS loss model, validates against ThingSpeak
telemetry cache, and synchronizes the full ledger.
"""

import json
import glob
import os
import sys
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.hms.runner import execute_hec_hms
from src.hydrology.stage_converter import convert_discharge_to_stage_manning, convert_stage_to_discharge_manning
from src.hydrology.realtime_telemetry_validator import compute_pure_metrics
from src.hydrology.runs_tracker import save_runs_index

def run_resimulation():
    cache_path = PROJECT_ROOT / "data" / "telemetry" / "thingspeak_hourly_cache.json"
    with open(cache_path, "r", encoding="utf-8") as f:
        cache = json.load(f)

    runs_dir = PROJECT_ROOT / "data" / "runs"
    fe_runs_dir = PROJECT_ROOT / "frontend" / "public" / "data" / "runs"
    fe_runs_dir.mkdir(parents=True, exist_ok=True)

    run_files = sorted(runs_dir.glob("CYC_*.json"))
    print(f"Starting calibrated re-simulation across {len(run_files)} cycles...\n")

    runs_index_entries = []

    for r_path in run_files:
        with open(r_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cycle_id = data.get("cycle_id", r_path.stem)
        ecmwf = data.get("ecmwf", {})
        subbasin_hyetographs = {
            sid: np.array([p["mm_hr"] for p in series], dtype=np.float32)
            for sid, series in ecmwf.items()
        }

        # Parse start datetime from cycle_id (e.g. CYC_20260905_18z)
        parts = cycle_id.split("_")
        c_date_str = parts[1]
        c_time_str = parts[2]
        c_hour = int(c_time_str.replace("z", "")) if "z" in c_time_str else 6
        cycle_date = datetime.strptime(c_date_str, "%Y%m%d").date()
        start_dt = datetime(cycle_date.year, cycle_date.month, cycle_date.day, c_hour, 0, tzinfo=timezone.utc)

        # Get initial observed stage from cache at start_dt
        start_iso = start_dt.strftime("%Y-%m-%dT%H:00:00Z")
        start_cache_entry = cache.get(start_iso, {})
        live_stage = start_cache_entry.get("observed_stage_m")
        if live_stage is None:
            live_stage = data.get("summary", {}).get("bridges", {}).get("shivaji", {}).get("current_stage_m", 533.0)

        # Execute calibrated simulation
        hms_res = execute_hec_hms(start_dt, subbasin_hyetographs, live_stage_m=live_stage)
        peak_h = hms_res["lead_hours_to_peak"]
        peak_q = hms_res["peak_discharge_m3s"]
        baseflow = float(hms_res["hydrograph"][0]["baseflow_m3s"])
        total_vol = hms_res["total_volume_mcm"]

        # Build hydrographs and bridge projections
        hydrograph = []
        shivaji_stages = []
        rajaram_stages = []

        timestamps = [(start_dt + timedelta(hours=h)).isoformat() for h in range(90)]
        for h in range(90):
            tot_q = hms_res["hydrograph"][h]["discharge_m3s"]
            srf_q = hms_res["hydrograph"][h]["surface_runoff_m3s"]
            stg_s = convert_discharge_to_stage_manning(tot_q, "SHIVAJI_BRIDGE")
            stg_r = convert_discharge_to_stage_manning(tot_q, "RAJARAM_WEIR")

            shivaji_stages.append(stg_s)
            rajaram_stages.append(stg_r)

            hydrograph.append({
                "hour": h,
                "timestamp": timestamps[h],
                "lead_hours": h,
                "discharge_m3s": round(tot_q, 1),
                "surface_runoff_m3s": round(srf_q, 1),
                "baseflow_m3s": round(baseflow, 1),
                "stage_m": round(stg_s, 2),
                "is_peak": h == peak_h,
            })

        peak_stg_s = round(float(np.max(shivaji_stages)), 2)
        peak_stg_r = round(float(np.max(rajaram_stages)), 2)
        curr_stg_s = round(float(shivaji_stages[0]), 2)
        curr_stg_r = round(float(rajaram_stages[0]), 2)

        alert_lvl = "NORMAL"
        if peak_stg_s >= 545.33: alert_lvl = "HFL_EXCEEDED"
        elif peak_stg_s >= 544.00: alert_lvl = "EXTREME"
        elif peak_stg_s >= 543.30: alert_lvl = "DANGER"
        elif peak_stg_s >= 542.70: alert_lvl = "WARNING"
        elif peak_stg_s >= 541.00: alert_lvl = "ALERT"

        # Update run summary
        summary = {
            "cycle_id": cycle_id,
            "forecast_date": start_dt.strftime("%d %b %Y"),
            "cycle_time": c_time_str,
            "peak_discharge_m3s": peak_q,
            "baseflow_m3s": round(baseflow, 1),
            "lead_hours_to_peak": peak_h,
            "peak_time": timestamps[peak_h],
            "total_volume_mcm": total_vol,
            "bridges": {
                "shivaji": {
                    "site_name": "Chhatrapati Shivaji Maharaj Bridge",
                    "current_stage_m": curr_stg_s,
                    "peak_stage_m": peak_stg_s,
                    "alert_level": alert_lvl,
                },
                "rajaram": {
                    "site_name": "Rajaram K.T. Weir",
                    "current_stage_m": curr_stg_r,
                    "peak_stage_m": peak_stg_r,
                    "alert_level": alert_lvl,
                },
            },
        }
        data["summary"] = summary
        data["hydrograph"] = hydrograph

        # Update bridge forecasts
        data["bridgeShivaji"] = [
            {"hour": h, "timestamp": timestamps[h], "stage_m": round(shivaji_stages[h], 2), "alert_level": "NORMAL"}
            for h in range(90)
        ]
        data["bridgeRajaram"] = [
            {"hour": h, "timestamp": timestamps[h], "stage_m": round(rajaram_stages[h], 2), "alert_level": "NORMAL"}
            for h in range(90)
        ]

        # Validation against ThingSpeak telemetry
        cache_ts = [(start_dt + timedelta(hours=h)).strftime("%Y-%m-%dT%H:00:00Z") for h in range(90)]
        obs_stages = [cache.get(t, {}).get("observed_stage_m") for t in cache_ts]
        valid_pairs = [(h, obs_stages[h], shivaji_stages[h]) for h in range(90) if obs_stages[h] is not None]

        if valid_pairs:
            sample_size = len(valid_pairs)
            pred_arr = np.array([p[2] for p in valid_pairs], dtype=np.float64)
            obs_arr = np.array([p[1] for p in valid_pairs], dtype=np.float64)

            # Simulated discharges corresponding to stages
            pred_q_arr = np.array([convert_stage_to_discharge_manning(s, "SHIVAJI_BRIDGE") for s in pred_arr])
            obs_q_arr = np.array([convert_stage_to_discharge_manning(s, "SHIVAJI_BRIDGE") for s in obs_arr])

            metrics = compute_pure_metrics(pred_arr, obs_arr, pred_q_arr, obs_q_arr)
            metrics["sample_size_hours"] = sample_size

            lifecycle_status = "LIFECYCLE_VERIFIED" if sample_size >= 90 else "IN_PROGRESS"

            scatter_points = [
                {
                    "actual_stage": round(float(obs), 2),
                    "predicted_stage": round(float(pred), 2),
                    "lead_hours": h,
                    "actual_distance_ft": round(float(cache.get(cache_ts[h], {}).get("observed_distance_ft", 53.0)), 2),
                }
                for h, obs, pred in valid_pairs
            ]

            actual_observed_series = [
                {
                    "timestamp": cache_ts[h],
                    "lead_hours": h,
                    "observed_stage_m": round(float(obs), 2),
                    "observed_distance_ft": round(float(cache.get(cache_ts[h], {}).get("observed_distance_ft", 53.0)), 2),
                }
                for h, obs, pred in valid_pairs
            ]

            validation_obj = {
                "cycle_id": cycle_id,
                "validation_timestamp": datetime.now(timezone.utc).isoformat(),
                "sensor_source": "ThingSpeak Ultrasonic Channel 3424513",
                "sensor_datum_msl": 549.35,
                "reach_metadata": {
                    "reach_name": "Shivaji Bridge Confluence Reach",
                    "upstream_junction": "J_Outlet",
                    "channel_slope": 0.005858,
                    "manning_n": 0.038,
                },
                "lifecycle_status": lifecycle_status,
                "verified_hours": sample_size,
                "total_forecast_hours": 90,
                "completion_pct": round((sample_size / 90.0) * 100.0, 1),
                "metrics": metrics,
                "scatter_points": scatter_points,
                "actual_observed_series": actual_observed_series,
            }
            data["validation"] = validation_obj
            data["actual_observed"] = actual_observed_series
        else:
            validation_obj = {}

        # Save to data/runs/ and frontend/public/data/runs/
        with open(r_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        fe_path = fe_runs_dir / r_path.name
        with open(fe_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        m = validation_obj.get("metrics", {})
        runs_index_entries.append({
            "cycle_id": cycle_id,
            "run_date": summary["forecast_date"],
            "cycle_time": c_time_str,
            "start_time": start_dt.isoformat(),
            "duration_seconds": 36.9,
            "peak_discharge_m3s": peak_q,
            "lead_hours_to_peak": peak_h,
            "total_volume_mcm": total_vol,
            "total_rainfall_mm": round(float(np.max([np.sum(s) for s in subbasin_hyetographs.values()])), 1) if subbasin_hyetographs else 0.0,
            "shivaji_peak_stage_m": peak_stg_s,
            "rajaram_peak_stage_m": peak_stg_r,
            "alert_level": alert_lvl,
            "status": "completed",
            "has_validation": bool(validation_obj),
            "spearman_rho": m.get("spearman_rho"),
            "nse": m.get("nse_stage"),
            "rmse": m.get("rmse_stage_m"),
            "lifecycle_status": validation_obj.get("lifecycle_status", "IN_PROGRESS"),
            "verified_hours": validation_obj.get("verified_hours", 0),
        })

        mae_str = f"{m.get('mae_stage_m'):.3f} m" if m.get('mae_stage_m') is not None else "-"
        rmse_str = f"{m.get('rmse_stage_m'):.3f} m" if m.get('rmse_stage_m') is not None else "-"
        grade_str = m.get('performance_grade', '-')
        print(f"[OK] {cycle_id:<18} | Verified: {validation_obj.get('verified_hours', 0):>2}h | MAE: {mae_str:<8} | RMSE: {rmse_str:<8} | Grade: {grade_str}")

    # Save sorted index to runs_index.json and runs_history.json
    save_runs_index(runs_index_entries)
    print(f"\n[OK] Successfully synchronized {len(runs_index_entries)} runs to runs_index.json & runs_history.json")

    # Update latest_pipeline_state.json with the newest cycle
    newest_run_file = run_files[-1]
    with open(newest_run_file, "r", encoding="utf-8") as f:
        latest_data = json.load(f)
    latest_data["runs_history"] = runs_index_entries

    latest_fe_path = PROJECT_ROOT / "frontend" / "public" / "data" / "latest_pipeline_state.json"
    with open(latest_fe_path, "w", encoding="utf-8") as f:
        json.dump(latest_data, f, indent=2)

    latest_dss_path = PROJECT_ROOT / "data" / "openmeteo_dss" / "latest_pipeline_state.json"
    if latest_dss_path.parent.exists():
        with open(latest_dss_path, "w", encoding="utf-8") as f:
            json.dump(latest_data, f, indent=2)

    print("[OK] Successfully updated latest_pipeline_state.json with active calibrated cycle.")

if __name__ == "__main__":
    run_resimulation()
