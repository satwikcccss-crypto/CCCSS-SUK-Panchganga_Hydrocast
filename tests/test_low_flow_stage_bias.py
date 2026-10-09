"""Regression tests for the low-flow stage/baseflow bias.

The dry-season bias was two stacked defects:

  1. ``runner.py`` floored the sensor-derived baseflow at
     ``WRD_MONSOON_BASEFLOW_FLOOR_M3S`` (40 m3/s) even when a live ultrasonic
     reading was available. The Panchganga genuinely carries a few m3/s at low
     flow, so this forced a ~+2 m stage bias across the whole 90-hour window.

  2. Baseflow was derived by shifting the observed Shivaji stage by the
     surveyed 0.648 m bed drop and inverting at Rajaram. The two rating curves
     are a constant 0.648 m shift only from about 20 m3/s upward; below that both
     are pinned to their own surveyed bed level, so the offset widens to ~1.02 m
     at Q = 2.8 m3/s. Transferring stage compounded two errors exactly where the
     curve is steepest (dStage/dQ ~ 0.63 m per m3/s at the bottom) and
     understated the observed flow by more than half.

Discharge is conserved along a reach; stage is not. The fix reads the observed
stage at the site where it was measured and converts once.

The baseflow rule itself is ``src.hms.runner.derive_baseflow_m3s``, so these
tests exercise the production function rather than a copy of it. The surveyed
cross-section geometry is pinned separately in
``tests/test_cross_section_survey.py``.
"""

import numpy as np
import pytest

from src.hydrology import stage_converter as sc
from src.hms.runner import derive_baseflow_m3s


def _observed_baseflow(live_stage_m: float) -> float:
    """The production baseflow rule, called directly."""
    return derive_baseflow_m3s(live_stage_m)


@pytest.fixture(scope="module")
def shivaji_curve():
    return sc.get_shivaji_rating_curve()


class TestLowFlowStageBias:
    """The reported symptom: ~2 m mean absolute error in predicted stage."""

    def test_reported_case_has_no_bias(self, shivaji_curve):
        # ThingSpeak: 549.35 m sensor datum, ~62.05 ft -> 530.44 m MSL.
        observed = 530.44
        predicted = sc.discharge_to_stage(_observed_baseflow(observed), shivaji_curve)
        assert predicted == pytest.approx(observed, abs=0.01)

    def test_old_floor_caused_the_two_metre_bias(self):
        """Pins the defect so the floor cannot be reintroduced silently."""
        observed = 530.44
        old_baseflow = max(_observed_baseflow(observed), sc.WRD_MONSOON_BASEFLOW_FLOOR_M3S)
        assert old_baseflow == sc.WRD_MONSOON_BASEFLOW_FLOOR_M3S
        assert sc.discharge_to_stage(old_baseflow, sc.get_shivaji_rating_curve()) == pytest.approx(
            532.42, abs=0.05
        )

    @pytest.mark.parametrize("observed", [530.20, 530.34, 530.44, 530.60, 531.00, 532.00])
    def test_round_trip_is_neutral_across_low_flow(self, shivaji_curve, observed):
        predicted = sc.discharge_to_stage(_observed_baseflow(observed), shivaji_curve)
        assert predicted == pytest.approx(observed, abs=0.05)

    @pytest.mark.parametrize(
        "observed", [541.50, 542.10, 542.70, 543.30, 545.33]
    )
    def test_alert_levels_still_round_trip(self, shivaji_curve, observed):
        """Flood-period behaviour must be unchanged by the fix."""
        predicted = sc.discharge_to_stage(_observed_baseflow(observed), shivaji_curve)
        assert predicted == pytest.approx(observed, abs=0.05)


class TestDatumOffsetIsNotConstantAtLowFlow:
    """Documents why the cross-site stage transfer had to be removed."""

    @pytest.mark.parametrize(
        "q",
        [
            0.5,      # un-gauged band
            2.80,
            14.16,    # lowest WRD observation
            40.0,
            274.4,
            1480.0,
            3850.0,
        ],
    )
    def test_offset_is_survey_bed_drop_at_all_flows(self, q):
        """The site transfer is the survey bed drop at every discharge.

        This was previously only asserted at and above 20 m3/s, because an
        extra fabricated anchor (530.18 -> Q=0) made the offset appear to
        widen below 20 m3/s.  That anchor was removed on 2026-09-30 because
        530.18 m is the WRD zero-gauge DATUM, not a weir crest.  With it gone
        the two curves are exact translates and the offset is uniform, which
        is the correct behaviour for the uniform-flow transfer being modelled.
        """
        s = sc.discharge_to_stage(q, sc.get_shivaji_rating_curve())
        r = sc.discharge_to_stage(q, sc.get_rajaram_rating_curve())
        assert r - s == pytest.approx(sc.SHIVAJI_RC_OFFSET_M, abs=0.01)

    def test_low_flow_round_trip_is_consistent(self):
        """Transferring the stage to Rajaram and back must not change Q.

        An earlier version double-applied the datum offset when a stage was
        moved between sites before being inverted into a discharge, which
        understated low flow badly.  The two curves being exact translates
        makes the round trip an identity, so any regression here means the
        offset is being applied twice.
        """
        observed = 530.44
        q_direct = _observed_baseflow(observed)
        q_transferred = sc.convert_stage_to_discharge_manning(
            sc.infer_rajaram_stage_from_shivaji(
                observed, q_m3s=q_direct, apply_backwater=False
            ),
            "RAJARAM_BRIDGE",
        )
        assert q_transferred == pytest.approx(q_direct, abs=0.05)


