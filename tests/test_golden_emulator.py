"""
tests/test_golden_emulator.py
=============================
Golden regression lock for the calibrated Panchganga emulator.

WHY THIS EXISTS
---------------
``src/hms/runner.py`` asserts that the Python emulator "exactly mirrors HEC-HMS".
Until a real HEC-HMS DSS reference run is checked in, that claim is unproven and
the numerical chain (SCS loss -> SCS unit hydrograph -> Muskingum network) has no
guard against silent drift.

This test freezes the CURRENT, validated emulator output for one deterministic
storm. Any unintended change to the loss/UH/routing maths fails loudly. The
constants below are a *regression baseline*, not a physical truth — when a HEC-HMS
``Run_1.dss`` reference is available, replace them with values diffed against the
binary and rename this to a true equivalence test.
"""

from datetime import datetime, timezone

import numpy as np
import pytest

from src.hms.basin_parser import load_immutable_baseline
from src.hms.runner import compute_emulator_hydrograph

# Frozen baseline captured from the validated promoted digital-twin config.
_GOLDEN = {
    "amc": "AMC-III",
    "peak_q_m3s": 3345.6,
    "peak_h": 105,
    "volume_mcm": 754.115,
    "surface_volume_m3": 704_719_669.7,
}


def _fixed_storm(hours: int = 90) -> dict:
    """Deterministic per-subbasin storm peaking at hour 30 (no RNG)."""
    t = np.arange(hours, dtype=np.float64)
    return {
        f"S{i}": (12.0 * np.exp(-0.5 * ((t - 30) / 14.0) ** 2) + 0.2).astype(np.float32)
        for i in range(1, 10)
    }


def _run():
    sub, rch = load_immutable_baseline()
    return compute_emulator_hydrograph(
        sub,
        rch,
        _fixed_storm(),
        baseflow_m3s=91.1,
        run_dt=datetime(2026, 8, 22, 6, tzinfo=timezone.utc),
        amc="AMC-III",
        ia_frac=0.05,
        uh_max_hr=90,
        uh_m_exp=20.0,
    )


def test_emulator_matches_frozen_golden_baseline():
    hg = _run()

    assert hg["amc"] == _GOLDEN["amc"]
    assert hg["peak_h"] == _GOLDEN["peak_h"]

    # 0.5% tolerance absorbs float32 rounding, not real model changes.
    assert hg["peak_q"] == pytest.approx(_GOLDEN["peak_q_m3s"], rel=0.005)

    vol_mcm = float(np.sum(hg["q_total"]) * 3600.0 / 1e6)
    assert vol_mcm == pytest.approx(_GOLDEN["volume_mcm"], rel=0.005)

    surface_m3 = float(np.sum(hg["q_surface"]) * 3600.0)
    assert surface_m3 == pytest.approx(_GOLDEN["surface_volume_m3"], rel=0.005)


def test_emulator_is_deterministic():
    """Same inputs must yield bit-identical hydrographs (no hidden RNG)."""
    a = _run()
    b = _run()
    assert np.array_equal(a["q_total"], b["q_total"])
    assert np.array_equal(a["q_surface"], b["q_surface"])
