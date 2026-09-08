import json
import numpy as np

# Let's inspect Basin_1.basin reach parameters and subbasin lag
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

reaches = {
    "R5": {"k_hr": 4.619,  "x": 0.2},
    "R4": {"k_hr": 1.224,  "x": 0.2},
    "R2": {"k_hr": 11.827, "x": 0.2},
    "R3": {"k_hr": 3.829,  "x": 0.2},
    "R1": {"k_hr": 2.899,  "x": 0.2},
}

print("Current runner.py Reach K (hours):")
for r, p in reaches.items():
    print(f"{r}: K = {p['k_hr']} h, x = {p['x']}")

print("\nOptimization_1.results calibrated parameters:")
# From OPT_Optimization_1.results:
# R5 Muskingum K: 18.338 h
# R4 Muskingum K: 8.085 h
# R3 Muskingum K: 9.484 h
# CN Scale Factor: 46.103 / 60.0 = 0.7684
opt_k = {"R5": 18.338, "R4": 8.085, "R3": 9.484}
for r, k in opt_k.items():
    print(f"{r}: Optimized K = {k} h (Original was {reaches[r]['k_hr']} h)")
