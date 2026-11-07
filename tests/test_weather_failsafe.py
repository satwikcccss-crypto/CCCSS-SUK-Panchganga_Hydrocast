"""
tests/test_weather_failsafe.py
==============================
Unit tests for the multi-tier weather failsafe engine.
"""

from datetime import datetime, timezone
import pytest
from backend.rainfall.open_meteo_failsafe import (
    fetch_tier2_predecessor_cache,
    fetch_tier3_climatology,
    get_weather_failsafe,
    CLIMATOLOGICAL_HOURLY_BASELINES,
)


def test_tier3_climatology_fallback():
    """Verify that Tier 3 climatology produces valid 90-hr precipitation series for all stations."""
    now = datetime.now(timezone.utc)
    res = fetch_tier3_climatology(now)

    assert res["tier"] == "tier3_climatology_baseline"
    assert res["lead_hours"] == 90
    assert len(res["stations"]) >= 12

    # Check that Karveer (S1) and Gaganbawda (S6) have non-negative rainfall
    assert "KARVEER" in res["stations"]
    assert "GAGANBAWDA" in res["stations"]

    p_karveer = res["stations"]["KARVEER"]["precipitation_mm_hr"]
    p_gaganbawda = res["stations"]["GAGANBAWDA"]["precipitation_mm_hr"]

    assert len(p_karveer) == 90
    assert len(p_gaganbawda) == 90
    assert all(p >= 0.0 for p in p_karveer)
    assert all(p >= 0.0 for p in p_gaganbawda)

    # Gaganbawda (orographic crest) should have higher mean intensity than Karveer (valley)
    assert sum(p_gaganbawda) > sum(p_karveer)


def test_master_failsafe_always_returns_valid_weather():
    """Verify that get_weather_failsafe never raises an exception and always returns 90h weather."""
    now = datetime.now(timezone.utc)
    res = get_weather_failsafe(now)

    assert res is not None
    assert "stations" in res
    assert "lead_hours" in res
    assert res["lead_hours"] == 90
    assert res["tier"] in ("tier1_live_api", "tier2_predecessor_extrapolated", "tier3_climatology_baseline")

