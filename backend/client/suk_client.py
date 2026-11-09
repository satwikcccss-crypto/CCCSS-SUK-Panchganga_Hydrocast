"""
backend/client/suk_client.py
============================
Official Shivaji University Kolhapur (SUK) Python Client for HydroCast.
Provides high-level, read-only Python functions to retrieve:
  - Basin Flood Peak Summary & Total Volume
  - 90-Hour Stage & Discharge Hydrographs (Shivaji Bridge & Rajaram Weir)
  - 90-Hour Basin Outlet Discharge Hydrograph
  - Station-wise Peak Rainfall & Cumulative Precipitation
  - Flood Arrival Time with Calibrated Confidence Windows

Usage:
    from backend.client.suk_client import (
        get_peak_summary,
        get_stage_forecast,
        get_hydrograph,
        get_station_rainfall,
        get_flood_arrival_time,
        get_complete_forecast,
    )

    summary = get_peak_summary()
    print("Peak Discharge:", summary["peak_discharge_m3s"], "m3/s")
    print("Total Runoff Volume:", summary["total_volume_mcm"], "MCM")

    stage_series = get_stage_forecast("SHIVAJI_BRIDGE")
    print("Shivaji 90h points:", len(stage_series))
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_BASE_URL = os.getenv("HYDROCAST_BASE_URL", "http://localhost:8000")
ENDPOINT_PATH = "/api/SUK_hydrocast_v1"


def get_configured_key() -> str:
    """Resolve read-only API key from environment or project .env."""
    key = os.getenv("HYDROCAST_READONLY_KEY", "").strip()
    if key:
        return key
    key = os.getenv("HYDROSIM_API_KEY", "").strip()
    if key:
        return key
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith(("HYDROCAST_READONLY_KEY=", "HYDROSIM_API_KEY=")):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""


def get_complete_forecast(
    base_url: str = DEFAULT_BASE_URL,
    key: Optional[str] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """
    Fetch the complete authenticated flood intelligence payload from SUK HydroCast.

    :param base_url: Base URL of the HydroCast service (default: http://localhost:8000).
    :param key: Read-only API key. If omitted, automatically resolved from environment.
    :param timeout: Network timeout in seconds.
    :return: Full dictionary containing summary, bridges, stations_rainfall, and outlet_hydrograph_90h.
    :raises ConnectionError: If unable to reach the API.
    :raises PermissionError: If the API key is missing or rejected (HTTP 401).
    :raises RuntimeError: On rate limiting (HTTP 429) or other server errors.
    """
    api_key = (key or get_configured_key()).strip()
    url = f"{base_url.rstrip('/')}{ENDPOINT_PATH}"
    if api_key:
        url += f"?key={urllib.parse.quote(api_key)}"

    req = urllib.request.Request(url, headers={"User-Agent": "SUK-HydroCast-Client/1.0"})
    if api_key:
        req.add_header("X-API-Key", api_key)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as err:
        if err.code == 401:
            raise PermissionError("HTTP 401: Invalid or missing HydroCast API key.") from err
        if err.code == 429:
            retry_sec = err.headers.get("Retry-After", "60")
            raise RuntimeError(f"HTTP 429: Rate limit exceeded. Retry after {retry_sec} seconds.") from err
        raise RuntimeError(f"HTTP {err.code}: {err.reason}") from err
    except Exception as exc:
        raise ConnectionError(f"Failed to connect to HydroCast server at {base_url}: {exc}") from exc


def get_peak_summary(
    base_url: str = DEFAULT_BASE_URL,
    key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve executive hydrological KPIs for the latest cycle:
      - peak_discharge_m3s: Peak outflow at basin sink
      - total_volume_mcm: Total forecasted runoff volume in Million Cubic Metres
      - lead_hours_to_peak: Number of hours from forecast cycle to peak arrival
      - alert_level: CWC status ('NORMAL', 'ALERT', 'WARNING', 'DANGER')
      - bridge_peaks: Dictionary with peak water levels at Shivaji Bridge & Rajaram Weir
      - flood_arrival_times: Timestamp of peak arrival per location
    """
    data = get_complete_forecast(base_url=base_url, key=key)
    summary = data.get("summary", {})
    bridges = data.get("bridges", {})

    bridge_peaks = {}
    for sid, b in bridges.items():
        bridge_peaks[sid] = {
            "site_name": b.get("site_name", sid),
            "peak_stage_m": b.get("peak_stage_m", 0.0),
            "current_stage_m": b.get("current_stage_m", 0.0),
            "peak_discharge_m3s": b.get("peak_discharge_m3s", 0.0),
            "alert_level": b.get("alert_level", "NORMAL"),
        }

    return {
        "cycle_id": data.get("cycle_id"),
        "issued_at": data.get("issued_at"),
        "peak_discharge_m3s": summary.get("peak_discharge_m3s", 0.0),
        "total_volume_mcm": summary.get("total_volume_mcm", 0.0),
        "lead_hours_to_peak": summary.get("lead_hours_to_peak", 0),
        "alert_level": summary.get("alert_level", "NORMAL"),
        "bridge_peaks": bridge_peaks,
        "flood_arrival_times": summary.get("peak_arrival", {}),
    }


def get_stage_forecast(
    site: str = "SHIVAJI_BRIDGE",
    base_url: str = DEFAULT_BASE_URL,
    key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve the 90-hour water-level and discharge forecast series for a bridge.

    :param site: Bridge identifier ('SHIVAJI_BRIDGE', 'RAJARAM_BRIDGE' or 'RAJARAM_WEIR').
    :return: List of 90 hourly records:
             [{"lead_hours": int, "forecast_time": str, "stage_m": float, "discharge_m3s": float, "alert_level": str, ...}]
    """
    data = get_complete_forecast(base_url=base_url, key=key)
    bridges = data.get("bridges", {})

    # Normalize name
    normalized_site = site.upper().strip()
    if normalized_site in ("RAJARAM", "RAJARAM_WEIR"):
        normalized_site = "RAJARAM_BRIDGE"
    elif normalized_site in ("SHIVAJI", "SHIVAJI_GHAT"):
        normalized_site = "SHIVAJI_BRIDGE"

    if normalized_site in bridges:
        return bridges[normalized_site].get("series_90h", [])

    # If asking for all bridges combined
    if normalized_site == "ALL":
        combined = []
        for sid, b in bridges.items():
            for pt in b.get("series_90h", []):
                combined.append({"site_id": sid, **pt})
        return combined

    # Fallback: check case-insensitive match
    for k, v in bridges.items():
        if normalized_site in k.upper():
            return v.get("series_90h", [])

    return []


def get_hydrograph(
    base_url: str = DEFAULT_BASE_URL,
    key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve the 90-hour basin outlet discharge hydrograph series at the terminal sink.

    :return: List of 90 hourly records:
             [{"lead_hours": int, "discharge_m3s": float, "stage_m": float, "timestamp": str}, ...]
    """
    data = get_complete_forecast(base_url=base_url, key=key)
    return data.get("outlet_hydrograph_90h", [])


def get_station_rainfall(
    base_url: str = DEFAULT_BASE_URL,
    key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve station-wise rainfall intelligence across the 20 Panchganga basin stations.

    :return: List of station records sorted by total precipitation:
             [{"station_id": str, "station_name": str, "peak_rainfall_mm_hr": float, "peak_time": str, "cumulative_90h_mm": float}, ...]
    """
    data = get_complete_forecast(base_url=base_url, key=key)
    return data.get("stations_rainfall", [])


def get_flood_arrival_time(
    site: str = "SHIVAJI_BRIDGE",
    base_url: str = DEFAULT_BASE_URL,
    key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve calibrated flood arrival timing and confidence intervals for a specific bridge.

    :param site: 'SHIVAJI_BRIDGE', 'RAJARAM_BRIDGE', or 'OUTLET'.
    :return: Dictionary with arrival timestamp, confidence range (earliest/latest), and receding status.
    """
    data = get_complete_forecast(base_url=base_url, key=key)
    pa = data.get("summary", {}).get("peak_arrival", {})

    site_key = "shivaji" if "SHIVAJI" in site.upper() else ("rajaram" if "RAJARAM" in site.upper() else "outlet")
    return pa.get(site_key, {})
