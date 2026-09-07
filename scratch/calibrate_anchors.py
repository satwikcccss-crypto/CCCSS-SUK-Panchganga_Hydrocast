import pandas as pd
import numpy as np
from scipy.interpolate import PchipInterpolator, interp1d
from scipy import stats

df_hourly = pd.read_csv("data/wrd_rajaram_hourly_2021_2023.csv")
df_daily = pd.read_csv("data/wrd_rajaram_2020_2021.csv")

# Extract unique stage and median Q across all data
combined = pd.concat([
    df_hourly[["stage_m", "q_cumec"]],
    df_daily[["stage_m", "q_cumec"]]
]).dropna()

# Sort by stage
combined["stage_round"] = combined["stage_m"].round(2)
median_by_stage = combined.groupby("stage_round")["q_cumec"].median().reset_index()
median_by_stage = median_by_stage.sort_values("stage_round")

# Build smooth empirical anchors covering the entire range
# Key physical points:
# 530.18: Datum / Zero flow crest
# 532.70: 500 cfs = 14.16 m3/s
# 532.80: 250 cfs = 7.08 m3/s (low flow weir notch) -> let's start gently from 531.50
# 533.36: 2516 cfs = 71.25 m3/s
# 533.54: 2825 cfs = 80.00 m3/s
# 534.15: 4414 cfs = 125.00 m3/s
# 535.19: 7566 cfs = 214.25 m3/s
# 536.00: 10777 cfs = 305.17 m3/s
# 537.04: 15825 cfs = 448.12 m3/s
# 538.29: 22894 cfs = 648.29 m3/s
# 539.46: 31211 cfs = 883.87 m3/s
# 540.37: 34110 cfs = 965.89 m3/s
# 541.51: 43053 cfs = 1219.13 m3/s
# 542.38: 59682 cfs = 1690.01 m3/s
# 543.29: 62737 cfs = 1776.51 m3/s
# 544.39: 65605 cfs = 1857.73 m3/s
# 545.38: 68334 cfs = 1935.00 m3/s
# 546.19: 71170 cfs = 2015.31 m3/s
# 547.00: 74730 cfs = 2116.14 m3/s
# 547.33: 76383 cfs = 2162.93 m3/s (July 2021 peak)
# 549.00: Extrapolation (2450 m3/s)

anchors_h = np.array([
    530.18, 531.50, 532.70, 533.36, 533.54, 534.15, 535.19, 536.00,
    537.04, 538.29, 539.46, 540.37, 541.51, 542.38, 543.29, 544.39,
    545.38, 546.19, 547.00, 547.33, 549.00
])
anchors_q = np.array([
    0.0,    3.00,   14.16,  71.25,  80.00,  125.00, 214.25, 305.17,
    448.12, 648.29, 883.87, 965.89, 1219.13, 1690.01, 1776.51, 1857.73,
    1935.00, 2015.31, 2116.14, 2162.93, 2450.00
])

pchip = PchipInterpolator(anchors_h, anchors_q)

for name, df in [("HOURLY 2021-2023", df_hourly), ("DAILY 2020-2021", df_daily)]:
    obs_q = df["q_cumec"].values
    pred_q = np.maximum(0.0, pchip(df["stage_m"].values))
    rmse_q = np.sqrt(np.mean((pred_q - obs_q)**2))
    mae_q = np.mean(np.abs(pred_q - obs_q))
    nse_q = 1.0 - (np.sum((obs_q - pred_q)**2) / np.sum((obs_q - np.mean(obs_q))**2))
    pbias_q = (np.sum(pred_q - obs_q) / np.sum(obs_q)) * 100.0
    rho_q, _ = stats.spearmanr(pred_q, obs_q)
    r2_q = stats.pearsonr(pred_q, obs_q)[0]**2

    # Inverse stage
    n_pts = 500
    wse_grid = np.linspace(530.18, 549.00, n_pts)
    q_grid = np.maximum(0.0, pchip(wse_grid))
    f_inv = interp1d(q_grid, wse_grid, kind="linear", bounds_error=False, fill_value=(wse_grid[0], wse_grid[-1]))
    
    obs_s = df["stage_m"].values
    pred_s = f_inv(obs_q)
    rmse_s = np.sqrt(np.mean((pred_s - obs_s)**2))
    mae_s = np.mean(np.abs(pred_s - obs_s))
    nse_s = 1.0 - (np.sum((obs_s - pred_s)**2) / np.sum((obs_s - np.mean(obs_s))**2))
    rho_s, _ = stats.spearmanr(pred_s, obs_s)

    print(f"\n==================== {name} (N={len(df)}) ====================")
    print(f"STAGE RMSE    : {rmse_s:.3f} m ({rmse_s*100:.1f} cm)")
    print(f"STAGE MAE     : {mae_s:.3f} m ({mae_s*100:.1f} cm)")
    print(f"STAGE NSE     : {nse_s:.4f}")
    print(f"STAGE Rho     : {rho_s:.4f}")
    print(f"DISCHARGE RMSE: {rmse_q:.2f} m3/s")
    print(f"DISCHARGE MAE : {mae_q:.2f} m3/s")
    print(f"DISCHARGE NSE : {nse_q:.4f}")
    print(f"DISCHARGE PBIAS: {pbias_q:.2f} %")
    print(f"DISCHARGE Rho : {rho_q:.4f}")
    print(f"DISCHARGE R2  : {r2_q:.4f}")
