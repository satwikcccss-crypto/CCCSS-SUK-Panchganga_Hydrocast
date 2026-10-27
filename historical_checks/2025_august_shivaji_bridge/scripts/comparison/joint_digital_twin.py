"""
Joint multi-event digital-twin calibration — Aug 2019 / Jul 2021 / Aug 2025.

Fixes the overfit found by multievent_generalization.py (2025 NSE=0.929 but 2019 peakQ +59%):

  1. DYNAMIC, ANTECEDENT-BASED AMC — classify each event's antecedent moisture from the
     5-day (120h) rainfall BEFORE the storm (SCS thresholds 12.7 / 27.9 mm), instead of
     forcing AMC-III on every monsoon event. A drier 2019 antecedent -> AMC-II -> less
     runoff; a saturated 2025 -> AMC-III. This is the physically-correct lever that lets
     one parameter set fit both a wet and a marginally-drier flood.

  2. JOINT OBJECTIVE — tune per-subbasin CN uplift + per-reach alpha_K to balance:
        2025: maximize NSE (full hourly observed at Shivaji Bridge)
        2019: minimize |peak discharge error| vs reported 2111 m3/s (at Rajaram sink)
        2021: sanity (peak stage, reported at Rajaram; site offset noted)

Per-subbasin CN and per-reach K/lag remain physically differentiated throughout.
"""
import copy
import json
from datetime import datetime, timedelta
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

OUT_DIR = BRIDGE / "results" / "dynamic_calibration"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SUBS = [f"S{i}" for i in range(1, 10)]

# SCS 5-day antecedent-rain AMC thresholds (mm)
AMC5_DRY = 12.7
AMC5_WET = 27.9

EVENTS = {
    "2019_august": {"start": "2019-08-01", "end": "2019-08-15", "rep_peak_q": 2111.0,
                    "obs_csv": None, "weight": 1.0},
    "2021_july":   {"start": "2021-07-18", "end": "2021-07-31", "rep_peak_q": None,
                    "obs_csv": None, "weight": 0.3},
    "2025_august": {"start": "2025-08-08", "end": "2025-08-22", "rep_peak_q": None,
                    "obs_csv": "data/shivaji_bridge_2025_hourly_observed.csv", "weight": 1.0},
}


