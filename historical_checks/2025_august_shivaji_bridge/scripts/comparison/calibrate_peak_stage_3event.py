"""
PEAK-STAGE 3-event digital-twin calibration (hydrologist directive, 2026-10-27).

User guidance integrated:
  * WSE (water level) is the truth; ultimate goal = forecast flood LEVELS.
  * Backwater (Krishna) is SMALL: 0.4-0.5 m, up to ~1 m — NOT the 4-6 m I once attributed
    to it. So the large 2019/2021 peak-stage gaps are mostly ROUTING (K, X, lag), not backwater.
  * FORGET NSE. Match PEAK STAGE accuracy. 80-90% on 2019 AND 2021 is "very good".

Peak-stage accuracy (fraction of flood depth above channel bed that the model captures):
    acc = 1 - |sim_peak - obs_peak| / (obs_peak - bed)
    2019/2021 @ Rajaram bed 529.318 ; 2025 @ Shivaji bed 528.670

Tunes ROUTING (alpha_K = Muskingum K, muskingum_x = X, alpha_lag = basin lag) with a small
CN sweep. Objective = peak-stage miss across the 3 events, with a conservative (never
under-predict) bias. Fixed: ia_frac=0.05, uh_max_hr=90, uh_m_exp=20 (validated 2025 shaping).
"""
import copy
import json
from datetime import timedelta
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
from src.ecmwf.station_selector import STATION_REGISTRY, select_active_subbasin_gages
from run_historical_event import fetch_historical_rainfall_for_station   # noqa: E402

OUT_DIR = BRIDGE / "results" / "dynamic_calibration"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SUBS = [f"S{i}" for i in range(1, 10)]
AMC5_DRY, AMC5_WET = 12.7, 27.9

SHIVAJI_BED, RAJARAM_BED = 528.670, 529.318

EVENTS = {
    "2019_august": {"start": "2019-08-01", "end": "2019-08-15", "site": "RAJARAM_WEIR",
                    "obs_peak": 546.97, "bed": RAJARAM_BED, "obs_q": 2111.0},
    "2021_july":   {"start": "2021-07-18", "end": "2021-07-31", "site": "RAJARAM_WEIR",
                    "obs_peak": 547.83, "bed": RAJARAM_BED, "obs_q": None},
    "2025_august": {"start": "2025-08-08", "end": "2025-08-22", "site": "SHIVAJI_BRIDGE",
                    "obs_peak": 542.57, "bed": SHIVAJI_BED, "obs_q": None},
}


def fetch_event_antecedent(cfg):
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
        an = fetch_historical_rainfall_for_station(st.lat, st.lon, ant_start, ant_end, hours=120)
        st_ant[st.station_id] = float(np.sum(an))
    sel = select_active_subbasin_gages(st_cum)
    hyetos = {}
    for sub in SUBS:
        sid = sel.get(sub, {}).get("selected_station_id", "KARVEER")
        hyetos[sub] = st_event.get(sid, np.zeros(hours, dtype=np.float32)).copy()
    mean_ant = float(np.mean([st_ant.get(sel.get(s, {}).get("selected_station_id", "KARVEER"), 0.0) for s in SUBS]))
    return hyetos, mean_ant, hours, start


def classify_amc5(ant):
    if ant < AMC5_DRY:
        return "AMC-I"
    if ant >= AMC5_WET:
        return "AMC-III"
    return "AMC-II"


def run_sim(hyetos, run_dt, hours, cn_uplift, alpha_k, alpha_lag, musk_x, amc, site):
    base_sub, base_reach = load_immutable_baseline()
    sub_models = copy.deepcopy(base_sub)
    reaches = copy.deepcopy(base_reach)
    for sid in sub_models:
        sub_models[sid]["cn"] = float(np.clip(float(sub_models[sid]["cn"]) + cn_uplift, 45.0, 98.0))
        sub_models[sid]["lag_min"] = float(sub_models[sid]["lag_min"] * alpha_lag)
    for rid in reaches:
        reaches[rid]["k_hr"] = float(reaches[rid]["k_hr"] * alpha_k)
        reaches[rid]["x"] = musk_x
    po = {
        "sub_models": {sid: {"cn": sub_models[sid]["cn"], "lag_min": sub_models[sid]["lag_min"]} for sid in sub_models},
        "reaches": {rid: {"k_hr": reaches[rid]["k_hr"], "x": reaches[rid]["x"]} for rid in reaches},
        "alpha_k": alpha_k, "alpha_lag": alpha_lag, "delta_cn": cn_uplift, "muskingum_x": musk_x,
    }
    res = _execute_hec_hms_core(run_dt, subbasin_hyetographs=hyetos, live_stage_m=None,
                                parameter_overrides=po, amc=amc, sim_hours=hours,
                                ia_frac=0.05, uh_max_hr=90, uh_m_exp=20)
    hg = res["hydrograph"]
    q = np.array([e.get("discharge_m3s") or 0.0 for e in hg], dtype=float)
    ts = [pd.to_datetime(e["timestamp"]) for e in hg]
    stage = np.array([convert_discharge_to_stage_manning(float(x), site) for x in q])
    return ts, stage, float(q.max())


