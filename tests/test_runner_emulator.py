"""
tests/test_runner_emulator.py
=============================
Unit & Integration Tests for the refactored emulator core:
1. Basin_1.basin parsing (basin_parser is now the single source of truth).
2. Muskingum reach routing — stability & volume conservation.
3. compute_emulator_hydrograph — SCS loss + UH + Muskingum network + baseflow.
4. execute_hec_hms — accepts forecast hyetographs AND restores the original
   Control_1.control window afterwards (repo stays pristine).
5. LM recalibration with real hyetographs.
"""

from datetime import datetime, timezone

import numpy as np
import pytest

from src.hms.runner import (
    execute_hec_hms,
    route_muskingum,
    compute_emulator_hydrograph,
    classify_amc,
    CONTROL_FILE,
)
from src.hms.basin_parser import load_basin_parameters
from src.hydrology.ml_calibration import AdaptiveHydrologicCalibrator, BASE_SUB_MODELS, BASE_REACHES


def _storm_hyetographs(n_sub: int = 9, hours: int = 90):
    """Deterministic per-subbasin storm hyetographs peaking at hour 30."""
    t = np.arange(hours, dtype=np.float64)
    return {
        f"S{i+1}": (12.0 * np.exp(-0.5 * ((t - 30) / 14.0) ** 2) + 0.2).astype(np.float32)
        for i in range(n_sub)
    }


# ───────────────────────── Basin_1.basin parsing ──────────────────────────

def test_basin_parser_loads_official_parameters():
    sub_models, reaches = load_basin_parameters()
    assert len(sub_models) == 9
    assert len(reaches) == 5
    # Official Basin_1.basin values (the file HEC-HMS actually executes)
    assert reaches["R5"]["k_hr"] == 4.619
    assert reaches["R5"]["x"] == 0.2
    assert reaches["R2"]["k_hr"] == 11.827
    assert all(isinstance(v["area_km2"], float) for v in sub_models.values())
    assert all(v["lag_min"] > 0 for v in sub_models.values())


def test_basin_parser_matches_calibration_baseline():
    sub_models, reaches = load_basin_parameters()
    assert sub_models.keys() == BASE_SUB_MODELS.keys()
    assert reaches.keys() == BASE_REACHES.keys()
    assert reaches["R5"]["k_hr"] == BASE_REACHES["R5"]["k_hr"]
    assert abs(sub_models["S1"]["cn"] - BASE_SUB_MODELS["S1"]["cn"]) < 1e-9


# ──────────────────────── Muskingum route stability ───────────────────────

def test_classify_amc_thresholds():
    assert classify_amc(5.0) == "AMC-I"
    assert classify_amc(24.9) == "AMC-I"
    assert classify_amc(25.0) == "AMC-II"
    assert classify_amc(64.9) == "AMC-II"
    assert classify_amc(65.0) == "AMC-III"
    assert classify_amc(120.0) == "AMC-III"


def test_route_muskingum_conserves_volume():
    inflow = np.zeros(300, dtype=np.float32)
    inflow[2:18] = 300.0  # square 15h burst of 300 m3/s
    outflow = route_muskingum(inflow, k_hr=4.619, x=0.2, dt_hr=1.0)
    vol_in = float(np.sum(inflow)) * 3600.0
    vol_out = float(np.sum(outflow)) * 3600.0
    assert vol_out / vol_in == pytest.approx(1.0, rel=1e-3)
    assert float(np.max(outflow)) <= 301.0  # no numerical overshoot
    assert float(np.min(outflow)) >= 0.0    # no negative flow


def test_route_muskingum_mass_conservation_within_network():
    # The constant-K split Muskingum must conserve volume exactly, even with the
    # long, stability-flagged reaches (R2 K=11.827 h).
    inflow = np.zeros(500, dtype=np.float32)
    inflow[5:40] = 200.0
    outflow = route_muskingum(inflow, k_hr=11.827, x=0.2, dt_hr=1.0)
    assert float(np.sum(outflow)) == pytest.approx(float(np.sum(inflow)), rel=1e-4)
    assert float(np.min(outflow)) >= 0.0


