import json
import numpy as np
from datetime import datetime, timedelta

# Load CYC_20260905_18z run
with open('data/runs/CYC_20260905_18z.json', 'r') as f:
    run_data = json.load(f)

with open('data/telemetry/thingspeak_hourly_cache.json', 'r') as f:
    cache = json.load(f)

# Extract ECMWF hyetographs
ecmwf = run_data.get('ecmwf', {})
subbasin_hyetographs = {sid: np.array([p['mm_hr'] for p in series], dtype=np.float32) for sid, series in ecmwf.items()}

# Observed stages
run_dt = datetime.fromisoformat(run_data['summary']['peak_time']) - timedelta(hours=run_data['summary']['lead_hours_to_peak'])
timestamps = [(run_dt + timedelta(hours=h)).strftime('%Y-%m-%dT%H:00:00Z') for h in range(90)]
obs_stages = [cache.get(t, {}).get('observed_stage_m') for t in timestamps]
valid_obs = [(h, s) for h, s in enumerate(obs_stages) if s is not None]

from src.hydrology.stage_converter import convert_stage_to_discharge_manning, convert_discharge_to_stage_manning

live_stage_m = 533.07
baseflow = convert_stage_to_discharge_manning(live_stage_m, "SHIVAJI_BRIDGE")

def run_simulation(cn_scale=1.0, use_amc_iii=True, ia_coeff=0.05, lag_scale=1.0, muskingum_scale=1.0, opt_reaches=False):
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

    if opt_reaches:
        reaches = {
            "R5": {"k_hr": 18.338, "x": 0.25},
            "R4": {"k_hr": 8.085,  "x": 0.25},
            "R2": {"k_hr": 16.500, "x": 0.25},
            "R3": {"k_hr": 9.484,  "x": 0.25},
            "R1": {"k_hr": 4.500,  "x": 0.25},
        }
    else:
        reaches = {
            "R5": {"k_hr": 4.619 * muskingum_scale,  "x": 0.2},
            "R4": {"k_hr": 1.224 * muskingum_scale,  "x": 0.2},
            "R2": {"k_hr": 11.827 * muskingum_scale, "x": 0.2},
            "R3": {"k_hr": 3.829 * muskingum_scale,  "x": 0.2},
            "R1": {"k_hr": 2.899 * muskingum_scale,  "x": 0.2},
        }

    sub_q_direct = {}
    for sid, props in sub_models.items():
        cn_ii = props["cn"] * cn_scale
        if use_amc_iii:
            cn = min(98.0, cn_ii / (0.427 + 0.00573 * cn_ii))
        else:
            cn = cn_ii
        s_ret = (25400.0 / cn) - 254.0
        ia = ia_coeff * s_ret

        p_series = subbasin_hyetographs.get(sid, np.zeros(90, dtype=np.float32))[:90]
        cum_p = np.cumsum(p_series)
        cum_q = np.zeros(90, dtype=np.float32)

        for h in range(90):
            if cum_p[h] > ia:
                cum_q[h] = ((cum_p[h] - ia) ** 2) / (cum_p[h] - ia + s_ret)

        excess_p = np.diff(cum_q, prepend=0.0)
        excess_p = np.maximum(0.0, excess_p)

        lag_hr = (props["lag_min"] * lag_scale) / 60.0
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

    def route_muskingum(inflow: np.ndarray, k_hr: float, x: float = 0.2, dt_hr: float = 1.0) -> np.ndarray:
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

    stages = [convert_discharge_to_stage_manning(q, "SHIVAJI_BRIDGE") for q in q_total]
    errs = [abs(stages[h] - s) for h, s in valid_obs]
    mae = np.mean(errs)
    rmse = np.sqrt(np.mean([e**2 for e in errs]))
    peak_q = np.max(q_total)
    peak_stage = np.max(stages)
    return mae, rmse, peak_q, peak_stage

print(f"{'Config':<45} {'MAE (m)':<10} {'RMSE (m)':<10} {'Peak Q':<10} {'Peak Stg'}")
print("-" * 85)
mae, rmse, pq, ps = run_simulation(cn_scale=1.0, use_amc_iii=True, ia_coeff=0.05, lag_scale=1.0)
print(f"{'Baseline (AMC-III, ia=0.05, orig lag & reaches)':<45} {mae:<10.3f} {rmse:<10.3f} {pq:<10.1f} {ps:<10.2f}")

mae, rmse, pq, ps = run_simulation(cn_scale=1.0, use_amc_iii=True, ia_coeff=0.05, opt_reaches=True)
print(f"{'HEC-HMS Opt Reaches (K=18.3, 8.1, 9.5)':<45} {mae:<10.3f} {rmse:<10.3f} {pq:<10.1f} {ps:<10.2f}")

mae, rmse, pq, ps = run_simulation(cn_scale=0.768, use_amc_iii=True, ia_coeff=0.05, opt_reaches=True)
print(f"{'Opt CN scale=0.768 + Opt Reaches':<45} {mae:<10.3f} {rmse:<10.3f} {pq:<10.1f} {ps:<10.2f}")

mae, rmse, pq, ps = run_simulation(cn_scale=1.0, use_amc_iii=False, ia_coeff=0.20, opt_reaches=True)
print(f"{'Standard AMC-II (ia=0.2*S) + Opt Reaches':<45} {mae:<10.3f} {rmse:<10.3f} {pq:<10.1f} {ps:<10.2f}")

mae, rmse, pq, ps = run_simulation(cn_scale=0.9, use_amc_iii=False, ia_coeff=0.10, opt_reaches=True)
print(f"{'Moderate AMC-II (ia=0.1*S) + Opt Reaches':<45} {mae:<10.3f} {rmse:<10.3f} {pq:<10.1f} {ps:<10.2f}")
