"""
rating_physics.py
=================
Pure cross-section geometry for the rating-curve engine.

Extracted from ``stage_converter.py`` as part of the P1 de-bloat: these helpers
depend only on NumPy — no database, files, or environment. Isolating them makes
the hydraulics independently testable (see ``tests/test_rating_physics.py``).

``stage_converter`` re-exports both names unchanged, so every existing import
and internal call site keeps working.
"""

from __future__ import annotations

import numpy as np


def wetted_properties(
    station: np.ndarray, elevation: np.ndarray, wse: float
) -> tuple[float, float]:
    """Compute wetted Area (A) and wetted Perimeter (P) via vectorized trapezoidal integration."""
    if len(station) == 0 or len(elevation) == 0 or wse <= np.min(elevation):
        return 0.0, 0.0

    d = np.maximum(wse - elevation, 0.0)
    dx = np.diff(station)
    dz = np.diff(elevation)
    d1 = d[:-1]
    d2 = d[1:]

    # Wetted Area
    a = float(np.sum(0.5 * (d1 + d2) * dx))

    # Wetted Perimeter
    wet_both = (d1 > 0) & (d2 > 0)
    wet_1 = (d1 > 0) & (d2 <= 0)
    wet_2 = (d1 <= 0) & (d2 > 0)

    hyp = np.hypot(dx, dz)
    p = float(np.sum(hyp[wet_both]))
    if np.any(wet_1):
        frac1 = d1[wet_1] / (d1[wet_1] - d2[wet_1] + 1e-12)
        p += float(np.sum(np.hypot(dx[wet_1] * frac1, dz[wet_1] * frac1)))
    if np.any(wet_2):
        frac2 = d2[wet_2] / (d2[wet_2] - d1[wet_2] + 1e-12)
        p += float(np.sum(np.hypot(dx[wet_2] * (1 - frac2), dz[wet_2] * (1 - frac2))))

    return a, p


def station_from_points(points: np.ndarray) -> np.ndarray:
    """Cumulative chainage along a surveyed cross-section."""
    north, east = points[:, 0], points[:, 1]
    return np.concatenate(
        [[0.0], np.cumsum(np.hypot(np.diff(east), np.diff(north)))]
    )
