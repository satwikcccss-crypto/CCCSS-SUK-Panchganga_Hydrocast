"""
Absolute-parameter calibration — August 2025 Shivaji Bridge.

Sets absolute lag_min (min) and k_hr (hr) values directly, bypassing the
baseline scaling limits. The Sahyadri canyons are flashy — subbasin response
should be hours, not days.

Search:
  * lag_min: [300, 600, 900, 1200] min  (5-20 h subbasin response)
  * k_hr:    [1.0, 2.0, 3.0, 4.0] hr   (1-4 h reach routing)
  * cn:      [90, 95]                   (max curve number)
  * musk_x:  [0.15]
  * ia_frac: 0.05 (saturated monsoon)

Criteria:
  * peak_err_m >= 0 (conservative), |peak_err_m| <= 0.20
  * |peak_timing_err_h| <= 1.0
  * NSE >= 0.92, KGE >= 0.88
"""
import json
import copy
import itertools
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


def run_sim(hyetos, lag_min, k_hr, cn, musk_x, ia_frac):
    """Set absolute lag_min, k_hr, cn for all subbasins/reaches."""
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

    all_results = []
    passing = []
    for lag in [300, 600, 900, 1200]:
        for k in [1.0, 2.0, 3.0, 4.0]:
            for cn in [90, 95]:
                params = {"lag_min": lag, "k_hr": k, "cn": cn,
                          "muskingum_x": 0.15, "ia_frac": 0.05}
                try:
                    sim_df, result = run_sim(hyetos, lag, k, cn, 0.15, 0.05)
                    r = evaluate(sim_df, obs, params)
                    all_results.append(r)
                    ok = passes(r)
                    status = "PASS" if ok else ""
                    print(f"  lag={lag}min k={k}h cn={cn} x=0.15 "
                          f"-> NSE={r['nse']:.3f} KGE={r['kge']:.3f} "
                          f"peak_err={r['peak_err_m']:+.2f}m timing={r['peak_timing_err_h']:+.1f}h {status}")
                    if ok:
                        passing.append(r)
                except Exception as e:
                    print(f"  lag={lag} k={k} cn={cn} ERROR: {e}")

    print(f"\nTotal: {len(all_results)}, Passing: {len(passing)}")

    if passing:
        passing.sort(key=lambda r: (-r["nse"], abs(r["peak_err_m"])))
        best = passing[0]
        print(f"\nBEST PASSING: {json.dumps(best['params'], indent=2)}")
        print(f"  NSE={best['nse']:.3f} KGE={best['kge']:.3f} RMSE={best['rmse']:.3f}")
        print(f"  Peak: {best['sim_peak_m']}m vs {best['obs_peak_m']}m (err={best['peak_err_m']:+.2f}m)")
        print(f"  Timing err: {best['peak_timing_err_h']:+.1f}h")
        best_sim, _ = run_sim(hyetos, best["params"]["lag_min"], best["params"]["k_hr"],
                              best["params"]["cn"], best["params"]["muskingum_x"], 0.05)
        plot_comparison(obs, best_sim, best, OUT_DIR)
    else:
        print("\nNO combination passes all criteria. Best by composite score:")
        def score(r):
            s = r["nse"] * 100
            if r["peak_err_m"] >= 0: s += 10
            if abs(r["peak_timing_err_h"]) <= 1.0: s += 10
            return s
        all_results.sort(key=score, reverse=True)
        for r in all_results[:10]:
            print(f"  NSE={r['nse']:.3f} KGE={r['kge']:.3f} peak_err={r['peak_err_m']:+.2f}m "
                  f"timing={r['peak_timing_err_h']:+.1f}h params={r['params']}")

    with open(OUT_DIR / "absolute_search_results.json", "w") as f:
        json.dump({"all_results": all_results, "passing": passing,
                   "best": passing[0] if passing else None}, f, indent=2, default=str)
    print(f"\nSaved to {OUT_DIR / 'absolute_search_results.json'}")


