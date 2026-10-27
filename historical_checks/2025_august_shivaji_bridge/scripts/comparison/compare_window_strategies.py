"""
Window-strategy comparison for the August 2025 Shivaji Bridge flood.

Question: does splitting a 14-day (360-h) monsoon event into four consecutive
90-hour windows improve accuracy vs. one continuous 360-h block?

Strategies (all calibration-aware, using the same delta_cn=0.89 offset that
_execute_hec_hms_core applies from data/telemetry/ml_calibration_state.json):

  A) Single 360-h block — baseflow 91.1 m3/s at T+0, runs straight through.
  B) Four 90-h windows, fresh start — each window resets baseflow to 91.1 m3/s
     and SCS antecedent moisture (operationally independent forecast cycles).
  C) Four 90-h windows, rolling — each window initializes baseflow from the
     previous window's ending discharge (the river does not reset every 90 h).

For each strategy we convert hourly discharge -> Shivaji Bridge stage via the
WRD rating curve, align to observed hourly stage, and compute NSE, KGE, RMSE,
MAE, PBIAS, peak-stage error, and peak-timing error.
"""
import json
import copy
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(REPO))

from src.ecmwf.station_selector import STATION_REGISTRY, select_active_subbasin_gages
from src.hms.basin_parser import load_immutable_baseline
from src.hms.runner import compute_emulator_hydrograph
from src.hydrology.stage_converter import convert_discharge_to_stage_manning
from src.hydrology.validation_metrics import (
    compute_nse, compute_rmse_mae, compute_kge, compute_pbias,
)
sys.path.insert(0, str(REPO / "historical_checks"))
from run_historical_event import fetch_historical_rainfall_for_station  # noqa: E402

START = "2025-08-08"
END = "2025-08-22"
HOURS = 360
WINDOW_H = 90
N_WIN = HOURS // WINDOW_H   # 4

# Calibration offsets that _execute_hec_hms_core applies from ml_calibration_state.json
DELTA_CN = 0.89
MUSKINGUM_X = 0.25
BASEFLOW_FALLBACK = 91.1

OBS_CSV = REPO / "data" / "shivaji_bridge_2025_hourly_observed.csv"


def apply_calibration(sub_models, reaches):
    """Apply the same offsets _execute_hec_hms_core applies from disk state:
    CN + delta_cn (clipped), reach k*x alpha (alpha_k=1.0 -> no change), and
    reach x = muskingum_x (0.25 vs baseline 0.20)."""
    for sid in sub_models:
        sub_models[sid]["cn"] = float(np.clip(
            sub_models[sid]["cn"] + DELTA_CN, 45.0, 95.0))
    for rid in reaches:
        reaches[rid]["x"] = MUSKINGUM_X


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


def stage_series(q_total, run_dt):
    rows = []
    for h, q in enumerate(q_total):
        stg = convert_discharge_to_stage_manning(float(q), "SHIVAJI_BRIDGE")
        rows.append({"timestamp": run_dt + timedelta(hours=h), "stage_m": stg})
    return pd.DataFrame(rows)


def run_strategy_A(hyetos, run_dt, sub_models, reaches):
    hg = compute_emulator_hydrograph(
        sub_models, reaches, hyetos, baseflow_m3s=BASEFLOW_FALLBACK,
        run_dt=run_dt, sim_hours=HOURS,
    )
    return stage_series(hg["q_total"], run_dt), hg


def run_strategy_B(hyetos, run_dt, sub_models, reaches):
    frames, peaks = [], []
    for w in range(N_WIN):
        s, e = w * WINDOW_H, (w + 1) * WINDOW_H
        win_hy = {k: v[s:e].copy() for k, v in hyetos.items()}
        wdt = run_dt + timedelta(hours=s)
        hg = compute_emulator_hydrograph(
            sub_models, reaches, win_hy, baseflow_m3s=BASEFLOW_FALLBACK,
            run_dt=wdt, sim_hours=WINDOW_H,
        )
        frames.append(stage_series(hg["q_total"], wdt))
        peaks.append((float(hg["peak_q"]), int(hg["peak_h"])))
    return pd.concat(frames, ignore_index=True), peaks


def run_strategy_C(hyetos, run_dt, sub_models, reaches):
    frames, peaks, prev_q = [], [], BASEFLOW_FALLBACK
    for w in range(N_WIN):
        s, e = w * WINDOW_H, (w + 1) * WINDOW_H
        win_hy = {k: v[s:e].copy() for k, v in hyetos.items()}
        wdt = run_dt + timedelta(hours=s)
        hg = compute_emulator_hydrograph(
            sub_models, reaches, win_hy, baseflow_m3s=prev_q,
            run_dt=wdt, sim_hours=WINDOW_H,
        )
        frames.append(stage_series(hg["q_total"], wdt))
        peaks.append((float(hg["peak_q"]), int(hg["peak_h"])))
        prev_q = float(hg["q_total"][-1])
    return pd.concat(frames, ignore_index=True), peaks


