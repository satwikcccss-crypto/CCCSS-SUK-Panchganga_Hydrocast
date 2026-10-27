"""
Focused pass — close the peak gap while keeping per-subbasin CN structure.

Base config from pass 1 (best NSE): alpha_k=0.85, alpha_lag=0.82, uh_m_exp=20/50,
ia_frac=0.05, uh_max_hr=90, muskingum_x=0.15.

Now sweep a GLOBAL CN uplift applied on top of per-subbasin baseline CN (+ optional
extra headwater delta) to raise the peak ~0.55m toward conservative, while watching
NSE so we don't overshoot. Per-subbasin differentiation is preserved throughout.
"""
import json
import copy
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

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
HEADWATERS = {"S4", "S5", "S6", "S7"}


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


def run_sim(hyetos, alpha_k, alpha_lag, cn_global_uplift, head_cn_delta, musk_x,
            ia_frac, uh_max_hr, uh_m_exp):
    base_sub, base_reach = load_immutable_baseline()
    sub_models = copy.deepcopy(base_sub)
    reaches = copy.deepcopy(base_reach)
    for sid in sub_models:
        cn_base = float(sub_models[sid]["cn"])
        extra = float(cn_global_uplift) + (float(head_cn_delta) if sid in HEADWATERS else 0.0)
        sub_models[sid]["cn"] = float(np.clip(cn_base + extra, 45.0, 95.0))
        sub_models[sid]["lag_min"] = float(sub_models[sid]["lag_min"] * float(alpha_lag))
    for rid in reaches:
        reaches[rid]["k_hr"] = float(reaches[rid]["k_hr"] * float(alpha_k))
        reaches[rid]["x"] = float(musk_x)
    parameter_overrides = {
        "sub_models": {sid: {"cn": sub_models[sid]["cn"], "lag_min": sub_models[sid]["lag_min"]}
                       for sid in sub_models},
        "reaches": {rid: {"k_hr": reaches[rid]["k_hr"], "x": reaches[rid]["x"]}
                    for rid in reaches},
        "alpha_k": alpha_k, "alpha_lag": alpha_lag, "delta_cn": cn_global_uplift + head_cn_delta,
        "muskingum_x": musk_x,
    }
    result = _execute_hec_hms_core(
        RUN_DT, subbasin_hyetographs=hyetos, live_stage_m=None,
        parameter_overrides=parameter_overrides, amc="AMC-III",
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
        obs_df.loc[:, ["timestamp", "stage_m"]].rename(columns={"stage_m": "obs_stage"}),
        sim_df.loc[:, ["timestamp", "stage_m"]].rename(columns={"stage_m": "sim_stage"}),
        on="timestamp", how="inner",
    )
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

    all_results, passing = [], []
    grid = [(ak, alag, gcn, hcn, me)
            for ak in [0.80, 0.85]
            for alag in [0.82]
            for gcn in [10.0, 14.0, 18.0, 22.0, 26.0]
            for hcn in [0.0, 3.0]
            for me in [50, 90, 120]]
    print(f"Grid size: {len(grid)} (HIGH CN-uplift pass — per-basin kept)", flush=True)
    for ak, alag, gcn, hcn, me in grid:
        params = {"alpha_k": ak, "alpha_lag": alag, "cn_global_uplift": gcn,
                  "head_cn_delta": hcn, "muskingum_x": 0.15, "ia_frac": 0.05,
                  "uh_max_hr": 90, "uh_m_exp": me,
                  "cn_style": "per_subbasin_baseline_plus_uplift"}
        try:
            sim_df, result = run_sim(hyetos, ak, alag, gcn, hcn, 0.15, 0.05, 90, me)
            r = evaluate(sim_df, obs, params)
            all_results.append(r)
            ok = passes(r)
            status = "PASS" if ok else ""
            print(f"  ak={ak} gcn=+{gcn} hcn=+{hcn} me={me} -> "
                  f"NSE={r['nse']:.3f} KGE={r['kge']:.3f} peak_err={r['peak_err_m']:+.2f}m "
                  f"timing={r['peak_timing_err_h']:+.1f}h {status}", flush=True)
            if ok:
                passing.append(r)
        except Exception as e:
            print(f"  ak={ak} gcn={gcn} hcn={hcn} me={me} ERROR: {e}", flush=True)

    print(f"\nTotal: {len(all_results)}, Passing: {len(passing)}")
    if passing:
        passing.sort(key=lambda r: (-r["nse"], abs(r["peak_err_m"])))
        best = passing[0]
    else:
        print("\nNo passes. Top by (NSE + conservative bonus):")
        def score(r):
            s = r["nse"] * 100
            if r["peak_err_m"] >= 0: s += 15
            if abs(r["peak_err_m"]) <= 0.20: s += 10
            if abs(r["peak_timing_err_h"]) <= 1.0: s += 10
            return s
        all_results.sort(key=score, reverse=True)
        best = all_results[0]
        for r in all_results[:10]:
            print(f"  NSE={r['nse']:.3f} KGE={r['kge']:.3f} peak_err={r['peak_err_m']:+.2f}m "
                  f"timing={r['peak_timing_err_h']:+.1f}h params={json.dumps(r['params'])}")

    print(f"\nBEST: {json.dumps(best['params'], indent=2, default=str)}")
    print(f"  NSE={best['nse']:.3f} KGE={best['kge']:.3f} RMSE={best['rmse']:.3f}")
    print(f"  Peak: {best['sim_peak_m']}m vs {best['obs_peak_m']}m (err={best['peak_err_m']:+.2f}m)")
    print(f"  Timing err: {best['peak_timing_err_h']:+.1f}h")

    with open(OUT_DIR / "per_subbasin_uplift_high_results.json", "w") as f:
        json.dump({"all_results": all_results, "passing": passing, "best": best}, f, indent=2, default=str)
    print(f"Saved to {OUT_DIR / 'per_subbasin_uplift_high_results.json'}")


if __name__ == "__main__":
    main()
