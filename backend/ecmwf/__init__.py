"""
backend/ecmwf/__init__.py
==========================
Compatibility shim: re-exports from backend.rainfall.

The ecmwf module was renamed to backend.rainfall during the Windows Server
production alignment. This shim keeps legacy imports working.
"""

from backend.rainfall import *  # noqa: F401, F403
from backend.rainfall.open_meteo import (  # noqa: F401
    fetch_point_forecast,
    MAX_PHYSICAL_PRECIP_MM_HR,
)
from backend.rainfall.retry_utils import (  # noqa: F401
    with_retry,
    calculate_backoff,
    retry_call,
)
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
    "fetch_point_forecast",
    "MAX_PHYSICAL_PRECIP_MM_HR",
    "with_retry",
    "calculate_backoff",
    "retry_call",
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
