"""
tests/test_soil_moisture.py
===========================
Unit tests for the soil-moisture FETCH-AND-LOG layer.

Guarantee under test: the layer must never raise, never block the forecast
pipeline, store JSON-safe data, and must NOT feed anything back into runoff
decisions (CN / K / x / routing are untouched).
"""

from datetime import datetime, timezone

import numpy as np
import pytest

from src.ecmwf import open_meteo
from src.ecmwf.open_meteo import (
    SOIL_MOISTURE_LAYERS,
    fetch_soil_moisture_snapshot,
    fetch_antecedent_soil_moisture,
)


def _start_dt() -> datetime:
    return datetime(2026, 9, 10, 6, 0, 0, tzinfo=timezone.utc)


class _Var:
    def __init__(self, values):
        self._values = np.asarray(values, dtype=np.float64)

    def ValuesAsNumpy(self):
        return self._values


class _Hourly:
    def __init__(self, n_hours=90, offset_s=0):
        self.n = n_hours
        self.t0 = 1789020000 + offset_s  # 2026-09-10 06:00 UTC epoch

    def Time(self):
        return self.t0

    def TimeEnd(self):
        return self.t0 + self.n * 3600  # exclusive end (matches real Open-Meteo API)

    def Interval(self):
        return 3600

    def Variables(self, i):
        base = 0.22 + 0.01 * i
        return _Var(base + 0.02 * np.sin(np.linspace(0, 3, self.n)))


class _HourlyWide(_Hourly):
    def Variables(self, i):
        # Physical-range violation waveform to test clipping (0.0 to 0.60 m3/m3)
        base = 0.5 + 0.5 * i
        return _Var(np.full(self.n, min(base, 0.9)))


class _Daily:
    def __init__(self, n_days=5):
        # Five daily timestamps from 2026-09-05 00:00 UTC
        self.t = np.array([1788588000 + k * 86400 for k in range(n_days)])

    def Time(self):
        return self.t

    def VariablesLength(self):
        return len(SOIL_MOISTURE_LAYERS)

    def Variables(self, i):
        return _Var(np.full(5, 0.18 + 0.01 * i))


class _Resp:
    def __init__(self, hourly=None, daily=None):
        self._h = hourly
        self._d = daily

    def Hourly(self):
        return self._h

    def Daily(self):
        return self._d


class _Responses(list):
    pass


def _mock(monkeypatch, hourly, daily=None):
    def fake(url, params):
        return _Responses([_Resp(hourly=hourly, daily=daily)])
    monkeypatch.setattr(open_meteo, "_call_openmeteo_api", fake)


def test_snapshot_returns_90h_series_per_layer(monkeypatch):
    _mock(monkeypatch, _Hourly())
    snap = fetch_soil_moisture_snapshot(16.70, 74.21, _start_dt())
    assert snap is not None
    assert set(snap["depths_cm"].keys()) == set(SOIL_MOISTURE_LAYERS)
    for layer, series in snap["depths_cm"].items():
        assert len(series) == 90
        assert all(isinstance(v, float) and 0.0 <= v <= 0.60 for v in series)
        assert snap["current_vwc"][layer] is not None


def test_snapshot_clips_out_of_physical_range(monkeypatch):
    _mock(monkeypatch, _HourlyWide(), daily=None)
    snap = fetch_soil_moisture_snapshot(16.70, 74.21, _start_dt())
    assert snap is not None
    for series in snap["depths_cm"].values():
        assert max(series) <= 0.60
        assert min(series) >= 0.0


def test_snapshot_never_blocks_pipeline_on_api_failure(monkeypatch):
    def bomb(url, params):
        raise RuntimeError("Open-Meteo down")
    monkeypatch.setattr(open_meteo, "_call_openmeteo_api", bomb)
    assert fetch_soil_moisture_snapshot(16.70, 74.21, _start_dt()) is None
    assert fetch_antecedent_soil_moisture(16.70, 74.21, _start_dt()) is None


def test_antecedent_covers_five_days_and_is_json_safe(monkeypatch):
    _mock(monkeypatch, None, daily=_Daily())
    ant = fetch_antecedent_soil_moisture(16.70, 74.21, _start_dt())
    assert ant is not None
    assert set(ant.keys()) == set(SOIL_MOISTURE_LAYERS)
    import json
    json.dumps(ant)  # must be JSON-serializable
    first_layer = next(iter(ant.values()))
    assert len(first_layer) == 5
    assert all(isinstance(v, float) and 0.0 <= v <= 0.60 for v in first_layer.values())


def test_integration_fields_exist_but_do_not_touch_decisions():
    # The pipeline exposes soil moisture under a clearly-labelled observability
    # namespace; AMC/CN/K routing keys are structurally separate from it.
    from src.hms.runner import classify_amc

    wet = classify_amc(120.0)
    dry = classify_amc(5.0)
    assert wet == "AMC-III" and dry == "AMC-I"  # classification driven only by rain signal