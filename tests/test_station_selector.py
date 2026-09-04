"""
Unit Tests for Station Selection & Catchment Topology
=====================================================
Validates:
  - Station registry completeness (Primary & Alternate stations)
  - Subbasin area coverage (S1 to S9)
  - Haversine distance calculations
  - Conservative maximum rainfall selection logic
"""

import unittest
from src.ecmwf.station_selector import (
    STATION_REGISTRY,
    SUBBASIN_AREAS_KM2,
    haversine_km,
    select_active_subbasin_gages,
)


class TestStationSelector(unittest.TestCase):

    def test_station_registry_coverage(self):
        """Must cover all 9 Panchganga subbasins (S1 to S9)."""
        registered_subbasins = {st.subbasin for st in STATION_REGISTRY}
        expected_subbasins = {f"S{i}" for i in range(1, 10)}
        self.assertTrue(expected_subbasins.issubset(registered_subbasins))
        self.assertGreaterEqual(len(STATION_REGISTRY), 9)

    def test_subbasin_areas_consistency(self):
        """Check all subbasins have defined catchment areas."""
        for i in range(1, 10):
            sub_id = f"S{i}"
            self.assertIn(sub_id, SUBBASIN_AREAS_KM2)
            self.assertGreater(SUBBASIN_AREAS_KM2[sub_id], 0.0)

    def test_haversine_distance(self):
        """Test distance between known points."""
        # Distance between identical points should be 0
        d_zero = haversine_km(16.706, 74.248, 16.706, 74.248)
        self.assertAlmostEqual(d_zero, 0.0, places=2)

        # Distance between Karveer and Radhanagari (~40 km)
        d_dist = haversine_km(16.706, 74.248, 16.410, 73.997)
        self.assertGreater(d_dist, 25.0)
        self.assertLess(d_dist, 60.0)

    def test_conservative_max_rain_selection(self):
        """Dynamic selection must pick the station with highest rainfall in a subbasin."""
        # Mock 90-hr cumulative rainfall
        rainfall_mock = {
            "KARVEER": 150.0,
            "SANGARUL": 220.0,
            "KOTOLI": 180.0,
            "KARANJPHEN": 290.0,
            "PADASALI": 310.0,
            "GAGANBAWDA": 450.0,
            "GARIVADE": 260.0,
            "BEED": 140.0,
            "RADHANAGARI": 380.0,
        }
        selections = select_active_subbasin_gages(rainfall_mock)
        self.assertEqual(len(selections), 9)
        self.assertEqual(selections["S6"]["selected_station_id"], "GAGANBAWDA")
        self.assertEqual(selections["S6"]["cumulative_mm"], 450.0)


if __name__ == "__main__":
    unittest.main()
