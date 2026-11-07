"""
backend/ecmwf/open_meteo.py
============================
Compatibility shim: re-exports from backend.rainfall.open_meteo.
"""

from backend.rainfall.open_meteo import (  # noqa: F401
    fetch_point_forecast,
    MAX_PHYSICAL_PRECIP_MM_HR,
)

__all__ = ["fetch_point_forecast", "MAX_PHYSICAL_PRECIP_MM_HR"]
