import json
import glob
import os
import sys
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, '.')
from src.hydrology.stage_converter import convert_stage_to_discharge_manning, convert_discharge_to_stage_manning

with open('data/telemetry/thingspeak_hourly_cache.json', 'r') as f:
    cache = json.load(f)

runs = sorted(glob.glob('data/runs/CYC_*.json'))

sub_models = {
    "S1": {"name": "Karveer",     "area_km2": 86.213, "cn": 74.85, "lag_min": 2152.0},
    "S2": {"name": "Sangarul",    "area_km2": 153.77, "cn": 65.74, "lag_min": 3154.3},
    "S3": {"name": "Kotoli",      "area_km2": 261.32, "cn": 64.82, "lag_min": 3997.7},
    "S4": {"name": "Karanjphen",  "area_km2": 262.00, "cn": 61.89, "lag_min": 3115.5},
    "S5": {"name": "Padasali",    "area_km2": 106.39, "cn": 60.97, "lag_min": 2117.1},
    "S6": {"name": "Gaganbawda",  "area_km2": 227.72, "cn": 61.78, "lag_min": 3318.1},
    "S7": {"name": "Garivade",    "area_km2": 195.39, "cn": 61.28, "lag_min": 3362.3},
    "S8": {"name": "Beed",        "area_km2": 177.44, "cn": 65.76, "lag_min": 3387.1},
    "S9": {"name": "Radhanagari", "area_km2": 366.97, "cn": 64.31, "lag_min": 5199.0},
}

# Calibrated Muskingum reaches from Optimization_1.results & Basin_1.basin
reaches = {
    "R5": {"k_hr": 18.338, "x": 0.25},
    "R4": {"k_hr": 8.085,  "x": 0.25},
    "R2": {"k_hr": 16.500, "x": 0.25},
    "R3": {"k_hr": 9.484,  "x": 0.25},
    "R1": {"k_hr": 4.500,  "x": 0.25},
}

def route_muskingum(inflow: np.ndarray, k_hr: float, x: float = 0.25, dt_hr: float = 1.0) -> np.ndarray:
    n = len(inflow)
    steps = max(1, int(round(k_hr / max(0.1, 2.0 * k_hr * x)))) if x > 0 else 1
    sub_k = k_hr / steps
    cur_in = np.copy(inflow)
    for _ in range(steps):
        denom = 2.0 * sub_k * (1.0 - x) + dt_hr
        c0 = (dt_hr - 2.0 * sub_k * x) / denom
        c1 = (dt_hr + 2.0 * sub_k * x) / denom
        c2 = (2.0 * sub_k * (1.0 - x) - dt_hr) / denom
        sub_out = np.zeros(n, dtype=np.float32)
        sub_out[0] = cur_in[0]
        for t_step in range(1, n):
            sub_out[t_step] = c0 * cur_in[t_step] + c1 * cur_in[t_step - 1] + c2 * sub_out[t_step - 1]
            if sub_out[t_step] < 0:
                sub_out[t_step] = 0.0
        cur_in = sub_out
    return cur_in

print(f"{'Cycle ID':<18} {'Obs H':<6} {'Old MAE':<10} {'Cal MAE':<10} {'Cal RMSE':<10} {'Obs Mean':<10} {'Cal Peak'}")
print("-" * 80)

