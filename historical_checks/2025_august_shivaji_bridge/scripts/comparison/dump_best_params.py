"""Dump the exact per-subbasin CN/lag and per-reach K/X used in the best per-subbasin run."""
import copy
import sys
from pathlib import Path

import numpy as np

REPO = Path("E:/hydrocast_complete")
sys.path.insert(0, str(REPO))

from src.hms.basin_parser import load_immutable_baseline

# Best per-subbasin life-safety config (pass 1, best NSE)
ALPHA_K = 0.80
ALPHA_LAG = 0.82
CN_UPLIFT = 0.0          # no global uplift -> per-basin baseline CN preserved
MUSK_X = 0.15
IA_FRAC = 0.05

base_sub, base_reach = load_immutable_baseline()


def amc_iii(cn_ii):
    # TR-55 saturated-soil transform (what the emulator applies under AMC-III)
    eff = (23.0 * cn_ii) / (10.0 + 0.13 * cn_ii)
    return float(np.clip(eff, 40.0, 98.0))


print("=== PER-SUBBASIN (used in best run) ===")
print(f"{'Sub':<4}{'Name':<12}{'Area_km2':>10}{'CN_base':>10}{'CN_used':>10}{'CN_eff(III)':>13}"
      f"{'lag_base':>11}{'lag_used':>11}{'lag_h':>8}")
for sid in sorted(base_sub.keys()):
    s = base_sub[sid]
    cn_base = float(s["cn"])
    cn_used = float(np.clip(cn_base + CN_UPLIFT, 45.0, 95.0))
    cn_eff = amc_iii(cn_used)
    lag_base = float(s["lag_min"])
    lag_used = lag_base * ALPHA_LAG
    print(f"{sid:<4}{s['name']:<12}{s['area_km2']:>10.1f}{cn_base:>10.2f}{cn_used:>10.2f}"
          f"{cn_eff:>13.2f}{lag_base:>11.1f}{lag_used:>11.1f}{lag_used/60.0:>8.2f}")

print("\n=== PER-REACH (used in best run) ===")
print(f"{'Reach':<7}{'K_base_h':>10}{'K_used_h':>10}{'X':>6}")
for rid in sorted(base_reach.keys()):
    r = base_reach[rid]
    k_base = float(r["k_hr"])
    k_used = k_base * ALPHA_K
    print(f"{rid:<7}{k_base:>10.3f}{k_used:>10.3f}{MUSK_X:>6.2f}")

print(f"\nConfig: ia_frac={IA_FRAC}, uh_max_hr=90, uh_m_exp=20, muskingum_x={MUSK_X}, "
      f"alpha_k={ALPHA_K}, alpha_lag={ALPHA_LAG}, cn_uplift={CN_UPLIFT} (AMC-III)")
