"""
Promote the 2025-validated per-subbasin digital-twin config into production calibration state.

Writes into data/telemetry/ml_calibration_state.json:
  - Relative offsets applied by the production runner to the immutable baseline:
        alpha_k=0.80, alpha_lag=0.82, delta_cn=0.0, muskingum_x=0.15
  - Digital-twin loss/UH settings (new; read by _execute_hec_hms_core when not passed):
        ia_frac=0.05, uh_max_hr=90, uh_m_exp=20
  - active_sub_models / active_reaches recomputed as the ABSOLUTE per-basin values
    (baseline + delta_cn, baseline*alpha_lag; baseline K*alpha_k, x=muskingum_x) for display.
  - A history entry documenting the promotion + the 2019 data-integrity caveat.

baseline_* are left untouched (immutable reference). A timestamped backup is written first.
"""
import copy
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("E:/hydrocast_complete")
import sys
sys.path.insert(0, str(REPO))

from src.hms.basin_parser import load_immutable_baseline

STATE = REPO / "data" / "telemetry" / "ml_calibration_state.json"
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
BACKUP = STATE.with_suffix(f".json.bak_{STAMP}")

# --- Digital-twin config (timing-faithful, peak-stage optimized) ---
# Recommended by calibrate_peak_stage_3event.py + verify_recommended_config.py (2026-10-27):
#   2019 @ Rajaram peak-stage acc 86.2% (err -2.04 m)
#   2025 @ Shivaji peak-stage acc 96.5% (err -0.28 m), crest timing -4 h, NSE 0.932 / KGE 0.848
#   2021 @ Rajaram ~68% -- Open-Meteo input-rainfall ceiling (NOT a parameter limit; documented)
ALPHA_K = 0.60
ALPHA_LAG = 0.82
DELTA_CN = 0.0
MUSKINGUM_X = 0.30
IA_FRAC = 0.05
UH_MAX_HR = 90
UH_M_EXP = 20.0


def main():
    # Backup
    shutil.copy2(STATE, BACKUP)
    print(f"Backup -> {BACKUP}")

    state = json.loads(STATE.read_text(encoding="utf-8"))
    base_sub, base_reach = load_immutable_baseline()

    # Relative offsets (what the production runner applies to baseline)
    state["alpha_k"] = ALPHA_K
    state["alpha_lag"] = ALPHA_LAG
    state["delta_cn"] = DELTA_CN
    state["muskingum_x"] = MUSKINGUM_X

    # Digital-twin loss/UH settings (read by runner when not passed explicitly)
    state["ia_frac"] = IA_FRAC
    state["uh_max_hr"] = UH_MAX_HR
    state["uh_m_exp"] = UH_M_EXP

    # Absolute active values (for display / telegram) = baseline transformed by the offsets
    active_sub = {}
    for sid, s in base_sub.items():
        active_sub[sid] = {
            "name": s.get("name"),
            "area_km2": s.get("area_km2"),
            "cn": round(float(s["cn"]) + DELTA_CN, 3),
            "lag_min": round(float(s["lag_min"]) * ALPHA_LAG, 1),
        }
    active_reach = {}
    for rid, r in base_reach.items():
        active_reach[rid] = {
            "k_hr": round(float(r["k_hr"]) * ALPHA_K, 3),
            "x": MUSKINGUM_X,
        }
    state["active_sub_models"] = active_sub
    state["active_reaches"] = active_reach

    # Metadata
    now_iso = datetime.now(timezone.utc).isoformat()
    state["last_calibrated_at"] = now_iso
    state["is_recalibrated"] = True
    state["trigger_reason"] = (
        "Promoted timing-faithful peak-stage config: 2025@Shivaji 96.5% (NSE 0.93, -4h), "
        "2019@Rajaram 86.2%; 2021@Rajaram ~68% is an Open-Meteo input-rainfall ceiling"
    )
    state["confidence_pct"] = 92.0
    state["provenance"] = {
        "validated_event": "2025_august (Shivaji Bridge, hourly observed, peak-stage acc 96.5%, NSE 0.93, timing -4h)",
        "second_event": "2019_august (Rajaram, peak-stage acc 86.2%; reported Q 2111 m3/s confirmed accurate)",
        "third_event": "2021_july (Rajaram, ~68% ONLY - Open-Meteo under-estimates the largest flood; input-data limitation, not tuning)",
        "calibration_script": "historical_checks/2025_august_shivaji_bridge/scripts/comparison/calibrate_peak_stage_3event.py",
        "results_json": "historical_checks/2025_august_shivaji_bridge/results/dynamic_calibration/peak_stage_3event_results.json",
        "metric": "peak_stage_acc = 1 - |sim-obs|/(obs-bed); Rajaram bed 529.318, Shivaji bed 528.670",
        "cn_style": "per_subbasin_baseline (differentiated 61-75; AMC-III -> eff 78-87)",
        "backwater": "Krishna backwater bounded at ~0.4-1.0 m (user); NOT the driver of 2019/2021 gaps -- routing (K/X/lag) is.",
        "caveat": "Do not chase 2021 with parameter tuning: its ~69% ceiling is Open-Meteo rainfall under-estimation (largest observed flood, smallest reanalysis rain). Fixing 2021 needs gauge/orographic rainfall forcing.",
    }

    # History entry
    state.setdefault("history", []).append({
        "timestamp": now_iso,
        "timing_offset_hours": -4.0,
        "stage_error_m": -0.28,
        "peak_discharge_error_m3s": None,
        "alpha_k": ALPHA_K,
        "alpha_lag": ALPHA_LAG,
        "delta_cn": DELTA_CN,
        "muskingum_x": MUSKINGUM_X,
        "ia_frac": IA_FRAC,
        "uh_max_hr": UH_MAX_HR,
        "uh_m_exp": UH_M_EXP,
        "confidence_pct": 92.0,
        "note": "Promoted timing-faithful peak-stage config (replaces round-2 LM params NSE=0.45). "
                "2025 acc 96.5% / NSE 0.93 / timing -4h; 2019 acc 86.2%; 2021 ~68% data-capped.",
    })

    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print("Promoted config:")
    print(f"  alpha_k={ALPHA_K} alpha_lag={ALPHA_LAG} delta_cn={DELTA_CN} muskingum_x={MUSKINGUM_X}")
    print(f"  ia_frac={IA_FRAC} uh_max_hr={UH_MAX_HR} uh_m_exp={UH_M_EXP}")
    print("  active_sub_models:")
    for sid in sorted(active_sub):
        s = active_sub[sid]
        print(f"    {sid} {s['name']:<12} cn={s['cn']:.2f} lag={s['lag_min']:.1f}")
    print("  active_reaches:")
    for rid in sorted(active_reach):
        r = active_reach[rid]
        print(f"    {rid} k={r['k_hr']:.3f} x={r['x']}")
    print(f"Saved -> {STATE}")


if __name__ == "__main__":
    main()
