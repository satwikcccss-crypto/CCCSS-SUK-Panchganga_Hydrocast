"""
Standalone Historical Flood Event Runner v2
===========================================

Runs the HydroCast pipeline for historical flood events using
Open-Meteo archive data with station-based rainfall selection
for improved accuracy (mimics production pipeline station selection).

Usage:
    python run_historical_event.py --event 2019_august --start 2019-08-01 --end 2019-08-15
    python run_historical_event.py --event 2021_july --start 2021-07-18 --end 2021-07-31

This version uses the station network to select governing gages per subbasin,
similar to the production forecast cycle, which should improve rainfall
accuracy compared to a single-point estimate.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# Add project root to path
_HERE = Path(__file__).resolve()
PROJECT_ROOT = _HERE.parents[1]          # repo root (historical_checks/ is a child)
sys.path.insert(0, str(PROJECT_ROOT))

from src.ecmwf.open_meteo import fetch_point_forecast
from src.hms.runner import execute_hec_hms, _execute_hec_hms_core
from src.hydrology.stage_converter import convert_discharge_to_stage_manning
from src.ecmwf.station_selector import STATION_REGISTRY, SUBBASIN_AREAS_KM2, select_active_subbasin_gages
from src.hydrology.validation_metrics import (
    evaluate_forecast_accuracy,
    compute_nse,
    compute_rmse_mae,
    compute_kge,
    compute_pbias,
)

os.environ["HMS_FORCE_EMULATOR"] = "1"
log = logging.getLogger(__name__)

# Historical event configurations based on documentation
EVENTS = {
    "2019_august": {
        "name": "August 2019 Flood - Rajaram Weir",
        "start_date": "2019-08-01",
        "end_date": "2019-08-15",
        "observed": {
            "peak_stage_m": 546.97,  # from event narrative
            "peak_discharge_m3s": 2111.0,  # from report
            "peak_date": "2019-08-08",
            "peak_time": "11:00 AM",
            "receded_below_danger": "2019-08-14",
        },
        "model_window": "2019-08-01 to 2019-08-15",
    },
    "2021_july": {
        "name": "July 2021 Flood - Rajaram Weir",
        "start_date": "2021-07-18",
        "end_date": "2021-07-31",
        "observed": {
            "peak_stage_m": 547.83,  # from KMC 2025 assessment
            "peak_discharge_m3s": None,  # Not verified
            "peak_date": "2021-07-24",
            "peak_time": "3:00 AM (KMC) / 6:00 AM (NDTV)",
        },
        "model_window": "2021-07-18 to 2021-07-31",
    },
    "2025_august": {
        "name": "August 2025 Flood - Shivaji Bridge",
        "start_date": "2025-08-08",
        "end_date": "2025-08-22",
        "model_window": "2025-08-08 to 2025-08-22",
        "observed_csv": "data/shivaji_bridge_2025_hourly_observed.csv",
        "sim_hours": 360,
        # Life-safety calibration for saturated monsoon orographic crest:
        #   ia_frac=0.05 -> Ia = 0.05*S (saturated soil absorbs far less before runoff)
        #   alpha_k/alpha_lag < 1.0 -> faster wave celerity in steep Sahyadri canyons
        #   headwater_delta_cn -> +CN on S4/S5/S6/S7 (headwater subbasins)
        "ia_frac": 0.05,
        "alpha_k": 0.85,
        "alpha_lag": 0.86,
        "headwater_subbasins": ["S4", "S5", "S6", "S7"],
        "headwater_delta_cn": 2.0,
        "observed": {
            "peak_stage_m": 542.57,  # hourly-resampled observed peak, 2025-08-21 14:00 IST
            "peak_date": "2025-08-21",
            "peak_time": "14:00",
        },
    },
}


def fetch_historical_rainfall_for_station(
    lat: float,
    lon: float,
    start_date_str: str,
    end_date_str: str,
    hours: int = 90,
) -> np.ndarray:
    """
    Fetch historical hourly rainfall from Open-Meteo archive for a specific station.
    
    Uses the archive API (/v1/archive) which supports historical dates.
    Returns a ``hours``-long precipitation array aligned to start_date.
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    
    fetch_start = start_date_str
    fetch_end = end_date_str
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": fetch_start,
        "end_date": fetch_end,
        "hourly": "precipitation",
        "timezone": "UTC",
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise RuntimeError(f"Open-Meteo archive fetch failed: {response.text}")
    
    data = response.json()
    
    # Convert to DataFrame
    df = pd.DataFrame({
        "time": pd.to_datetime(data["hourly"]["time"]),
        "precip": data["hourly"]["precipitation"],
    })
    
    # Align to `hours`-long window starting at start_date
    window_start = pd.Timestamp(start_date_str)
    window_end = window_start + timedelta(hours=hours - 1)
    
    df_window = df[(df["time"] >= window_start) & (df["time"] <= window_end)].copy()
    
    # Create `hours`-long array (zero-padded if needed)
    arr = np.zeros(hours, dtype=np.float32)
    if len(df_window) > 0:
        df_window = df_window.sort_values("time")
        vals = df_window["precip"].values.astype(np.float32)
        n = min(len(vals), hours)
        arr[:n] = vals[:n]
    
    total_rain = float(np.sum(arr))
    log.info("Fetched %d hours of historical rainfall, total: %.1f mm", len(arr), total_rain)
    
    return arr


