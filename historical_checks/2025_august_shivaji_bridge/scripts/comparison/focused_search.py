"""
Focused life-safety calibration test — August 2025 Shivaji Bridge.

Tests aggressive parameter combinations to meet life-safety criteria:
  * Peak stage sim >= obs (never under-predict)
  * |peak_err_m| <= 0.20 m, |peak_timing_err_h| <= 1.0 h
  * NSE >= 0.92, KGE >= 0.88

Parameters tested:
  * alpha_k: [0.60, 0.70, 0.80]  (faster routing = less attenuation)
  * alpha_lag: [0.60, 0.70, 0.80] (shorter lag = more concentrated runoff)
  * dcn_all: [4.0, 6.0, 8.0]     (maximum CN boost)
  * muskingum_x: [0.15, 0.20]     (less wedge storage = less attenuation)
  * ia_frac: 0.05 (saturated monsoon)
"""
import json
import copy
import itertools
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

REPO = Path("E:/hydrocast_complete")
BRIDGE = REPO / "historical_checks" / "2025_august_shivaji_bridge"
import sys
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "historical_checks"))

from src.hms.basin_parser import load_immutable_baseline
from src.hms.runner import _execute_hec_hms_core
from src.hydrology.stage_converter import (
    convert_discharge_to_stage_manning,
    convert_stage_to_discharge_manning,
)
from src.hydrology.validation_metrics import compute_nse, compute_rmse_mae, compute_kge, compute_pbias
from src.ecmwf.station_selector import STATION_REGISTRY, select_active_subbasin_gages
from run_historical_event import fetch_historical_rainfall_for_station   # noqa: E402

START = "2025-08-08"
END = "2025-08-22"
HOURS = 360
RUN_DT = datetime(2025, 8, 8, 0, 0, 0)

OUT_DIR = BRIDGE / "results" / "dynamic_calibration"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEADWATER_SUBS = ["S4", "S5", "S6", "S7"]


def fetch_hyetographs():
    station_ts, station_cum = {}, {}
    for st in STATION_REGISTRY:
        series = fetch_historical_rainfall_for_station(st.lat, st.lon, START, END, hours=HOURS)
        station_ts[st.station_id] = series
        station_cum[st.station_id] = float(np.sum(series))
    sel = select_active_subbasin_gages(station_cum)
    hyetos = {}
    for sub in [f"S{i}" for i in range(1, 10)]:
        info = sel.get(sub, {})
        sid = info.get("selected_station_id", "KARVEER")
        hyetos[sub] = station_ts.get(sid, np.zeros(HOURS, dtype=np.float32)).copy()
    return hyetos, sel


def run_sim(hyetos, alpha_k, alpha_lag, dcn_all, dcn_hw, musk_x, ia_frac):
    base_sub, base_reach = load_immutable_baseline()
    sub_models = copy.deepcopy(base_sub)
    reaches = copy.deepcopy(base_reach)

    for sid in sub_models:
        total_dcn = dcn_all + (dcn_hw if sid in HEADWATER_SUBS else 0.0)
        sub_models[sid]["cn"] = float(np.clip(sub_models[sid]["cn"] + total_dcn, 45.0, 95.0))
        sub_models[sid]["lag_min"] = float(sub_models[sid]["lag_min"] * alpha_lag)

    for rid in reaches:
        reaches[rid]["k_hr"] = float(reaches[rid]["k_hr"] * alpha_k)
        reaches[rid]["x"] = musk_x

    parameter_overrides = {
        "sub_models": {sid: {"cn": sub_models[sid]["cn"], "lag_min": sub_models[sid]["lag_min"]}
                       for sid in sub_models},
        "reaches": {rid: {"k_hr": reaches[rid]["k_hr"], "x": reaches[rid]["x"]}
                    for rid in reaches},
        "alpha_k": alpha_k, "alpha_lag": alpha_lag,
        "delta_cn": dcn_all, "muskingum_x": musk_x,
    }

    result = _execute_hec_hms_core(
        RUN_DT, subbasin_hyetographs=hyetos, live_stage_m=None,
        parameter_overrides=parameter_overrides, amc=None,
        sim_hours=HOURS, ia_frac=ia_frac,
    )

    rows = []
    for entry in result["hydrograph"]:
        ts = pd.to_datetime(entry["timestamp"])
        q = float(entry.get("discharge_m3s") or 0.0)
        rows.append({"timestamp": ts,
                     "stage_m": convert_discharge_to_stage_manning(q, "SHIVAJI_BRIDGE"),
                     "discharge_m3s": q})
    return pd.DataFrame(rows), result


