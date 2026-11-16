"""Regression tests for backend.spatial.hand_inundation.

The module shipped with a missing ``numpy`` import and a ``src_cr`` typo that
made every reprojection silently fall back to raw projected coordinates. These
tests pin the contract that a server without the optional geospatial stack gets
a clean ``available: false`` instead of a traceback.
"""

from __future__ import annotations

import inspect

import pytest

from backend.spatial import hand_inundation


def test_numpy_is_imported():
    assert hand_inundation.np is not None


def test_missing_raster_reports_unavailable(tmp_path):
    missing = tmp_path / "does-not-exist.tif"
    result = hand_inundation.compute_hand_inundation(540.0, str(missing))

    assert result["available"] is False
    assert "not found" in result["reason"].lower()


def test_unconfigured_raster_reports_unavailable(monkeypatch):
    monkeypatch.setattr(hand_inundation, "HAND_RASTER_PATH", None)
    result = hand_inundation.compute_hand_inundation(540.0, None)

    assert result["available"] is False
    assert "HAND_RASTER_PATH" in result["reason"]


def test_transform_helper_handles_missing_crs():
    geom = {"type": "Point", "coordinates": [1.0, 2.0]}
    assert hand_inundation._transform_geom_to_wgs84(geom, None) == geom


def test_cell_size_returns_none_without_crs():
    class Transform:
        a = 30.0
        e = -30.0

    assert hand_inundation._cell_size_metres(None, Transform()) is None


def test_public_signature_is_stable():
    signature = inspect.signature(hand_inundation.compute_hand_inundation)
    assert list(signature.parameters) == [
        "stage_m",
        "hand_raster_path",
        "max_polygons",
        "simplify_tolerance_m",
    ]


@pytest.mark.skipif(
    not (hand_inundation._HAS_RASTERIO and hand_inundation._HAS_NUMPY),
    reason="optional geospatial stack not installed",
)
def test_synthetic_raster_classifies_depth(tmp_path):
    """End-to-end check when rasterio is available (skipped otherwise)."""
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    path = tmp_path / "hand.tif"
    data = np.array([[0.0, 0.4], [1.0, 2.0]], dtype="float32")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs="EPSG:32643",
        transform=from_origin(500000, 1800000, 30, 30),
    ) as dst:
        dst.write(data, 1)

    result = hand_inundation.compute_hand_inundation(2.5, str(path))

    assert result["available"] is True
    severities = {f["properties"]["severity"] for f in result["features"]}
    assert "severe" in severities
    assert result["truncated"] is False
