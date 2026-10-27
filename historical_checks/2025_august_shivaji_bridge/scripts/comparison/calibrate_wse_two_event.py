"""
WSE-first two-event digital-twin calibration.

Hydrologic-modeller framing (user directive): the WATER SURFACE ELEVATION (stage) is the
ultimate deliverable and the single source of truth. Discharge is a derived intermediate
(inferred via rating curve) and is DISREGARDED as a calibration target — especially for 2019
where the reported stage 546.97 m and discharge 2111 m3/s are ~2x-inconsistent on the WRD
rating. Trusting the LEVEL, the model UNDER-predicts 2019 WSE by ~2.6 m (needs MORE runoff).

Objective (conservative — never under-predict a flood level):
  2025 @ Shivaji : maximize NSE on hourly WSE, heavily penalize peak UNDER-prediction.
  2019 @ Rajaram : match observed WSE 546.97 m, heavily penalize under-prediction.

Tunes per-subbasin CN uplift + per-reach alpha_k + Ia (per-event antecedent AMC).
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
                    "obs_wse_m": 546.97, "site": "RAJARAM_WEIR", "obs_csv": None},
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


def run_sim(hyetos, run_dt, hours, cn_uplift, alpha_k, alpha_lag, amc, ia_frac, uh_m_exp, site):
    base_sub, base_reach = load_immutable_baseline()
    sub_models = copy.deepcopy(base_sub)
    reaches = copy.deepcopy(base_reach)
    for sid in sub_models:
        sub_models[sid]["cn"] = float(np.clip(float(sub_models[sid]["cn"]) + cn_uplift, 45.0, 98.0))
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
                                   sim_hours=hours, ia_frac=ia_frac, uh_max_hr=90, uh_m_exp=uh_m_exp)
    hg = result["hydrograph"]
    q = np.array([e.get("discharge_m3s") or 0.0 for e in hg], dtype=float)
    ts = [pd.to_datetime(e["timestamp"]) for e in hg]
    stage = np.array([convert_discharge_to_stage_manning(float(x), site) for x in q])
    return ts, stage


def score_event(key, cfg, ts, stage):
    site = cfg["site"]
    out = {"event": key, "site": site}
    si = int(np.argmax(stage))
    out["sim_peak_wse_m"] = round(float(stage[si]), 2)
    out["sim_peak_ts"] = str(ts[si])
    obj = 0.0
    if cfg.get("obs_csv") and (REPO / cfg["obs_csv"]).exists():
        obs = pd.read_csv(REPO / cfg["obs_csv"], parse_dates=["timestamp"]).dropna(subset=["stage_m"])
        sim_df = pd.DataFrame({"timestamp": ts, "sim": stage})
        m = pd.merge(obs.loc[:, ["timestamp", "stage_m"]].rename(columns={"stage_m": "obs"}),
                     sim_df, on="timestamp", how="inner")
        obs_s = m["obs"].to_numpy(dtype=float); sim_s = m["sim"].to_numpy(dtype=float)
        nse = compute_nse(sim_s, obs_s); rmse, mae = compute_rmse_mae(sim_s, obs_s); kge = compute_kge(sim_s, obs_s)
        oi = int(np.argmax(obs_s)); sj = int(np.argmax(sim_s))
        peak_err = float(sim_s[sj] - obs_s[oi])
        timing = (m.iloc[sj]["timestamp"] - m.iloc[oi]["timestamp"]).total_seconds() / 3600.0
        out.update({"nse": round(nse, 4), "kge": round(kge, 4), "rmse": round(rmse, 3),
                    "peak_err_m": round(peak_err, 2), "timing_err_h": round(timing, 1),
                    "obs_peak_wse_m": round(float(obs_s[oi]), 2)})
        # conservative: under-prediction (peak_err<0) penalized hard (life-safety)
        obj += (1.0 - nse) * 40.0 + max(0.0, -peak_err) * 50.0 + abs(peak_err) * 8.0 + abs(timing) * 2.0
    if cfg.get("obs_wse_m"):
        wse_err = out["sim_peak_wse_m"] - cfg["obs_wse_m"]
        out["obs_wse_m"] = cfg["obs_wse_m"]
        out["wse_err_m"] = round(wse_err, 2)
        # conservative: under-prediction (wse_err<0) penalized hard
        obj += max(0.0, -wse_err) * 50.0 + abs(wse_err) * 8.0
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
    for cn_uplift in [0.0, 4.0, 8.0, 12.0, 16.0, 20.0]:
        for alpha_k in [0.80, 0.85]:
            for ia_frac in [0.05, 0.08]:
                per_event, total = {}, 0.0
                ok = True
                for key, cfg in EVENTS.items():
                    p = preps[key]; site = cfg["site"]
                    try:
                        ts, stage = run_sim(p["hyetos"], p["start"], p["hours"], cn_uplift, alpha_k, 0.82, p["amc"], ia_frac, 20, site)
                        r = score_event(key, cfg, ts, stage)
                        per_event[key] = r
                        total += r["obj"]
                    except Exception as e:
                        ok = False; print(f"  ERROR {key} cn=+{cn_uplift} ak={alpha_k} ia={ia_frac}: {e}", flush=True); break
                if not ok:
                    continue
                row = {"cn_uplift": cn_uplift, "alpha_k": alpha_k, "ia_frac": ia_frac,
                       "total_obj": round(total, 2), "events": per_event}
                all_rows.append(row)
                e25 = per_event.get("2025_august", {}); e19 = per_event.get("2019_august", {})
                print(f"cn=+{cn_uplift} ak={alpha_k} ia={ia_frac} obj={total:.1f} | "
                      f"2025 NSE={e25.get('nse','n/a')} WSEerr={e25.get('peak_err_m','n/a')}m | "
                      f"2019 WSE={e19.get('sim_peak_wse_m','n/a')}(err {e19.get('wse_err_m','n/a')})m", flush=True)

    all_rows.sort(key=lambda r: r["total_obj"])
    print("\n=== TOP 6 WSE-FIRST (lower obj better) ===")
    for r in all_rows[:6]:
        e25 = r["events"].get("2025_august", {}); e19 = r["events"].get("2019_august", {})
        print(f"  cn=+{r['cn_uplift']} ak={r['alpha_k']} ia={r['ia_frac']} obj={r['total_obj']} | "
              f"2025 NSE={e25.get('nse')} WSEerr={e25.get('peak_err_m')}m timing={e25.get('timing_err_h')}h | "
              f"2019 WSE={e19.get('sim_peak_wse_m')}(err {e19.get('wse_err_m')})m")

    with open(OUT_DIR / "wse_two_event_calibration_results.json", "w") as f:
        json.dump({"all": all_rows, "best": all_rows[0] if all_rows else None}, f, indent=2, default=str)
    print(f"\nSaved to {OUT_DIR / 'wse_two_event_calibration_results.json'}")


if __name__ == "__main__":
    main()