def plot_comparison(obs, sim_df, result, out_dir):
    fig, ax = plt.subplots(figsize=(15, 7))
    ax.plot(obs["timestamp"], obs["stage_m"], color="#1f77b4", lw=2.5,
            label="Observed (Shivaji Bridge)", zorder=4, alpha=0.95)
    ax.plot(sim_df["timestamp"], sim_df["stage_m"], color="#d62728", lw=2.2,
            label=f"Calibrated (NSE={result['nse']:.3f}, KGE={result['kge']:.3f}, "
                  f"peak_err={result['peak_err_m']:+.2f}m)",
            zorder=3)
    ax.axhline(542.10, color="#ff7f0e", ls="--", lw=1.5, alpha=0.7, label="Alert 542.10 m")
    ax.axhline(542.70, color="#ff0000", ls="--", lw=1.5, alpha=0.7, label="Warning 542.70 m")
    oi = int(obs["stage_m"].idxmax())
    si = int(sim_df["stage_m"].idxmax())
    ax.annotate(f"Obs peak {obs.loc[oi,'stage_m']:.2f}m\n{obs.loc[oi,'timestamp']:%b %d %H:%M}",
                xy=(obs.loc[oi, "timestamp"], obs.loc[oi, "stage_m"]),
                xytext=(15, 30), textcoords="offset points", fontsize=9, color="#1f77b4",
                arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=1))
    ax.annotate(f"Sim peak {sim_df.loc[si,'stage_m']:.2f}m\n{sim_df.loc[si,'timestamp']:%b %d %H:%M}",
                xy=(sim_df.loc[si, "timestamp"], sim_df.loc[si, "stage_m"]),
                xytext=(15, -50), textcoords="offset points", fontsize=9, color="#d62728",
                arrowprops=dict(arrowstyle="->", color="#d62728", lw=1))
    ax.set_title(f"HydroCast — Absolute-Param Calibration, Aug 2025 Shivaji Bridge\n"
                 f"NSE={result['nse']:.3f} KGE={result['kge']:.3f} Peak err={result['peak_err_m']:+.2f}m "
                 f"Timing err={result['peak_timing_err_h']:+.1f}h",
                 fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("Date (2025)", fontsize=11)
    ax.set_ylabel("Stage (m MSL)", fontsize=11)
    ax.set_ylim(528, 546)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.legend(loc="upper left", fontsize=10)
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    p1 = out_dir / "hydrograph_absolute_calibrated.png"
    fig.tight_layout()
    fig.savefig(p1, dpi=150)
    print(f"Saved {p1}")

    fig2, ax2 = plt.subplots(figsize=(14, 6))
    mask_obs = (obs["timestamp"] >= "2025-08-20") & (obs["timestamp"] <= "2025-08-22 23:00")
    mask_sim = (sim_df["timestamp"] >= "2025-08-20") & (sim_df["timestamp"] <= "2025-08-22 23:00")
    ax2.plot(obs.loc[mask_obs, "timestamp"], obs.loc[mask_obs, "stage_m"],
             color="#1f77b4", lw=2.5, label="Observed", marker="o", ms=4, alpha=0.95)
    ax2.plot(sim_df.loc[mask_sim, "timestamp"], sim_df.loc[mask_sim, "stage_m"],
             color="#d62728", lw=2.5, label=f"Calibrated (NSE={result['nse']:.3f})")
    ax2.axhline(542.10, color="#ff7f0e", ls="--", lw=1.5, alpha=0.7)
    ax2.axhline(542.70, color="#ff0000", ls="--", lw=1.5, alpha=0.7)
    ax2.set_title("Peak Flood Window — Aug 20 to Aug 22, 2025", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Date (2025)", fontsize=11)
    ax2.set_ylabel("Stage (m MSL)", fontsize=11)
    ax2.set_ylim(535, 546)
    ax2.grid(True, alpha=0.3, linestyle="--")
    ax2.legend(loc="upper left", fontsize=10)
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %d\n%H:%M"))
    plt.setp(ax2.get_xticklabels(), rotation=0, ha="center")
    p2 = out_dir / "hydrograph_absolute_calibrated_peak_zoom.png"
    fig2.tight_layout()
    fig2.savefig(p2, dpi=150)
    print(f"Saved {p2}")


if __name__ == "__main__":
    main()
