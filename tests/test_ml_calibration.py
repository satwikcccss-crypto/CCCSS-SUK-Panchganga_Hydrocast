"""
tests/test_ml_calibration.py
============================
Unit & Integration Tests for:
1. Peak Flood Arrival Time calculation with ±2.0 hour confidence interval.
2. Real-Time ML Adaptive Hydrologic Recalibrator (Muskingum K & X, Subbasin lag, SCS Curve Number).
3. Simultaneous synchronization of Python emulator and HEC-HMS Basin_1.basin.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pytest

from src.hydrology.ml_calibration import (
    calculate_peak_arrival_window,
    AdaptiveHydrologicCalibrator,
    calibrator,
    BASE_SUB_MODELS,
    BASE_REACHES,
)
from src.hms.runner import execute_hec_hms


def test_calculate_peak_arrival_window():
    """Verify peak arrival calculation and ±2.0h confidence interval."""
    start_dt = datetime(2026, 9, 10, 6, 0, 0, tzinfo=timezone.utc)
    mock_forecast = []
    # Create hydrograph peaking at hour 36
    for h in range(90):
        # Gaussian peak around hour 36
        q = 100.0 + 1200.0 * np.exp(-0.5 * ((h - 36) / 8.0) ** 2)
        stg = 532.60 + 11.0 * (q / 1300.0)
        mock_forecast.append({
            "lead_hours": h,
            "forecast_time": (start_dt + timedelta(hours=h)).isoformat(),
            "stage_m": round(stg, 2),
            "discharge_m3s": round(q, 1),
        })

    res = calculate_peak_arrival_window(
        mock_forecast,
        site_id="SHIVAJI_BRIDGE",
        margin_hours=2.0,
    )

    assert res["site_id"] == "SHIVAJI_BRIDGE"
    assert res["peak_lead_hours"] == 36
    expected_peak_time = (start_dt + timedelta(hours=36)).isoformat()
    assert res["peak_arrival_time"] == expected_peak_time

    ci = res["confidence_interval"]
    assert ci["margin_hours"] == 2.0
    assert ci["confidence_pct"] == 95
    assert ci["earliest_lead_hours"] == 34.0
    assert ci["latest_lead_hours"] == 38.0
    assert ci["earliest_arrival_time"] == (start_dt + timedelta(hours=34)).isoformat()
    assert ci["latest_arrival_time"] == (start_dt + timedelta(hours=38)).isoformat()

    assert ci["stage_range_m"][0] < res["peak_stage_m"] < ci["stage_range_m"][1]
    assert ci["discharge_range_m3s"][0] < res["peak_discharge_m3s"] < ci["discharge_range_m3s"][1]


def test_recalibrate_early_arrival():
    """Verify parameter scaling when flood wave arrives early (Δt < 0)."""
    cal = AdaptiveHydrologicCalibrator()
    # Wave arrives 2.5 hours early, stage underpredicted by 0.35m
    res = cal.recalibrate_parameters(
        timing_offset_hours=-2.5,
        stage_error_m=-0.35,
    )

    # Physical expectations:
    # 1. Faster velocity -> Muskingum K scaled down (α_K < 1.0)
    assert res["alpha_k"] < 1.0, f"Expected alpha_k < 1.0, got {res['alpha_k']}"
    # 2. Faster catchment response -> Subbasin lag scaled down (α_lag < 1.0)
    assert res["alpha_lag"] < 1.0, f"Expected alpha_lag < 1.0, got {res['alpha_lag']}"
    # 3. Steeper wave -> Muskingum X increases towards 0.30+
    assert res["muskingum_x"] >= 0.25, f"Expected muskingum_x >= 0.25, got {res['muskingum_x']}"
    # 4. Underprediction of stage on rising limb -> higher Curve Number (ΔCN > 0)
    assert res["delta_cn"] > 0.0, f"Expected delta_cn > 0.0, got {res['delta_cn']}"

    # Verify that subbasin and reach dictionaries contain valid adjusted values
    for sid, props in res["sub_models"].items():
        base_cn = BASE_SUB_MODELS[sid]["cn"]
        base_lag = BASE_SUB_MODELS[sid]["lag_min"]
        assert props["cn"] > base_cn
        assert props["lag_min"] < base_lag

    for rid, rprops in res["reaches"].items():
        base_k = BASE_REACHES[rid]["k_hr"]
        assert rprops["k_hr"] < base_k
        assert rprops["x"] == res["muskingum_x"]


def test_recalibrate_late_arrival():
    """Verify parameter scaling when flood wave arrives late (Δt > 0)."""
    cal = AdaptiveHydrologicCalibrator()
    # Wave arrives 2.0 hours late
    res = cal.recalibrate_parameters(
        timing_offset_hours=2.0,
        stage_error_m=0.20,
    )

    # Physical expectations:
    # 1. Attenuated slower wave -> Muskingum K scaled up (α_K > 1.0)
    assert res["alpha_k"] > 1.0, f"Expected alpha_k > 1.0, got {res['alpha_k']}"
    # 2. Slower catchment response -> Subbasin lag scaled up (α_lag > 1.0)
    assert res["alpha_lag"] > 1.0, f"Expected alpha_lag > 1.0, got {res['alpha_lag']}"


def test_recalibration_physical_bounds():
    """Verify parameters never exceed strict physical bounds even with extreme inputs."""
    cal = AdaptiveHydrologicCalibrator()
    # Extreme input test: -15 hours offset
    res = cal.recalibrate_parameters(
        timing_offset_hours=-15.0,
        stage_error_m=-2.5,
    )

    assert 0.50 <= res["alpha_k"] <= 1.80
    assert 0.50 <= res["alpha_lag"] <= 1.80
    assert -8.0 <= res["delta_cn"] <= 8.0
    assert 0.15 <= res["muskingum_x"] <= 0.40

    for sid, props in res["sub_models"].items():
        assert 45.0 <= props["cn"] <= 95.0
        assert props["lag_min"] > 0


def test_sync_to_hec_hms_basin(tmp_path):
    """Verify atomic Basin_1.basin updating and backup creation."""
    cal = AdaptiveHydrologicCalibrator()

    # Create dummy basin file
    dummy_basin = tmp_path / "Basin_1.basin"
    dummy_basin.write_text("""