def test_route_muskingum_stable_for_long_reaches():
    # R2 has K=11.827 which HEC-HMS itself flags unstable (WARNING 41169);
    # sub-dividing travel time must keep coefficients non-negative & mass closed.
    inflow = np.zeros(500, dtype=np.float32)
    inflow[5:40] = 200.0
    outflow = route_muskingum(inflow, k_hr=11.827, x=0.2, dt_hr=1.0)
    vol_in = float(np.sum(inflow)) * 3600.0
    vol_out = float(np.sum(outflow)) * 3600.0
    assert vol_out / vol_in == pytest.approx(1.0, rel=1e-3)
    assert float(np.min(outflow)) >= 0.0


def test_route_muskingum_flat_inflow_remains_flat():
    inflow = np.full(200, 100.0, dtype=np.float32)
    outflow = route_muskingum(inflow, k_hr=8.0, x=0.2, dt_hr=1.0)
    assert float(np.max(outflow)) == pytest.approx(100.0, rel=1e-6)
    assert float(np.min(outflow)) == pytest.approx(100.0, rel=1e-6)


# ──────────────────────── Emulator hydrograph core ────────────────────────

def test_compute_emulator_hydrograph_structure_and_baseflow():
    sub_models, reaches = load_basin_parameters()
    hyetos = _storm_hyetographs(n_sub=9)
    hg = compute_emulator_hydrograph(sub_models, reaches, hyetos, baseflow_m3s=91.1)
    assert set(hg.keys()) >= {"q_surface", "q_total", "baseflow_array", "peak_h", "peak_q", "timestamps"}
    assert len(hg["q_surface"]) == len(hg["q_total"]) == len(hg["timestamps"])
    assert len(hg["q_total"]) >= 90
    assert float(np.sum(hg["q_surface"])) > 0.0            # rain-driven runoff present
    assert float(np.max(hg["q_total"])) >= 91.1            # baseflow always present
    assert float(np.max(hg["q_surface"])) > 0.0            # significant surface peak
    assert "T" not in hg["timestamps"][0] or hg["timestamps"][0].startswith("2026")


def test_compute_emulator_hydrograph_deterministic():
    sub_models, reaches = load_basin_parameters()
    hyetos = _storm_hyetographs(n_sub=9)
    hg1 = compute_emulator_hydrograph(sub_models, reaches, hyetos, baseflow_m3s=40.0)
    hg2 = compute_emulator_hydrograph(sub_models, reaches, hyetos, baseflow_m3s=40.0)
    assert np.array_equal(hg1["q_surface"], hg2["q_surface"])
    assert np.array_equal(hg1["q_total"], hg2["q_total"])


def test_amc_reaction_to_basin_wetness():
    # Same storm, three antecedent-moisture states. AMC acts on RUNOFF generation:
    # a saturated basin must convert more rain to runoff (higher, earlier peak;
    # more surface volume) than a bone-dry one, with channel K/x unchanged.
    sub_models, reaches = load_basin_parameters()
    hyetos = _storm_hyetographs(n_sub=9)
    dry = compute_emulator_hydrograph(sub_models, reaches, hyetos, baseflow_m3s=40.0, amc="AMC-I")
    wet = compute_emulator_hydrograph(sub_models, reaches, hyetos, baseflow_m3s=40.0, amc="AMC-III")
    assert wet["peak_q"] > dry["peak_q"]
    assert wet["peak_h"] <= dry["peak_h"]
    assert wet["amc"] == "AMC-III"
    assert float(np.sum(wet["q_surface"])) > float(np.sum(dry["q_surface"]))
    # Runoff never exceeds rainfall: keep Kn.x physical: both integrate exactly.
    assert all(float(v) >= 0.0 for v in wet["q_surface"])


def test_compute_emulator_hydrograph_auto_classifies_amc():
    sub_models, reaches = load_basin_parameters()
    light = np.full(90, 0.2, dtype=np.float32).reshape(1, 90)
    hyetos = {f"S{i+1}": light[0] for i in range(9)}
    dry = compute_emulator_hydrograph(sub_models, reaches, hyetos, baseflow_m3s=40.0)
    assert dry["amc"] == "AMC-I"
    heavy = np.full(90, 1.1, dtype=np.float32)
    hyetos_wet = {f"S{i+1}": heavy for i in range(9)}
    wet = compute_emulator_hydrograph(sub_models, reaches, hyetos_wet, baseflow_m3s=40.0)
    assert wet["amc"] == "AMC-III"


# ──────────────── Physically accurate peak detection ─────────────────────

