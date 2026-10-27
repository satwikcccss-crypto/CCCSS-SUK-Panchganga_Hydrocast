"""
Dynamic Adaptive Calibration — August 2025 Shivaji Bridge flood.

This reproduces the REAL HydroCast production behavior:
  1. RUN  — simulate with current (static/disk) parameters
  2. COMPARE — vs observed telemetry (peak stage, peak timing, peak discharge)
  3. RECALIBRATE — AdaptiveHydrologicCalibrator.recalibrate_parameters()
     solves for new α_K, α_lag, ΔCN, X via physics + ML + Levenberg-Marquardt
  4. RE-RUN — simulate again with the dynamically-calibrated parameters
  5. COMPARE — before/after accuracy

Saves per-iteration results and a before/after hydrograph overlay plot.
"""
import json
import copy
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
from src.hydrology.ml_calibration import AdaptiveHydrologicCalibrator
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


def run_sim(hyetos, parameter_overrides=None):
    """Run 360-h simulation; optionally with parameter_overrides (dynamic calibration)."""
    result = _execute_hec_hms_core(
        RUN_DT,
        subbasin_hyetographs=hyetos,
        live_stage_m=None,
        parameter_overrides=parameter_overrides,
        amc=None,
        sim_hours=HOURS,
    )
    # Build stage series (convert discharge -> stage via WRD rating curve)
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


def evaluate(sim_df, obs_df, label):
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
    peak_err = sim_s[si] - obs_s[oi]
    peak_dt_err = (m.iloc[si]["timestamp"] - m.iloc[oi]["timestamp"]).total_seconds() / 3600.0
    # Discharge errors at peaks
    sim_d = sim_df.set_index("timestamp")["discharge_m3s"]
    obs_d = obs_df.set_index("timestamp")["stage_m"].apply(
        lambda s: convert_stage_to_discharge_manning(float(s), "SHIVAJI_BRIDGE")
    )
    md = pd.merge(
        obs_d.rename("obs_q").to_frame(),
        sim_d.rename("sim_q").to_frame(),
        left_index=True, right_index=True, how="inner",
    )
    q_err = None
    if len(md) > 0:
        oqi = md["obs_q"].idxmax()          # timestamp of observed peak discharge
        sq_at_oi = float(md.loc[oqi, "sim_q"])
        oq_at_oi = float(md.loc[oqi, "obs_q"])
        q_err = sq_at_oi - oq_at_oi
    res = {
        "label": label, "matched": int(len(m)),
        "nse": round(nse, 4), "kge": round(kge, 4),
        "rmse": round(rmse, 3), "mae": round(mae, 3), "pbias": round(pbias, 2),
        "peak_err_m": round(float(peak_err), 2),
        "peak_timing_err_h": round(float(peak_dt_err), 2),
        "obs_peak_m": round(float(obs_s[oi]), 2),
        "sim_peak_m": round(float(sim_s[si]), 2),
        "obs_peak_ts": str(m.iloc[oi]["timestamp"]),
        "sim_peak_ts": str(m.iloc[si]["timestamp"]),
        "peak_q_err_m3s": round(float(q_err), 1) if q_err is not None else None,
    }
    return res, m