def fetch_event_and_antecedent(key, cfg):
    """Fetch event-window hyetographs + 5-day antecedent rain per governing station."""
    start = pd.Timestamp(cfg["start"])
    ant_start = (start - timedelta(days=5)).strftime("%Y-%m-%d")
    ant_end = start.strftime("%Y-%m-%d")
    end = cfg["end"]
    hours = int((pd.Timestamp(end) - start).total_seconds() // 3600) + 24

    st_event, st_ant, st_cum = {}, {}, {}
    for st in STATION_REGISTRY:
        ev = fetch_historical_rainfall_for_station(st.lat, st.lon, cfg["start"], end, hours=hours)
        st_event[st.station_id] = ev
        st_cum[st.station_id] = float(np.sum(ev))
        # antecedent: 120h window ending at event start
        an = fetch_historical_rainfall_for_station(st.lat, st.lon, ant_start, ant_end, hours=120)
        st_ant[st.station_id] = float(np.sum(an))

    sel = select_active_subbasin_gages(st_cum)
    hyetos, ant_mm = {}, {}
    for sub in SUBS:
        info = sel.get(sub, {})
        sid = info.get("selected_station_id", "KARVEER")
        hyetos[sub] = st_event.get(sid, np.zeros(hours, dtype=np.float32)).copy()
        ant_mm[sub] = st_ant.get(sid, 0.0)
    mean_ant = float(np.mean([ant_mm[s] for s in SUBS]))
    return hyetos, mean_ant, hours, start


def classify_amc5(mean_ant_mm):
    if mean_ant_mm < AMC5_DRY:
        return "AMC-I"
    if mean_ant_mm >= AMC5_WET:
        return "AMC-III"
    return "AMC-II"


def run_sim(hyetos, run_dt, hours, cn_uplift, alpha_k, alpha_lag, amc, ia_frac):
    base_sub, base_reach = load_immutable_baseline()
    sub_models = copy.deepcopy(base_sub)
    reaches = copy.deepcopy(base_reach)
    for sid in sub_models:
        sub_models[sid]["cn"] = float(np.clip(float(sub_models[sid]["cn"]) + cn_uplift, 45.0, 95.0))
        sub_models[sid]["lag_min"] = float(sub_models[sid]["lag_min"] * alpha_lag)
    for rid in reaches:
        reaches[rid]["k_hr"] = float(reaches[rid]["k_hr"] * alpha_k)
        reaches[rid]["x"] = 0.15
    parameter_overrides = {
        "sub_models": {sid: {"cn": sub_models[sid]["cn"], "lag_min": sub_models[sid]["lag_min"]} for sid in sub_models},
        "reaches": {rid: {"k_hr": reaches[rid]["k_hr"], "x": reaches[rid]["x"]} for rid in reaches},
        "alpha_k": alpha_k, "alpha_lag": alpha_lag, "delta_cn": cn_uplift, "muskingum_x": 0.15,
    }
    result = _execute_hec_hms_core(run_dt, subbasin_hyetographs=hyetos, live_stage_m=None,
                                   parameter_overrides=parameter_overrides, amc=amc,
                                   sim_hours=hours, ia_frac=ia_frac, uh_max_hr=90, uh_m_exp=20)
    rows = []
    for entry in result["hydrograph"]:
        ts = pd.to_datetime(entry["timestamp"])
        q = float(entry.get("discharge_m3s") or 0.0)
        rows.append({"timestamp": ts, "stage_m": convert_discharge_to_stage_manning(q, "SHIVAJI_BRIDGE"),
                     "discharge_m3s": q})
    return pd.DataFrame(rows)


def score_event(key, cfg, sim, prep):
    out = {"event": key, "amc": prep["amc"], "mean_antecedent_mm": round(prep["ant"], 1)}
    pq = int(np.argmax(sim["discharge_m3s"].to_numpy()))
    out["sim_peak_q_m3s"] = round(float(sim["discharge_m3s"].iloc[pq]), 1)
    out["sim_peak_ts"] = str(sim["timestamp"].iloc[pq])
    obj = 0.0
    if cfg.get("rep_peak_q"):
        rep = cfg["rep_peak_q"]
        frac = (out["sim_peak_q_m3s"] - rep) / rep
        out["rep_peak_q_m3s"] = rep
        out["peak_q_err_pct"] = round(100.0 * frac, 1)
        obj += cfg["weight"] * abs(frac) * 100.0   # penalize % peak-Q error
    if cfg.get("obs_csv") and (REPO / cfg["obs_csv"]).exists():
        obs = pd.read_csv(REPO / cfg["obs_csv"], parse_dates=["timestamp"]).dropna(subset=["stage_m"])
        m = pd.merge(obs.loc[:, ["timestamp", "stage_m"]].rename(columns={"stage_m": "obs"}),
                     sim.loc[:, ["timestamp", "stage_m"]].rename(columns={"stage_m": "sim"}),
                     on="timestamp", how="inner")
        obs_s = m["obs"].to_numpy(dtype=float); sim_s = m["sim"].to_numpy(dtype=float)
        nse = compute_nse(sim_s, obs_s); rmse, mae = compute_rmse_mae(sim_s, obs_s)
        kge = compute_kge(sim_s, obs_s)
        oi = int(np.argmax(obs_s)); si = int(np.argmax(sim_s))
        out.update({"nse": round(nse, 4), "kge": round(kge, 4), "rmse": round(rmse, 3),
                    "peak_err_m": round(float(sim_s[si] - obs_s[oi]), 2),
                    "timing_err_h": round((m.iloc[si]["timestamp"] - m.iloc[oi]["timestamp"]).total_seconds()/3600.0, 1)})
        # joint objective: reward NSE, penalize peak under/over & timing
        obj += cfg["weight"] * ((1.0 - nse) * 100.0)
        obj += cfg["weight"] * (abs(out["peak_err_m"]) * 20.0)
        obj += cfg["weight"] * (abs(out["timing_err_h"]) * 1.5)
    out["obj"] = round(obj, 2)
    return out


def main():
    # Pre-fetch all events once (slow Open-Meteo calls)
    preps = {}
    for key, cfg in EVENTS.items():
        hyetos, ant, hours, start = fetch_event_and_antecedent(key, cfg)
        amc = classify_amc5(ant)
        preps[key] = {"hyetos": hyetos, "ant": ant, "hours": hours, "start": start, "amc": amc}
        print(f"[fetch] {key}: antecedent5d={ant:.1f}mm -> {amc}, hours={hours}", flush=True)

    best = None
    all_rows = []
    for cn_uplift in [-2.0, 0.0, 2.0, 4.0]:
        for alpha_k in [0.80, 0.85, 0.90]:
            for ia_frac in [0.05, 0.08]:
                per_event, total_obj = {}, 0.0
                ok = True
                for key, cfg in EVENTS.items():
                    p = preps[key]
                    try:
                        sim = run_sim(p["hyetos"], p["start"], p["hours"], cn_uplift, alpha_k, 0.82,
                                      p["amc"], ia_frac)
                        r = score_event(key, cfg, sim, p)
                        per_event[key] = r
                        total_obj += r["obj"]
                    except Exception as e:
                        ok = False
                        print(f"  ERROR {key} cn=+{cn_uplift} ak={alpha_k} ia={ia_frac}: {e}", flush=True)
                        break
                if not ok:
                    continue
                row = {"cn_uplift": cn_uplift, "alpha_k": alpha_k, "ia_frac": ia_frac,
                       "total_obj": round(total_obj, 2), "events": per_event}
                all_rows.append(row)
                e25 = per_event.get("2025_august", {})
                e19 = per_event.get("2019_august", {})
                print(f"cn=+{cn_uplift} ak={alpha_k} ia={ia_frac} -> obj={total_obj:.1f} | "
                      f"2025 NSE={e25.get('nse','n/a')} peak={e25.get('peak_err_m','n/a')}m | "
                      f"2019 peakQ%={e19.get('peak_q_err_pct','n/a')} (AMC {e19.get('amc')})", flush=True)
                if best is None or total_obj < best["total_obj"]:
                    best = row

    all_rows.sort(key=lambda r: r["total_obj"])
    print("\n=== TOP 5 JOINT CONFIGS (lower obj better) ===")
    for r in all_rows[:5]:
        e25 = r["events"].get("2025_august", {}); e19 = r["events"].get("2019_august", {})
        print(f"  cn=+{r['cn_uplift']} ak={r['alpha_k']} ia={r['ia_frac']} obj={r['total_obj']} | "
              f"2025 NSE={e25.get('nse')} peak={e25.get('peak_err_m')}m timing={e25.get('timing_err_h')}h | "
              f"2019 peakQ%={e19.get('peak_q_err_pct')} AMC={e19.get('amc')}")

    with open(OUT_DIR / "joint_digital_twin_results.json", "w") as f:
        json.dump({"best": best, "all": all_rows}, f, indent=2, default=str)
    print(f"\nSaved to {OUT_DIR / 'joint_digital_twin_results.json'}")


if __name__ == "__main__":
    main()
