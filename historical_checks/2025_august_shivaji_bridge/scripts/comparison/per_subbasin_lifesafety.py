"""
Per-subbasin CN + per-reach K/lag/X life-safety calibration — Aug 2025 Shivaji Bridge.

Hydrologist framing (NOT a single global CN/K):
  - Per-subbasin CN  = immutable-basin baseline CN (differentiated 61-75) + headwater delta CN.
    Under AMC-III (saturated monsoon) the TR-55 transform raises these to ~78-87, matching
    the peak that the uniform CN=90 hack produced but now physically differentiated per basin.
  - Per-subbasin lag = baseline lag * alpha_lag (routing speed, per basin geometry).
  - Per-reach K      = baseline K * alpha_k  (channel storage, per reach length/geometry).
  - Per-reach X      = 0.15 (wedge storage factor).
  - ia_frac = 0.05, uh_max_hr = 90, uh_m_exp tunable (sharp monsoon crest).

Goal: peak_err >= 0 (conservative), |peak_err| <= 0.20m, timing <= +/-1.0h, NSE>=0.92, KGE>=0.88.
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
HEADWATERS = {"S4", "S5", "S6", "S7"}  # Karan, Padasali, Gaganbawda, Garivade


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


def run_sim(hyetos, alpha_k, alpha_lag, head_cn_delta, musk_x, ia_frac, uh_max_hr, uh_m_exp):
    base_sub, base_reach = load_immutable_baseline()
    sub_models = copy.deepcopy(base_sub)
    reaches = copy.deepcopy(base_reach)
    # Per-subbasin CN + lag (differentiated by baseline), per-reach K/X.
    for sid in sub_models:
        cn_base = float(sub_models[sid]["cn"])
        cn_delta = float(head_cn_delta) if sid in HEADWATERS else 0.0
        sub_models[sid]["cn"] = float(np.clip(cn_base + cn_delta, 45.0, 95.0))
        sub_models[sid]["lag_min"] = float(sub_models[sid]["lag_min"] * float(alpha_lag))
    for rid in reaches:
        reaches[rid]["k_hr"] = float(reaches[rid]["k_hr"] * float(alpha_k))
        reaches[rid]["x"] = float(musk_x)
    parameter_overrides = {
        "sub_models": {sid: {"cn": sub_models[sid]["cn"], "lag_min": sub_models[sid]["lag_min"]}
                       for sid in sub_models},
        "reaches": {rid: {"k_hr": reaches[rid]["k_hr"], "x": reaches[rid]["x"]}
                    for rid in reaches},
        "alpha_k": alpha_k, "alpha_lag": alpha_lag, "delta_cn": head_cn_delta,
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


def plot_best(sim_df, obs_df, r, out_png):
    m = pd.merge(
        obs_df.loc[:, ["timestamp", "stage_m"]].rename(columns={"stage_m": "obs"}),
        sim_df.loc[:, ["timestamp", "stage_m"]].rename(columns={"stage_m": "sim"}),
        on="timestamp", how="inner",
    )
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(m["timestamp"], m["obs"], "o-", color="tab:blue", ms=3, lw=1.2, label="Observed")
    ax.plot(m["timestamp"], m["sim"], "-", color="tab:red", lw=1.4, label="Per-subbasin sim")
    ax.axhline(542.10, color="orange", ls="--", lw=1, label="Alert 542.10")
    ax.axhline(542.70, color="red", ls="--", lw=1, label="Warning 542.70")
    ax.set_ylabel("Stage (m MSL)")
    ax.set_title(f"Per-subbasin life-safety run: NSE={r['nse']:.3f} KGE={r['kge']:.3f} "
                 f"peak={r['peak_err_m']:+.2f}m timing={r['peak_timing_err_h']:+.1f}h")
    ax.legend(loc="best", fontsize=8)
    ax.grid(alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %Hh"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)
    return out_png


def main():
    hyetos, sel = fetch_hyetographs()
    obs = pd.read_csv(REPO / "data" / "shivaji_bridge_2025_hourly_observed.csv",
                      parse_dates=["timestamp"]).dropna(subset=["stage_m"])

    all_results = []
    passing = []
    grid = [(ak, alag, hcn, me)
            for ak in [0.80, 0.85, 0.90]
            for alag in [0.82, 0.86, 0.90]
            for hcn in [0.0, 2.0, 3.0]
            for me in [20, 50, 90]]
    print(f"Grid size: {len(grid)} combos (per-subbasin CN + per-reach K/lag)", flush=True)
    for ak, alag, hcn, me in grid:
        params = {"alpha_k": ak, "alpha_lag": alag, "head_cn_delta": hcn,
                  "muskingum_x": 0.15, "ia_frac": 0.05,
                  "uh_max_hr": 90, "uh_m_exp": me, "cn_style": "per_subbasin_baseline",
                  "k_style": "per_reach_baseline"}
        try:
            sim_df, result = run_sim(hyetos, ak, alag, hcn, 0.15, 0.05, 90, me)
            r = evaluate(sim_df, obs, params)
            all_results.append(r)
            ok = passes(r)
            status = "PASS" if ok else ""
            print(f"  ak={ak} alag={alag} hcn=+{hcn} me={me} -> "
                  f"NSE={r['nse']:.3f} KGE={r['kge']:.3f} peak_err={r['peak_err_m']:+.2f}m "
                  f"timing={r['peak_timing_err_h']:+.1f}h {status}", flush=True)
            if ok:
                passing.append((r, sim_df))
        except Exception as e:
            print(f"  ak={ak} alag={alag} hcn={hcn} me={me} ERROR: {e}", flush=True)

    print(f"\nTotal: {len(all_results)}, Passing: {len(passing)}")
    if passing:
        passing.sort(key=lambda t: (-t[0]["nse"], abs(t[0]["peak_err_m"])))
        best_r, best_df = passing[0]
    else:
        print("\nNo passes. Best by composite score:")
        def score(r):
            s = r["nse"] * 100
            if r["peak_err_m"] >= 0: s += 10
            if abs(r["peak_timing_err_h"]) <= 1.0: s += 10
            return s
        all_results.sort(key=score, reverse=True)
        best_r = all_results[0]
        best_df = None
        for r in all_results[:10]:
            print(f"  NSE={r['nse']:.3f} KGE={r['kge']:.3f} peak_err={r['peak_err_m']:+.2f}m "
                  f"timing={r['peak_timing_err_h']:+.1f}h params={r['params']}")

    print(f"\nBEST: {json.dumps(best_r['params'], indent=2, default=str)}")
    print(f"  NSE={best_r['nse']:.3f} KGE={best_r['kge']:.3f} RMSE={best_r['rmse']:.3f}")
    print(f"  Peak: {best_r['sim_peak_m']}m vs {best_r['obs_peak_m']}m (err={best_r['peak_err_m']:+.2f}m)")
    print(f"  Timing err: {best_r['peak_timing_err_h']:+.1f}h")

    if best_df is not None:
        png = plot_best(best_df, obs, best_r, OUT_DIR / "hydrograph_per_subbasin_best.png")
        print(f"  Plot: {png}")

    with open(OUT_DIR / "per_subbasin_life_safety_results.json", "w") as f:
        json.dump({"all_results": all_results,
                   "passing": [t[0] for t in passing],
                   "best": best_r}, f, indent=2, default=str)
    print(f"Saved to {OUT_DIR / 'per_subbasin_life_safety_results.json'}")


if __name__ == "__main__":
    main()
