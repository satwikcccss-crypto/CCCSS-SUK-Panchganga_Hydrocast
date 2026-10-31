"""
restore_calibration_state.py
============================
Recover `data/telemetry/ml_calibration_state.json` after it was corrupted by an
external git operation.

WHAT HAPPENED
-------------
During a workspace restart the working-tree copy of the calibration state file
was swapped back to a committed "checkpoint" revision (commit 087cd64c) that had
been committed WITH unresolved git conflict markers (`<<<<<<< HEAD`). The result
was a JSON file that no longer parses (line 95: `<<<<<<< HEAD`), and the valid
promoted working-tree copy plus its timestamped backup were lost.

The conflict was NOT cleanly resolvable by choosing one side, because the two
sides had diverged independently by region:
  * active config  -> HEAD=older (alpha_k=1.218, x=0.19) vs 087cd64c=promoted
                      (alpha_k=0.60, x=0.30); the PROMOTED side is correct.
  * history        -> HEAD=cleaner vs 087cd64c=degenerate (Δt=-314, stage=-542);

so a whole-file "ours"/"theirs" checkout would have picked a wrong half somewhere.

FIX
---
Regenerate the state deterministically from `load_immutable_baseline()` + the
validated timing-faithful peak-stage config (the exact values promote_digital_twin.py
wrote and the 3-event calibration validated: 2019 86.2% / 2025 96.5% NSE 0.93).
The corrupted file is preserved as `*.corrupted_<stamp>` for forensics.
"""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO = Path("E:/hydrocast_complete")
sys.path.insert(0, str(REPO))

from src.hms.basin_parser import load_immutable_baseline

STATE = REPO / "data" / "telemetry" / "ml_calibration_state.json"
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
CORRUPTED = STATE.with_suffix(f".json.corrupted_{STAMP}")

# Validated timing-faithful peak-stage config (see promote_digital_twin.py header,
# calibrate_peak_stage_3event.py, verify_recommended_config.json).
ALPHA_K, ALPHA_LAG, DELTA_CN, MUSKINGUM_X = 0.60, 0.82, 0.0, 0.30
IA_FRAC, UH_MAX_HR, UH_M_EXP = 0.05, 90, 20.0


