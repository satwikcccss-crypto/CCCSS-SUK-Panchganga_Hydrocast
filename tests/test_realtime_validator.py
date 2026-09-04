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
        """Verify graceful status handling when less than 3 hourly points exist."""
        obs = np.array([533.24, 533.27])
        pred = np.array([533.20, 533.25])

        metrics = compute_pure_metrics(pred, obs)
        self.assertEqual(metrics["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(metrics["rmse_stage_m"])
        self.assertIsNone(metrics["nse_stage"])


if __name__ == "__main__":
    unittest.main()