class TestLowFlowUncertaintyBand:
    """The un-gauged band must be visible, not silently reported as precise."""

    def test_live_stage_is_flagged_ungauged(self):
        assert sc.is_ungauged_stage(530.44, "SHIVAJI_BRIDGE")
        assert not sc.is_ungauged_stage(533.0, "SHIVAJI_BRIDGE")

    def test_production_value_lies_inside_geometry_band(self):
        """Both geometry closures must bracket the production PCHIP value."""
        est = sc.estimate_low_flow_discharge(530.44, "SHIVAJI_BRIDGE")
        assert est["q_low_m3s"] <= est["q_m3s"] <= est["q_high_m3s"]
        assert est["is_ungauged"] is True

    def test_band_brackets_are_ordered_and_narrow(self):
        est = sc.estimate_low_flow_discharge(530.44, "SHIVAJI_BRIDGE")
        assert est["q_conveyance_m3s"] < est["q_velocity_m3s"]
        # sanity: the band must be a bracket, not a blow-up
        assert est["q_high_m3s"] / est["q_low_m3s"] < 2.0

    def test_measured_reference_comes_from_the_lowest_wrd_gauge(self):
        velocity, conveyance = sc._low_flow_reference()
        assert velocity == pytest.approx(0.0767, abs=0.001)
        assert conveyance == pytest.approx(0.0539, abs=0.001)

    def test_zero_discharge_at_bed(self):
        est = sc.estimate_low_flow_discharge(sc.SHIVAJI_BED_RL_M, "SHIVAJI_BRIDGE")
        assert est["q_m3s"] == 0.0


class TestWrdRegisterCleaning:
    """The ft_dec cross-check that exposed the 56 bad register rows."""

    def test_gauge_zero_is_the_zero_datum_not_a_crest(self):
        assert sc.RAJARAM_GAUGE_ZERO_M == 530.18
        assert sc.RAJARAM_KT_WEIR_CREST_RL_M == 535.77
        assert sc.RAJARAM_GAUGE_ZERO_M != sc.RAJARAM_KT_WEIR_CREST_RL_M

    def test_no_anchor_at_the_gauge_zero(self):
        """530.18 m must not carry a Q=0 anchor; only the surveyed bed may."""
        stages = list(sc.RAJARAM_ANCHORS_STAGE)
        assert sc.RAJARAM_GAUGE_ZERO_M not in stages
        assert stages[0] == pytest.approx(sc.RAJARAM_BED_RL_M)
        assert sc.RAJARAM_ANCHORS_Q[0] == 0.0

    def test_lowest_anchor_is_the_lowest_wrd_observation(self):
        """The gauged domain starts exactly where the register starts."""
        assert sc.RAJARAM_ANCHORS_STAGE[1] == pytest.approx(
            sc.WRD_LOWEST_GAUGE_STAGE_M
        )
        assert sc.RAJARAM_ANCHORS_Q[1] == pytest.approx(sc.WRD_LOWEST_GAUGE_Q_M3S)

    def test_measured_surface_drop_is_recorded_and_differs_from_bed_drop(self):
        """Backwater evidence: 0.600 m measured vs 0.648 m bed drop."""
        assert sc.SHIVAJI_MEASURED_SURFACE_DROP_M == 0.600
        assert sc.SHIVAJI_RC_OFFSET_M == 0.648
        assert sc.SHIVAJI_MEASURED_SURFACE_DROP_M < sc.SHIVAJI_RC_OFFSET_M

    def test_official_sheet_equation_reproduces_its_own_band(self):
        """Q = 1.5 * (H - bed)^2.778 over 533.54-541.50 m, R^2 = 0.99858."""
        for stage, q in ((533.54, 80.0), (535.77, 274.39), (538.16, 613.06),
                         (541.50, 1480.0)):
            predicted = sc.WRD_SHEET_COEFFICIENT * (
                (stage - sc.RAJARAM_BED_RL_M) ** sc.WRD_SHEET_EXPONENT
            )
            assert predicted == pytest.approx(q, rel=0.08)


