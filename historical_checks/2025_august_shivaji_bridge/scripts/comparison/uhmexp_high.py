"""
UH-shape-exponent high search — August 2025 Shivaji Bridge.

Tests higher SCS unit-hydrograph shape exponents: m_exp in [15, 20, 30, 50, 100].
Higher m_exp -> sharper hydrograph at same time-to-peak -> higher peak magnitude.

Combines with best-timing params from prior runs:
  * lag_min: [2700, 3000] min (45-50 h, near-correct timing)
  * k_hr:    [6.0, 8.0] hr
  * cn:      [90, 95]
  * musk_x:  [0.15]
  * ia_frac: 0.05
  * uh_max_hr: 90
  * uh_m_exp: [15, 20, 30, 50, 100]
"""
import json
import copy
from datetime import datetime
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
from src.hydrology.stage_converter import convert_discharge_to_stage_manning
from src.hydrology.validation_metrics import compute_nse, compute_rmse_mae, compute_kge, compute_pbias
from src.ecmwf.station_selector import STATION_REGISTRY, select_active_subbasin_gages
from run_historical_event import fetch_historical_rainfall_for_station   # noqa: E402

START = "2025-08-08"
END = "2025-08-22"
HOURS = 360
RUN_DT = datetime(2025, 8, 8, 0, 0, 0)
OUT_DIR = BRIDGE / "results" / "dynamic_calibration"
OUT_DIR.mkdir(parents=True, exist_ok=True)
UH_MAX_HR = 90


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


def run_sim(hyetos, lag_min, k_hr, cn, musk_x, ia_frac, uh_max_hr, uh_m_exp):
    base_sub, base_reach = load_immutable_baseline()
    sub_models = copy.deepcopy(base_sub)
    reaches = copy.deepcopy(base_reach)
    for sid in sub_models:
        sub_models[sid]["cn"] = float(cn)
        sub_models[sid]["lag_min"] = float(lag_min)
    for rid in reaches:
        reaches[rid]["k_hr"] = float(k_hr)
        reaches[rid]["x"] = float(musk_x)
    parameter_overrides = {
        "sub_models": {sid: {"cn": sub_models[sid]["cn"], "lag_min": sub_models[sid]["lag_min"]}
                       for sid in sub_models},
        "reaches": {rid: {"k_hr": reaches[rid]["k_hr"], "x": reaches[rid]["x"]}
                    for rid in reaches},
        "alpha_k": 1.0, "alpha_lag": 1.0, "delta_cn": 0.0, "muskingum_x": musk_x,
    }
    result = _execute_hec_hms_core(
        RUN_DT, subbasin_hyetographs=hyetos, live_stage_m=None,
        parameter_overrides=parameter_overrides, amc=None,
        sim_hours=HOURS, ia_frac=ia_frac, uh_max_hr=uh_max_hr, uh_m_exp=uh_m_exp,
    )
    rows = []
    for entry in result["hydrograph"]:
        ts = pd.to_datetime(entry["timestamp"])
        q = float(entry.get("discharge_m3s") or 0.0)
        rows.append({"timestamp": ts, "stage_m": convert_discharge_to_stage_manning(q, "SHIVAJI_BRIDGE"),
                     "discharge_m3s": q})
    return pd.DataFrame(rows), result


def evaluate(sim_df, obs_df, params):
    m = pd.merge(
        obs_df[["timestamp", "stage_m"]].rename(columns={"stage_m": "obs_stage"}),
        sim_df.loc[:, ["timestamp", "stage_m"]].rename(columns={"stage_m": "sim_stage"}),
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
        "nse": round(nse, 4), "kge": round(kge, 4), "rmse": round(rmse, 3),
        "mae": round(mae, 3), "pbias": round(pbias, 2),
        "peak_err_m": round(peak_err, 2), "peak_timing_err_h": round(peak_dt_err, 2),
        "obs_peak_m": round(float(obs_s[oi]), 2), "sim_peak_m": round(float(sim_s[si]), 2),
        "sim_peak_ts": str(m.iloc[si]["timestamp"]), "matched": int(len(m)),
        "params": params,
    }


def passes(r):
    return (r["peak_err_m"] >= 0.0 and abs(r["peak_err_m"]) <= 0.20
            and abs(r["peak_timing_err_h"]) <= 1.0
            and r["nse"] >= 0.92 and r["kge"] >= 0.88)


def main():
    hyetos, sel = fetch_hyetographs()
    obs = pd.read_csv(REPO / "data" / "shivaji_bridge_2025_hourly_observed.csv",
                      parse_dates=["timestamp"]).dropna(subset=["stage_m"])

    all_results = []
    passing = []
    for lag in [2700, 3000]:
        for k in [6.0, 8.0]:
            for cn in [90, 95]:
                for mexp in [15, 20, 30, 50, 100]:
                    params = {"lag_min": lag, "k_hr": k, "cn": cn,
                              "muskingum_x": 0.15, "ia_frac": 0.05,
                              "uh_max_hr": 90, "uh_m_exp": mexp}
                    try:
                        sim_df, result = run_sim(hyetos, lag, k, cn, 0.15, 0.05, 90, mexp)
                        r = evaluate(sim_df, obs, params)
                        all_results.append(r)
                        ok = passes(r)
                        status = "PASS" if ok else ""
                        print(f"  lag={lag}min k={k}h cn={cn} mexp={mexp} uh=90h "
                                  f"-> NSE={r['nse']:.3f} KGE={r['kge']:.3f} "
                                  f"peak_err={r['peak_err_m']:+.2f}m timing={r['peak_timing_err_h']:+.1f}h {status}", flush=True)
                        if ok:
                            passing.append(r)
                    except Exception as e:
                        print(f"  lag={lag} k={k} cn={cn} mexp={mexp} ERROR: {e}", flush=True)

    print(f"\nTotal: {len(all_results)}, Passing: {len(passing)}")
    if passing:
        passing.sort(key=lambda r: (-r["nse"], abs(r["peak_err_m"])))
        best = passing[0]
        print(f"\nBEST PASSING: {json.dumps(best['params'], indent=2)}")
        print(f"  NSE={best['nse']:.3f} KGE={best['kge']:.3f} RMSE={best['rmse']:.3f}")
        print(f"  Peak: {best['sim_peak_m']}m vs {best['obs_peak_m']}m (err={best['peak_err_m']:+.2f}m)")
        print(f"  Timing err: {best['peak_timing_err_h']:+.1f}h")
    else:
        all_results.sort(key=lambda r: -r["nse"])
        print("\nNo passes. Best by NSE:")
        for r in all_results[:8]:
            print(f"  NSE={r['nse']:.3f} KGE={r['kge']:.3f} peak_err={r['peak_err_m']:+.2f}m "
                      f"timing={r['peak_timing_err_h']:+.1f}h params={r['params']}")

    with open(OUT_DIR / "uhmexp_high_results.json", "w") as f:
        json.dump({"all_results": all_results, "passing": passing,
                   "best": passing[0] if passing else None}, f, indent=2, default=str)
    print(f"\nSaved to {OUT_DIR / 'uhmexp_high_results.json'}")


if __name__ == "__main__":
    main()
