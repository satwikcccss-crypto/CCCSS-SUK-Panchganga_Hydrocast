"""
tests/test_qc_pipeline.py
=========================
Quality control & robustness tests cross-checking meteorological ingestion,
physical bounds sanitization, and pipeline telemetry integrity.
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd

from src.ecmwf.open_meteo import fetch_point_forecast, MAX_PHYSICAL_PRECIP_MM_HR
from src.alerts.evaluator import _get_bridge_metadata, evaluate_and_notify


class TestQualityControlPipeline(unittest.TestCase):

    @patch("src.ecmwf.open_meteo._call_openmeteo_api")
    def test_precip_nan_and_inf_sanitization(self, mock_api):
        """Verify NaNs, Infs, and negative rainfall are sanitized into valid physical bounds."""
        mock_response = MagicMock()
        mock_hourly = MagicMock()
        
        # 96 raw hours including NaN, Inf, and negative values
        raw_vals = np.array([5.0, np.nan, -2.5, np.inf, 12.0] + [1.0] * 91)
        mock_hourly.Variables.return_value.ValuesAsNumpy.return_value = raw_vals
        mock_hourly.Time.return_value = 1757462400  # epoch
        mock_hourly.TimeEnd.return_value = 1757462400 + (96 * 3600)
        mock_hourly.Interval.return_value = 3600
        mock_response.Hourly.return_value = mock_hourly
        mock_api.return_value = [mock_response]

        start_dt = datetime.fromtimestamp(1757462400, tz=timezone.utc)
        arr = fetch_point_forecast(16.70, 74.24, start_dt)

        self.assertEqual(len(arr), 90)
        self.assertFalse(np.isnan(arr).any())
        self.assertFalse(np.isinf(arr).any())
        self.assertTrue((arr >= 0.0).all())
        # The NaN should have become 0.0
        self.assertEqual(arr[1], 0.0)
        # The -2.5 should have become 0.0
        self.assertEqual(arr[2], 0.0)
        # The inf should have been capped to MAX_PHYSICAL_PRECIP_MM_HR
        self.assertEqual(arr[3], MAX_PHYSICAL_PRECIP_MM_HR)

    @patch("src.ecmwf.open_meteo._call_openmeteo_api")
    def test_precip_anomaly_ceiling_capping(self, mock_api):
        """Verify unphysical sensor spikes (> 250 mm/hr) are safely capped."""
        mock_response = MagicMock()
        mock_hourly = MagicMock()
        
        raw_vals = np.array([500.0] * 96)  # Unphysical 500 mm/hr
        mock_hourly.Variables.return_value.ValuesAsNumpy.return_value = raw_vals
        mock_hourly.Time.return_value = 1757462400
        mock_hourly.TimeEnd.return_value = 1757462400 + (96 * 3600)
        mock_hourly.Interval.return_value = 3600
        mock_response.Hourly.return_value = mock_hourly
        mock_api.return_value = [mock_response]

        start_dt = datetime.fromtimestamp(1757462400, tz=timezone.utc)
        arr = fetch_point_forecast(16.70, 74.24, start_dt)

        self.assertTrue((arr <= MAX_PHYSICAL_PRECIP_MM_HR).all())
        self.assertEqual(arr[0], MAX_PHYSICAL_PRECIP_MM_HR)

    @patch("src.ecmwf.open_meteo._call_openmeteo_api", side_effect=Exception("Connection reset"))
    def test_automated_physical_fallback_on_failure(self, mock_api):
        """Verify fallback generates a smooth, physically bounded diurnal hydrograph."""
        start_dt = datetime(2026, 9, 10, 6, 0, 0, tzinfo=timezone.utc)
        arr = fetch_point_forecast(16.70, 74.24, start_dt)

        self.assertEqual(len(arr), 90)
        self.assertTrue((arr >= 0.0).all())
        self.assertTrue((arr <= 50.0).all())
        self.assertGreater(float(np.max(arr)), 0.0)

    def test_bridge_metadata_defaults(self):
        """Verify bridge metadata fallback contains correct CWC warning & danger marks."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None  # Force default fallback
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        meta = _get_bridge_metadata(mock_conn, "SHIVAJI_BRIDGE")
        self.assertEqual(meta["warning"], 542.70)
        self.assertEqual(meta["danger"], 543.30)
        self.assertEqual(meta["hfl"], 545.33)

        rajaram_meta = _get_bridge_metadata(mock_conn, "RAJARAM_BRIDGE")
        self.assertEqual(rajaram_meta["warning"], 542.07)
        self.assertEqual(rajaram_meta["danger"], 543.30)


if __name__ == "__main__":
    unittest.main()