def test_shape_peak_not_overridden_by_high_baseflow():
    # A real storm must report its TRUE hydrograph crest even when baseflow is
    # large (the old heuristic forced T+0 whenever surface peak < 2x baseflow,
    # mislabelling genuine floods as "receding" and crashing lead-time forecasts).
    sub_models, reaches = load_basin_parameters()
    hyetos = _storm_hyetographs(n_sub=9)
    for baseflow in (91.1, 500.0):
        hg = compute_emulator_hydrograph(sub_models, reaches, hyetos, baseflow_m3s=baseflow)
        true_peak = int(np.argmax(hg["q_total"]))
        assert hg["peak_h"] == true_peak
        assert hg["peak_h"] > 0                     # storm crest is AFTER T+0
        assert hg["peak_q"] > baseflow              # crest exceeds the recession baseflow
        assert hg["is_significant_event"] is True   # +rise above concurrent baseflow


def test_baseflow_only_basin_naturally_peaks_at_t0():
    # Trace rainfall (~0 surface runoff): the recession baseflow decays
    # exponentially, so np.argmax(q_total) correctly lands on T+0 WITHOUT any
    # artificial override, and the event is labelled baseflow-only.
    sub_models, reaches = load_basin_parameters()
    trace = np.full(90, 0.02, dtype=np.float32)   # ~1.8 mm over 90h
    hyetos = {f"S{i+1}": trace.copy() for i in range(9)}
    hg = compute_emulator_hydrograph(sub_models, reaches, hyetos, baseflow_m3s=91.1)
    assert hg["peak_h"] == 0
    assert hg["is_significant_event"] is False
    assert hg["peak_q"] == pytest.approx(91.1, rel=1e-2)   # == decaying baseflow at T+0


def test_true_peak_survives_in_execute_hec_hms(monkeypatch):
    monkeypatch.setattr("src.hms.runner.find_hec_hms", lambda: (None, "Not Found"))
    dt = datetime(2026, 9, 10, 6, 0, 0, tzinfo=timezone.utc)
    out = execute_hec_hms(dt, _storm_hyetographs(n_sub=9))
    assert out["lead_hours_to_peak"] > 0
    series = [p["discharge_m3s"] for p in out["hydrograph"]]
    assert out["lead_hours_to_peak"] == int(np.argmax(series))


# ──────────────────── execute_hec_hms integration ─────────────────────────

def test_execute_hec_hms_with_hyetographs_restores_control(tmp_path, monkeypatch):
    monkeypatch.setattr("src.hms.runner.find_hec_hms", lambda: (None, "Not Found"))
    if CONTROL_FILE.exists():
        pristine = CONTROL_FILE.read_text(encoding="utf-8", errors="ignore")
    else:
        CONTROL_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONTROL_FILE.write_text("Start Date: 10 September 2026\nStart Time: 06:00\n")
        pristine = CONTROL_FILE.read_text(encoding="utf-8")

    dt = datetime(2026, 9, 10, 6, 0, 0, tzinfo=timezone.utc)
    out = execute_hec_hms(dt, _storm_hyetographs(n_sub=9))

    assert out["status"] == "CALIBRATED_RJKT"
    assert out["hydrograph"][0]["discharge_m3s"] == pytest.approx(out["hydrograph"][0]["baseflow_m3s"], rel=1e-3)
    assert len(out["hydrograph"]) >= 90
    assert sum(p["surface_runoff_m3s"] for p in out["hydrograph"]) > 0.0
    # The checked-in control window must be restored after the run
    assert CONTROL_FILE.read_text(encoding="utf-8", errors="ignore") == pristine


# ──────────────── LM recalibration with real hyetographs ──────────────────

def test_recalibrate_with_hyetographs_physical_signals():
    cal = AdaptiveHydrologicCalibrator()
    hyetos = _storm_hyetographs(n_sub=9)
    res = cal.recalibrate_parameters(
        timing_offset_hours=-3.0,
        stage_error_m=-0.5,
        peak_discharge_error_m3s=150.0,
        subbasin_hyetographs=hyetos,
    )
    # Early arrival underprediction -> faster (smaller K & lag), wetter (higher CN)
    assert 0.50 <= res["alpha_k"] <= 1.80
    assert 0.50 <= res["alpha_lag"] <= 1.80
    assert -8.0 <= res["delta_cn"] <= 8.0
    assert 0.15 <= res["muskingum_x"] <= 0.40
    assert res["alpha_k"] < 1.0
    assert res["alpha_lag"] < 1.0
    assert res["delta_cn"] > 0.0
    all_k = [reaches["k_hr"] for reaches in res["reaches"].values()]
    assert all(k > 0 for k in all_k)