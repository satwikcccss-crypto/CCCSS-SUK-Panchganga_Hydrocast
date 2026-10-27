"""
Life-safety grid search calibration — August 2025 Shivaji Bridge flood.

Searches over:
  * alpha_k      : Muskingum K scaling (faster wave celerity)  [0.80, 0.85, 0.90]
  * alpha_lag    : Subbasin lag scaling                         [0.82, 0.86, 0.90]
  * delta_cn_all : CN boost applied to ALL subbasins            [0.0, 2.0, 4.0, 6.0]
  * delta_cn_hw  : EXTRA CN boost on headwaters (S4,S5,S6,S7)   [0.0, 2.0, 4.0]
  * ia_frac      : SCS initial abstraction fraction             [0.05] (saturated monsoon)

Criteria (life-safety, non-negotiable):
  * Peak stage sim >= obs (never under-predict)  -> peak_err_m >= 0
  * |peak_err_m| <= 0.20 m
  * |peak_timing_err_h| <= 1.0 h
  * NSE >= 0.92
  * KGE >= 0.88

Saves results to results/dynamic_calibration/grid_search_results.json
and a comparison plot.
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
OBS_PEAK_STAGE = 542.57
OBS_PEAK_TS = datetime(2025, 8, 21, 14, 0, 0)

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


def run_sim(hyetos, alpha_k, alpha_lag, dcn_all, dcn_hw, ia_frac):
    """Run 360-h simulation with given calibration parameters."""
    base_sub, base_reach = load_immutable_baseline()
    sub_models = copy.deepcopy(base_sub)
    reaches = copy.deepcopy(base_reach)

    # Apply CN boosts (all subbasins + extra on headwaters)
    for sid in sub_models:
        total_dcn = dcn_all + (dcn_hw if sid in HEADWATER_SUBS else 0.0)
        sub_models[sid]["cn"] = float(np.clip(sub_models[sid]["cn"] + total_dcn, 45.0, 95.0))
        sub_models[sid]["lag_min"] = float(sub_models[sid]["lag_min"] * alpha_lag)

    # Apply reach K scaling
    for rid in reaches:
        reaches[rid]["k_hr"] = float(reaches[rid]["k_hr"] * alpha_k)
        reaches[rid]["x"] = 0.25

    parameter_overrides = {
        "sub_models": {sid: {"cn": sub_models[sid]["cn"], "lag_min": sub_models[sid]["lag_min"]}
                       for sid in sub_models},
        "reaches": {rid: {"k_hr": reaches[rid]["k_hr"], "x": reaches[rid]["x"]}
                    for rid in reaches},
        "alpha_k": alpha_k,
        "alpha_lag": alpha_lag,
        "delta_cn": dcn_all,
        "muskingum_x": 0.25,
    }

    result = _execute_hec_hms_core(
        RUN_DT,
        subbasin_hyetographs=hyetos,
        live_stage_m=None,
        parameter_overrides=parameter_overrides,
        amc=None,
        sim_hours=HOURS,
        ia_frac=ia_frac,
    )

    # Build stage series
    rows = []
    for entry in result["hydrograph"]:
        ts = pd.to_datetime(entry["timestamp"])
        q = float(entry.get("discharge_m3s") or 0.0)
        rows.append({
            "timestamp": ts,
            "stage_m": convert_discharge_to_stage_manning(q, "SHIVAJI_BRIDGE"),
            "discharge_m3s": q,
        })
    df = pd.DataFrame(rows)
    return df, result


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

    # Discharge at observed peak time
    sim_d = sim_df.set_index("timestamp")["discharge_m3s"]
    obs_d = obs_df.set_index("timestamp")["stage_m"].apply(
        lambda s: convert_stage_to_discharge_manning(float(s), "SHIVAJI_BRIDGE")
    )
    md = pd.merge(
        obs_d.rename("obs_q").to_frame(),
        sim_d.rename("sim_q").to_frame(),
        left_index=True, right_index=True, how="inner",
    )
    peak_q_err = None
    if len(md) > 0:
        oqi = md["obs_q"].idxmax()
        peak_q_err = float(md.loc[oqi, "sim_q"] - md.loc[oqi, "obs_q"])

    return {
        "nse": round(nse, 4), "kge": round(kge, 4),
        "rmse": round(rmse, 3), "mae": round(mae, 3), "pbias": round(pbias, 2),
        "peak_err_m": round(peak_err, 2),
        "peak_timing_err_h": round(peak_dt_err, 2),
        "obs_peak_m": round(float(obs_s[oi]), 2),
        "sim_peak_m": round(float(sim_s[si]), 2),
        "obs_peak_ts": str(m.iloc[oi]["timestamp"]),
        "sim_peak_ts": str(m.iloc[si]["timestamp"]),
        "peak_q_err_m3s": round(peak_q_err, 1) if peak_q_err is not None else None,
        "matched": int(len(m)),
    }, m


def passes_criteria(r):
    """Life-safety criteria: all must pass."""
    return (
        r["peak_err_m"] >= 0.0 and                     # never under-predict
        abs(r["peak_err_m"]) <= 0.20 and               # within 0.20 m
        abs(r["peak_timing_err_h"]) <= 1.0 and         # within 1.0 h
        r["nse"] >= 0.92 and                           # NSE >= 0.92
        r["kge"] >= 0.88                               # KGE >= 0.88
    )


def main():
    hyetos, sel = fetch_hyetographs()
    print("Governing stations:")
    for sub in [f"S{i}" for i in range(1, 10)]:
        print(f"  {sub} -> {sel[sub]['selected_station_id']} "
              f"({sel[sub]['station_name']}, {sel[sub]['cumulative_mm']:.1f} mm)")

    obs = pd.read_csv(REPO / "data" / "shivaji_bridge_2025_hourly_observed.csv",
                      parse_dates=["timestamp"]).dropna(subset=["stage_m"])

    # Grid search
    alpha_k_vals = [0.80, 0.85, 0.90]
    alpha_lag_vals = [0.82, 0.86, 0.90]
    dcn_all_vals = [0.0, 2.0, 4.0, 6.0]
    dcn_hw_vals = [0.0, 2.0, 4.0]
    ia_frac_vals = [0.05]

    all_results = []
    passing = []
    total = len(alpha_k_vals) * len(alpha_lag_vals) * len(dcn_all_vals) * len(dcn_hw_vals) * len(ia_frac_vals)
    count = 0

    print(f"\nGrid search: {total} combinations...")
    for ak, al, dcn_all, dcn_hw, ia in itertools.product(
        alpha_k_vals, alpha_lag_vals, dcn_all_vals, dcn_hw_vals, ia_frac_vals
    ):
        count += 1
        params = {"alpha_k": ak, "alpha_lag": al, "dcn_all": dcn_all,
                  "dcn_hw": dcn_hw, "ia_frac": ia}
        try:
            sim_df, result = run_sim(hyetos, ak, al, dcn_all, dcn_hw, ia)
            r, m = evaluate(sim_df, obs, params)
            r["params"] = params
            all_results.append(r)

            ok = passes_criteria(r)
            if ok:
                passing.append(r)
                print(f"  [{count:3d}/{total}] PASS: ak={ak}, al={al}, dcn_all={dcn_all}, "
                      f"dcn_hw={dcn_hw}, ia={ia} -> NSE={r['nse']:.3f} KGE={r['kge']:.3f} "
                      f"peak_err={r['peak_err_m']:+.2f}m timing_err={r['peak_timing_err_h']:+.1f}h")
            elif count <= 5 or ok:
                print(f"  [{count:3d}/{total}]   : ak={ak}, al={al}, dcn_all={dcn_all}, "
                      f"dcn_hw={dcn_hw}, ia={ia} -> NSE={r['nse']:.3f} KGE={r['kge']:.3f} "
                      f"peak_err={r['peak_err_m']:+.2f}m timing_err={r['peak_timing_err_h']:+.1f}h "
                      f"{'PASS' if ok else ''}")
        except Exception as e:
            print(f"  [{count:3d}/{total}] ERROR: {e}")

    print(f"\nTotal combinations: {total}, Passing: {len(passing)}")

    if passing:
        # Pick the best passing result (highest NSE, then lowest peak_err)
        passing.sort(key=lambda r: (-r["nse"], abs(r["peak_err_m"])))
        best = passing[0]
        print(f"\nBEST PASSING: {json.dumps(best['params'], indent=2)}")
        print(f"  NSE={best['nse']:.3f} KGE={best['kge']:.3f} RMSE={best['rmse']:.3f}")
        print(f"  Peak: {best['sim_peak_m']}m vs {best['obs_peak_m']}m (err={best['peak_err_m']:+.2f}m)")
        print(f"  Timing err: {best['peak_timing_err_h']:+.1f}h")
    else:
        print("\nNO combination passes all criteria. Best by NSE:")
        all_results.sort(key=lambda r: -r["nse"])
        for r in all_results[:5]:
            print(f"  NSE={r['nse']:.3f} KGE={r['kge']:.3f} peak_err={r['peak_err_m']:+.2f}m "
                  f"timing_err={r['peak_timing_err_h']:+.1f}h params={r['params']}")

    # Save all results
    out = {
        "all_results": all_results,
        "passing": passing,
        "best": passing[0] if passing else None,
    }
    with open(OUT_DIR / "grid_search_results.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved grid search results to {OUT_DIR / 'grid_search_results.json'}")

    # Plot: best passing vs observed (or best NSE if none passing)
    if passing:
        best_sim, _ = run_sim(hyetos, **{k: best["params"][k] for k in
                                         ["alpha_k", "alpha_lag", "dcn_all", "dcn_hw", "ia_frac"]})
        plot_comparison(obs, best_sim, best, OUT_DIR, label="best_passing")
    else:
        best_sim, _ = run_sim(hyetos, **{k: all_results[0]["params"][k] for k in
                                         ["alpha_k", "alpha_lag", "dcn_all", "dcn_hw", "ia_frac"]})
        plot_comparison(obs, best_sim, all_results[0], OUT_DIR, label="best_nse")


def plot_comparison(obs, sim_df, result, out_dir, label):
    fig, ax = plt.subplots(figsize=(15, 7))

    ax.plot(obs["timestamp"], obs["stage_m"], color="#1f77b4", lw=2.5,
            label="Observed (Shivaji Bridge)", zorder=4, alpha=0.95)
    ax.plot(sim_df["timestamp"], sim_df["stage_m"], color="#d62728", lw=2.2,
            label=f"Calibrated (NSE={result['nse']:.3f}, peak_err={result['peak_err_m']:+.2f}m)",
            zorder=3)

    # Alert/warning thresholds
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

    ax.set_title(f"HydroCast — Life-Safety Calibrated, Aug 2025 Shivaji Bridge ({label})\n"
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

    p1 = out_dir / f"hydrograph_{label}.png"
    fig.tight_layout()
    fig.savefig(p1, dpi=150)
    print(f"Saved {p1}")

    # Peak zoom
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

    p2 = out_dir / f"hydrograph_{label}_peak_zoom.png"
    fig2.tight_layout()
    fig2.savefig(p2, dpi=150)
    print(f"Saved {p2}")


if __name__ == "__main__":
    main()