def run_historical_event(
    event_name: str,
    start_date_str: str,
    end_date_str: str,
    observed_peak_stage: float = None,
    observed_peak_discharge: float = None,
    event_info: dict = None,
) -> dict:
    """
    Run the HydroCast pipeline for a historical flood event using station-based
    rainfall selection for improved accuracy.
    
    Returns dict with calculated peak stage/discharge and observed values for comparison.
    """
    event_info = event_info or {}
    log.info("=" * 70)
    log.info("Historical Event: %s", event_name)
    log.info("Model window: %s to %s", start_date_str, end_date_str)
    log.info("=" * 70)
    
    # Parse dates
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    # Simulation window (default 90 h for legacy flash-flood events; 360 h for
    # the 14-day August 2025 monsoon flood so the simulated hydrograph spans the
    # full observed period including the Aug-21 peak).
    sim_hours = int(event_info.get("sim_hours", 90))
    
    # Load station config
    station_registry, subbasin_areas = load_station_config()
    
    # Step 1: Fetch historical rainfall for all 18 stations (from archive)
    log.info("Fetching historical rainfall from Open-Meteo archive for 18 stations (%d-h window)...", sim_hours)
    station_cumulative_mm = {}  # station_id -> total cumulative mm
    station_time_series = {}
    
    for st in STATION_REGISTRY:
        try:
            series = fetch_historical_rainfall_for_station(
                st.lat, st.lon, start_date_str, end_date_str, hours=sim_hours
            )
            station_time_series[st.station_id] = series
            cum_mm = float(np.sum(series))
            station_cumulative_mm[st.station_id] = cum_mm
        except Exception as e:
            log.warning("Station %s fetch failed: %s — marked as zeros", st.station_id, e)
            series = np.zeros(sim_hours, dtype=np.float32)
            station_time_series[st.station_id] = series
            station_cumulative_mm[st.station_id] = 0.0
    
    # Step 2: Dynamic subbasin station selection (using cumulative rainfall)
    log.info("Selecting governing gages per subbasin by max rain volume...")
    governing_subbasin_gages = select_active_subbasin_gages(station_cumulative_mm)
    
    log.info("Subbasin station selection:")
    for sub in ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"]:
        info = governing_subbasin_gages.get(sub, {})
        st_id = info.get("selected_station_id", "KARVIR")
        st_name = info.get("station_name", "N/A")
        cum_rain = info.get("cumulative_90h_mm", 0.0)
        log.info("  %s -> Station %s (%.1f mm)", sub, st_name, cum_rain)
    
    # Step 3: Build subbasin hyetographs from governing stations
    subbasins_list = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"]
    subbasin_arrays = {}
    
    for sub in subbasins_list:
        info = governing_subbasin_gages.get(sub, {})
        st_id = info.get("selected_station_id", "KARVIR")
        series = station_time_series.get(st_id, np.zeros(sim_hours))
        subbasin_arrays[sub] = series.copy()
    
    # Step 4: Build life-safety parameter overrides from event config
    #   - ia_frac: SCS initial abstraction (0.05 = saturated monsoon)
    #   - alpha_k / alpha_lag: faster wave celerity (< 1.0 speeds up arrival)
    #   - headwater_delta_cn: +CN on headwater subbasins (more runoff generation)
    parameter_overrides = None
    ia_frac = None
    if event_info.get("ia_frac") is not None:
        ia_frac = float(event_info["ia_frac"])
    if event_info.get("alpha_k") is not None or event_info.get("headwater_delta_cn") is not None:
        sub_model_overrides = {}
        for sid in subbasins_list:
            cn_delta = 0.0
            if sid in event_info.get("headwater_subbasins", []):
                cn_delta = float(event_info.get("headwater_delta_cn", 0.0))
            sub_model_overrides[sid] = {
                "cn_delta": cn_delta,
            }
        reach_overrides = {}
        if event_info.get("alpha_k") is not None:
            ak = float(event_info["alpha_k"])
            for rid in ["R1", "R2", "R3", "R4", "R5"]:
                reach_overrides[rid] = {"k_scale": ak}
        if event_info.get("alpha_lag") is not None:
            alag = float(event_info["alpha_lag"])
            # lag scaling applied via sub_model_overrides below
            for sid in subbasins_list:
                sub_model_overrides[sid]["lag_scale"] = alag
        parameter_overrides = {
            "sub_models": sub_model_overrides,
            "reaches": reach_overrides,
            "alpha_k": event_info.get("alpha_k", 1.0),
            "alpha_lag": event_info.get("alpha_lag", 1.0),
            "delta_cn": 0.0,
            "muskingum_x": 0.25,
        }

    # Step 5: Run the HEC-HMS emulator with life-safety calibration
    log.info("Running HEC-HMS emulator for historical event...")
    run_dt = start_dt
    
    result = _execute_hec_hms_core(
        run_dt,
        subbasin_hyetographs=subbasin_arrays,
        live_stage_m=None,  # No live telemetry for historical
        parameter_overrides=parameter_overrides,
        amc=None,
        sim_hours=sim_hours,
        ia_frac=ia_frac,
    )
    
    peak_q = result["peak_discharge_m3s"]
    peak_h = result["lead_hours_to_peak"]
    peak_time = result["time_of_peak"]
    
    # Calculate stage from discharge at Shivaji Bridge
    peak_stage_shivaji = convert_discharge_to_stage_manning(peak_q, "SHIVAJI_BRIDGE")
    
    # Calculate stage at Rajaram Weir
    peak_stage_rajaram = convert_discharge_to_stage_manning(peak_q, "RAJARAM_WEIR")
    
    # Extract hourly hydrograph data
    hydrograph = result.get("hydrograph", [])
    # Convert to serializable format (ensure all values are basic types)
    hydrograph_serializable = []
    for entry in hydrograph:
        serializable_entry = {
            "hour": entry.get("hour"),
            "timestamp": entry.get("timestamp"),
            "discharge_m3s": float(entry.get("discharge_m3s", 0)),
            "surface_runoff_m3s": float(entry.get("surface_runoff_m3s", 0)),
            "baseflow_m3s": float(entry.get("baseflow_m3s", 0)),
            "stage_m_shivaji": float(convert_discharge_to_stage_manning(float(entry.get("discharge_m3s", 0)), "SHIVAJI_BRIDGE")) if entry.get("discharge_m3s") else None,
            "stage_m_rajaram": float(convert_discharge_to_stage_manning(float(entry.get("discharge_m3s", 0)), "RAJARAM_WEIR")) if entry.get("discharge_m3s") else None,
            "is_peak": entry.get("is_peak", False),
        }
        hydrograph_serializable.append(serializable_entry)
    
    # Build results
    results = {
        "event": event_name,
        "model_window": f"{start_date_str} to {end_date_str}",
        
        # Calculated results
        "calculated": {
            "peak_discharge_m3s": round(peak_q, 1),
            "peak_lead_hours": peak_h,
            "peak_time_iso": peak_time,
            "peak_stage_m_shivaji": round(peak_stage_shivaji, 2),
            "peak_stage_m_rajaram": round(peak_stage_rajaram, 2),
            "mean_catchment_rain_90h_mm": round(result["mean_catchment_rain_90h"], 1),
            "amc": result["amc"],
        },
        
        # Hourly hydrograph data (90 hours)
        "hydrograph": hydrograph_serializable,
        
        # Observed results (for comparison)
        "observed": {
            "peak_stage_m": observed_peak_stage,
            "peak_discharge_m3s": observed_peak_discharge,
            "peak_date": None,
            "peak_time": None,
        } if observed_peak_stage else {},
        
        # Error metrics
        "errors": {
            "stage_error_m": None,
            "discharge_error_pct": None,
        } if observed_peak_stage else {},
    }
    
    # Calculate error metrics if observed data available
    if observed_peak_stage is not None:
        stage_error = peak_stage_shivaji - observed_peak_stage
        discharge_error_pct = None
        if observed_peak_discharge is not None and observed_peak_discharge > 0:
            discharge_error_pct = ((peak_q - observed_peak_discharge) / observed_peak_discharge) * 100
        
        results["errors"] = {
            "stage_error_m": round(stage_error, 2),
            "discharge_error_pct": round(discharge_error_pct, 1) if discharge_error_pct is not None else None,
        }

    # Hourly validation against the cleaned observed telemetry (2025 event)
    validation = {}
    observed_csv = event_info.get("observed_csv")
    if observed_csv:
        obs_path = Path(observed_csv)
        if not obs_path.is_absolute():
            obs_path = PROJECT_ROOT / obs_path
        if obs_path.exists():
            obs_df = pd.read_csv(obs_path, parse_dates=["timestamp"])
            obs_df = obs_df.dropna(subset=["stage_m"]).copy()
            obs_df["timestamp"] = pd.to_datetime(obs_df["timestamp"])

            # Simulated hourly stage at Shivaji Bridge from the emulator hydrograph.
            sim_rows = []
            for entry in hydrograph_serializable:
                ts = entry.get("timestamp")
                if ts is None:
                    continue
                sim_rows.append({
                    "timestamp": pd.to_datetime(ts),
                    "sim_stage_m": float(entry.get("stage_m_shivaji") or 0.0),
                    "sim_discharge_m3s": float(entry.get("discharge_m3s") or 0.0),
                })
            sim_df = pd.DataFrame(sim_rows)

            merged = pd.merge(obs_df, sim_df, on="timestamp", how="inner")
            if len(merged) >= 3:
                sim_s = merged["sim_stage_m"].to_numpy(dtype=float)
                obs_s = merged["stage_m"].to_numpy(dtype=float)
                nse = compute_nse(sim_s, obs_s)
                rmse, mae = compute_rmse_mae(sim_s, obs_s)
                kge = compute_kge(sim_s, obs_s)
                pbias = compute_pbias(sim_s, obs_s)

                # Peak stage & timing error on the aligned (matched) series.
                obs_peak_idx = int(np.argmax(obs_s))
                sim_peak_idx = int(np.argmax(sim_s))
                obs_peak_stage = float(obs_s[obs_peak_idx])
                sim_peak_stage = float(sim_s[sim_peak_idx])
                obs_peak_ts = merged.iloc[obs_peak_idx]["timestamp"]
                sim_peak_ts = merged.iloc[sim_peak_idx]["timestamp"]
                peak_stage_error = sim_peak_stage - obs_peak_stage
                peak_timing_error_h = (sim_peak_ts - obs_peak_ts).total_seconds() / 3600.0

                validation = {
                    "nse_stage": nse,
                    "kge_stage": kge,
                    "rmse_stage_m": rmse,
                    "mae_stage_m": mae,
                    "pbias_stage_pct": pbias,
                    "matched_hours": int(len(merged)),
                    "peak_stage_error_m": round(peak_stage_error, 2),
                    "peak_timing_error_h": round(peak_timing_error_h, 2),
                    "observed_peak_stage_m": round(obs_peak_stage, 2),
                    "observed_peak_timestamp": str(obs_peak_ts),
                    "simulated_peak_stage_m": round(sim_peak_stage, 2),
                    "simulated_peak_timestamp": str(sim_peak_ts),
                }
                log.info("HOURLY VALIDATION vs observed (%d matched hours):", len(merged))
                log.info("  NSE=%.4f  KGE=%.4f  RMSE=%.3f m  MAE=%.3f m  PBIAS=%.2f%%",
                         nse, kge, rmse, mae, pbias)
                log.info("  Peak stage error: %.2f m  |  Peak timing error: %.2f h",
                         peak_stage_error, peak_timing_error_h)
        else:
            log.warning("Observed CSV not found: %s", obs_path)
    results["validation"] = validation

    # Log summary
    log.info("RESULTS SUMMARY")
    log.info("=" * 70)
    log.info("Calculated Peak Discharge: %.1f m³/s at T+%dh", peak_q, peak_h)
    log.info("Calculated Peak Stage (Shivaji): %.2f m MSL", peak_stage_shivaji)
    log.info("Calculated Peak Stage (Rajaram): %.2f m MSL", peak_stage_rajaram)
    
    if observed_peak_stage is not None:
        log.info("Observed Peak Stage: %.2f m MSL", observed_peak_stage)
        log.info("Stage Error: %.2f m (calculated - observed)", stage_error)
        if discharge_error_pct is not None:
            log.info("Discharge Error: %.1f%% (calculated - observed)", discharge_error_pct)
    
    log.info("AMC Regime: %s", result["amc"])
    log.info("Mean 90h Catchment Rain: %.1f mm", result["mean_catchment_rain_90h"])
    log.info("=" * 70)
    
    return results


