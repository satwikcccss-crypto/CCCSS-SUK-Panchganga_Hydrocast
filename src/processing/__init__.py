"""Compatibility shim: re-export backend.processing and related public names."""

from backend.processing import *  # noqa: F401,F403
from backend.processing.gauge_fetcher import *  # noqa: F401,F403
from backend.rainfall.station_selector import *  # noqa: F401,F403

__all__ = ["gauge_fetcher", "station_selector"]
