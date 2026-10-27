"""
Two-event digital-twin calibration — defend the twin on TWO floods.

  2025_august @ Shivaji Bridge : full hourly observed -> NSE / peak / timing (stage, Shivaji rating)
  2019_august @ Rajaram Weir   : reported peak stage 546.97 m + peak Q 2111 m3/s (Rajaram rating)

The model's Sink-1 discharge is natively AT Rajaram KT Weir, so comparing 2019 to the Rajaram
reported values is the apples-to-apples comparison (unlike the earlier 2019-vs-Shivaji check).

Tunes per-subbasin CN uplift + per-reach alpha_K + Ia_frac jointly, with per-event antecedent
AMC. Reports the Pareto trade-off between 2025 NSE and 2019 Rajaram peak match.
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
from src.hydrology.validation_metrics import compute_nse, compute_rmse_mae, compute_kge
from src.ecmwf.station_selector import STATION_REGISTRY, select_active_subbasin_gages
from run_historical_event import fetch_historical_rainfall_for_station   # noqa: E402

OUT_DIR = BRIDGE / "results" / "dynamic_calibration"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SUBS = [f"S{i}" for i in range(1, 10)]
AMC5_DRY, AMC5_WET = 12.7, 27.9

EVENTS = {
    "2019_august": {"start": "2019-08-01", "end": "2019-08-15",
                    "obs_stage_m": 546.97, "obs_q_m3s": 2111.0, "site": "RAJARAM_WEIR",
                    "obs_csv": None},
    "2025_august": {"start": "2025-08-08", "end": "2025-08-22",
                    "site": "SHIVAJI_BRIDGE",
                    "obs_csv": "data/shivaji_bridge_2025_hourly_observed.csv"},
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
    return result["hydrograph"]


def score_event(key, cfg, hg, amc):
    q = np.array([e.get("discharge_m3s") or 0.0 for e in hg], dtype=float)
    ts = [pd.to_datetime(e["timestamp"]) for e in hg]
    site = cfg["site"]
    stage = np.array([convert_discharge_to_stage_manning(float(x), site) for x in q])
    out = {"event": key, "site": site, "amc": amc}
    pq = int(np.argmax(q))
    out["sim_peak_q_m3s"] = round(float(q[pq]), 1)
    out["sim_peak_stage_m"] = round(float(stage[int(np.argmax(stage))]), 2)
    out["sim_peak_ts"] = str(ts[int(np.argmax(stage))])
    obj = 0.0
    if cfg.get("obs_csv") and (REPO / cfg["obs_csv"]).exists():
        obs = pd.read_csv(REPO / cfg["obs_csv"], parse_dates=["timestamp"]).dropna(subset=["stage_m"])
        sim_df = pd.DataFrame({"timestamp": ts, "sim": stage})
        m = pd.merge(obs.loc[:, ["timestamp", "stage_m"]].rename(columns={"stage_m": "obs"}),
                     sim_df, on="timestamp", how="inner")
        obs_s = m["obs"].to_numpy(dtype=float); sim_s = m["sim"].to_numpy(dtype=float)
        nse = compute_nse(sim_s, obs_s); rmse, mae = compute_rmse_mae(sim_s, obs_s); kge = compute_kge(sim_s, obs_s)
        oi = int(np.argmax(obs_s)); si = int(np.argmax(sim_s))
        out.update({"nse": round(nse, 4), "kge": round(kge, 4), "rmse": round(rmse, 3),
                    "peak_err_m": round(float(sim_s[si] - obs_s[oi]), 2),
                    "timing_err_h": round((m.iloc[si]["timestamp"] - m.iloc[oi]["timestamp"]).total_seconds()/3600.0, 1)})
        obj += (1.0 - nse) * 100.0 + abs(out["peak_err_m"]) * 15.0 + abs(out["timing_err_h"]) * 2.0
    if cfg.get("obs_stage_m"):
        s_err = out["sim_peak_stage_m"] - cfg["obs_stage_m"]
        out["obs_stage_m"] = cfg["obs_stage_m"]
        out["peak_stage_err_m"] = round(s_err, 2)
        obj += abs(s_err) * 25.0
    if cfg.get("obs_q_m3s"):
        q_err_pct = 100.0 * (out["sim_peak_q_m3s"] - cfg["obs_q_m3s"]) / cfg["obs_q_m3s"]
        out["obs_q_m3s"] = cfg["obs_q_m3s"]
        out["peak_q_err_pct"] = round(q_err_pct, 1)
        obj += abs(q_err_pct) * 0.3
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
    for cn_uplift in [-4.0, -2.0, 0.0, 2.0]:
        for alpha_k in [0.80, 0.85, 0.90]:
            for ia_frac in [0.05, 0.08, 0.15]:
                per_event, total = {}, 0.0
                ok = True
                for key, cfg in EVENTS.items():
                    p = preps[key]
                    try:
                        hg = run_sim(p["hyetos"], p["start"], p["hours"], cn_uplift, alpha_k, 0.82, p["amc"], ia_frac)
                        r = score_event(key, cfg, hg, p["amc"])
                        per_event[key] = r
                        total += r["obj"]
                    except Exception as e:
                        ok = False
                        print(f"  ERROR {key} cn=+{cn_uplift} ak={alpha_k} ia={ia_frac}: {e}", flush=True)
                        break
                if not ok:
                    continue
                row = {"cn_uplift": cn_uplift, "alpha_k": alpha_k, "ia_frac": ia_frac,
                       "total_obj": round(total, 2), "events": per_event}
                all_rows.append(row)
                e25 = per_event.get("2025_august", {}); e19 = per_event.get("2019_august", {})
                print(f"cn=+{cn_uplift} ak={alpha_k} ia={ia_frac} obj={total:.1f} | "
                      f"2025 NSE={e25.get('nse','n/a')} peak={e25.get('peak_err_m','n/a')}m | "
                      f"2019 stageErr={e19.get('peak_stage_err_m','n/a')}m qErr={e19.get('peak_q_err_pct','n/a')}%",
                      flush=True)

    all_rows.sort(key=lambda r: r["total_obj"])
    print("\n=== TOP 6 (lower obj better) ===")
    for r in all_rows[:6]:
        e25 = r["events"].get("2025_august", {}); e19 = r["events"].get("2019_august", {})
        print(f"  cn=+{r['cn_uplift']} ak={r['alpha_k']} ia={r['ia_frac']} obj={r['total_obj']} | "
              f"2025 NSE={e25.get('nse')} peak={e25.get('peak_err_m')}m timing={e25.get('timing_err_h')}h | "
              f"2019 stage={e19.get('sim_peak_stage_m')}(err {e19.get('peak_stage_err_m')})m "
              f"q={e19.get('sim_peak_q_m3s')}(err {e19.get('peak_q_err_pct')}%)")

    with open(OUT_DIR / "two_event_calibration_results.json", "w") as f:
        json.dump({"all": all_rows, "best": all_rows[0] if all_rows else None}, f, indent=2, default=str)
    print(f"\nSaved to {OUT_DIR / 'two_event_calibration_results.json'}")


if __name__ == "__main__":
    main()
