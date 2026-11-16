"""HAND (Height Above Nearest Drainage) 2D inundation engine.

Given a water stage (metres above MSL) and a HAND raster, returns a GeoJSON
FeatureCollection of flooded areas classified by depth:

===========  =========================
Class        Depth
===========  =========================
``minor``    ``0 < depth <= 0.5 m``
``moderate`` ``0.5 < depth <= 1.5 m``
``severe``   ``depth > 1.5 m``
===========  =========================

Depth model: ``D(x, y) = max(0, stage_m - HAND(x, y))``.

The engine is **optional-dependency tolerant**. ``rasterio``, ``shapely`` and
``pyproj`` are not in ``requirements.txt``; when they are absent — or when
``HAND_RASTER_PATH`` is unset — :func:`compute_hand_inundation` returns
``{"available": False, "reason": ...}`` instead of raising. Callers can expose
that verbatim.

Environment
-----------
``HAND_RASTER_PATH``
    Path to the Panchganga 30 m HAND GeoTIFF (EPSG:4326 or a projected CRS).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

# ── Optional dependency guards ─────────────────────────────────────────────
_HAS_NUMPY = False
_HAS_RASTERIO = False
_HAS_SHAPELY = False
_HAS_PYPROJ = False

try:  # numpy is a hard requirement of the backend, but keep this module importable
    import numpy as np

    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]

try:
    import rasterio
    from rasterio import features as rasterio_features
    from rasterio.errors import RasterioError

    _RASTERIO_ERRORS: tuple = (RasterioError, OSError, ValueError)
    _HAS_RASTERIO = True
except ImportError:  # pragma: no cover
    rasterio = None  # type: ignore[assignment]
    rasterio_features = None  # type: ignore[assignment]
    _RASTERIO_ERRORS = (OSError, ValueError)

try:
    from shapely.geometry import mapping, shape
    from shapely.ops import transform as shapely_transform

    _HAS_SHAPELY = True
except ImportError:  # pragma: no cover
    shape = None  # type: ignore[assignment]
    mapping = None  # type: ignore[assignment]
    shapely_transform = None  # type: ignore[assignment]

try:
    from pyproj import CRS, Transformer

    _HAS_PYPROJ = True
except ImportError:  # pragma: no cover
    CRS = None  # type: ignore[assignment]
    Transformer = None  # type: ignore[assignment]

# ── Configuration ──────────────────────────────────────────────────────────
HAND_RASTER_PATH: Optional[str] = os.getenv("HAND_RASTER_PATH")

# Bound the response: a 30 m basin raster can yield thousands of polygons.
DEFAULT_MAX_POLYGONS = int(os.getenv("HAND_MAX_POLYGONS", "200"))

if HAND_RASTER_PATH:
    log.info("HAND raster configured: %s", HAND_RASTER_PATH)
else:
    log.debug("HAND_RASTER_PATH not set — HAND inundation will report unavailable")


# ── Helpers ────────────────────────────────────────────────────────────────
def _crs_from_dataset(dataset: Any) -> Optional[Any]:
    """Return the dataset CRS as a ``pyproj.CRS``, or ``None``."""
    if not _HAS_PYPROJ or dataset.crs is None:
        return None
    try:
        return CRS.from_user_input(dataset.crs.to_string())
    except Exception as exc:  # pragma: no cover - malformed GeoTIFF metadata
        log.warning("Could not parse raster CRS: %s", exc)
        return None


def _cell_size_metres(src_crs: Optional[Any], transform: Any) -> Optional[float]:
    """Cell size in metres for projected CRSs; ``None`` for geographic ones."""
    if src_crs is None:
        return None
    try:
        if not src_crs.is_projected:
            return None
        unit = (src_crs.axis_info[0].unit_name or "").lower()
        if "metre" not in unit and "meter" not in unit:
            return None
        area = abs(float(transform.a) * float(transform.e))
        return round(area**0.5, 2) if area > 0 else None
    except Exception:  # pragma: no cover - exotic CRS metadata
        return None


def _transform_geom_to_wgs84(geom: Dict[str, Any], src_crs: Optional[Any]) -> Dict[str, Any]:
    """Reproject a GeoJSON geometry to WGS84 (EPSG:4326).

    Returns the geometry unchanged when reprojection is impossible; the caller
    reports the source CRS so consumers can tell the difference.
    """
    if not (_HAS_PYPROJ and _HAS_SHAPELY) or src_crs is None:
        return geom
    try:
        if src_crs.to_epsg() == 4326:
            return geom
        transformer = Transformer.from_crs(src_crs, CRS.from_epsg(4326), always_xy=True)

        def _project(x, y, z=None):
            px, py = transformer.transform(x, y)
            return (px, py) if z is None else (px, py, z)

        return mapping(shapely_transform(_project, shape(geom)))
    except Exception as exc:
        log.warning("Geometry reprojection failed, returning source CRS geometry: %s", exc)
        return geom


def _polygon_max_depth(
    geom: Dict[str, Any],
    depth: Any,
    transform: Any,
) -> float:
    """Maximum flood depth (m) inside *geom*."""
    if not (_HAS_RASTERIO and _HAS_NUMPY):
        return 0.0
    try:
        inside = ~rasterio_features.geometry_mask(
            [geom], out_shape=depth.shape, transform=transform, invert=False
        )
        values = depth[inside]
        values = values[np.isfinite(values)]
        return float(values.max()) if values.size else 0.0
    except Exception:  # pragma: no cover - defensive
        return 0.0


# ── Public API ─────────────────────────────────────────────────────────────
def compute_hand_inundation(
    stage_m: float,
    hand_raster_path: Optional[str] = None,
    *,
    max_polygons: int = DEFAULT_MAX_POLYGONS,
    simplify_tolerance_m: Optional[float] = None,
) -> Dict[str, Any]:
    """Compute HAND-based inundation polygons for a given water stage.

    Parameters
    ----------
    stage_m:
        Water surface elevation in metres above mean sea level.
    hand_raster_path:
        HAND GeoTIFF path. Defaults to ``HAND_RASTER_PATH``.
    max_polygons:
        Hard cap on returned features (``0`` disables the cap). When the cap is
        reached the response carries ``"truncated": True``.
    simplify_tolerance_m:
        Optional Douglas–Peucker tolerance in metres (only with Shapely).

    Returns
    -------
    dict
        ``{"available": True, "features": [...], ...}`` on success, otherwise
        ``{"available": False, "reason": "..."}``.
    """
    raster_path = hand_raster_path or HAND_RASTER_PATH
    if not raster_path:
        return {
            "available": False,
            "reason": "HAND_RASTER_PATH is not configured and no path was supplied",
        }

    if not os.path.exists(raster_path):
        return {"available": False, "reason": f"HAND raster not found: {raster_path}"}

    if not (_HAS_RASTERIO and _HAS_NUMPY):
        missing = []
        if not _HAS_RASTERIO:
            missing.append("rasterio")
        if not _HAS_NUMPY:
            missing.append("numpy")
        return {
            "available": False,
            "reason": f"Missing optional dependencies: {', '.join(missing)}",
        }

    try:
        with rasterio.open(raster_path) as src:
            src_crs = _crs_from_dataset(src)
            hand = src.read(1).astype("float32")
            transform = src.transform

            if src.nodata is not None:
                hand[hand == np.float32(src.nodata)] = np.nan

            valid = np.isfinite(hand)
            if not valid.any():
                return {"available": False, "reason": "HAND raster contains no valid cells"}

            # Depth = stage - HAND, floored at zero.
            depth = np.zeros_like(hand, dtype="float32")
            depth[valid] = np.maximum(0.0, float(stage_m) - hand[valid])

            classes = (
                ("minor", (depth > 0.0) & (depth <= 0.5)),
                ("moderate", (depth > 0.5) & (depth <= 1.5)),
                ("severe", depth > 1.5),
            )

            features_list: List[Dict[str, Any]] = []
            truncated = False
            seen = 0

            for class_name, class_mask in classes:
                combined = class_mask & valid
                if not combined.any():
                    continue

                for geom_dict, _ in rasterio_features.shapes(
                    combined.astype("uint8"),
                    mask=combined,
                    transform=transform,
                    connectivity=4,
                ):
                    if max_polygons and seen >= max_polygons:
                        truncated = True
                        break
                    seen += 1

                    depth_m = _polygon_max_depth(geom_dict, depth, transform)

                    if simplify_tolerance_m and _HAS_SHAPELY:
                        try:
                            geom_dict = mapping(
                                shape(geom_dict).simplify(
                                    simplify_tolerance_m, preserve_topology=True
                                )
                            )
                        except Exception:  # pragma: no cover - geometry edge case
                            pass

                    output_geom = _transform_geom_to_wgs84(geom_dict, src_crs)

                    features_list.append(
                        {
                            "type": "Feature",
                            "geometry": output_geom,
                            "properties": {
                                "severity": class_name,
                                "class": class_name,
                                "depth_m": round(depth_m, 3),
                            },
                        }
                    )

                if truncated:
                    break

            return {
                "available": True,
                "features": features_list,
                "stage_m": float(stage_m),
                "raster_path": raster_path,
                "crs": src_crs.to_epsg() if src_crs is not None else None,
                "resolution_m": _cell_size_metres(src_crs, transform),
                "polygon_count": len(features_list),
                "truncated": truncated,
            }

    except _RASTERIO_ERRORS as exc:
        log.error("Could not read HAND raster %s: %s", raster_path, exc)
        return {"available": False, "reason": f"Could not read HAND raster: {exc}"}
    except Exception as exc:  # pragma: no cover - defensive
        log.exception("Unexpected error in HAND inundation")
        return {"available": False, "reason": f"Unexpected error: {exc}"}
