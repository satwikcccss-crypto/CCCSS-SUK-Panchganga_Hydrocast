"""
Multi-Station ThingSpeak IoT Telemetry
=======================================
Fetches live readings from all configured ultrasonic radar / water level
sensors across the Panchganga Basin sensor network.

Station Registry:
  - SS (Shivaji Bridge)   : Channel 3424513  - field1=distance(ft), field2=voltage, field3=signal
  - NW (Nitawade RWLS)    : Channel 3417870  - field1=distance(ft), field2=level, field3=altitude
  - IK (Ichalkaranji)     : Channel 3417872  - field1=distance(ft), field2=?
  - BL (Balinga)          : rain gauge / Bhogavati upstream sensor (NOT_CONFIGURED until env set)

Important:
  - ThingSpeak limits: 1 update per 15 seconds per channel.
  - All fetch functions are safe to call from asyncio tasks; use a shared
    AsyncClient with a 3-second total timeout per request.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

try:
    from dotenv import load_dotenv
    _env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    if _env_file.exists():
        load_dotenv(_env_file, override=False)
except ImportError:
    pass

log = logging.getLogger(__name__)

# ── Balinga station entry (river sensor / rain gauge upstream) ────────────
# Channel ID and API key are expected in the environment:
#   THINGSPEAK_BALINGA_CHANNEL_ID   – ThingSpeak channel number
#   THINGSPEAK_BALINGA_READ_API_KEY – read key for that channel
# If either is missing or empty the station will report NOT_CONFIGURED.
_STATIONS: List[Dict[str, Any]] = [
    {
        "station_id": "SS",
        "name": "Shivaji Bridge",
        "full_name": "Chhatrapati Shivaji Maharaj Bridge, Kolhapur",
        "river": "Panchganga",
        "type": "ultrasonic_radar",
        "unit": "feet",
        "channel_id_env": "THINGSPEAK_CHANNEL_ID",
        "default_channel_id": "3424513",
        "api_key_env": "THINGSPEAK_READ_API_KEY",
        "fields_env": "THINGSPEAK_FIELDS",
        "sensor_datum_m": 549.35,
        "zero_level_m": 530.18,
        "latitude": 16.6950,
        "longitude": 74.2275,
        "has_voltage": True,
        "has_signal_strength": True,
        "field_map": {"distance": "field1", "voltage": "field2", "signal_strength": "field3"},
    },
    {
        "station_id": "NW",
        "name": "Nitawade RWLS",
        "full_name": "Nitawade River Water Level Station",
        "river": "Panchganga",
        "type": "ultrasonic_radar",
        "unit": "meters",
        "channel_id_env": "THINGSPEAK_NITAWADE_CHANNEL_ID",
        "default_channel_id": "3417870",
        "api_key_env": "THINGSPEAK_NITAWADE_READ_API_KEY",
        "fields_env": "THINGSPEAK_NITAWADE_FIELDS",
        "sensor_datum_m": 552.80,
        "zero_level_m": 528.00,
        "latitude": 16.7200,
        "longitude": 74.2050,
        "has_voltage": False,
        "has_signal_strength": False,
        "field_map": {"distance": "field1", "level": "field2", "altitude": "field3"},
    },
    {
        "station_id": "IK",
        "name": "Ichalkaranji",
        "full_name": "Ichalkaranji Water Level Station",
        "river": "Panchganga",
        "type": "ultrasonic_radar",
        "unit": "meters",
        "channel_id_env": "THINGSPEAK_ICHALKARANJI_CHANNEL_ID",
        "default_channel_id": "3417872",
        "api_key_env": "THINGSPEAK_ICHALKARANJI_READ_API_KEY",
        "fields_env": "THINGSPEAK_ICHALKARANJI_FIELDS",
        "sensor_datum_m": 543.71,
        "zero_level_m": 525.00,
        "latitude": 16.6910,
        "longitude": 74.4610,
        "has_voltage": False,
        "has_signal_strength": False,
        "field_map": {"distance": "field1"},
    },
    {
        "station_id": "BL",
        "name": "Balinga",
        "full_name": "Bhogavati River Upstream Sensor",
        "river": "Bhogavati",
        "type": "ultrasonic_radar",
        "unit": "meters",
        "channel_id_env": "THINGSPEAK_BALINGA_CHANNEL_ID",
        "default_channel_id": "",
        "api_key_env": "THINGSPEAK_BALINGA_READ_API_KEY",
        "fields_env": "THINGSPEAK_BALINGA_FIELDS",
        "sensor_datum_m": 560.00,
        "zero_level_m": 548.00,
        "latitude": 16.6878443,
        "longitude": 74.17031,
        "has_voltage": False,
        "has_signal_strength": False,
        "field_map": {"distance": "field1"},
    },
]


def _fetch_latest(channel_id: str, api_key: str, timeout: int = 10) -> Optional[Dict]:
    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds/last.json"
    if api_key and "REPLACE_ME" not in api_key and "change-this" not in api_key:
        url += f"?api_key={api_key}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HydroCast/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log.warning("ThingSpeak fetch failed for channel %s: %s", channel_id, e)
        return None


def _compute_stage(raw_distance: Optional[float], datum_m: float, unit: str = "meters") -> Optional[float]:
    if raw_distance is None:
        return None
    dist_m = raw_distance * 0.3048 if unit == "feet" else raw_distance
    return round(datum_m - dist_m, 2)


def fetch_all_stations() -> List[Dict[str, Any]]:
    """Fetch live readings from all configured ThingSpeak sensor stations."""
    results = []
    for station in STATIONS:
        channel_id = os.getenv(station["channel_id_env"], "") or station.get("default_channel_id", "")
        api_key = os.getenv(station["api_key_env"], "")
        unit = station.get("unit", "meters")

        if not channel_id:
            results.append({
                **_station_meta(station),
                "status": "NOT_CONFIGURED",
                "stage_m": None,
                "timestamp": None,
            })
            continue

        data = _fetch_latest(channel_id, api_key)
        if not data:
            results.append({
                **_station_meta(station),
                "status": "OFFLINE",
                "stage_m": None,
                "timestamp": None,
            })
            continue

        distance_field = station["field_map"].get("distance", station["field_map"].get("distance_ft", "field1"))
        voltage_field = station["field_map"].get("voltage", "field2")

        raw_val = None
        voltage = None
        try:
            raw_str = data.get(distance_field)
            if raw_str is not None and raw_str != "":
                raw_val = float(raw_str)
        except (ValueError, TypeError):
            pass

        if station.get("has_voltage"):
            try:
                v_str = data.get(voltage_field)
                if v_str is not None and v_str != "":
                    voltage = round(float(v_str), 2)
            except (ValueError, TypeError):
                pass

        signal_strength = None
        signal_field = station["field_map"].get("signal_strength")
        if signal_field:
            try:
                sig_str = data.get(signal_field)
                if sig_str is not None and sig_str != "":
                    signal_strength = int(float(sig_str))
            except (ValueError, TypeError):
                pass

        if raw_val is None:
            results.append({
                **_station_meta(station),
                "status": "NO_DATA",
                "stage_m": None,
                "timestamp": data.get("created_at"),
            })
            continue

        stage_m = _compute_stage(raw_val, station["sensor_datum_m"], unit=unit)
        ts_str = data.get("created_at")
        status = "ONLINE"
        if ts_str:
            try:
                ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                age = datetime.now(timezone.utc) - ts_dt
                if age > timedelta(hours=1):
                    status = "STALE"
            except (ValueError, TypeError):
                pass

        dist_ft = round(raw_val if unit == "feet" else raw_val / 0.3048, 2)
        dist_m = round(raw_val * 0.3048 if unit == "feet" else raw_val, 2)

        results.append({
            **_station_meta(station),
            "status": status,
            "stage_m": stage_m,
            "raw_distance": round(raw_val, 2),
            "raw_unit": "ft" if unit == "feet" else "m",
            "raw_distance_ft": dist_ft,
            "raw_distance_m": dist_m,
            "voltage": voltage,
            "signal_strength": signal_strength,
            "timestamp": ts_str,
            "entry_id": data.get("entry_id"),
            **({"stale_since": ts_str} if status == "STALE" else {}),
        })

    return results


def fetch_station(station_id: str) -> Optional[Dict[str, Any]]:
    """Fetch live reading from a single station by ID (SS, NW, IK)."""
    for station in STATIONS:
        if station["station_id"] == station_id.upper():
            result = fetch_all_stations()
            for r in result:
                if r["station_id"] == station_id.upper():
                    return r
    return None


def _station_meta(station: Dict) -> Dict[str, Any]:
    return {
        "station_id": station["station_id"],
        "name": station["name"],
        "full_name": station["full_name"],
        "river": station["river"],
        "type": station["type"],
        "unit": station.get("unit", "meters"),
        "sensor_datum_m": station["sensor_datum_m"],
        "zero_level_m": station["zero_level_m"],
        "latitude": station["latitude"],
        "longitude": station["longitude"],
        "has_voltage": station.get("has_voltage", False),
        "has_signal_strength": station.get("has_signal_strength", False),
    }


def get_station_registry() -> List[Dict[str, Any]]:
    """Return station metadata without fetching live data."""
    return [_station_meta(s) for s in STATIONS]


# ── Async helpers ──────────────────────────────────────────────────────────
_async_client: Optional[httpx.AsyncClient] = None


async def _get_async_client() -> httpx.AsyncClient:
    """Return a shared AsyncClient, creating it on first call."""
    global _async_client
    if _async_client is None:
        _async_client = httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=3.0))
    return _async_client


async def _fetch_latest_async(channel_id: str, api_key: str, timeout: int = 3) -> Optional[Dict]:
    """Async version of _fetch_latest using httpx.AsyncClient."""
    client = await _get_async_client()
    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds/last.json"
    params: Dict[str, str] = {}
    if api_key and "REPLACE_ME" not in api_key and "change-this" not in api_key:
        params["api_key"] = api_key
    try:
        resp = await client.get(url, params=params, headers={"User-Agent": "HydroCast/2.0"})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.warning("Async ThingSpeak fetch failed for channel %s: %s", channel_id, e)
        return None


async def fetch_all_stations_async() -> List[Dict[str, Any]]:
    """Fetch live readings from all configured ThingSpeak stations concurrently.

    Uses httpx.AsyncClient + asyncio.gather with a 3-second per-request timeout.
    Stations without a configured channel_id/env report NOT_CONFIGURED.
    """
    client = await _get_async_client()
    tasks: List = []
    for station in _STATIONS:
        channel_id = os.getenv(station["channel_id_env"], "") or station.get("default_channel_id", "")
        api_key = os.getenv(station["api_key_env"], "")
        if not channel_id:
            # No channel configured – station will be NOT_CONFIGURED; we still include it
            # but skip the HTTP request so we don't waste a task slot.
            tasks.append(_station_meta_async(station, status="NOT_CONFIGURED"))
            continue
        tasks.append(_fetch_and_process_async(client, station, channel_id, api_key))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Exceptions from individual stations are logged inside _fetch_and_process_async;
    # convert any unexpected exceptions to a generic OFFLINE result.
    processed: List[Dict[str, Any]] = []
    for r in results:
        if isinstance(r, Exception):
            log.error("Unexpected error fetching station: %s", r)
            processed.append({
                **_station_meta_next_id(),
                "status": "OFFLINE",
                "stage_m": None,
                "timestamp": None,
            })
        else:
            processed.append(r)
    return processed


async def _fetch_and_process_async(
    client: httpx.AsyncClient,
    station: Dict[str, Any],
    channel_id: str,
    api_key: str,
) -> Dict[str, Any]:
    """Fetch a single station and return a processed result dict."""
    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds/last.json"
    params: Dict[str, str] = {}
    if api_key and "REPLACE_ME" not in api_key and "change-this" not in api_key:
        params["api_key"] = api_key
    try:
        resp = await client.get(url, params=params, headers={"User-Agent": "HydroCast/2.0"})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.warning("Async ThingSpeak fetch failed for channel %s: %s", channel_id, e)
        return {
            **_station_meta(station),
            "status": "OFFLINE",
            "stage_m": None,
            "timestamp": None,
        }

    # ---- parse fields using the station's field_map ----
    distance_field = station["field_map"].get("distance", station["field_map"].get("distance_ft", "field1"))
    voltage_field = station["field_map"].get("voltage", "field2")

    raw_val = None
    voltage = None
    try:
        raw_str = data.get(distance_field)
        if raw_str is not None and raw_str != "":
            raw_val = float(raw_str)
    except (ValueError, TypeError):
        pass

    if station.get("has_voltage"):
        try:
            v_str = data.get(voltage_field)
            if v_str is not None and v_str != "":
                voltage = round(float(v_str), 2)
        except (ValueError, TypeError):
            pass

    signal_strength = None
    signal_field = station["field_map"].get("signal_strength")
    if signal_field:
        try:
            sig_str = data.get(signal_field)
            if sig_str is not None and sig_str != "":
                signal_strength = int(float(sig_str))
        except (ValueError, TypeError):
            pass

    if raw_val is None:
        return {
            **_station_meta(station),
            "status": "NO_DATA",
            "stage_m": None,
            "timestamp": data.get("created_at"),
        }

    stage_m = _compute_stage(raw_val, station["sensor_datum_m"], unit=station.get("unit", "meters"))
    ts_str = data.get("created_at")
    status = "ONLINE"
    if ts_str:
        try:
            ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - ts_dt
            if age > timedelta(hours=1):
                status = "STALE"
        except (ValueError, TypeError):
            pass

    dist_ft = round(raw_val if station.get("unit") == "feet" else raw_val / 0.3048, 2)
    dist_m = round(raw_val * 0.3048 if station.get("unit") == "feet" else raw_val, 2)

    return {
        **_station_meta(station),
        "status": status,
        "stage_m": stage_m,
        "raw_distance": round(raw_val, 2),
        "raw_unit": "ft" if station.get("unit") == "feet" else "m",
        "raw_distance_ft": dist_ft,
        "raw_distance_m": dist_m,
        "voltage": voltage,
        "signal_strength": signal_strength,
        "timestamp": ts_str,
        "entry_id": data.get("entry_id"),
        **({"stale_since": ts_str} if status == "STALE" else {}),
    }


async def _station_meta_async(station: Dict[str, Any], status: str = "OFFLINE") -> Dict[str, Any]:
    """Produce a minimal metadata result when no channel is configured."""
    return {
        **_station_meta(station),
        "status": status,
        "stage_m": None,
        "timestamp": None,
    }


def _station_meta_next_id() -> Dict[str, Any]:
    """Return a generic station dict with next-id placeholder (used for error recovery)."""
    # This mirrors the last station_id iteration pattern; not a real station.
    return {
        "station_id": "XX",
        "name": "Unknown",
        "full_name": "Unknown station",
        "river": "Unknown",
        "type": "unknown",
        "unit": "meters",
        "sensor_datum_m": 0.0,
        "zero_level_m": 0.0,
        "latitude": 0.0,
        "longitude": 0.0,
        "has_voltage": False,
        "has_signal_strength": False,
    }


# ── Sync wrappers for backward compatibility ───────────────────────────────
def fetch_all_stations() -> List[Dict[str, Any]]:
    """Synchronous wrapper: runs the async version in a new event loop.

    Kept for existing callers (e.g. pipeline steps, health checks) that are not yet
    async. Prefer the new async version where possible.
    """
    try:
        return asyncio.get_event_loop().run_until_complete(fetch_all_stations_async())
    except RuntimeError:
        # No running loop – create a fresh one
        import asyncio as a
        return a.run(fetch_all_stations_async())


def fetch_station(station_id: str) -> Optional[Dict[str, Any]]:
    """Sync wrapper for a single station; delegates to fetch_all_stations then filters."""
    results = fetch_all_stations()
    for r in results:
        if r.get("station_id") == station_id.upper():
            return r
    return None


# ── Public API for the new async function ──────────────────────────────────
# Keep STATIONS as the public name (the original list used by fetch_all_stations)
STATIONS = _STATIONS

__all__ = [
    "STATIONS",
    "_STATIONS",
    "fetch_all_stations",
    "fetch_station",
    "get_station_registry",
    "fetch_all_stations_async",
    "_fetch_latest_async",
]
