"""
Verify the top routing configs with FULL metrics: peak-stage accuracy (the target) + peak timing
+ NSE (deprioritized per user, shown for reference). Picks the balanced recommendation.

For 2025 (hourly observed @ Shivaji) timing/NSE are verifiable. For 2019/2021 only the peak
stage is available (observed @ Rajaram).
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
from src.hydrology.validation_metrics import compute_nse, compute_kge
from src.ecmwf.station_selector import STATION_REGISTRY, select_active_subbasin_gages
from run_historical_event import fetch_historical_rainfall_for_station   # noqa: E402

OUT_DIR = BRIDGE / "results" / "dynamic_calibration"
SUBS = [f"S{i}" for i in range(1, 10)]
AMC5_DRY, AMC5_WET = 12.7, 27.9
SHIVAJI_BED, RAJARAM_BED = 528.670, 529.318

EVENTS = {
    "2019_august": {"start": "2019-08-01", "end": "2019-08-15", "site": "RAJARAM_WEIR",
                    "obs_peak": 546.97, "bed": RAJARAM_BED, "obs_csv": None},
    "2021_july":   {"start": "2021-07-18", "end": "2021-07-31", "site": "RAJARAM_WEIR",
                    "obs_peak": 547.83, "bed": RAJARAM_BED, "obs_csv": None},
    "2025_august": {"start": "2025-08-08", "end": "2025-08-22", "site": "SHIVAJI_BRIDGE",
                    "obs_peak": 542.57, "bed": SHIVAJI_BED,
                    "obs_csv": "data/shivaji_bridge_2025_hourly_observed.csv"},
}

CANDIDATES = [
    {"alpha_k": 0.45, "alpha_lag": 0.60, "muskingum_x": 0.30},
    {"alpha_k": 0.60, "alpha_lag": 0.60, "muskingum_x": 0.30},
    {"alpha_k": 0.80, "alpha_lag": 0.60, "muskingum_x": 0.30},
    {"alpha_k": 0.60, "alpha_lag": 0.82, "muskingum_x": 0.30},
]


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


def run_sim(hyetos, run_dt, hours, amc, site, cand):
    base_sub, base_reach = load_immutable_baseline()
    sub_models = copy.deepcopy(base_sub)
    reaches = copy.deepcopy(base_reach)
    for sid in sub_models:
        sub_models[sid]["cn"] = float(sub_models[sid]["cn"])
        sub_models[sid]["lag_min"] = float(sub_models[sid]["lag_min"] * cand["alpha_lag"])
    for rid in reaches:
        reaches[rid]["k_hr"] = float(reaches[rid]["k_hr"] * cand["alpha_k"])
        reaches[rid]["x"] = cand["muskingum_x"]
    po = {
        "sub_models": {sid: {"cn": sub_models[sid]["cn"], "lag_min": sub_models[sid]["lag_min"]} for sid in sub_models},
        "reaches": {rid: {"k_hr": reaches[rid]["k_hr"], "x": reaches[rid]["x"]} for rid in reaches},
        "alpha_k": cand["alpha_k"], "alpha_lag": cand["alpha_lag"], "delta_cn": 0.0,
        "muskingum_x": cand["muskingum_x"],
    }
    res = _execute_hec_hms_core(run_dt, subbasin_hyetographs=hyetos, live_stage_m=None,
                                parameter_overrides=po, amc=amc, sim_hours=hours,
                                ia_frac=0.05, uh_max_hr=90, uh_m_exp=20)
    hg = res["hydrograph"]
    q = np.array([e.get("discharge_m3s") or 0.0 for e in hg], dtype=float)
    ts = [pd.to_datetime(e["timestamp"]) for e in hg]
    stage = np.array([convert_discharge_to_stage_manning(float(x), site) for x in q])
    return ts, stage, float(q.max())


def evaluate(key, cfg, ts, stage, peak_q):
    depth = cfg["obs_peak"] - cfg["bed"]
    si = int(np.argmax(stage))
    sim_peak = float(stage[si]); err = sim_peak - cfg["obs_peak"]
    acc = 100.0 * (1.0 - abs(err) / depth)
    out = {"event": key, "sim_peak_wse_m": round(sim_peak, 2), "peak_err_m": round(err, 2),
           "peak_stage_acc_pct": round(acc, 1), "sim_peak_q_m3s": round(peak_q, 0),
           "sim_peak_ts": str(ts[si])}
    if cfg.get("obs_csv") and (REPO / cfg["obs_csv"]).exists():
        obs = pd.read_csv(REPO / cfg["obs_csv"], parse_dates=["timestamp"]).dropna(subset=["stage_m"])
        sim_df = pd.DataFrame({"timestamp": ts, "sim": stage})
        m = pd.merge(obs.loc[:, ["timestamp", "stage_m"]].rename(columns={"stage_m": "obs"}),
                     sim_df, on="timestamp", how="inner")
        obs_s = m["obs"].to_numpy(dtype=float); sim_s = m["sim"].to_numpy(dtype=float)
        nse = compute_nse(sim_s, obs_s); kge = compute_kge(sim_s, obs_s)
        oi = int(np.argmax(obs_s)); sj = int(np.argmax(sim_s))
        timing = (m.iloc[sj]["timestamp"] - m.iloc[oi]["timestamp"]).total_seconds() / 3600.0
        out.update({"nse": round(nse, 4), "kge": round(kge, 4), "peak_timing_h": round(timing, 1),
                    "obs_peak_ts": str(m.iloc[oi]["timestamp"]), "sim_peak_ts_obs": str(m.iloc[sj]["timestamp"])})
    return out


def main():
    preps = {}
    for key, cfg in EVENTS.items():
        hyetos, ant, hours, start = fetch_event_antecedent(cfg)
        preps[key] = {"hyetos": hyetos, "hours": hours, "start": start, "amc": classify_amc5(ant)}
        print(f"[fetch] {key}: ant5d={ant:.1f}mm -> {preps[key]['amc']}", flush=True)

    all_res = []
    for cand in CANDIDATES:
        per_event = {}
        for key, cfg in EVENTS.items():
            p = preps[key]
            ts, stage, pq = run_sim(p["hyetos"], p["start"], p["hours"], p["amc"], cfg["site"], cand)
            per_event[key] = evaluate(key, cfg, ts, stage, pq)
        e19 = per_event["2019_august"]; e21 = per_event["2021_july"]; e25 = per_event["2025_august"]
        row = {"cand": cand, "events": per_event}
        all_res.append(row)
        print(f"\nak={cand['alpha_k']} alag={cand['alpha_lag']} x={cand['muskingum_x']}", flush=True)
        print(f"  2019: acc={e19['peak_stage_acc_pct']}% err={e19['peak_err_m']}m", flush=True)
        print(f"  2021: acc={e21['peak_stage_acc_pct']}% err={e21['peak_err_m']}m", flush=True)
        print(f"  2025: acc={e25['peak_stage_acc_pct']}% err={e25['peak_err_m']}m "
              f"timing={e25.get('peak_timing_h','n/a')}h NSE={e25.get('nse','n/a')} KGE={e25.get('kge','n/a')}", flush=True)

    with open(OUT_DIR / "verify_recommended_config.json", "w") as f:
        json.dump(all_res, f, indent=2, default=str)
    print(f"\nSaved to {OUT_DIR / 'verify_recommended_config.json'}")


if __name__ == "__main__":
    main()
