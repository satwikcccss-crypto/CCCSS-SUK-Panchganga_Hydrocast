"""
tests/test_telemetry_metrics.py
===============================
Direct tests for the pure telemetry core extracted from the 852-line
``realtime_telemetry_validator`` monolith. No network, cache, or DB.
"""

from datetime import datetime, timezone

import numpy as np

from src.hydrology import realtime_telemetry_validator as v
from src.hydrology import telemetry_metrics as t


def test_reexports_are_the_same_objects():
    # The monolith must re-export the moved functions, not shadow them.
    assert v.compute_pure_metrics is t.compute_pure_metrics
    assert v.resample_feeds_hourly is t.resample_feeds_hourly
    assert v.parse_cycle_time is t.parse_cycle_time
    assert v.SHIVAJI_DATUM_MSL == t.SHIVAJI_DATUM_MSL


def test_parse_cycle_time_valid():
    dt = t.parse_cycle_time("CYC_20260822_06z")
    assert dt == datetime(2026, 8, 22, 6, tzinfo=timezone.utc)


def test_parse_cycle_time_invalid_returns_none():
    assert t.parse_cycle_time("not-a-cycle") is None
    assert t.parse_cycle_time("CYC_2026_06z") is None


def test_compute_pure_metrics_empty_is_insufficient():
    m = t.compute_pure_metrics(np.array([]), np.array([]))
    assert m["status"] == "INSUFFICIENT_DATA"
    assert m["sample_size_hours"] == 0
    assert m["rmse_stage_m"] is None
    assert m["nse_stage"] is None


def test_compute_pure_metrics_short_window_is_accumulating():
    pred = np.array([1.0, 2.0, 3.0])
    obs = np.array([1.1, 1.9, 3.2])
    m = t.compute_pure_metrics(pred, obs)
    # 3 < MIN_CORRELATION_SAMPLES => skill metrics withheld, errors reported.
    assert m["status"] == "ACCUMULATING_TELEMETRY"
    assert m["skill_metrics_reliable"] is False
    assert m["rmse_stage_m"] is not None
    assert m["nse_stage"] is None


def test_resample_feeds_filters_outliers_and_bins_hourly():
    feeds = [
        {"created_at": "2026-08-22T06:05:00Z", "field1": "40.0"},
        {"created_at": "2026-08-22T06:35:00Z", "field1": "42.0"},
        {"created_at": "2026-08-22T06:40:00Z", "field1": "5.0"},   # outlier (<15 ft)
        {"created_at": "2026-08-22T06:45:00Z", "field1": "200.0"}, # outlier (>80 ft)
        {"created_at": "bad", "field1": "40.0"},                    # unparseable
    ]
    out = t.resample_feeds_hourly(feeds, datum_msl=549.35)
    assert list(out) == ["2026-08-22T06:00:00Z"]
    row = out["2026-08-22T06:00:00Z"]
    assert row["sample_count"] == 2
    assert row["observed_distance_ft"] == 41.0