def load_station_config():
    """Load station registry and subbasin areas."""
    return STATION_REGISTRY, SUBBASIN_AREAS_KM2


def main():
    parser = argparse.ArgumentParser(
        description="Run HydroCast pipeline for historical flood events (v2 with station selection)"
    )
    parser.add_argument(
        "--event",
        choices=sorted(EVENTS.keys()),
        help="Historical flood event to analyze",
        required=True,
    )
    parser.add_argument(
        "--start",
        help="Start date (YYYY-MM-DD). Overrides event default.",
    )
    parser.add_argument(
        "--end",
        help="End date (YYYY-MM-DD). Overrides event default.",
    )
    
    args = parser.parse_args()
    
    # Determine event parameters
    event_key = args.event
    event_info = EVENTS[event_key]
    
    # Use specified dates or event defaults
    start_date = args.start or event_info["start_date"]
    end_date = args.end or event_info["end_date"]
    
    # Get observed values from event config
    observed_stage = event_info["observed"].get("peak_stage_m")
    observed_discharge = event_info["observed"].get("peak_discharge_m3s")
    
    # Run the historical event
    results = run_historical_event(
        event_name=event_info["name"],
        start_date_str=start_date,
        end_date_str=end_date,
        observed_peak_stage=observed_stage,
        observed_peak_discharge=observed_discharge,
        event_info=event_info,
    )
    
    # Save results to file for later analysis
    output_path = _HERE.parent / f"historical_event_{event_key}_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info("Results saved to %s", output_path)
    
    # Print summary
    print("\n" + "=" * 70)
    print("HISTORICAL EVENT ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"Event: {results['event']}")
    print(f"Model window: {results['model_window']}")
    print()
    print("CALCULATED:")
    print(f"  Peak Discharge: {results['calculated']['peak_discharge_m3s']} m³/s")
    print(f"  Peak Lead Time: +{results['calculated']['peak_lead_hours']}h")
    print(f"  Peak Stage (Shivaji): {results['calculated']['peak_stage_m_shivaji']} m MSL")
    print(f"  Peak Stage (Rajaram): {results['calculated']['peak_stage_m_rajaram']} m MSL")
    print(f"  AMC: {results['calculated']['amc']}")
    print()
    if results['observed']:
        print("OBSERVED:")
        print(f"  Peak Stage: {results['observed']['peak_stage_m']} m MSL")
        if results['errors']['stage_error_m'] is not None:
            print(f"  Stage Error: {results['errors']['stage_error_m']} m")
        if results['errors']['discharge_error_pct'] is not None:
            print(f"  Discharge Error: {results['errors']['discharge_error_pct']}%")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    main()