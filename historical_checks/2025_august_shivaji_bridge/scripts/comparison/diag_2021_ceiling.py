"""
2021 ceiling diagnostic: can ANY Curve Number close the 2021 peak-stage gap?

The 3-event routing sweep showed 2021 stuck at ~68% accuracy (-5.9 m) regardless of routing.
This test holds the BEST routing (alpha_k=0.45, alpha_lag=0.60, x=0.30) and sweeps CN upward to
find 2021's runoff ceiling. If the peak-stage plateaus well below the 80% target (>=544.13 m),
the 2021 gap is an Open-Meteo INPUT-RAINFALL limitation, not a model-parameter limitation.
"""
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
from src.hydrology.stage_converter import convert_discharge_to_stage_manning, convert_stage_to_discharge_manning
from src.ecmwf.station_selector import STATION_REGISTRY, select_active_subbasin_gages
from run_historical_event import fetch_historical_rainfall_for_station   # noqa: E402

SUBS = [f"S{i}" for i in range(1, 10)]
START, END = "2021-07-18", "2021-07-31"
OBS_PEAK, BED = 547.83, 529.318
SITE = "RAJARAM_WEIR"
AK, ALAG, X = 0.45, 0.60, 0.30


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
        sub_models[sid]["lag_min"] = float(sub_models[sid]["lag_min"] * ALAG)
    for rid in reaches:
        reaches[rid]["k_hr"] = float(reaches[rid]["k_hr"] * AK)
        reaches[rid]["x"] = X
    po = {
        "sub_models": {s: {"cn": sub_models[s]["cn"], "lag_min": sub_models[s]["lag_min"]} for s in sub_models},
        "reaches": {r: {"k_hr": reaches[r]["k_hr"], "x": reaches[r]["x"]} for r in reaches},
        "alpha_k": AK, "alpha_lag": ALAG, "delta_cn": cn_uplift, "muskingum_x": X,
    }
    res = _execute_hec_hms_core(pd.Timestamp(START).to_pydatetime(), subbasin_hyetographs=hyetos,
                                live_stage_m=None, parameter_overrides=po, amc="AMC-III",
                                sim_hours=hours, ia_frac=0.05, uh_max_hr=90, uh_m_exp=20)
    hg = res["hydrograph"]
    q = np.array([e.get("discharge_m3s") or 0.0 for e in hg], dtype=float)
    wse = np.array([convert_discharge_to_stage_manning(float(x), SITE) for x in q])
    return float(q.max()), float(wse.max())


def main():
    hyetos, hours, mean_rain = fetch()
    depth = OBS_PEAK - BED
    target_80 = OBS_PEAK - 0.20 * depth   # stage at exactly 80% accuracy
    print(f"2021 mean catchment event rainfall = {mean_rain:.1f} mm (over {hours} h)", flush=True)
    print(f"Observed 2021 peak = {OBS_PEAK} m; 80% accuracy needs >= {target_80:.2f} m "
          f"(Q >= {convert_stage_to_discharge_manning(target_80, SITE):.0f} m3/s on WRD rating)\n", flush=True)
    print(f"{'CN_uplift':>10}{'peakQ':>10}{'peakWSE':>10}{'acc%':>8}")
    for cu in [0.0, 10.0, 20.0, 30.0, 45.0]:
        pq, pw = run(hyetos, hours, cu)
        acc = 100.0 * (1.0 - abs(pw - OBS_PEAK) / depth)
        print(f"{cu:>10.0f}{pq:>10.0f}{pw:>10.2f}{acc:>8.1f}", flush=True)


if __name__ == "__main__":
    main()