class TestBackwaterCorrection:
    """Ponding raises the surface; it must not be inverted into a discharge."""

    def test_backwater_adds_head_by_default(self):
        on = sc.infer_rajaram_stage_from_shivaji(530.44, q_m3s=5.0)
        off = sc.infer_rajaram_stage_from_shivaji(
            530.44, q_m3s=5.0, apply_backwater=False
        )
        assert on > off
        assert on - off == pytest.approx(0.8 * (1 - 5.0 / 100.0), abs=1e-6)

    def test_backwater_suppressed_when_not_requested(self):
        expected = 530.44 + (sc.RAJARAM_BED_RL_M - sc.SHIVAJI_BED_RL_M)
        assert sc.infer_rajaram_stage_from_shivaji(
            530.44, q_m3s=5.0, apply_backwater=False
        ) == pytest.approx(expected, abs=1e-3)

    def test_backwater_inactive_at_high_discharge(self):
        on = sc.infer_rajaram_stage_from_shivaji(540.0, q_m3s=5.0)
        off = sc.infer_rajaram_stage_from_shivaji(540.0, q_m3s=5.0, apply_backwater=False)
        assert on == off


class TestDatumsAreNotConflated:
    def test_weir_crest_is_not_gauge_zero(self):
        """530.18 m is the gauge zero datum; the weir overflows at 535.77 m."""
        assert sc.RAJARAM_GAUGE_ZERO_M == 530.18
        assert sc.RAJARAM_KT_WEIR_CREST_RL_M == 535.77
        assert sc.RAJARAM_KT_WEIR_CREST_RL_M != sc.RAJARAM_GAUGE_ZERO_M

    def test_bed_drop_matches_survey(self):
        assert sc.RAJARAM_BED_RL_M - sc.SHIVAJI_BED_RL_M == pytest.approx(0.648, abs=1e-6)


class TestRatingCurveIntegrity:
    def test_curve_is_monotonic(self, shivaji_curve):
        df = shivaji_curve.sort_values("stage_m")
        assert np.all(np.diff(df.q_m3s.to_numpy()) >= -1e-9)

    def test_observed_operating_range_is_anchored(self, shivaji_curve):
        """Low-flow stages must be interpolated, not extrapolated."""
        assert shivaji_curve.stage_m.min() <= 530.44
        assert shivaji_curve.stage_m.max() >= 545.33


class TestLowFlowGuard:
    """Verifies that datum/baseflow offsets and un-gauged stages are flagged."""

    def test_constant_bias_detected_on_two_metre_offset(self):
        obs = np.full(10, 530.40)
        pred = np.full(10, 532.42)
        guard = sc.assess_low_flow_guard(pred, obs)
        assert guard["constant_bias_detected"] is True
        assert guard["baseflow_stage_offset_m"] == pytest.approx(2.02, abs=0.01)
        assert guard["rating_extrapolated"] is True
        assert guard["ungauged_fraction"] == 1.0
        assert "Constant baseflow stage offset" in guard["note"]

    def test_clean_baseflow_not_flagged_as_mismatch(self):
        obs = np.full(10, 530.40)
        pred = np.full(10, 530.42)
        guard = sc.assess_low_flow_guard(pred, obs)
        assert guard["constant_bias_detected"] is False
        assert guard["baseflow_stage_offset_m"] == pytest.approx(0.02, abs=0.01)
        assert guard["note"] is None

    def test_is_ungauged_stage_thresholds(self):
        # Shivaji lowest gauged anchor is ~532.052 m MSL
        assert sc.is_ungauged_stage(530.40, "SHIVAJI_BRIDGE") is True
        assert sc.is_ungauged_stage(532.50, "SHIVAJI_BRIDGE") is False
        # Rajaram lowest gauged anchor is 532.70 m MSL
        assert sc.is_ungauged_stage(531.00, "RAJARAM_BRIDGE") is True
        assert sc.is_ungauged_stage(533.00, "RAJARAM_BRIDGE") is False

    def test_empty_series_handled_safely(self):
        guard = sc.assess_low_flow_guard([], [])
        assert guard["constant_bias_detected"] is False
        assert guard["rating_extrapolated"] is False
        assert guard["baseflow_stage_offset_m"] is None


class TestTelemetryObservationFallback:
    """Never fabricate a stage: fall back to cached observations or unverified."""

    def test_latest_cached_observation_reads_cache(self, monkeypatch):
        from src.ecmwf import open_meteo as om
        mock_cache = {
            "2026-09-29T17:00:00Z": {"observed_stage_m": 530.41, "observed_distance_ft": 62.14},
            "2026-09-29T18:00:00Z": {"observed_stage_m": 530.44, "observed_distance_ft": 62.05},
        }
        monkeypatch.setattr(om, "load_telemetry_cache", lambda: mock_cache)
        latest = om._latest_cached_observation()
        assert latest is not None
        assert latest["stage_m"] == 530.44
        assert latest["timestamp"] == "2026-09-29T18:00:00Z"

    def test_latest_cached_observation_handles_empty(self, monkeypatch):
        from src.ecmwf import open_meteo as om
        monkeypatch.setattr(om, "load_telemetry_cache", lambda: {})
        assert om._latest_cached_observation() is None
        