def main():
    # 1. Preserve the corrupted file for forensics (do NOT delete evidence).
    shutil.copy2(STATE, CORRUPTED)
    print(f"Corrupted file preserved -> {CORRUPTED.name}")

    base_sub, base_reach = load_immutable_baseline()
    now_iso = datetime.now(timezone.utc).isoformat()

    baseline_sub = {
        sid: {"name": p["name"], "area_km2": p["area_km2"],
              "cn": round(float(p["cn"]), 3), "lag_min": round(float(p["lag_min"]), 1)}
        for sid, p in base_sub.items()
    }
    baseline_rch = {
        rid: {"k_hr": round(float(p["k_hr"]), 3), "x": round(float(p["x"]), 3)}
        for rid, p in base_reach.items()
    }
    active_sub = {
        sid: {"name": p["name"], "area_km2": p["area_km2"],
              "cn": round(float(p["cn"]) + DELTA_CN, 3),
              "lag_min": round(float(p["lag_min"]) * ALPHA_LAG, 1)}
        for sid, p in base_sub.items()
    }
    active_reach = {
        rid: {"k_hr": round(float(p["k_hr"]) * ALPHA_K, 3), "x": MUSKINGUM_X}
        for rid, p in base_reach.items()
    }

    state = {
        "last_calibrated_at": now_iso,
        "is_recalibrated": True,
        "trigger_reason": (
            "Promoted timing-faithful peak-stage config: 2025@Shivaji 96.5% (NSE 0.93, -4h), "
            "2019@Rajaram 86.2%; 2021@Rajaram ~68% is an Open-Meteo input-rainfall ceiling"
        ),
        "timing_offset_hours": -4.0,
        "stage_discrepancy_m": -0.28,
        "peak_discharge_error_m3s": 0.0,
        "alpha_k": ALPHA_K,
        "alpha_lag": ALPHA_LAG,
        "delta_cn": DELTA_CN,
        "muskingum_x": MUSKINGUM_X,
        "ia_frac": IA_FRAC,
        "uh_max_hr": UH_MAX_HR,
        "uh_m_exp": UH_M_EXP,
        # 92.0 is the OFFLINE 3-event backtest confidence for this promoted config,
        # distinct from the live `observation-fit` score the engine writes on each
        # recalibration (see confidence_basis).
        "confidence_pct": 92.0,
        "confidence_basis": (
            "Offline 3-event backtest confidence for the promoted config (2019 86.2% / "
            "2025 96.5% NSE 0.93). Live recalibrations instead write an observation-fit "
            "score, not this offline figure."
        ),
        "ml_predictor_state": "UNTRAINED",
        "baseline_sub_models": baseline_sub,
        "baseline_reaches": baseline_rch,
        "active_sub_models": active_sub,
        "active_reaches": active_reach,
        "provenance": {
            "restored": (
                f"Regenerated {STAMP} after git conflict-marker corruption; values match the "
                "validated promote_digital_twin.py output."
            ),
            "validated_event": "2025_august (Shivaji Bridge, hourly observed, peak-stage acc 96.5%, NSE 0.93, timing -4h)",
            "second_event": "2019_august (Rajaram, peak-stage acc 86.2%; reported Q 2111 m3/s confirmed accurate)",
            "third_event": "2021_july (Rajaram, ~68% ONLY - Open-Meteo under-estimates the largest flood; input-data limitation, not tuning)",
            "calibration_script": "historical_checks/2025_august_shivaji_bridge/scripts/comparison/calibrate_peak_stage_3event.py",
            "results_json": "historical_checks/2025_august_shivaji_bridge/results/dynamic_calibration/peak_stage_3event_results.json",
            "metric": "peak_stage_acc = 1 - |sim-obs|/(obs-bed); Rajaram bed 529.318, Shivaji bed 528.670",
            "cn_style": "per_subbasin_baseline (differentiated 61-75; AMC-III -> eff 78-87)",
        },
        # Clean history: only the meaningful promotion entry. The degenerate
        # Δt=-314 / stage=-542 entries from a broken offline run were dropped.
        "history": [{
            "timestamp": now_iso,
            "timing_offset_hours": -4.0,
            "stage_error_m": -0.28,
            "peak_discharge_error_m3s": 0.0,
            "alpha_k": ALPHA_K,
            "alpha_lag": ALPHA_LAG,
            "delta_cn": DELTA_CN,
            "muskingum_x": MUSKINGUM_X,
            "ia_frac": IA_FRAC,
            "uh_max_hr": UH_MAX_HR,
            "uh_m_exp": UH_M_EXP,
            "confidence_pct": 92.0,
            "ml_predictor_state": "UNTRAINED",
            "note": "Restored promoted timing-faithful peak-stage config (2025 96.5% / NSE 0.93, 2019 86.2%).",
        }],
    }

    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # 2. Verify it round-trips.
    check = json.loads(STATE.read_text(encoding="utf-8"))
    assert check["alpha_k"] == ALPHA_K and check["muskingum_x"] == MUSKINGUM_X
    assert check["active_reaches"]["R1"]["x"] == MUSKINGUM_X
    print(f"Restored valid JSON -> {STATE.name} ({STATE.stat().st_size} bytes)")
    print(f"  alpha_k={ALPHA_K} alpha_lag={ALPHA_LAG} delta_cn={DELTA_CN} muskingum_x={MUSKINGUM_X}")
    print(f"  ia_frac={IA_FRAC} uh_max_hr={UH_MAX_HR} uh_m_exp={UH_M_EXP}")
    print(f"  active R1 k={active_reach['R1']['k_hr']} x={active_reach['R1']['x']}")
    print(f"  active S6 cn={active_sub['S6']['cn']} lag={active_sub['S6']['lag_min']}")


if __name__ == "__main__":
    main()
