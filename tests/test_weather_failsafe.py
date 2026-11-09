"""
tests/test_weather_failsafe.py
==============================
Unit tests for the live-first weather retrieval and failsafe engine.
"""

from datetime import datetime, timezone
from unittest.mock import patch
import pytest

from backend.rainfall.open_meteo_failsafe import (
    STATIONS_MAP,
    FORECAST_HOURS,
    fetch_tier1_open_meteo,
    get_weather_failsafe,
    WeatherDataUnavailable,
)


def test_station_registry_geometry():
    """Verify that all stations are registered with valid coordinates and subbasins."""
    assert len(STATIONS_MAP) >= 12
    for st_id, info in STATIONS_MAP.items():
        assert "lat" in info and "lon" in info
        assert "subbasin" in info
        assert 15.5 <= info["lat"] <= 17.5
        assert 73.5 <= info["lon"] <= 75.0


def test_master_failsafe_degraded_fallback():
    """Verify that get_weather_failsafe returns a well-formed degraded payload when live API fails."""
    now = datetime.now(timezone.utc)
    with patch("backend.rainfall.open_meteo_failsafe.fetch_tier1_open_meteo", return_value=None):
        res = get_weather_failsafe(now)

    assert res is not None
    assert res["is_live"] is False
    assert res["tier"] == "tier1_failed"
    assert "provenance" in res
    assert "warning" in res
    assert res["provenance"]["tier"] == "tier1_failed"


def test_master_failsafe_live_success():
    """Verify that get_weather_failsafe passes through live API results correctly."""
    now = datetime.now(timezone.utc)
    mock_payload = {
        "tier": "tier1_live_api",
        "is_live": True,
        "timestamp_utc": now.isoformat(),
        "run_dt": now.isoformat(),
        "stations": {
            "KARVEER": {
                "precipitation_mm_hr": [1.0] * FORECAST_HOURS,
                "temperature_c": [24.0] * FORECAST_HOURS,
                "relative_humidity_pct": [75.0] * FORECAST_HOURS,
            }
        },
        "lead_hours": FORECAST_HOURS,
        "provenance": {"tier": "tier1_live_api", "is_live": True},
        "error": None,
    }

    with patch("backend.rainfall.open_meteo_failsafe.fetch_tier1_open_meteo", return_value=mock_payload):
        res = get_weather_failsafe(now)

    assert res is not None
    assert res["is_live"] is True
    assert res["tier"] == "tier1_live_api"
    assert "KARVEER" in res["stations"]
    assert len(res["stations"]["KARVEER"]["precipitation_mm_hr"]) == FORECAST_HOURS
