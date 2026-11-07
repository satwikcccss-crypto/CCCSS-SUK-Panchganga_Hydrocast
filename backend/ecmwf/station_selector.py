"""
backend/ecmwf/station_selector.py
==================================
Compatibility shim: re-exports from backend.rainfall.station_selector.
"""

from backend.rainfall.station_selector import (  # noqa: F401
    STATION_REGISTRY,
    select_active_subbasin_gages,
    SUBBASIN_AREAS_KM2,
    load_stations,
    select_stations,
    store_selection,
    interpolate_ecmwf_to_station,
    fetch_observed_gauge_ts,
    RainStation,
    SubbasinRainfall,
)

__all__ = [
    "STATION_REGISTRY",
    "select_active_subbasin_gages",
    "SUBBASIN_AREAS_KM2",
    "load_stations",
    "select_stations",
    "store_selection",
    "interpolate_ecmwf_to_station",
    "fetch_observed_gauge_ts",
    "RainStation",
    "SubbasinRainfall",
]
