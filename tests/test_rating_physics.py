"""
tests/test_rating_physics.py
============================
Direct unit tests for ``src/hydrology/rating_physics.py`` — the pure cross-section
geometry extracted from the ``stage_converter`` monolith. No I/O, no DB.
"""

import numpy as np
import pytest

from src.hydrology.rating_physics import station_from_points, wetted_properties


def test_empty_or_dry_section_returns_zero():
    assert wetted_properties(np.array([]), np.array([]), 5.0) == (0.0, 0.0)
    # wse at/below the bed is dry
    assert wetted_properties(np.array([0.0, 10.0]), np.array([2.0, 2.0]), 2.0) == (0.0, 0.0)


def test_rectangular_channel_area_and_perimeter():
    station = np.array([0.0, 10.0])
    elevation = np.array([0.0, 0.0])
    a, p = wetted_properties(station, elevation, 2.0)
    assert a == pytest.approx(20.0)      # 2 m deep x 10 m wide
    assert p == pytest.approx(10.0)      # bed only (vertical banks not in the profile)


def test_partially_wetted_banks():
    # V-shaped valley: only the two lower banks are wet at wse=2.
    station = np.array([0.0, 5.0, 10.0])
    elevation = np.array([0.0, 5.0, 0.0])
    a, p = wetted_properties(station, elevation, 2.0)
    assert a == pytest.approx(10.0)
    assert p == pytest.approx(np.hypot(5.0, 5.0), rel=1e-6)


def test_area_is_monotonic_in_wse():
    station = np.linspace(0, 20, 11)
    elevation = np.linspace(1.0, 1.0, 11)  # flat bed at 1 m
    areas = [wetted_properties(station, elevation, w)[0] for w in (0.5, 1.0, 2.0, 3.0)]
    assert areas[0] == 0.0
    assert areas == sorted(areas)
    assert areas[1] == pytest.approx(0.0)  # wse == bed => dry


def test_station_from_points_chainage():
    points = np.array([[0.0, 0.0], [0.0, 3.0], [4.0, 3.0]])
    out = station_from_points(points)
    assert np.allclose(out, [0.0, 3.0, 7.0])


def test_station_from_single_point_is_zero():
    assert np.allclose(station_from_points(np.array([[1.0, 2.0]])), [0.0])