def main():
    hyetos, sel = fetch_hyetographs()
    print("Governing stations:")
    for sub in [f"S{i}" for i in range(1, 10)]:
        print(f"  {sub} -> {sel[sub]['selected_station_id']} "
              f"({sel[sub]['station_name']}, {sel[sub]['cumulative_mm']:.1f} mm)")

    obs = pd.read_csv(REPO / "data" / "shivaji_bridge_2025_hourly_observed.csv",
                      parse_dates=["timestamp"]).dropna(subset=["stage_m"])

    results = []
    sims = {}

    # ── Iteration 1: STATIC (baseline + disk calibration offset) ──
    print("\n" + "=" * 70)
    print("ITERATION 1 — STATIC (baseline + disk offset delta_cn=+0.89, x=0.25)")
    print("=" * 70)
    sim1, res1 = run_sim(hyetos, parameter_overrides=None)  # disk calibration applied inside
    r1, m1 = evaluate(sim1, obs, "static")
    results.append(r1); sims["static"] = sim1
    print(json.dumps(r1, indent=2))

    # Extract errors for dynamic recalibration
    stage_error_m = r1["sim_peak_m"] - r1["obs_peak_m"]          # forecast - observed
    # timing: positive = sim late
    sim_peak_dt = pd.to_datetime(r1["sim_peak_ts"])
    obs_peak_dt = pd.to_datetime(r1["obs_peak_ts"])
    timing_offset_hours = (sim_peak_dt - obs_peak_dt).total_seconds() / 3600.0
    print(f"\nDerived for recalibration: stage_error_m={stage_error_m:+.2f}, "
          f"timing_offset_hours={timing_offset_hours:+.1f}h "
          f"(sim peak {r1['sim_peak_ts']} vs obs {r1['obs_peak_ts']})")
    peak_q_err = r1.get("peak_q_err_m3s") or 0.0

    # ── Iteration 2: DYNAMIC recalibration ──
    print("\n" + "=" * 70)
    print("ITERATION 2 — DYNAMIC (AdaptiveHydrologicCalibrator recalibration)")
    print("=" * 70)
    calibrator = AdaptiveHydrologicCalibrator()
    cal = calibrator.recalibrate_parameters(
        timing_offset_hours=timing_offset_hours,
        stage_error_m=stage_error_m,
        peak_discharge_error_m3s=peak_q_err,
        subbasin_hyetographs=hyetos,
    )
    print("Calibrated parameters:")
    print(json.dumps(cal, indent=2)[:2000])

    # Build parameter_overrides for the runner (absolute CN/lag/K/x)
    parameter_overrides = {
        "sub_models": cal["sub_models"],
        "reaches": cal["reaches"],
        "alpha_k": cal["alpha_k"],
        "alpha_lag": cal["alpha_lag"],
        "delta_cn": cal["delta_cn"],
        "muskingum_x": cal["muskingum_x"],
    }

    sim2, res2 = run_sim(hyetos, parameter_overrides=parameter_overrides)
    r2, m2 = evaluate(sim2, obs, "dynamic_calibrated")
    results.append(r2); sims["dynamic"] = sim2
    print(json.dumps(r2, indent=2))

    # ── Iteration 3: second dynamic round (optional, if still off) ──
    print("\n" + "=" * 70)
    print("ITERATION 3 — DYNAMIC round 2 (recalibrate again on iteration-2 errors)")
    print("=" * 70)
    stage_error_m2 = r2["sim_peak_m"] - r2["obs_peak_m"]
    sim_peak_dt2 = pd.to_datetime(r2["sim_peak_ts"])
    timing_offset_hours2 = (sim_peak_dt2 - obs_peak_dt).total_seconds() / 3600.0
    peak_q_err2 = r2.get("peak_q_err_m3s") or 0.0
    print(f"Round-2 errors: stage_error_m={stage_error_m2:+.2f}, "
          f"timing_offset_hours={timing_offset_hours2:+.1f}h, "
          f"peak_q_err={peak_q_err2:+.1f} m3/s")

    # Fresh calibrator instance so round 2 starts from baseline (not compounded)
    calibrator2 = AdaptiveHydrologicCalibrator()
    cal2 = calibrator2.recalibrate_parameters(
        timing_offset_hours=timing_offset_hours2,
        stage_error_m=stage_error_m2,
        peak_discharge_error_m3s=peak_q_err2,
        subbasin_hyetographs=hyetos,
    )
    parameter_overrides2 = {
        "sub_models": cal2["sub_models"],
        "reaches": cal2["reaches"],
        "alpha_k": cal2["alpha_k"],
        "alpha_lag": cal2["alpha_lag"],
        "delta_cn": cal2["delta_cn"],
        "muskingum_x": cal2["muskingum_x"],
    }
    sim3, res3 = run_sim(hyetos, parameter_overrides=parameter_overrides2)
    r3, m3 = evaluate(sim3, obs, "dynamic_calibrated_round2")
    results.append(r3); sims["dynamic_round2"] = sim3
    print(json.dumps(r3, indent=2))

    # ── Save results ──
    out = {
        "iterations": results,
        "calibration_round1": cal,
        "calibration_round2": cal2,
    }
    with open(OUT_DIR / "dynamic_calibration_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved results to {OUT_DIR / 'dynamic_calibration_results.json'}")

    # ── Summary table ──
    print("\n" + "=" * 70)
    print("DYNAMIC CALIBRATION SUMMARY")
    print("=" * 70)
    print(f"{'iteration':<30}{'NSE':>7}{'KGE':>7}{'RMSE':>8}{'MAE':>8}{'PBIAS':>8}{'peakErr':>9}{'timingErr':>10}")
    for r in results:
        print(f"{r['label']:<30}{r['nse']:>7.3f}{r['kge']:>7.3f}{r['rmse']:>8.3f}"
              f"{r['mae']:>8.3f}{r['pbias']:>8.2f}{r['peak_err_m']:>9.2f}{r['peak_timing_err_h']:>10.2f}")

    # ── Plot: observed vs static vs dynamic ──
    plot_comparison(obs, sims, results, OUT_DIR)
    # Save aligned CSV
    aligned = pd.merge(
        obs.rename(columns={"stage_m": "obs_stage_m"}),
        sims["static"].rename(columns={"stage_m": "static_stage_m", "discharge_m3s": "static_q_m3s"}),
        on="timestamp", how="outer",
    )
    aligned = pd.merge(
        aligned,
        sims["dynamic"].rename(columns={"stage_m": "dynamic_stage_m", "discharge_m3s": "dynamic_q_m3s"}),
        on="timestamp", how="outer",
    )
    if "dynamic_round2" in sims:
        aligned = pd.merge(
            aligned,
            sims["dynamic_round2"].rename(columns={"stage_m": "dynamic2_stage_m"}),
            on="timestamp", how="outer",
        )
    aligned.to_csv(OUT_DIR / "hydrograph_aligned.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
    print(f"Saved aligned CSV to {OUT_DIR / 'hydrograph_aligned.csv'}")


def plot_comparison(obs, sims, results, out_dir):
    fig, ax = plt.subplots(figsize=(15, 7))

    ax.plot(obs["timestamp"], obs["stage_m"], color="#1f77b4", lw=2.5,
            label="Observed (Shivaji Bridge)", zorder=4, alpha=0.95)

    labels = {"static": "Static (disk offset)", "dynamic": "Dynamic (calibrated round 1)",
              "dynamic_round2": "Dynamic (calibrated round 2)"}
    colors = {"static": "#d62728", "dynamic": "#2ca02c", "dynamic_round2": "#9467bd"}
    styles = {"static": "-", "dynamic": "--", "dynamic_round2": ":"}

    # Build a clean label->result map
    result_by_label = {r["label"]: r for r in results}

    for key in ["static", "dynamic", "dynamic_round2"]:
        if key not in sims:
            continue
        # match label: "static"->"static", "dynamic"->"dynamic_calibrated", "dynamic_round2"->"dynamic_calibrated_round2"
        if key == "static":
            lbl = "static"
        elif key == "dynamic":
            lbl = "dynamic_calibrated"
        else:
            lbl = "dynamic_calibrated_round2"
        r = result_by_label.get(lbl)
        if r is None:
            continue
        ax.plot(sims[key]["timestamp"], sims[key]["stage_m"],
                color=colors[key], lw=2.2, ls=styles[key],
                label=f"{labels[key]} (NSE={r['nse']:.2f})", zorder=3)

    # Peak annotations on observed
    oi = int(obs["stage_m"].idxmax())
    ax.annotate(f"Obs peak {obs.loc[oi,'stage_m']:.2f} m\n{obs.loc[oi,'timestamp']:%b %d %H:%M}",
                xy=(obs.loc[oi, "timestamp"], obs.loc[oi, "stage_m"]),
                xytext=(15, 30), textcoords="offset points", fontsize=9, color="#1f77b4",
                arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=1))

    ax.set_title("HydroCast — Dynamic Adaptive Calibration, Aug 2025 Shivaji Bridge\n"
                 "Observed vs Static vs Dynamically-Calibrated Simulated Stage",
                 fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("Date (2025)", fontsize=11)
    ax.set_ylabel("Stage (m MSL)", fontsize=11)
    ax.set_ylim(528, 546)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.legend(loc="upper left", fontsize=10)
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    p1 = out_dir / "hydrograph_static_vs_dynamic.png"
    fig.tight_layout()
    fig.savefig(p1, dpi=150)
    print(f"Saved {p1}")

    # Peak zoom (Aug 20-22)
    fig2, ax2 = plt.subplots(figsize=(14, 6))
    for key in ["static", "dynamic", "dynamic_round2"]:
        if key not in sims:
            continue
        dfx = sims[key]
        mask = (dfx["timestamp"] >= "2025-08-20") & (dfx["timestamp"] <= "2025-08-22 23:00")
        if key == "static":
            lbl = "static"
        elif key == "dynamic":
            lbl = "dynamic_calibrated"
        else:
            lbl = "dynamic_calibrated_round2"
        r = result_by_label.get(lbl)
        if r is None:
            continue
        ax2.plot(dfx.loc[mask, "timestamp"], dfx.loc[mask, "stage_m"],
                 color=colors[key], lw=2.2, ls=styles[key],
                 label=f"{labels[key]} (NSE={r['nse']:.2f})")
    mask_obs = (obs["timestamp"] >= "2025-08-20") & (obs["timestamp"] <= "2025-08-22 23:00")
    ax2.plot(obs.loc[mask_obs, "timestamp"], obs.loc[mask_obs, "stage_m"],
             color="#1f77b4", lw=2.5, label="Observed", marker="o", ms=4, alpha=0.95)
    ax2.set_title("Peak Flood Window — Aug 20 to Aug 22, 2025", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Date (2025)", fontsize=11)
    ax2.set_ylabel("Stage (m MSL)", fontsize=11)
    ax2.set_ylim(535, 545)
    ax2.grid(True, alpha=0.3, linestyle="--")
    ax2.legend(loc="upper left", fontsize=10)
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %d\n%H:%M"))
    plt.setp(ax2.get_xticklabels(), rotation=0, ha="center")

    p2 = out_dir / "hydrograph_static_vs_dynamic_peak_zoom.png"
    fig2.tight_layout()
    fig2.savefig(p2, dpi=150)
    print(f"Saved {p2}")


if __name__ == "__main__":
    main()
