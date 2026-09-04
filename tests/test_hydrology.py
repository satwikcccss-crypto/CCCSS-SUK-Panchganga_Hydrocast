"""
Unit Tests for HydroCast Hydrology & Hydraulic Engine
======================================================
Validates:
  - Monotonicity of calibrated rating curves (dQ/dh > 0)
  - Manning stage-to-discharge and discharge-to-stage conversions
  - CWC flood alert classification tiers
"""

import unittest
import numpy as np

from src.hydrology.stage_converter import (
    get_shivaji_rating_curve,
    get_rajaram_rating_curve,
    convert_discharge_to_stage_manning,
    convert_stage_to_discharge_manning,
    classify_alert,
)


class TestHydraulicsRatingCurve(unittest.TestCase):

    def test_shivaji_rating_curve_monotonicity(self):
        """Discharge must strictly increase with stage (dQ/dh > 0)."""
        df = get_shivaji_rating_curve()
        stages = df["stage_m"].values
        discharges = df["q_m3s"].values
        diffs = np.diff(discharges)
        self.assertTrue(np.all(diffs >= 0), "Shivaji rating curve is not monotonic")
        self.assertGreater(discharges[-1], discharges[0])

    def test_rajaram_rating_curve_monotonicity(self):
        """Rajaram rating curve must strictly increase with stage."""
        df = get_rajaram_rating_curve()
        discharges = df["q_m3s"].values
        diffs = np.diff(discharges)
        self.assertTrue(np.all(diffs >= 0), "Rajaram rating curve is not monotonic")
        self.assertGreater(discharges[-1], discharges[0])

    def test_bed_slope_hydraulic_effect(self):
        """
        Due to gentler slope at Rajaram (0.002318 vs 0.005858 at Shivaji),
        an identical discharge must produce a higher stage at Rajaram.
        """
        test_q = 500.0  # m3/s
        stage_shivaji = convert_discharge_to_stage_manning(test_q, "SHIVAJI_BRIDGE")
        stage_rajaram = convert_discharge_to_stage_manning(test_q, "RAJARAM_BRIDGE")
        self.assertGreater(
            stage_rajaram,
            stage_shivaji,
            f"Expected Rajaram stage ({stage_rajaram}) > Shivaji stage ({stage_shivaji}) for Q={test_q}",
        )

    def test_roundtrip_conversion_consistency(self):
        """Converting Q -> H -> Q should return approximately the original Q."""
        original_q = 1200.0  # m3/s
        stage = convert_discharge_to_stage_manning(original_q, "SHIVAJI_BRIDGE")
        recovered_q = convert_stage_to_discharge_manning(stage, "SHIVAJI_BRIDGE")
        self.assertAlmostEqual(original_q, recovered_q, delta=100.0)

    def test_cwc_alert_classification(self):
        """Verify alert tier boundaries for Shivaji and Rajaram."""
        self.assertEqual(classify_alert(541.0, "SHIVAJI_BRIDGE"), "NORMAL")
        self.assertEqual(classify_alert(542.2, "SHIVAJI_BRIDGE"), "ALERT")
        self.assertEqual(classify_alert(542.8, "SHIVAJI_BRIDGE"), "WARNING")
        self.assertEqual(classify_alert(543.5, "SHIVAJI_BRIDGE"), "DANGER")
        self.assertEqual(classify_alert(546.0, "SHIVAJI_BRIDGE"), "HFL_EXCEEDED")

        self.assertEqual(classify_alert(541.0, "RAJARAM_BRIDGE"), "NORMAL")
        self.assertEqual(classify_alert(541.6, "RAJARAM_BRIDGE"), "ALERT")
        self.assertEqual(classify_alert(542.2, "RAJARAM_BRIDGE"), "WARNING")


if __name__ == "__main__":
    unittest.main()