def evaluate(sim_df, obs_df, params):
    m = pd.merge(
        obs_df[["timestamp", "stage_m"]].rename(columns={"stage_m": "obs_stage"}),
        sim_df[["timestamp", "stage_m"]].rename(columns={"stage_m": "sim_stage"}),
        on="timestamp", how="inner",
    )
    if len(m) < 3:
        return None
    sim_s = m["sim_stage"].to_numpy(dtype=float)
    obs_s = m["obs_stage"].to_numpy(dtype=float)
    nse = compute_nse(sim_s, obs_s)
    rmse, mae = compute_rmse_mae(sim_s, obs_s)
    kge = compute_kge(sim_s, obs_s)
    pbias = compute_pbias(sim_s, obs_s)
    oi = int(np.argmax(obs_s)); si = int(np.argmax(sim_s))
    peak_err = float(sim_s[si] - obs_s[oi])
    peak_dt_err = (m.iloc[si]["timestamp"] - m.iloc[oi]["timestamp"]).total_seconds() / 3600.0
    return {
        "nse": round(nse, 4), "kge": round(kge, 4),
        "rmse": round(rmse, 3), "mae": round(mae, 3), "pbias": round(pbias, 2),
        "peak_err_m": round(peak_err, 2),
        "peak_timing_err_h": round(peak_dt_err, 2),
        "obs_peak_m": round(float(obs_s[oi]), 2),
        "sim_peak_m": round(float(sim_s[si]), 2),
        "sim_peak_ts": str(m.iloc[si]["timestamp"]),
        "matched": int(len(m)), "params": params,
    }


def passes(r):
    return (r["peak_err_m"] >= 0.0 and abs(r["peak_err_m"]) <= 0.20
            and abs(r["peak_timing_err_h"]) <= 1.0
            and r["nse"] >= 0.92 and r["kge"] >= 0.88)


def main():
    hyetos, sel = fetch_hyetographs()
    obs = pd.read_csv(REPO / "data" / "shivaji_bridge_2025_hourly_observed.csv",
                      parse_dates=["timestamp"]).dropna(subset=["stage_m"])

    alpha_k_vals = [0.60, 0.70, 0.80]
    alpha_lag_vals = [0.60, 0.70, 0.80]
    dcn_all_vals = [4.0, 6.0, 8.0]
    dcn_hw_vals = [4.0]
    musk_x_vals = [0.15, 0.20]
    ia_frac_vals = [0.05]

    all_results = []
    passing = []
    total = (len(alpha_k_vals) * len(alpha_lag_vals) * len(dcn_all_vals) *
             len(dcn_hw_vals) * len(musk_x_vals) * len(ia_frac_vals))
    count = 0

    print(f"Focused search: {total} combinations...")
    for ak, al, dcn_a, dcn_h, mx, ia in itertools.product(
        alpha_k_vals, alpha_lag_vals, dcn_all_vals, dcn_hw_vals, musk_x_vals, ia_frac_vals
    ):
        count += 1
        params = {"alpha_k": ak, "alpha_lag": al, "dcn_all": dcn_a,
                  "dcn_hw": dcn_h, "muskingum_x": mx, "ia_frac": ia}
        try:
            sim_df, result = run_sim(hyetos, ak, al, dcn_a, dcn_h, mx, ia)
            r = evaluate(sim_df, obs, params)
            all_results.append(r)
            ok = passes(r)
            status = "PASS" if ok else ""
            print(f"  [{count:3d}/{total}] ak={ak} al={al} dcn={dcn_a}+{dcn_h} x={mx} "
                  f"-> NSE={r['nse']:.3f} KGE={r['kge']:.3f} peak_err={r['peak_err_m']:+.2f}m "
                  f"timing={r['peak_timing_err_h']:+.1f}h {status}")
            if ok:
                passing.append(r)
        except Exception as e:
            print(f"  [{count:3d}/{total}] ERROR: {e}")

    print(f"\nTotal: {total}, Passing: {len(passing)}")

    if passing:
        passing.sort(key=lambda r: (-r["nse"], abs(r["peak_err_m"])))
        best = passing[0]
        print(f"\nBEST PASSING: {json.dumps(best['params'], indent=2)}")
        print(f"  NSE={best['nse']:.3f} KGE={best['kge']:.3f} RMSE={best['rmse']:.3f}")
        print(f"  Peak: {best['sim_peak_m']}m vs {best['obs_peak_m']}m (err={best['peak_err_m']:+.2f}m)")
        print(f"  Timing err: {best['peak_timing_err_h']:+.1f}h")
    else:
        print("\nNO combination passes. Best by NSE:")
        all_results.sort(key=lambda r: -r["nse"])
        for r in all_results[:10]:
            print(f"  NSE={r['nse']:.3f} KGE={r['kge']:.3f} peak_err={r['peak_err_m']:+.2f}m "
                  f"timing={r['peak_timing_err_h']:+.1f}h params={r['params']}")

    with open(OUT_DIR / "focused_search_results.json", "w") as f:
        json.dump({"all_results": all_results, "passing": passing,
                   "best": passing[0] if passing else None}, f, indent=2, default=str)
    print(f"\nSaved to {OUT_DIR / 'focused_search_results.json'}")


if __name__ == "__main__":
    main()
