"""
Hydrograph comparison plot — August 2025 Shivaji Bridge flood.

Overlays on ONE plot:
  * Observed stage (cleaned 1-hourly telemetry)
  * Simulated stage — single 360-h block  (Strategy A, NSE=0.86)
  * Simulated stage — four 90-h rolling windows (Strategy C, NSE=-1.50)

Saves:
  results/comparison/hydrograph_comparison.png
  results/comparison/hydrograph_comparison_peak_zoom.png   (Aug 20-22 zoom)
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
from src.hms.runner import compute_emulator_hydrograph
from src.hydrology.stage_converter import convert_discharge_to_stage_manning
from src.ecmwf.station_selector import STATION_REGISTRY, select_active_subbasin_gages
from run_historical_event import fetch_historical_rainfall_for_station   # noqa: E402

START = "2025-08-08"
END = "2025-08-22"
HOURS = 360
WINDOW_H = 90
N_WIN = HOURS // WINDOW_H
DELTA_CN = 0.89
MUSKINGUM_X = 0.25
BASEFLOW = 91.1


def fetch_hyetographs():
    station_ts, station_cum = {}, {}
    for st in STATION_REGISTRY:
        series = fetch_historical_rainfall_for_station(
            st.lat, st.lon, START, END, hours=HOURS
        )
        station_ts[st.station_id] = series
        station_cum[st.station_id] = float(np.sum(series))
    sel = select_active_subbasin_gages(station_cum)
    hyetos = {}
    for sub in [f"S{i}" for i in range(1, 10)]:
        info = sel.get(sub, {})
        sid = info.get("selected_station_id", "KARVEER")
        hyetos[sub] = station_ts.get(sid, np.zeros(HOURS, dtype=np.float32)).copy()
    return hyetos, sel


def apply_calibration(sub_models, reaches):
    for sid in sub_models:
        sub_models[sid]["cn"] = float(np.clip(
            sub_models[sid]["cn"] + DELTA_CN, 45.0, 95.0))
    for rid in reaches:
        reaches[rid]["x"] = MUSKINGUM_X


def stage_from_hg(hg, run_dt):
    rows = []
    for h, q in enumerate(hg["q_total"]):
        stg = convert_discharge_to_stage_manning(float(q), "SHIVAJI_BRIDGE")
        rows.append({"timestamp": run_dt + timedelta(hours=h), "stage_m": stg})
    return pd.DataFrame(rows)


def run_strategy_A(hyetos, run_dt, sub_models, reaches):
    hg = compute_emulator_hydrograph(
        sub_models, reaches, hyetos, baseflow_m3s=BASEFLOW,
        run_dt=run_dt, sim_hours=HOURS,
    )
    return stage_from_hg(hg, run_dt), hg


def run_strategy_C(hyetos, run_dt, sub_models, reaches):
    frames, prev_q = [], BASEFLOW
    for w in range(N_WIN):
        s, e = w * WINDOW_H, (w + 1) * WINDOW_H
        win_hy = {k: v[s:e].copy() for k, v in hyetos.items()}
        wdt = run_dt + timedelta(hours=s)
        hg = compute_emulator_hydrograph(
            sub_models, reaches, win_hy, baseflow_m3s=prev_q,
            run_dt=wdt, sim_hours=WINDOW_H,
        )
        frames.append(stage_from_hg(hg, wdt))
        prev_q = float(hg["q_total"][-1])
    return pd.concat(frames, ignore_index=True)


def main():
    base_sub, base_reach = load_immutable_baseline()
    apply_calibration(base_sub, base_reach)
    hyetos, sel = fetch_hyetographs()
    print("Governing stations:")
    for sub in [f"S{i}" for i in range(1, 10)]:
        print(f"  {sub} -> {sel[sub]['selected_station_id']} "
              f"({sel[sub]['station_name']}, {sel[sub]['cumulative_mm']:.1f} mm)")

    obs = pd.read_csv(REPO / "data" / "shivaji_bridge_2025_hourly_observed.csv",
                      parse_dates=["timestamp"]).dropna(subset=["stage_m"])
    run_dt = datetime(2025, 8, 8, 0, 0, 0)

    # Strategy A
    smA, rA = copy.deepcopy(base_sub), copy.deepcopy(base_reach)
    simA, hgA = run_strategy_A(hyetos, run_dt, smA, rA)
    # Strategy C
    smC, rC = copy.deepcopy(base_sub), copy.deepcopy(base_reach)
    simC = run_strategy_C(hyetos, run_dt, smC, rC)

    # Metrics for titles
    def nse(sim, obs):
        num = np.sum((obs - sim) ** 2)
        den = np.sum((obs - np.mean(obs)) ** 2)
        return 1 - num / den if den > 0 else 0

    mA = pd.merge(obs[["timestamp", "stage_m"]].rename(columns={"stage_m": "obs"}),
                  simA.rename(columns={"stage_m": "sim"}), on="timestamp", how="inner")
    mC = pd.merge(obs[["timestamp", "stage_m"]].rename(columns={"stage_m": "obs"}),
                  simC.rename(columns={"stage_m": "sim"}), on="timestamp", how="inner")
    nseA, nseC = nse(mA["sim"], mA["obs"]), nse(mC["sim"], mC["obs"])

    # ---- Plot 1: Full event ----
    fig, ax = plt.subplots(figsize=(15, 7))

    ax.plot(obs["timestamp"], obs["stage_m"], color="#1f77b4", lw=2,
            label="Observed stage (Shivaji Bridge)", alpha=0.9, zorder=3)
    ax.plot(simA["timestamp"], simA["stage_m"], color="#d62728", lw=2.2,
            label=f"Simulated: 360-h block (NSE={nseA:.2f})", zorder=2)
    ax.plot(simC["timestamp"], simC["stage_m"], color="#2ca02c", lw=2.0, ls="--",
            label=f"Simulated: 90-h rolling (NSE={nseC:.2f})", zorder=2)

    # Peak annotations
    oi = int(obs["stage_m"].idxmax())
    ai = int(simA["stage_m"].idxmax())
    ci = int(simC["stage_m"].idxmax())
    ax.annotate(f"Obs peak {obs.loc[oi,'stage_m']:.2f} m\n{obs.loc[oi,'timestamp']:%b %d %H:%M}",
                xy=(obs.loc[oi, "timestamp"], obs.loc[oi, "stage_m"]),
                xytext=(15, 30), textcoords="offset points",
                fontsize=9, color="#1f77b4",
                arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=1))
    ax.annotate(f"360-h peak {simA.loc[ai,'stage_m']:.2f} m\n{simA.loc[ai,'timestamp']:%b %d %H:%M}",
                xy=(simA.loc[ai, "timestamp"], simA.loc[ai, "stage_m"]),
                xytext=(15, -45), textcoords="offset points",
                fontsize=9, color="#d62728",
                arrowprops=dict(arrowstyle="->", color="#d62728", lw=1))
    ax.annotate(f"90-h rolling peak {simC.loc[ci,'stage_m']:.2f} m\n{simC.loc[ci,'timestamp']:%b %d %H:%M}",
                xy=(simC.loc[ci, "timestamp"], simC.loc[ci, "stage_m"]),
                xytext=(15, -90), textcoords="offset points",
                fontsize=9, color="#2ca02c",
                arrowprops=dict(arrowstyle="->", color="#2ca02c", lw=1))

    ax.set_title("HydroCast — August 2025 Flood, Shivaji Bridge\n"
                 "Observed vs Simulated Stage Hydrograph (360-h block vs 90-h rolling windows)",
                 fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("Date (2025)", fontsize=11)
    ax.set_ylabel("Stage (m MSL)", fontsize=11)
    ax.set_ylim(528, 546)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.legend(loc="upper left", fontsize=10)

    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    out_dir = BRIDGE / "results" / "comparison"
    out_dir.mkdir(parents=True, exist_ok=True)
    p1 = out_dir / "hydrograph_comparison.png"
    fig.tight_layout()
    fig.savefig(p1, dpi=150)
    print(f"Saved {p1}")

    # ---- Plot 2: Peak zoom (Aug 20-22) ----
    fig2, ax2 = plt.subplots(figsize=(14, 6))
    mask_obs = (obs["timestamp"] >= "2025-08-20") & (obs["timestamp"] <= "2025-08-22 23:00")
    maskA = (simA["timestamp"] >= "2025-08-20") & (simA["timestamp"] <= "2025-08-22 23:00")
    maskC = (simC["timestamp"] >= "2025-08-20") & (simC["timestamp"] <= "2025-08-22 23:00")

    ax2.plot(obs.loc[mask_obs, "timestamp"], obs.loc[mask_obs, "stage_m"],
             color="#1f77b4", lw=2.5, label="Observed stage", marker="o", ms=4, alpha=0.9)
    ax2.plot(simA.loc[maskA, "timestamp"], simA.loc[maskA, "stage_m"],
             color="#d62728", lw=2.5, label=f"360-h block (NSE={nseA:.2f})")
    ax2.plot(simC.loc[maskC, "timestamp"], simC.loc[maskC, "stage_m"],
             color="#2ca02c", lw=2.0, ls="--", label=f"90-h rolling (NSE={nseC:.2f})")

    ax2.set_title("Peak Flood Window — Aug 20 to Aug 22, 2025", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Date (2025)", fontsize=11)
    ax2.set_ylabel("Stage (m MSL)", fontsize=11)
    ax2.set_ylim(535, 545)
    ax2.grid(True, alpha=0.3, linestyle="--")
    ax2.legend(loc="upper left", fontsize=10)
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %d\n%H:%M"))
    plt.setp(ax2.get_xticklabels(), rotation=0, ha="center")

    p2 = out_dir / "hydrograph_comparison_peak_zoom.png"
    fig2.tight_layout()
    fig2.savefig(p2, dpi=150)
    print(f"Saved {p2}")

    # Save aligned CSV for reference
    aligned = pd.merge(obs.rename(columns={"stage_m": "obs_stage_m"}),
                       simA.rename(columns={"stage_m": "simA_360h_stage_m"}),
                       on="timestamp", how="outer")
    aligned = pd.merge(aligned, simC.rename(columns={"stage_m": "simC_90h_stage_m"}),
                       on="timestamp", how="outer")
    p3 = out_dir / "hydrograph_aligned.csv"
    aligned.to_csv(p3, index=False, date_format="%Y-%m-%d %H:%M:%S")
    print(f"Saved {p3}")


if __name__ == "__main__":
    main()