def score_event(cfg, ts, stage, peak_q):
    si = int(np.argmax(stage))
    sim_peak = float(stage[si])
    obs = cfg["obs_peak"]
    depth = obs - cfg["bed"]
    err = sim_peak - obs
    acc = 1.0 - abs(err) / depth
    out = {
        "sim_peak_wse_m": round(sim_peak, 2),
        "obs_peak_wse_m": obs,
        "peak_err_m": round(err, 2),
        "peak_stage_accuracy_pct": round(acc * 100.0, 1),
        "sim_peak_q_m3s": round(peak_q, 0),
        "sim_peak_ts": str(ts[si]),
    }
    if cfg.get("obs_q"):
        out["obs_q_m3s"] = cfg["obs_q"]
        out["peak_q_err_pct"] = round(100.0 * (peak_q - cfg["obs_q"]) / cfg["obs_q"], 1)
    # objective: miss fraction (x100) + extra penalty for under-prediction (conservative)
    obj = (abs(err) / depth) * 100.0 + max(0.0, -err) / depth * 50.0
    out["obj"] = round(obj, 2)
    return out


def main():
    preps = {}
    for key, cfg in EVENTS.items():
        hyetos, ant, hours, start = fetch_event_antecedent(cfg)
        amc = classify_amc5(ant)
        preps[key] = {"hyetos": hyetos, "ant": ant, "hours": hours, "start": start, "amc": amc}
        print(f"[fetch] {key}: ant5d={ant:.1f}mm -> {amc}, hours={hours}", flush=True)

    all_rows = []
    for alpha_k in [0.80, 0.60, 0.45]:
        for alpha_lag in [0.82, 0.60]:
            for musk_x in [0.15, 0.30]:
                for cn_uplift in [0.0]:
                    per_event, total = {}, 0.0
                    ok = True
                    for key, cfg in EVENTS.items():
                        p = preps[key]
                        try:
                            ts, stage, pq = run_sim(p["hyetos"], p["start"], p["hours"], cn_uplift,
                                                    alpha_k, alpha_lag, musk_x, p["amc"], cfg["site"])
                            r = score_event(cfg, ts, stage, pq)
                            per_event[key] = r
                            total += r["obj"]
                        except Exception as e:
                            ok = False
                            print(f"  ERROR {key} ak={alpha_k} alag={alpha_lag} x={musk_x}: {e}", flush=True)
                            break
                    if not ok:
                        continue
                    row = {"alpha_k": alpha_k, "alpha_lag": alpha_lag, "muskingum_x": musk_x,
                           "cn_uplift": cn_uplift, "total_obj": round(total, 2), "events": per_event}
                    all_rows.append(row)
                    e19 = per_event.get("2019_august", {}); e21 = per_event.get("2021_july", {}); e25 = per_event.get("2025_august", {})
                    print(f"ak={alpha_k} alag={alpha_lag} x={musk_x} obj={total:.1f} | "
                          f"2019 acc={e19.get('peak_stage_accuracy_pct','n/a')}% err={e19.get('peak_err_m','n/a')}m | "
                          f"2021 acc={e21.get('peak_stage_accuracy_pct','n/a')}% err={e21.get('peak_err_m','n/a')}m | "
                          f"2025 acc={e25.get('peak_stage_accuracy_pct','n/a')}% err={e25.get('peak_err_m','n/a')}m", flush=True)

    all_rows.sort(key=lambda r: r["total_obj"])
    print("\n=== TOP 6 PEAK-STAGE (lower obj better; 80-90% acc = target) ===")
    for r in all_rows[:6]:
        e19 = r["events"].get("2019_august", {}); e21 = r["events"].get("2021_july", {}); e25 = r["events"].get("2025_august", {})
        print(f"  ak={r['alpha_k']} alag={r['alpha_lag']} x={r['muskingum_x']} obj={r['total_obj']} | "
              f"2019 {e19.get('peak_stage_accuracy_pct')}% (err {e19.get('peak_err_m')}m) | "
              f"2021 {e21.get('peak_stage_accuracy_pct')}% (err {e21.get('peak_err_m')}m) | "
              f"2025 {e25.get('peak_stage_accuracy_pct')}% (err {e25.get('peak_err_m')}m)")

    with open(OUT_DIR / "peak_stage_3event_results.json", "w") as f:
        json.dump({"all": all_rows, "best": all_rows[0] if all_rows else None,
                   "metric": "acc = 1 - |sim-obs|/(obs-bed); Rajaram bed 529.318, Shivaji bed 528.670"},
                  f, indent=2, default=str)
    print(f"\nSaved to {OUT_DIR / 'peak_stage_3event_results.json'}")


if __name__ == "__main__":
    main()
