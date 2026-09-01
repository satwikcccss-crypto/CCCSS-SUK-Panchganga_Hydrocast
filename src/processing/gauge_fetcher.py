"""
src/processing/gauge_fetcher.py
================================
Fetches hourly gauge rainfall from IoT endpoints / CWC API.
Falls back to Open-Meteo historical API when station offline.
Inserts into rainfall_data table.

Configure station endpoints in environment or gauge_stations DB table.
"""

import logging
import os
from datetime import datetime, timezone, timedelta

import requests
import psycopg2

from src.ecmwf.open_meteo import fetch_historical

log = logging.getLogger(__name__)

# IoT endpoint template — replace with actual API
IOT_BASE = os.getenv("IOT_API_BASE", "https://your-iot-api/api/v1/gauges")
IOT_KEY  = os.getenv("IOT_API_KEY",  "")

REQUEST_TIMEOUT = 15   # seconds


def _fetch_iot(station_id: str, start: datetime, end: datetime) -> list[tuple[datetime, float]]:
    """
    Fetch hourly data from IoT sensor API.
    Returns [(timestamp_utc, rainfall_mm), ...].
    Adapt this function to your actual IoT platform (ThingSpeak, AWS IoT, custom).
    """
    url = f"{IOT_BASE}/{station_id}/data"
    params = {
        "start":    start.isoformat(),
        "end":      end.isoformat(),
        "interval": "1h",
    }
    headers = {"Authorization": f"Bearer {IOT_KEY}"} if IOT_KEY else {}
    r = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    data = r.json()

    rows = []
    for item in data.get("records", []):
        ts = datetime.fromisoformat(item["timestamp"]).replace(tzinfo=timezone.utc)
        mm = float(item.get("rainfall_mm", item.get("value", 0)))
        rows.append((ts, max(0.0, mm)))
    return rows


def fetch_all_gauges(conn, run_dt: datetime) -> int:
    """
    For every active gauge station:
      1. Attempt IoT fetch for last 90 hours.
      2. On failure, fall back to Open-Meteo historical.
      3. Insert into rainfall_data.
    Returns total rows inserted.
    """
    end_dt  = run_dt + timedelta(hours=90)
    total   = 0

    with conn.cursor() as cur:
        cur.execute("""
            SELECT station_id, subbasin_id, basin_id,
                   ST_Y(geom) AS lat, ST_X(geom) AS lon
            FROM gauge_stations
            WHERE is_active=TRUE
        """)
        stations = cur.fetchall()

    for station_id, subbasin_id, basin_id, lat, lon in stations:
        try:
            rows = _fetch_iot(station_id, run_dt, end_dt)
            source = "iot"
            log.info("%s: %d IoT records fetched", station_id, len(rows))
        except Exception as e:
            log.warning("%s IoT failed (%s) — using Open-Meteo fallback", station_id, e)
            try:
                df = fetch_historical(lat, lon, run_dt, end_dt)
                rows = [(row.time.to_pydatetime(), float(row.precip_mm_hr))
                        for _, row in df.iterrows()]
                source = "openmeteo_historical"
            except Exception as e2:
                log.error("%s fallback also failed: %s — skipping", station_id, e2)
                continue

        if not rows:
            log.warning("%s: 0 records — nothing to store", station_id)
            continue

        with conn.cursor() as cur:
            for ts, mm in rows:
                cur.execute("""
                    INSERT INTO rainfall_data
                        (basin_id, subbasin_id, gauge_id, source_id,
                         timestamp, rainfall_mm, quality_flag, measurement_interval_minutes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 60)
                    ON CONFLICT DO NOTHING
                """, (basin_id, subbasin_id, station_id, source, ts, mm, "ok"))
                total += 1
        conn.commit()
        log.info("%s: %d rows stored [%s]", station_id, len(rows), source)

    return total
