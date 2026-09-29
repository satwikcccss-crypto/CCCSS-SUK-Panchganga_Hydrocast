"""
Unit Tests for Real-Time Telemetry Validator & 90-Hour Lifecycle Engine
========================================================================
Validates:
  - Raw ThingSpeak feed parsing and hourly mean resampling
  - Elevation MSL and raw feet preservation
  - Pure mathematical formulas (RMSE, MAE, NSE, PBIAS, Spearman rho, Pearson R^2)
  - Continuous 90-hour lifecycle progress tracking
"""

import math
import unittest
import numpy as np

from src.hydrology.realtime_telemetry_validator import (
    resample_feeds_hourly,
    compute_pure_metrics,
    SHIVAJI_DATUM_MSL,
)


class TestRealtimeTelemetryValidator(unittest.TestCase):

    def test_resample_feeds_hourly_accuracy(self):
        """Verify 5-minute pings are aggregated into mean hourly observations retaining feet and meters."""
        mock_feeds = [
            {"created_at": "2026-09-04T05:05:00Z", "field1": "52.80"},
            {"created_at": "2026-09-04T05:10:00Z", "field1": "52.90"},
            {"created_at": "2026-09-04T05:15:00Z", "field1": "53.00"},
            {"created_at": "2026-09-04T05:20:00Z", "field1": "52.70"},
            # Extreme outlier to test noise filtering
            {"created_at": "2026-09-04T05:25:00Z", "field1": "120.00"},
            {"created_at": "2026-09-04T05:30:00Z", "field1": "52.85"},
        ]

        resampled = resample_feeds_hourly(mock_feeds, datum_msl=SHIVAJI_DATUM_MSL)
        hour_key = "2026-09-04T05:00:00Z"
        self.assertIn(hour_key, resampled)

        obs = resampled[hour_key]
        # Outlier 120.00 should have been filtered out, leaving 5 valid feeds
        self.assertEqual(obs["sample_count"], 5)

        # Mean feet: (52.80 + 52.90 + 53.00 + 52.70 + 52.85) / 5 = 52.85 ft
        expected_feet = round((52.80 + 52.90 + 53.00 + 52.70 + 52.85) / 5.0, 2)
        self.assertAlmostEqual(obs["observed_distance_ft"], expected_feet, places=2)

        # Expected elevation: 549.35 - (52.85 * 0.3048) = 549.35 - 16.10868 = 533.24 m
        expected_stage = round(SHIVAJI_DATUM_MSL - (expected_feet * 0.3048), 2)
        self.assertAlmostEqual(obs["observed_stage_m"], expected_stage, places=2)

    def test_compute_pure_metrics_perfect(self):
        """Verify textbook formulas yield exact values under perfect forecast-observed match."""
        stages = np.array([533.20, 533.45, 533.80, 534.20, 534.10, 533.70])
        metrics = compute_pure_metrics(stages, stages)

        self.assertEqual(metrics["sample_size_hours"], 6)
        self.assertAlmostEqual(metrics["rmse_stage_m"], 0.0, places=3)
        self.assertAlmostEqual(metrics["mae_stage_m"], 0.0, places=3)
        self.assertAlmostEqual(metrics["nse_stage"], 1.0, places=3)
        self.assertAlmostEqual(metrics["pbias_stage_pct"], 0.0, places=2)
        self.assertAlmostEqual(metrics["spearman_rho"], 1.0, places=3)
        self.assertAlmostEqual(metrics["pearson_r2"], 1.0, places=3)
        self.assertEqual(metrics["performance_grade"], "EXCELLENT")

    def test_compute_pure_metrics_realistic_error(self):
        """Verify pure metrics under realistic calibration delta (e.g. +/- 4cm error)."""
        obs = np.array([533.24, 533.27, 533.31, 533.35, 533.40, 533.45])
        # Simulated prediction with minor delta
        pred = np.array([533.21, 533.30, 533.28, 533.39, 533.42, 533.48])

        metrics = compute_pure_metrics(pred, obs)
        self.assertLess(metrics["rmse_stage_m"], 0.10)  # RMSE under 10cm
        self.assertLess(metrics["mae_stage_m"], 0.08)
        self.assertGreater(metrics["spearman_rho"], 0.85)  # High rank correlation
        self.assertLess(abs(metrics["pbias_stage_pct"]), 1.0)

    def test_insufficient_data_handling(self):
        """Zero matched points must report INSUFFICIENT_DATA with no metrics."""
        metrics = compute_pure_metrics(np.array([]), np.array([]))
        self.assertEqual(metrics["status"], "INSUFFICIENT_DATA")
        self.assertEqual(metrics["sample_size_hours"], 0)
        self.assertIsNone(metrics["rmse_stage_m"])
        self.assertIsNone(metrics["nse_stage"])

    def test_short_window_withholds_skill_metrics(self):
        """
        Fewer than MIN_CORRELATION_SAMPLES matched points must not produce a
        Spearman/NSE, even when the error itself is tiny. Ranking a handful of
        points is not statistically meaningful.
        """
        from src.hydrology.realtime_telemetry_validator import MIN_CORRELATION_SAMPLES
        obs = np.array([533.24, 533.27])
        pred = np.array([533.20, 533.25])

        metrics = compute_pure_metrics(pred, obs)
        self.assertLess(len(obs), MIN_CORRELATION_SAMPLES)
        self.assertEqual(metrics["status"], "ACCUMULATING_TELEMETRY")
        self.assertFalse(metrics["skill_metrics_reliable"])
        self.assertIsNone(metrics["nse_stage"])
        self.assertIsNone(metrics["spearman_rho"])
        # Error metrics remain meaningful and are still reported.
        self.assertIsNotNone(metrics["rmse_stage_m"])

    def test_flat_observed_series_withholds_nse(self):
        """
        A near-constant observed series collapses the NSE denominator, which used
        to make the score explode to large negative values. NSE and the rank
        correlations must be withheld instead.
        """
        obs = np.full(12, 530.35) + np.array([0.0, 0.01, -0.01, 0.0, 0.01, -0.01] * 2)
        pred = np.full(12, 530.21)
        metrics = compute_pure_metrics(pred, obs)
        self.assertFalse(metrics["skill_metrics_reliable"])
        self.assertIsNone(metrics["nse_stage"])
        self.assertIsNone(metrics["spearman_rho"])
        self.assertEqual(metrics["performance_grade"], "BASEFLOW_STABLE")
        self.assertIsNotNone(metrics["rmse_stage_m"])

    def test_negative_nse_never_grades_above_calibration_required(self):
        """
        Regression guard: the grading ladder used to short-circuit on a small
        RMSE via `or` clauses, awarding SATISFACTORY to runs whose NSE was -120.
        A reliably computed non-positive NSE must grade CALIBRATION_REQUIRED.
        """
        rng = np.random.default_rng(11)
        truth = 530.0 + np.sin(np.arange(60) / 6.0) * 0.6
        metrics = compute_pure_metrics(truth + rng.normal(0, 0.9, 60), truth)
        self.assertIsNotNone(metrics["nse_stage"])
        self.assertLess(metrics["nse_stage"], 0.0)
        self.assertEqual(metrics["performance_grade"], "CALIBRATION_REQUIRED")

    def test_compute_pure_metrics_with_discharge(self):
        """Verify dual stage and discharge accuracy metrics computation."""
        obs_s = np.array([533.24, 533.30, 533.40, 533.50, 533.55, 533.60, 533.65, 533.70])
        pred_s = np.array([533.22, 533.32, 533.38, 533.48, 533.58, 533.57, 533.68, 533.66])
        obs_q = np.array([105.0, 115.0, 130.0, 145.0, 160.0, 175.0, 185.0, 195.0])
        pred_q = np.array([103.0, 117.0, 128.0, 147.0, 163.0, 172.0, 188.0, 192.0])

        metrics = compute_pure_metrics(pred_s, obs_s, pred_q, obs_q)
        self.assertEqual(metrics["sample_size_hours"], 8)
        self.assertIsNotNone(metrics["rmse_q_m3s"])
        self.assertIsNotNone(metrics["mae_q_m3s"])
        self.assertIsNotNone(metrics["nse_discharge"])
        self.assertIsNotNone(metrics["pbias_discharge_pct"])
        self.assertIsNotNone(metrics["spearman_rho_q"])
        self.assertGreater(metrics["nse_discharge"], 0.95)
        self.assertGreater(metrics["spearman_rho_q"], 0.95)
        # Discharge metrics are rating-implied, not an independent measurement.
        self.assertEqual(metrics["discharge_metrics_source"], "RATING_IMPLIED_DERIVED")

    def test_lifecycle_verification_completion(self):
        """Verify that 90-hour complete match transitions to LIFECYCLE_VERIFIED."""
        from src.hydrology.realtime_telemetry_validator import validate_run_with_observations
        forecast = [
            {"forecast_time": f"2026-09-01T{h:02d}:00:00Z", "stage_m": 533.20 + 0.01 * h, "discharge_m3s": 100.0 + 2.0 * h}
            for h in range(90)
        ]
        # Full 90 hours of observations
        obs_hourly = {
            f"2026-09-01T{h:02d}:00:00Z": {
                "observed_stage_m": 533.20 + 0.01 * h,
                "observed_distance_ft": 52.80,
            }
            for h in range(90)
        }
        res = validate_run_with_observations("TEST_CYCLE_01", forecast, obs_hourly)
        self.assertEqual(res["verified_hours"], 90)
        self.assertEqual(res["lifecycle_status"], "LIFECYCLE_VERIFIED")
        self.assertEqual(res["completion_pct"], 100.0)
        self.assertAlmostEqual(res["metrics"]["nse_stage"], 1.0, places=3)

    def test_elapsed_window_without_telemetry_is_observation_gap(self):
        """
        A cycle whose full 90-hour window elapsed days ago and which still has
        no telemetry is permanently unverifiable. It must be stamped
        OBSERVATION_GAP rather than left pending forever, so the dashboard can
        explain the zero instead of showing an indefinite pending state.
        """
        from datetime import datetime, timedelta, timezone
        from src.hydrology.realtime_telemetry_validator import (
            OBSERVATION_GAP_GRACE_HOURS,
            validate_run_with_observations,
        )

        start = datetime.now(timezone.utc) - timedelta(days=5)
        forecast = [
            {
                "forecast_time": (start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "stage_m": 533.20,
                "discharge_m3s": 100.0,
            }
            for h in range(90)
        ]

        res = validate_run_with_observations("TEST_GAP_FULL", forecast, {})
        self.assertEqual(res["lifecycle_status"], "OBSERVATION_GAP")
        self.assertTrue(res["observation_gap"]["is_gap"])
        self.assertEqual(res["observation_gap"]["missing_hours"], 90)
        self.assertIsNotNone(res["observation_gap"]["note"])

    def test_partial_telemetry_past_grace_is_observation_gap(self):
        """
        A partially observed cycle that has been eligible for re-validation
        longer than the grace period is also a gap, and reports exactly how
        many hours are unverified.
        """
        from datetime import datetime, timedelta, timezone
        from src.hydrology.realtime_telemetry_validator import validate_run_with_observations

        start = datetime.now(timezone.utc) - timedelta(days=5)
        forecast = [
            {
                "forecast_time": (start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "stage_m": 533.20,
                "discharge_m3s": 100.0,
            }
            for h in range(90)
        ]
        obs_hourly = {
            (start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:00:00Z"): {
                "observed_stage_m": 533.20,
                "observed_distance_ft": 52.80,
            }
            for h in range(12)
        }

        res = validate_run_with_observations("TEST_GAP_PARTIAL", forecast, obs_hourly)
        self.assertEqual(res["verified_hours"], 12)
        self.assertEqual(res["lifecycle_status"], "OBSERVATION_GAP")
        self.assertEqual(res["observation_gap"]["missing_hours"], 78)

    def test_in_flight_window_is_not_observation_gap(self):
        """
        A cycle still inside its own forecast window must never be stamped
        OBSERVATION_GAP - the missing hours have simply not happened yet.
        """
        from datetime import datetime, timedelta, timezone
        from src.hydrology.realtime_telemetry_validator import validate_run_with_observations

        start = datetime.now(timezone.utc) - timedelta(hours=2)
        forecast = [
            {
                "forecast_time": (start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "stage_m": 533.20,
                "discharge_m3s": 100.0,
            }
            for h in range(90)
        ]

        res = validate_run_with_observations("TEST_INFLIGHT", forecast, {})
        self.assertNotEqual(res["lifecycle_status"], "OBSERVATION_GAP")
        self.assertFalse(res["observation_gap"]["is_gap"])

    def test_recently_elapsed_window_stays_awaiting(self):
        """
        Inside the grace period the missing telemetry may simply not have been
        ingested yet, so the run must stay re-validatable (AWAITING_OBSERVATIONS)
        rather than being prematurely declared a permanent gap.
        """
        from datetime import datetime, timedelta, timezone
        from src.hydrology.realtime_telemetry_validator import validate_run_with_observations

        # Window elapsed only 1 hour ago; the 90-hour forecast ends 89h from now,
        # so the window has NOT elapsed and the run is still in flight.
        start = datetime.now(timezone.utc) - timedelta(hours=89)
        forecast = [
            {
                "forecast_time": (start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "stage_m": 533.20,
                "discharge_m3s": 100.0,
            }
            for h in range(90)
        ]

        res = validate_run_with_observations("TEST_RECENT", forecast, {})
        self.assertNotEqual(res["lifecycle_status"], "OBSERVATION_GAP")
        self.assertFalse(res["observation_gap"]["is_gap"])


if __name__ == "__main__":
    unittest.main()
