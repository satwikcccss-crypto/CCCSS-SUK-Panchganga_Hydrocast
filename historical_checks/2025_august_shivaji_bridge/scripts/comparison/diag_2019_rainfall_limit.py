"""Diagnostic: is the 2019 WSE rainfall-limited or rating-limited? Print peak Q + WSE vs CN."""
import copy
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("E:/hydrocast_complete")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "historical_checks"))

from src.hms.basin_parser import load_immutable_baseline
from src.hms.runner import _execute_hec_hms_core
from src.hydrology.stage_converter import (
    convert_discharge_to_stage_manning,
    convert_stage_to_discharge_manning,
)
from src.ecmwf.station_selector import STATION_REGISTRY, select_active_subbasin_gages
from run_historical_event import fetch_historical_rainfall_for_station   # noqa: E402

SUBS = [f"S{i}" for i in range(1, 10)]
START, END = "2019-08-01", "2019-08-15"
OBS_WSE = 546.97


def fetch():
    hours = int((pd.Timestamp(END) - pd.Timestamp(START)).total_seconds() // 3600) + 24
    st_event, st_cum = {}, {}
    for st in STATION_REGISTRY:
        ev = fetch_historical_rainfall_for_station(st.lat, st.lon, START, END, hours=hours)
        st_event[st.station_id] = ev
        st_cum[st.station_id] = float(np.sum(ev))
    sel = select_active_subbasin_gages(st_cum)
    hyetos, tot = {}, 0.0
    for sub in SUBS:
        sid = sel.get(sub, {}).get("selected_station_id", "KARVEER")
        hyetos[sub] = st_event.get(sid, np.zeros(hours, dtype=np.float32)).copy()
        tot += float(np.sum(hyetos[sub]))
    return hyetos, hours, tot / len(SUBS)


def run(hyetos, hours, cn_uplift):
    base_sub, base_reach = load_immutable_baseline()
    sub_models = copy.deepcopy(base_sub)
    reaches = copy.deepcopy(base_reach)
    for sid in sub_models:
        sub_models[sid]["cn"] = float(np.clip(float(sub_models[sid]["cn"]) + cn_uplift, 45.0, 98.0))
        sub_models[sid]["lag_min"] = float(sub_models[sid]["lag_min"] * 0.82)
    for rid in reaches:
        reaches[rid]["k_hr"] = float(reaches[rid]["k_hr"] * 0.80)
        reaches[rid]["x"] = 0.15
    po = {
        "sub_models": {s: {"cn": sub_models[s]["cn"], "lag_min": sub_models[s]["lag_min"]} for s in sub_models},
        "reaches": {r: {"k_hr": reaches[r]["k_hr"], "x": reaches[r]["x"]} for r in reaches},
        "alpha_k": 0.80, "alpha_lag": 0.82, "delta_cn": cn_uplift, "muskingum_x": 0.15,
    }
    res = _execute_hec_hms_core(pd.Timestamp(START).to_pydatetime(), subbasin_hyetographs=hyetos,
                                live_stage_m=None, parameter_overrides=po, amc="AMC-III",
                                sim_hours=hours, ia_frac=0.05, uh_max_hr=90, uh_m_exp=20)
    hg = res["hydrograph"]
    q = np.array([e.get("discharge_m3s") or 0.0 for e in hg], dtype=float)
    wse = np.array([convert_discharge_to_stage_manning(float(x), "RAJARAM_WEIR") for x in q])
    return float(q.max()), float(wse.max())


def main():
    hyetos, hours, mean_rain = fetch()
    print(f"2019 mean catchment event rainfall = {mean_rain:.1f} mm (over {hours} h)", flush=True)
    print(f"Observed 2019 WSE = {OBS_WSE} m -> requires Q = "
          f"{convert_stage_to_discharge_manning(OBS_WSE, 'RAJARAM_WEIR'):.0f} m3/s on WRD rating\n", flush=True)
    print(f"{'CN_uplift':>10}{'peakQ':>10}{'peakWSE':>10}")
    for cu in [0.0, 8.0, 16.0, 24.0, 32.0, 40.0]:
        pq, pw = run(hyetos, hours, cu)
        print(f"{cu:>10.0f}{pq:>10.0f}{pw:>10.2f}", flush=True)


if __name__ == "__main__":
    main()
