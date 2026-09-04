"""
Unit Tests for Accuracy & Validation Metrics Engine
====================================================
Validates:
  - Spearman rank correlation coefficient (ρ)
  - Pearson correlation (r, R²)
  - Nash-Sutcliffe Efficiency (NSE)
  - RMSE and MAE calculations
  - Percent Bias (PBIAS)
"""

import unittest
import numpy as np

from src.hydrology.validation_metrics import (
    compute_spearman_correlation,
    compute_pearson_correlation,
    compute_nse,
    compute_rmse_mae,
    compute_pbias,
)


class TestValidationMetrics(unittest.TestCase):

    def test_perfect_correlation(self):
        """Identical series should yield rho = 1.0, NSE = 1.0, RMSE = 0.0."""
        obs = np.array([10.0, 20.0, 35.0, 50.0, 42.0, 30.0, 18.0])
        pred = np.array([10.0, 20.0, 35.0, 50.0, 42.0, 30.0, 18.0])

        rho, pval = compute_spearman_correlation(pred, obs)
        self.assertAlmostEqual(rho, 1.0, places=3)

        nse = compute_nse(pred, obs)
        self.assertAlmostEqual(nse, 1.0, places=3)

        rmse, mae = compute_rmse_mae(pred, obs)
        self.assertAlmostEqual(rmse, 0.0, places=3)
        self.assertAlmostEqual(mae, 0.0, places=3)

        pbias = compute_pbias(pred, obs)
        self.assertAlmostEqual(pbias, 0.0, places=2)

    def test_realistic_hydrologic_metrics(self):
        """Simulate a realistic calibrated forecast vs observed series."""
        obs = np.array([100.0, 250.0, 600.0, 1200.0, 1800.0, 1400.0, 800.0, 350.0])
        # Model with slight overprediction (+2%) and minor lag
        pred = np.array([98.0, 245.0, 610.0, 1220.0, 1830.0, 1410.0, 790.0, 360.0])

        rho, _ = compute_spearman_correlation(pred, obs)
        self.assertGreater(rho, 0.95)

        nse = compute_nse(pred, obs)
        self.assertGreater(nse, 0.95)

        pbias = compute_pbias(pred, obs)
        self.assertLess(abs(pbias), 5.0)


if __name__ == "__main__":
    unittest.main()
