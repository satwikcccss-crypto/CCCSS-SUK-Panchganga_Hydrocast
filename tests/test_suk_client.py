"""
tests/test_suk_client.py
========================
Unit tests for the official SUK HydroCast client module (backend.client.suk_client).
"""

import json
from unittest.mock import MagicMock, patch
import urllib.error
import pytest

from backend.client.suk_client import (
    get_complete_forecast,
    get_peak_summary,
    get_stage_forecast,
    get_hydrograph,
    get_station_rainfall,
    get_flood_arrival_time,
)

MOCK_PAYLOAD = {
    "status": "success",
    "cycle_id": "CYC_TEST_2026",
    "issued_at": "2026-11-09T06:00:00Z",
    "summary": {
        "peak_discharge_m3s": 1250.5,
        "total_volume_mcm": 45.2,
        "lead_hours_to_peak": 18,
        "alert_level": "WARNING",
        "peak_arrival": {
            "shivaji": {
                "site_id": "SHIVAJI_BRIDGE",
                "peak_arrival_time": "2026-11-10T00:00:00Z",
                "peak_stage_m": 542.85,
            },
            "rajaram": {
                "site_id": "RAJARAM_BRIDGE",
                "peak_arrival_time": "2026-11-10T01:00:00Z",
                "peak_stage_m": 541.95,
            },
        },
    },
    "bridges": {
        "SHIVAJI_BRIDGE": {
            "site_id": "SHIVAJI_BRIDGE",
            "site_name": "Chhatrapati Shivaji Maharaj Bridge",
            "peak_stage_m": 542.85,
            "current_stage_m": 535.10,
            "peak_discharge_m3s": 1250.5,
            "series_90h": [
                {"lead_hours": 0, "forecast_time": "2026-11-09T06:00:00Z", "stage_m": 535.10, "discharge_m3s": 250.0, "alert_level": "NORMAL"},
                {"lead_hours": 18, "forecast_time": "2026-11-10T00:00:00Z", "stage_m": 542.85, "discharge_m3s": 1250.5, "alert_level": "WARNING"},
            ],
        },
        "RAJARAM_BRIDGE": {
            "site_id": "RAJARAM_BRIDGE",
            "site_name": "Rajaram K.T. Weir",
            "peak_stage_m": 541.95,
            "current_stage_m": 536.00,
            "peak_discharge_m3s": 1250.5,
            "series_90h": [
                {"lead_hours": 0, "forecast_time": "2026-11-09T06:00:00Z", "stage_m": 536.00, "discharge_m3s": 250.0, "alert_level": "NORMAL"},
                {"lead_hours": 19, "forecast_time": "2026-11-10T01:00:00Z", "stage_m": 541.95, "discharge_m3s": 1250.5, "alert_level": "WARNING"},
            ],
        },
    },
    "stations_rainfall": [
        {
            "station_id": "GAGANBAWDA",
            "station_name": "Gaganbawda",
            "peak_rainfall_mm_hr": 24.5,
            "peak_time": "2026-11-09T14:00:00Z",
            "cumulative_90h_mm": 185.0,
        },
        {
            "station_id": "KARVEER",
            "station_name": "Karveer",
            "peak_rainfall_mm_hr": 8.2,
            "peak_time": "2026-11-09T12:00:00Z",
            "cumulative_90h_mm": 42.0,
        },
    ],
    "outlet_hydrograph_90h": [
        {"lead_hours": 0, "discharge_m3s": 250.0, "stage_m": 535.10, "timestamp": "2026-11-09T06:00:00Z"},
        {"lead_hours": 18, "discharge_m3s": 1250.5, "stage_m": 542.85, "timestamp": "2026-11-10T00:00:00Z"},
    ],
}


def _mock_urlopen(mock_data=MOCK_PAYLOAD):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    return mock_resp


def test_get_complete_forecast():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen()):
        data = get_complete_forecast(key="test-key")
        assert data["cycle_id"] == "CYC_TEST_2026"
        assert "summary" in data
        assert "bridges" in data
        assert "stations_rainfall" in data


def test_get_peak_summary():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen()):
        summary = get_peak_summary(key="test-key")
        assert summary["peak_discharge_m3s"] == 1250.5
        assert summary["total_volume_mcm"] == 45.2
        assert summary["lead_hours_to_peak"] == 18
        assert summary["alert_level"] == "WARNING"
        assert "SHIVAJI_BRIDGE" in summary["bridge_peaks"]
        assert summary["bridge_peaks"]["SHIVAJI_BRIDGE"]["peak_stage_m"] == 542.85


def test_get_stage_forecast():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen()):
        shivaji = get_stage_forecast("SHIVAJI_BRIDGE", key="test-key")
        assert len(shivaji) == 2
        assert shivaji[0]["stage_m"] == 535.10
        assert shivaji[1]["stage_m"] == 542.85

        rajaram = get_stage_forecast("RAJARAM_WEIR", key="test-key")
        assert len(rajaram) == 2
        assert rajaram[1]["stage_m"] == 541.95


def test_get_hydrograph():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen()):
        hg = get_hydrograph(key="test-key")
        assert len(hg) == 2
        assert hg[1]["discharge_m3s"] == 1250.5


def test_get_station_rainfall():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen()):
        st = get_station_rainfall(key="test-key")
        assert len(st) == 2
        assert st[0]["station_id"] == "GAGANBAWDA"
        assert st[0]["peak_rainfall_mm_hr"] == 24.5


def test_get_flood_arrival_time():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen()):
        arr = get_flood_arrival_time("SHIVAJI_BRIDGE", key="test-key")
        assert arr["peak_arrival_time"] == "2026-11-10T00:00:00Z"
        assert arr["peak_stage_m"] == 542.85


def test_client_error_handling_unauthorized():
    mock_err = urllib.error.HTTPError(
        url="http://test", code=401, msg="Unauthorized", hdrs={}, fp=None
    )
    with patch("urllib.request.urlopen", side_effect=mock_err):
        with pytest.raises(PermissionError) as exc_info:
            get_complete_forecast(key="bad-key")
        assert "401" in str(exc_info.value)


def test_client_error_handling_rate_limit():
    mock_err = urllib.error.HTTPError(
        url="http://test", code=429, msg="Too Many Requests", hdrs={"Retry-After": "45"}, fp=None
    )
    with patch("urllib.request.urlopen", side_effect=mock_err):
        with pytest.raises(RuntimeError) as exc_info:
            get_complete_forecast(key="test-key")
        assert "429" in str(exc_info.value)
        assert "45" in str(exc_info.value)
