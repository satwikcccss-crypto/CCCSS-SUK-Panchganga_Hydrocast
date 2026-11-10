"""
Multi-Station ThingSpeak IoT Telemetry
=======================================
Fetches live readings from all configured ultrasonic radar / water level
sensors across the Panchganga Basin sensor network.

Station Registry:
  - SS (Shivaji Bridge)   : Channel 3424513  - field1=distance(ft), field2=voltage, field3=?
  - NW (Nitawade RWLS)    : Channel 3417870  - field1=distance(ft), field2=voltage, field3=?
  - IK (Ichalkaranji)     : Channel 3417872  - field1=distance(ft), field2=?, field3=?
"""

import json
import logging
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

STATIONS: List[Dict[str, Any]] = [
    {
        "station_id": "SS",
        "name": "Shivaji Bridge",
        "full_name": "Chhatrapati Shivaji Maharaj Bridge, Kolhapur",
        "river": "Panchganga",
        "type": "ultrasonic_radar",
        "channel_id_env": "THINGSPEAK_CHANNEL_ID",
        "api_key_env": "THINGSPEAK_READ_API_KEY",
        "fields_env": "THINGSPEAK_FIELDS",
        "sensor_datum_m": 549.35,
        "zero_level_m": 530.18,
        "latitude": 16.6950,
        "longitude": 74.2275,
        "has_voltage": True,
        "field_map": {"distance_ft": "field1", "voltage": "field2"},
    },
    {
        "station_id": "NW",
        "name": "Nitawade RWLS",
        "full_name": "Nitawade River Water Level Station",
        "river": "Panchganga",
        "type": "ultrasonic_radar",
        "channel_id_env": "THINGSPEAK_NITAWADE_CHANNEL_ID",
        "api_key_env": "THINGSPEAK_NITAWADE_READ_API_KEY",
        "fields_env": "THINGSPEAK_NITAWADE_FIELDS",
        "sensor_datum_m": 552.80,
        "zero_level_m": 528.00,
        "latitude": 16.7200,
        "longitude": 74.2050,
        "has_voltage": True,
        "field_map": {"distance_ft": "field1", "voltage": "field2"},
    },
    {
        "station_id": "IK",
        "name": "Ichalkaranji",
        "full_name": "Ichalkaranji Water Level Station",
        "river": "Panchganga",
        "type": "ultrasonic_radar",
        "channel_id_env": "THINGSPEAK_ICHALKARANJI_CHANNEL_ID",
        "api_key_env": "THINGSPEAK_ICHALKARANJI_READ_API_KEY",
        "fields_env": "THINGSPEAK_ICHALKARANJI_FIELDS",
        "sensor_datum_m": 543.71,
        "zero_level_m": 525.00,
        "latitude": 16.6910,
        "longitude": 74.4610,
        "has_voltage": False,
        "field_map": {"distance_ft": "field1"},
    },
]


def _fetch_latest(channel_id: str, api_key: str, timeout: int = 10) -> Optional[Dict]:
    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds/last.json"
    if api_key:
        url += f"?api_key={api_key}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HydroCast/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log.warning("ThingSpeak fetch failed for channel %s: %s", channel_id, e)
        return None


def _compute_stage(raw_feet: float, datum_m: float) -> float:
    return round(datum_m - (raw_feet * 0.3048), 2)


def fetch_all_stations() -> List[Dict[str, Any]]:
    """Fetch live readings from all configured ThingSpeak sensor stations."""
    results = []
    for station in STATIONS:
        channel_id = os.getenv(station["channel_id_env"], "")
        api_key = os.getenv(station["api_key_env"], "")

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

        distance_field = station["field_map"].get("distance_ft", "field1")
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

        if raw_val is None:
            results.append({
                **_station_meta(station),
                "status": "NO_DATA",
                "stage_m": None,
                "timestamp": data.get("created_at"),
            })
            continue

        stage_m = _compute_stage(raw_val, station["sensor_datum_m"])
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
        results.append({
            **_station_meta(station),
            "status": status,
            "stage_m": stage_m,
            "raw_distance_ft": round(raw_val, 2),
            "voltage": voltage,
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
        "sensor_datum_m": station["sensor_datum_m"],
        "zero_level_m": station["zero_level_m"],
        "latitude": station["latitude"],
        "longitude": station["longitude"],
        "has_voltage": station.get("has_voltage", False),
    }


def get_station_registry() -> List[Dict[str, Any]]:
    """Return station metadata without fetching live data."""
    return [_station_meta(s) for s in STATIONS]