for r in runs:
    with open(r, 'r', encoding='utf-8') as f:
        d = json.load(f)
    cid = d.get('cycle_id', os.path.basename(r))
    summary = d.get('summary', {})
    val = d.get('validation', {})
    m = val.get('metrics', {})
    old_mae = m.get('mae_stage_m', '-')

    # Hyetographs
    ecmwf = d.get('ecmwf', {})
    subbasin_hyetographs = {sid: np.array([p['mm_hr'] for p in series], dtype=np.float32) for sid, series in ecmwf.items()}

    # Cycle start time
    parts = cid.replace('CYC_', '').replace('z', '').split('_')
    dt_str = parts[0] + parts[1]
    from datetime import timezone
    run_dt = datetime.strptime(dt_str, '%Y%m%d%H').replace(tzinfo=timezone.utc)

    timestamps = [(run_dt + timedelta(hours=h)).strftime('%Y-%m-%dT%H:00:00Z') for h in range(90)]
    obs_stages = [cache.get(t, {}).get('observed_stage_m') for t in timestamps]
    valid_obs = [(h, s) for h, s in enumerate(obs_stages) if s is not None]

    if not valid_obs:
        continue

    # Live stage at cycle start
    live_stage = valid_obs[0][1] if valid_obs[0][0] == 0 else valid_obs[0][1]
    baseflow = convert_stage_to_discharge_manning(live_stage, "SHIVAJI_BRIDGE")

    # Antecedent precipitation / moisture evaluation
    # Total rain in catchment over 90h
    total_catchment_rain = np.mean([np.sum(hye) for hye in subbasin_hyetographs.values()]) if subbasin_hyetographs else 0.0

    # Loss method: In late season / moderate rain, AMC-II with standard SCS initial abstraction
    sub_q_direct = {}
    for sid, props in sub_models.items():
        cn = props["cn"]
        # Standard SCS-CN storage
        s_ret = (25400.0 / cn) - 254.0
        # Standard SCS Initial Abstraction: Ia = 0.2 * S (or 0.1 * S during steady flow)
        ia = 0.15 * s_ret

        p_series = subbasin_hyetographs.get(sid, np.zeros(90, dtype=np.float32))[:90]
        cum_p = np.cumsum(p_series)
        cum_q = np.zeros(90, dtype=np.float32)

        for h in range(90):
            if cum_p[h] > ia:
                cum_q[h] = ((cum_p[h] - ia) ** 2) / (cum_p[h] - ia + s_ret)

        excess_p = np.diff(cum_q, prepend=0.0)
        excess_p = np.maximum(0.0, excess_p)

        # SCS unit hydrograph
        lag_hr = props["lag_min"] / 60.0
        tp = 0.5 + lag_hr
        t = np.arange(90, dtype=np.float32)
        m_exp = 3.7
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            uh = np.where(t > 0, (t / tp) ** m_exp * np.exp(m_exp * (1.0 - t / tp)), 0.0)
        uh = np.nan_to_num(uh, 0.0)
        target_vol_m3 = props["area_km2"] * 1000.0
        cur_vol_m3 = float(np.sum(uh) * 3600.0)
        if cur_vol_m3 > 0:
            uh = uh * (target_vol_m3 / cur_vol_m3)

        q_dir = np.convolve(excess_p, uh)[:90]
        sub_q_direct[sid] = np.maximum(0.0, q_dir)

    in_r5 = sub_q_direct["S6"] + sub_q_direct["S7"]
    out_r5 = route_muskingum(in_r5, reaches["R5"]["k_hr"], reaches["R5"]["x"])

    in_r4 = sub_q_direct["S9"]
    out_r4 = route_muskingum(in_r4, reaches["R4"]["k_hr"], reaches["R4"]["x"])

    in_r2 = out_r5 + out_r4 + sub_q_direct["S8"]
    out_r2 = route_muskingum(in_r2, reaches["R2"]["k_hr"], reaches["R2"]["x"])

    in_r3 = sub_q_direct["S4"] + sub_q_direct["S5"]
    out_r3 = route_muskingum(in_r3, reaches["R3"]["k_hr"], reaches["R3"]["x"])

    in_r1 = out_r2 + out_r3 + sub_q_direct["S3"] + sub_q_direct["S2"]
    out_r1 = route_muskingum(in_r1, reaches["R1"]["k_hr"], reaches["R1"]["x"])

    q_surface = out_r1 + sub_q_direct["S1"]
    q_total = q_surface + baseflow

    cal_stages = [convert_discharge_to_stage_manning(q, "SHIVAJI_BRIDGE") for q in q_total]
    cal_errs = [abs(cal_stages[h] - s) for h, s in valid_obs]
    cal_mae = np.mean(cal_errs)
    cal_rmse = np.sqrt(np.mean([e**2 for e in cal_errs]))
    obs_mean = np.mean([s for h, s in valid_obs])
    cal_peak = np.max(cal_stages)

    old_mae_str = f"{old_mae:.3f}" if isinstance(old_mae, (int, float)) else str(old_mae)
    print(f"{cid:<18} {len(valid_obs):<6} {old_mae_str:<10} {cal_mae:<10.3f} {cal_rmse:<10.3f} {obs_mean:<10.2f} {cal_peak:<10.2f}")
