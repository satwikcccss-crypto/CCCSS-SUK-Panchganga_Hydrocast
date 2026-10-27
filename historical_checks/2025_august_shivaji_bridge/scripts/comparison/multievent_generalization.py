"""
Multi-event generalization test — prove the per-subbasin config is a real digital twin,
not a one-event overfit.

Runs the physically-differentiated per-subbasin/per-reach config against ALL registered
historical events (2019_august, 2021_july, 2025_august) and checks:
  - 2025_august (Shivaji Bridge): full NSE/KGE/RMSE/peak/timing vs observed hourly CSV.
  - 2019/2021 (Rajaram Weir): peak discharge vs reported event peak (no hourly observed).

A config that holds up across events is safe to promote to production calibration state.
"""
import copy
import json
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
from run_historical_event import fetch_historical_rainfall_for_station, EVENTS   # noqa: E402

OUT_DIR = BRIDGE / "results" / "dynamic_calibration"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Per-subbasin life-safety config (physically differentiated; best-NSE from pass 1)
ALPHA_K = 0.80
ALPHA_LAG = 0.82
CN_UPLIFT = 0.0
MUSK_X = 0.15
IA_FRAC = 0.05
UH_MAX_HR = 90
UH_M_EXP = 20


def fetch_hyetographs(start_date, end_date, hours):
    station_ts, station_cum = {}, {}
    for st in STATION_REGISTRY:
        series = fetch_historical_rainfall_for_station(st.lat, st.lon, start_date, end_date, hours=hours)
        station_ts[st.station_id] = series
        station_cum[st.station_id] = float(np.sum(series))
    sel = select_active_subbasin_gages(station_cum)
    hyetos = {}
    for sub in [f"S{i}" for i in range(1, 10)]:
        info = sel.get(sub, {})
        sid = info.get("selected_station_id", "KARVEER")
        hyetos[sub] = station_ts.get(sid, np.zeros(hours, dtype=np.float32)).copy()
    return hyetos


def run_sim(hyetos, run_dt, hours):
    base_sub, base_reach = load_immutable_baseline()
    sub_models = copy.deepcopy(base_sub)
    reaches = copy.deepcopy(base_reach)
    for sid in sub_models:
        sub_models[sid]["cn"] = float(np.clip(float(sub_models[sid]["cn"]) + CN_UPLIFT, 45.0, 95.0))
        sub_models[sid]["lag_min"] = float(sub_models[sid]["lag_min"] * ALPHA_LAG)
    for rid in reaches:
        reaches[rid]["k_hr"] = float(reaches[rid]["k_hr"] * ALPHA_K)
        reaches[rid]["x"] = MUSK_X
    parameter_overrides = {
        "sub_models": {sid: {"cn": sub_models[sid]["cn"], "lag_min": sub_models[sid]["lag_min"]} for sid in sub_models},
        "reaches": {rid: {"k_hr": reaches[rid]["k_hr"], "x": reaches[rid]["x"]} for rid in reaches},
        "alpha_k": ALPHA_K, "alpha_lag": ALPHA_LAG, "delta_cn": CN_UPLIFT, "muskingum_x": MUSK_X,
    }
    result = _execute_hec_hms_core(run_dt, subbasin_hyetographs=hyetos, live_stage_m=None,
                                   parameter_overrides=parameter_overrides, amc="AMC-III",
                                   sim_hours=hours, ia_frac=IA_FRAC, uh_max_hr=UH_MAX_HR, uh_m_exp=UH_M_EXP)
    rows = []
    for entry in result["hydrograph"]:
        ts = pd.to_datetime(entry["timestamp"])
        q = float(entry.get("discharge_m3s") or 0.0)
        rows.append({"timestamp": ts, "stage_m": convert_discharge_to_stage_manning(q, "SHIVAJI_BRIDGE"),
                     "discharge_m3s": q})
    return pd.DataFrame(rows)


