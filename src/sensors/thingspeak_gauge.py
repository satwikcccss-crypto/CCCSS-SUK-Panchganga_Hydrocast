"""
ThingSpeak IoT Ultrasonic Water Level Sensor Telemetry
======================================================
Fetches live ultrasonic radar sensor telemetry for Chhatrapati Shivaji Maharaj Bridge.

Sensor Specifications:
- Sensor Mounting Datum: 549.35 m MSL (Bridge Deck Level)
- Raw Sensor Unit: Feet (distance from sensor down to water surface, or water depth)
- Conversion: 1 Foot = 0.3048 Meters
- Water Level Calculation: Water Stage (m MSL) = 549.35 m - (Distance_feet * 0.3048)
"""

import os
import logging
import requests
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)

THINGSPEAK_API_KEY = os.getenv("THINGSPEAK_API_KEY", "TSUKPZEUN1BXODUF")
THINGSPEAK_CHANNEL_ID = os.getenv("THINGSPEAK_CHANNEL_ID", "3424513")
SHIVAJI_SENSOR_DATUM_M = 549.35  # Elevation of sensor in meters MSL


def fetch_shivaji_live_telemetry(
    channel_id: Optional[str] = None,
    api_key: Optional[str] = None,
    datum_msl: float = SHIVAJI_SENSOR_DATUM_M
) -> Dict[str, Any]:
    """
    Fetches the latest reading from ThingSpeak for Shivaji Bridge.
    Converts raw distance in feet to elevation in meters MSL.
    """
    key = api_key or THINGSPEAK_API_KEY
    ch_id = channel_id or THINGSPEAK_CHANNEL_ID or os.getenv("THINGSPEAK_CHANNEL_ID", "")

    if not ch_id:
        log.warning("No THINGSPEAK_CHANNEL_ID provided. Please configure channel ID to fetch live IoT sensor feeds.")
        return {
            "status": "AWAITING_CHANNEL_ID",
            "api_key": key,
            "sensor_datum_msl": datum_msl,
            "stage_m": None,
            "raw_feet": None,
            "timestamp": None,
        }

    url = f"https://api.thingspeak.com/channels/{ch_id}/feeds/last.json"
    params = {"api_key": key}

    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            log.warning("ThingSpeak returned status %d: %s", resp.status_code, resp.text[:200])
            return {
                "status": "ERROR",
                "error": f"HTTP_{resp.status_code}",
                "stage_m": None,
            }

        data = resp.json()
        if not data:
            return {"status": "NO_DATA", "stage_m": None}

        # Scan fields for numerical sensor reading (distance in feet)
        raw_val = None
        for field_name in ["field1", "field2", "field3", "field4", "field5", "field6", "field7", "field8"]:
            val_str = data.get(field_name)
            if val_str is not None:
                try:
                    val = float(val_str)
                    raw_val = val
                    break
                except (ValueError, TypeError):
                    continue

        if raw_val is None:
            log.warning("No numeric field found in ThingSpeak feed: %s", data)
            return {"status": "NO_NUMERIC_FIELD", "stage_m": None, "raw_data": data}

        # Water level calculation: Datum (549.35m MSL) - Distance down (raw_val in feet * 0.3048)
        distance_m = raw_val * 0.3048
        stage_m = round(datum_msl - distance_m, 2)

        log.info("✓ ThingSpeak Shivaji Live Telemetry: Distance=%.2f ft (%.2f m) -> Water Level=%.2f m MSL (Datum: %.2f m)", 
                 raw_val, distance_m, stage_m, datum_msl)

        return {
            "status": "SUCCESS",
            "channel_id": ch_id,
            "timestamp": data.get("created_at"),
            "entry_id": data.get("entry_id"),
            "raw_feet": raw_val,
            "sensor_datum_msl": datum_msl,
            "stage_m": stage_m,
        }

    except Exception as e:
        log.error("ThingSpeak fetch failed: %s", e)
        return {
            "status": "ERROR",
            "error": str(e),
            "stage_m": None,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    res = fetch_shivaji_live_telemetry()
    print("Result:", res)
