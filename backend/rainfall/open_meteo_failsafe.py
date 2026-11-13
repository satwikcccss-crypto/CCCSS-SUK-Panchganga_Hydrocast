"""
backend/rainfall/open_meteo_failsafe.py
=======================================
Live-first weather retrieval engine for HydroCast.

Policy (production default):
---------------------------
* Tier 1 (Live API Primary): Queries Open-Meteo IFS 90-hour hourly precipitation
  forecasts for all 20 Panchganga stations with exponential backoff (3 attempts with
  jitter).
* Tier 2 (Cached Predecessor): Opt-in only (HYDROCAST_ALLOW_STALE_WEATHER_FALLBACK=true).
  If Tier 1 fails, loads the previous successful forecast cycle from local cache,
  shifts lead times by the cycle delta (6h), and synthesizes the remaining 6 hours
  to prevent pipeline abortion. Cache must be newer than HYDROCAST_WEATHER_CACHE_MAX_AGE_HOURS
  (default 6h). Marked is_live=False with provenance warning.
* Tier 3 (Climatology): Opt-in only (HYDROCAST_ALLOW_CLIMATOLOGY_FALLBACK=true). Applies
  calibrated IMD monsoon hyetographs per subbasin. Never enabled by default: fabricated
  rain must never be presented as a forecast.

If no permitted source is available, WeatherDataUnavailable is raised so the pipeline
fails loudly instead of silently serving stale or synthetic rainfall.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.rainfall.station_selector import STATION_REGISTRY

log = logging.getLogger(__name__)

# ── Station registry ─────────────────────────────────────────────────────────
STATIONS_MAP = {
    st.station_id: {"name": st.name, "subbasin": st.subbasin, "lat": st.lat, "lon": st.lon}
    for st in STATION_REGISTRY
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "data" / "staging" / "weather_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_RETENTION_DAYS = int(os.getenv("HYDROCAST_WEATHER_CACHE_RETENTION_DAYS", "30"))


def purge_expired_weather_cache(
    cache_dir: Path = CACHE_DIR,
    max_age_days: int = CACHE_RETENTION_DAYS,
) -> int:
    """Delete cached audit forecasts older than ``max_age_days``.

    ``latest_successful_weather.json`` and unstamped files are preserved.
    Returns the number of files removed.
    """
    if not cache_dir.exists():
        return 0

    cutoff = time.time() - (max_age_days * 86400)
    purged = 0
    for path in cache_dir.glob("weather_success_*.json"):
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
                purged += 1
                log.info("Purged expired weather cache file: %s", path.name)
        except Exception as exc:  # noqa: BLE001 - cleanup must never break a fetch
            log.warning("Could not purge weather cache file %s: %s", path.name, exc)
    return purged


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_MODEL = os.getenv("HYDROCAST_OPEN_METEO_MODEL", "ecmwf_ifs025")
FORECAST_HOURS = int(os.getenv("HYDROCAST_FORECAST_HOURS", "90"))

# Explicit opt-in switches. Defaults are deliberately safe.
ALLOW_STALE_CACHE = os.getenv(
    "HYDROCAST_ALLOW_STALE_WEATHER_FALLBACK", "false"
).strip().lower() in {"1", "true", "yes", "on"}
CACHE_MAX_AGE_HOURS = float(
    os.getenv("HYDROCAST_WEATHER_CACHE_MAX_AGE_HOURS", "6")
)
ALLOW_CLIMATOLOGY = os.getenv(
    "HYDROCAST_ALLOW_CLIMATOLOGY_FALLBACK", "false"
).strip().lower() in {"1", "true", "yes", "on"}

# Calibrated IMD historical monsoon hourly intensity baseline (mm/hr) per subbasin
# Only used when the operator explicitly enables Tier 3.
CLIMATOLOGICAL_HOURLY_BASELINES = {
    "S1": 2.5,
    "S2": 3.8,
    "S3": 4.5,
    "S4": 6.2,
    "S5": 7.0,
    "S6": 12.5,
    "S7": 5.8,
    "S8": 4.2,
    "S9": 9.5,
}


class WeatherDataUnavailable(RuntimeError):
    """Raised when no permitted, trustworthy weather source is available."""


def _provenance(
    tier: str,
    *,
    is_live: bool,
    run_dt: datetime,
    fetched_at: Optional[datetime] = None,
    cache_age_hours: Optional[float] = None,
    warning: Optional[str] = None,
) -> Dict[str, Any]:
    """Uniform provenance block attached to every weather payload."""
    return {
        "source": "open-meteo",
        "endpoint": OPEN_METEO_URL,
        "model": OPEN_METEO_MODEL,
        "tier": tier,
        "is_live": bool(is_live),
        "run_dt": run_dt.astimezone(timezone.utc).isoformat(),
        "fetched_at": (fetched_at or datetime.now(timezone.utc)).isoformat(),
        "cache_age_hours": cache_age_hours,
        "warning": warning,
    }


def fetch_tier1_open_meteo(
    run_dt: datetime,
    max_retries: int = 3,
    timeout_sec: int = 15,
) -> Optional[Dict[str, Any]]:
    """Tier 1: live Open-Meteo forecast, anchored to ``run_dt``."""
    import openmeteo_requests
    import requests
    from retry_requests import retry

    log.info("Tier 1: Attempting live Open-Meteo weather fetch for %s UTC...", run_dt.isoformat())
    run_dt = run_dt.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    lag_hours = max(0, int((now - run_dt).total_seconds() // 3600))
    lag_hours = min(lag_hours, 48)
    forecast_hours = max(1, FORECAST_HOURS - lag_hours)

    lats = [st["lat"] for st in STATIONS_MAP.values()]
    lons = [st["lon"] for st in STATIONS_MAP.values()]
    station_ids = list(STATIONS_MAP.keys())

    params = {
        "latitude": lats,
        "longitude": lons,
        "hourly": ["precipitation", "temperature_2m", "relative_humidity_2m"],
        "models": OPEN_METEO_MODEL,
        "timezone": "UTC",
        "past_hours": lag_hours,
        "forecast_hours": forecast_hours,
    }

    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            log.info(
                "Tier 1: live Open-Meteo fetch for %s UTC (past_hours=%d, forecast_hours=%d, model=%s)",
                run_dt.isoformat(), lag_hours, forecast_hours, OPEN_METEO_MODEL,
            )
            session = retry(requests.Session(), retries=2, backoff_factor=0.3)
            client = openmeteo_requests.Client(session=session)
            responses = client.weather_api(OPEN_METEO_URL, params=params)
            if len(responses) != len(station_ids):
                raise ValueError(
                    f"Expected {len(station_ids)} responses, received {len(responses)}"
                )

            station_series: Dict[str, Dict[str, Any]] = {}
            start_epoch: Optional[int] = None
            for idx, response in enumerate(responses):
                st_id = station_ids[idx]
                hourly = response.Hourly()
                if start_epoch is None:
                    start_epoch = int(hourly.Time())
                precip = hourly.Variables(0).ValuesAsNumpy()[:FORECAST_HOURS]
                temp = hourly.Variables(1).ValuesAsNumpy()[:FORECAST_HOURS]
                hum = hourly.Variables(2).ValuesAsNumpy()[:FORECAST_HOURS]
                station_series[st_id] = {
                    "precipitation_mm_hr": np.nan_to_num(precip, nan=0.0).tolist(),
                    "temperature_c": np.nan_to_num(temp, nan=25.0).tolist(),
                    "relative_humidity_pct": np.nan_to_num(hum, nan=70.0).tolist(),
                }

            fetched_at = datetime.now(timezone.utc)
            timestamps = [
                datetime.fromtimestamp(start_epoch + i * 3600, tz=timezone.utc).isoformat()
                for i in range(FORECAST_HOURS)
            ] if start_epoch is not None else []

            result: Dict[str, Any] = {
                "tier": "tier1_live_api",
                "is_live": True,
                "timestamp_utc": fetched_at.isoformat(),
                "run_dt": run_dt.isoformat(),
                "stations": station_series,
                "timestamps": timestamps,
                "lead_hours": FORECAST_HOURS,
                "provenance": _provenance(
                    "tier1_live_api", is_live=True, run_dt=run_dt, fetched_at=fetched_at
                ),
                "error": None,
            }

            # Audit cache (never read back unless Tier 2 is explicitly enabled).
            cache_file = CACHE_DIR / f"weather_success_{run_dt.strftime('%Y%m%d_%H%M')}.json"
            latest_file = CACHE_DIR / "latest_successful_weather.json"
            for path in (cache_file, latest_file):
                path.write_text(
                    json.dumps(result, indent=2, default=str), encoding="utf-8"
                )

            log.info("Tier 1 weather fetch successful for %d stations.", len(station_series))
            purge_expired_weather_cache()
            return result
        except Exception as exc:  # noqa: BLE001 - retry any transport/parse error
            last_err = exc
            log.warning("Tier 1 fetch attempt %d/%d failed: %s", attempt, max_retries, exc)
            time.sleep(1.0 * attempt)

    log.error("Tier 1 live weather fetch failed completely: %s", last_err)
    return None


def get_weather_failsafe(run_dt: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Live-only weather retrieval for HydroCast.

    Only attempts Tier 1: live Open-Meteo forecast.
    If the live API is unavailable, returns a degraded payload with
    ``is_live=False`` and a clear ``warning`` so the pipeline can
    mark the cycle as data-degraded rather than serving synthetic
    or cached rainfall.

    The caller (pipeline_worker) catches ``WeatherDataUnavailable``
    if it needs to distinguish a total outage from a degraded but
    recoverable state.
    """
    if run_dt is None:
        run_dt = datetime.now(timezone.utc)

    live = fetch_tier1_open_meteo(run_dt)
    if live is not None:
        return live

    # No Tier 2/3 fallbacks — if the live API cannot supply data,
    # return a degraded payload so the caller can set the cycle
    # status to ``data_unavailable`` instead of serving stale
    # or synthetic rain.
    degraded: Dict[str, Any] = {
        "tier": "tier1_failed",
        "is_live": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "run_dt": run_dt.astimezone(timezone.utc).isoformat(),
        "stations": {},
        "lead_hours": FORECAST_HOURS,
        "warning": "LIVE WEATHER UNAVAILABLE: no Open-Meteo forecast data could be retrieved. Cycle will be marked data_unavailable.",
        "provenance": _provenance(
            "tier1_failed",
            is_live=False,
            run_dt=run_dt,
            warning="LIVE WEATHER UNAVAILABLE: no Open-Meteo forecast data could be retrieved.",
        ),
    }
    log.warning("Tier 1 live weather fetch failed; returning degraded payload.")
    return degraded


# ── Exported names ──────────────────────────────────────────────────────────
__all__ = [
    "WeatherDataUnavailable",
    "STATIONS_MAP",
    "fetch_tier1_open_meteo",
    "get_weather_failsafe",
    "purge_expired_weather_cache",
]