Subbasin: S1
     Curve Number: 74.85
     Lag: 2152.0
End:

Reach: R1
     Muskingum K: 4.500
     Muskingum x: 0.25
End:
""", encoding="utf-8")

    # Patch BASIN_FILE in module temporarily
    import src.hydrology.ml_calibration as ml_mod
    orig_basin = ml_mod.BASIN_FILE
    ml_mod.BASIN_FILE = dummy_basin

    try:
        cal_params = {
            "sub_models": {
                "S1": {"cn": 76.50, "lag_min": 1950.0},
            },
            "reaches": {
                "R1": {"k_hr": 4.100, "x": 0.30},
            },
        }
        success = cal.sync_to_hec_hms_basin(cal_params)
        assert success is True

        updated_text = dummy_basin.read_text(encoding="utf-8")
        assert "Curve Number: 76.50" in updated_text
        assert "Lag: 1950.0" in updated_text
        assert "Muskingum K: 4.10" in updated_text
        assert "Muskingum x: 0.30" in updated_text

        # Verify backup was created
        backups = list(tmp_path.glob("Basin_1.basin.bak_*"))
        assert len(backups) == 1
    finally:
        ml_mod.BASIN_FILE = orig_basin


def test_discrepancy_detector_returns_signed_stage_error():
    """The detector must return a dict with a SIGNED stage error and peaks.

    Historically it returned ``max(abs(error))`` which is always >= 0, so the
    downstream ΔCN correction could only ever move one way.
    """
    cal = AdaptiveHydrologicCalibrator()
    start = datetime(2026, 9, 10, 0, 0, 0, tzinfo=timezone.utc)

    # Observed rising limb, forecast is consistently 0.30 m TOO HIGH.
    observed = {}
    forecast = []
    for h in range(6):
        t = start + timedelta(hours=h)
        obs_stage = 531.0 + 0.10 * h
        observed[t.isoformat()] = {"observed_stage_m": obs_stage}
        forecast.append({
            "forecast_time": t.isoformat(),
            "stage_m": obs_stage + 0.30,
        })

    res = cal.detect_timing_and_stage_discrepancy(forecast, observed)

    assert isinstance(res, dict)
    assert res["signed_stage_error_m"] > 0.0, "over-prediction must be positive"
    assert res["max_stage_error_m"] == pytest.approx(0.30, abs=0.05)
    assert res["forecast_peak_stage_m"] > res["observed_peak_stage_m"]
    assert res["warranted"] is True
    assert "reason" in res


def test_recalibration_marks_state_and_snapshots_params():
    """``is_recalibrated`` must flip True and the active params must be stored."""
    cal = AdaptiveHydrologicCalibrator()
    assert cal.state["is_recalibrated"] is False

    res = cal.recalibrate_parameters(
        timing_offset_hours=-2.0,
        stage_error_m=-0.30,
        peak_discharge_error_m3s=45.0,
    )

    assert cal.state["is_recalibrated"] is True
    assert 50.0 <= cal.state["confidence_pct"] <= 99.9
    assert cal.state["peak_discharge_error_m3s"] == 45.0
    assert cal.state["active_sub_models"] == res["sub_models"]
    assert cal.state["active_reaches"] == res["reaches"]
    # Baseline snapshot must remain pristine (not overwritten by active values).
    assert cal.state["baseline_sub_models"]["S1"]["cn"] == pytest.approx(
        BASE_SUB_MODELS["S1"]["cn"], abs=1e-3
    )


def test_runner_accepts_parameter_overrides():
    """Verify execute_hec_hms runs with parameter overrides."""
    now_dt = datetime(2026, 9, 10, 6, 0, 0, tzinfo=timezone.utc)
    overrides = {
        "alpha_k": 0.85,
        "alpha_lag": 0.90,
        "delta_cn": 2.0,
        "muskingum_x": 0.28,
        "sub_models": {
            "S1": {"cn": 76.85, "lag_min": 1936.8},
        },
        "reaches": {
            "R1": {"k_hr": 3.825, "x": 0.28},
        },
    }

    out = execute_hec_hms(now_dt, parameter_overrides=overrides)
    assert out["status"] in ("CALIBRATED_RJKT", "COMPLETED_BINARY")
    assert "calibration" in out
    assert out["calibration"]["is_recalibrated"] is True
    assert out["calibration"]["alpha_k"] == 0.85
    assert out["calibration"]["alpha_lag"] == 0.90