def evaluate(name, sim_df, obs_df):
    obs_r = obs_df.rename(columns={"stage_m": "obs_stage"})[["timestamp", "obs_stage"]]
    sim_r = sim_df.rename(columns={"stage_m": "sim_stage"})[["timestamp", "sim_stage"]]
    m = pd.merge(obs_r, sim_r, on="timestamp", how="inner")
    if len(m) < 3:
        return None
    sim_s = m["sim_stage"].to_numpy(dtype=float)
    obs_s = m["obs_stage"].to_numpy(dtype=float)
    nse = compute_nse(sim_s, obs_s)
    rmse, mae = compute_rmse_mae(sim_s, obs_s)
    kge = compute_kge(sim_s, obs_s)
    pbias = compute_pbias(sim_s, obs_s)
    oi = int(np.argmax(obs_s)); si = int(np.argmax(sim_s))
    p_err = sim_s[si] - obs_s[oi]
    p_dt = (m.iloc[si]["timestamp"] - m.iloc[oi]["timestamp"]).total_seconds() / 3600.0
    return {
        "strategy": name, "matched": int(len(m)),
        "nse": round(nse, 4), "kge": round(kge, 4),
        "rmse": round(rmse, 3), "mae": round(mae, 3), "pbias": round(pbias, 2),
        "peak_err_m": round(p_err, 2),
        "peak_timing_err_h": round(p_dt, 2),
        "obs_peak_m": round(float(obs_s[oi]), 2),
        "sim_peak_m": round(float(sim_s[si]), 2),
    }


def main():
    base_sub, base_reach = load_immutable_baseline()
    apply_calibration(base_sub, base_reach)   # match _execute_hec_hms_core calibration
    hyetos, sel = fetch_hyetographs()
    print("Governing stations per subbasin:")
    for sub in [f"S{i}" for i in range(1, 10)]:
        print(f"  {sub} -> {sel[sub]['selected_station_id']} "
              f"({sel[sub]['station_name']}, {sel[sub]['cumulative_mm']:.1f} mm)")

    obs = pd.read_csv(OBS_CSV, parse_dates=["timestamp"]).dropna(subset=["stage_m"])
    run_dt = datetime(2025, 8, 8, 0, 0, 0)
    results = []

    def fresh():
        return copy.deepcopy(base_sub), copy.deepcopy(base_reach)

    print("\n=== Strategy A: single 360-h block ===")
    sm, r = fresh()
    simA, hgA = run_strategy_A(hyetos, run_dt, sm, r)
    rA = evaluate("A_single_360h_block", simA, obs)
    results.append(rA)
    print(json.dumps(rA, indent=2))

    print("\n=== Strategy B: 4x90-h windows, fresh start each ===")
    sm, r = fresh()
    simB, peaksB = run_strategy_B(hyetos, run_dt, sm, r)
    rB = evaluate("B_4x90h_fresh_start", simB, obs)
    results.append(rB)
    print(json.dumps(rB, indent=2))

    print("\n=== Strategy C: 4x90-h windows, rolling baseflow ===")
    sm, r = fresh()
    simC, peaksC = run_strategy_C(hyetos, run_dt, sm, r)
    rC = evaluate("C_4x90h_rolling_baseflow", simC, obs)
    results.append(rC)
    print(json.dumps(rC, indent=2))

    print("\n=== Strategy C per-window peaks ===")
    for w, (q, ph) in enumerate(peaksC):
        print(f"  window {w+1} (h {w*90}-{(w+1)*90}): peak Q={q:.1f} m3/s at T+{ph}h")

    print("\n=== COMPARISON ===")
    print(f"{'strategy':<32}{'matched':>8}{'NSE':>8}{'KGE':>8}{'RMSE':>8}{'MAE':>8}{'PBIAS':>9}{'peakErr':>9}{'timingErr':>10}")
    for r in results:
        print(f"{r['strategy']:<32}{r['matched']:>8}{r['nse']:>8.3f}{r['kge']:>8.3f}"
              f"{r['rmse']:>8.3f}{r['mae']:>8.3f}{r['pbias']:>9.2f}{r['peak_err_m']:>9.2f}"
              f"{r['peak_timing_err_h']:>10.2f}")

    out_dir = REPO / "historical_checks" / "2025_august_shivaji_bridge" / "results" / "comparison"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "window_strategy_comparison.json"
    with open(out, "w") as f:
        json.dump({"results": results}, f, indent=2)
    print(f"\nSaved comparison to {out}")


if __name__ == "__main__":
    main()