def eval_event(key, cfg):
    start = cfg["start_date"]; end = cfg["end_date"]
    run_dt = datetime.strptime(start, "%Y-%m-%d")
    hours = cfg.get("sim_hours") or int((pd.Timestamp(end) - pd.Timestamp(start)).total_seconds() // 3600) + 24
    hyetos = fetch_hyetographs(start, end, hours)
    sim = run_sim(hyetos, run_dt, hours)
    obs_csv = cfg.get("observed_csv")
    out = {"event": key, "start": start, "end": end, "sim_hours": hours}
    peak_idx = int(np.argmax(sim["discharge_m3s"].to_numpy()))
    out["sim_peak_q_m3s"] = round(float(sim["discharge_m3s"].iloc[peak_idx]), 1)
    out["sim_peak_ts"] = str(sim["timestamp"].iloc[peak_idx])
    out["sim_peak_stage_shivaji_m"] = round(float(sim["stage_m"].iloc[peak_idx]), 2)
    rep_peak_q = cfg.get("observed", {}).get("peak_discharge_m3s")
    if rep_peak_q:
        out["reported_peak_q_m3s"] = rep_peak_q
        out["peak_q_err_pct"] = round(100.0 * (out["sim_peak_q_m3s"] - rep_peak_q) / rep_peak_q, 1)
    if obs_csv and (REPO / obs_csv).exists():
        obs = pd.read_csv(REPO / obs_csv, parse_dates=["timestamp"]).dropna(subset=["stage_m"])
        m = pd.merge(obs.loc[:, ["timestamp", "stage_m"]].rename(columns={"stage_m": "obs"}),
                     sim.loc[:, ["timestamp", "stage_m"]].rename(columns={"stage_m": "sim"}),
                     on="timestamp", how="inner")
        sim_s = m["sim_stage" if "sim_stage" in m else "sim"].to_numpy(dtype=float)
        obs_s = m["obs"].to_numpy(dtype=float)
        nse = compute_nse(sim_s, obs_s); rmse, mae = compute_rmse_mae(sim_s, obs_s)
        kge = compute_kge(sim_s, obs_s); pbias = compute_pbias(sim_s, obs_s)
        oi = int(np.argmax(obs_s)); si = int(np.argmax(sim_s))
        out.update({
            "nse": round(nse, 4), "kge": round(kge, 4), "rmse": round(rmse, 3),
            "mae": round(mae, 3), "pbias": round(pbias, 2),
            "peak_err_m": round(float(sim_s[si] - obs_s[oi]), 2),
            "timing_err_h": round((m.iloc[si]["timestamp"] - m.iloc[oi]["timestamp"]).total_seconds() / 3600.0, 1),
            "obs_peak_m": round(float(obs_s[oi]), 2), "sim_peak_m": round(float(sim_s[si]), 2),
            "matched": int(len(m)),
        })
    return out


def main():
    results = []
    for key in ["2019_august", "2021_july", "2025_august"]:
        cfg = EVENTS[key]
        try:
            r = eval_event(key, cfg)
            results.append(r)
            extra = ""
            if "nse" in r:
                extra = (f" NSE={r['nse']:.3f} KGE={r['kge']:.3f} peak_err={r['peak_err_m']:+.2f}m "
                         f"timing={r['timing_err_h']:+.1f}h")
            qpart = ""
            if "peak_q_err_pct" in r:
                qpart = f" | peakQ sim={r['sim_peak_q_m3s']} vs rep={r['reported_peak_q_m3s']} ({r['peak_q_err_pct']:+.1f}%)"
            print(f"{key}: simPeakStage(Shivaji)={r['sim_peak_stage_shivaji_m']}m @{r['sim_peak_ts']}{extra}{qpart}",
                  flush=True)
        except Exception as e:
            print(f"{key}: ERROR {e}", flush=True)
            results.append({"event": key, "error": str(e)})

    with open(OUT_DIR / "multievent_generalization_results.json", "w") as f:
        json.dump({"config": {"alpha_k": ALPHA_K, "alpha_lag": ALPHA_LAG, "cn_uplift": CN_UPLIFT,
                              "muskingum_x": MUSK_X, "ia_frac": IA_FRAC, "uh_max_hr": UH_MAX_HR,
                              "uh_m_exp": UH_M_EXP, "cn_style": "per_subbasin_baseline"},
                   "results": results}, f, indent=2, default=str)
    print(f"\nSaved to {OUT_DIR / 'multievent_generalization_results.json'}")


if __name__ == "__main__":
    main()
