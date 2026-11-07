"""
backend/rainfall/open_meteo_failsafe.py
=======================================
Live-first weather retrieval engine for HydroCast.

Policy (production default)
---------------------------
* **Tier 1 — Live Open-Meteo forecast (ECMWF IFS)**: the only source that is
  allowed to feed the hydrological model by default. The request is anchored to
  the forecast cycle's ``run_dt`` using ``past_hours`` + ``forecast_hours`` so
  the 90-point series always starts at the cycle hour.
* **Tier 2 — Cached predecessor**: opt-in only
  (``HYDROCAST_ALLOW_STALE_WEATHER_FALLBACK=true``). The cache must be newer
  than ``HYDROCAST_WEATHER_CACHE_MAX_AGE_HOURS`` (default 6 h). It is marked
  ``is_live=False`` and the provenance travels with the data.
* **Tier 3 — Climatology**: opt-in only
  (``HYDROCAST_ALLOW_CLIMATOLOGY_FALLBACK=true``). Never enabled by default:
  fabricated monsoon rain must never be presented as a forecast.

If no permitted source is available, :class:`WeatherDataUnavailable` is raised
so the pipeline fails loudly instead of silently serving stale or synthetic
rainfall.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from backend.rainfall.station_selector import STATION_REGISTRY

log = logging.getLogger(__name__)

# ── Station registry ─────────────────────────────────────────────────────────
STATIONS_MAP = {
    st.station_id: {
        "name": st.name,
        "subbasin": st.subbasin,
        "lat": st.lat,
        "lon": st.lon,
    }
    for st in STATION_REGISTRY
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "data" / "staging" / "weather_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

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

# Calibrated IMD historical monsoon hourly intensity baseline (mm/hr) per
# subbasin. Only used when the operator explicitly enables Tier 3.
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
        # Anchor the response to the cycle hour, not the wall-clock hour.
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
            return result
        except Exception as exc:  # noqa: BLE001 - retry any transport/parse error
            last_err = exc
            log.warning("Tier 1 fetch attempt %d/%d failed: %s", attempt, max_retries, exc)
            time.sleep(1.0 * attempt)

    log.error("Tier 1 live weather fetch failed completely: %s", last_err)
    return None


def _cache_age_hours(path: Path) -> float:
    age_seconds = max(0.0, time.time() - path.stat().st_mtime)
    return age_seconds / 3600.0


def fetch_tier2_predecessor_cache(run_dt: datetime) -> Optional[Dict[str, Any]]:
    """Tier 2 (opt-in): reuse a recent live cache, clearly marked as non-live."""
    if not ALLOW_STALE_CACHE:
        log.warning(
            "Tier 2 disabled: set HYDROCAST_ALLOW_STALE_WEATHER_FALLBACK=true to allow it."
        )
        return None

    latest_file = CACHE_DIR / "latest_successful_weather.json"
    if not latest_file.exists():
        log.warning("Tier 2 fallback failed: no predecessor cache at %s", latest_file)
        return None

    age_h = _cache_age_hours(latest_file)
    if age_h > CACHE_MAX_AGE_HOURS:
        log.warning(
            "Tier 2 rejected: cache is %.2f h old (max %.1f h).", age_h, CACHE_MAX_AGE_HOURS
        )
        return None

    try:
        prev_data = json.loads(latest_file.read_text(encoding="utf-8"))
        prev_stations = prev_data.get("stations", {}) or {}
        if not prev_stations:
            return None

        # Reuse exactly the cached values. Do not invent a decay tail.
        shifted_stations: Dict[str, Any] = {}
        for st_id, sdata in prev_stations.items():
            arr = list(sdata.get("precipitation_mm_hr", []) or [])
            arr = [float(x) for x in arr[:FORECAST_HOURS]]
            if len(arr) < FORECAST_HOURS:
                arr += [0.0] * (FORECAST_HOURS - len(arr))
            shifted_stations[st_id] = {
                "precipitation_mm_hr": arr,
                "temperature_c": (sdata.get("temperature_c") or [25.0] * FORECAST_HOURS)[:FORECAST_HOURS],
                "relative_humidity_pct": (sdata.get("relative_humidity_pct") or [70.0] * FORECAST_HOURS)[:FORECAST_HOURS],
            }

        fetched_at = datetime.now(timezone.utc)
        warning = (
            f"LIVE WEATHER UNAVAILABLE: serving cached Open-Meteo forecast from "
            f"{prev_data.get('timestamp_utc')} ({age_h:.1f} h old)."
        )
        result = {
            "tier": "tier2_cache",
            "is_live": False,
            "original_timestamp_utc": prev_data.get("timestamp_utc"),
            "timestamp_utc": fetched_at.isoformat(),
            "run_dt": run_dt.astimezone(timezone.utc).isoformat(),
            "stations": shifted_stations,
            "lead_hours": FORECAST_HOURS,
            "warning": warning,
            "provenance": _provenance(
                "tier2_cache",
                is_live=False,
                run_dt=run_dt,
                fetched_at=fetched_at,
                cache_age_hours=round(age_h, 2),
                warning=warning,
            ),
        }
        log.warning("Tier 2 cache in use (%s).", warning)
        return result
    except Exception as exc:  # noqa: BLE001
        log.error("Tier 2 cache parsing failed: %s", exc)
        return None


def fetch_tier3_climatology(run_dt: datetime) -> Dict[str, Any]:
    """Tier 3 (opt-in): synthetic monsoon baseline. Never used by default."""
    if not ALLOW_CLIMATOLOGY:
        raise WeatherDataUnavailable(
            "Live Open-Meteo forecast unavailable and no recent cache is permitted. "
            "Fabricated climatology is disabled (HYDROCAST_ALLOW_CLIMATOLOGY_FALLBACK=false)."
        )

    log.warning("Tier 3: generating SYNTHETIC climatological baseline (explicit opt-in).")
    station_series: Dict[str, Dict[str, Any]] = {}
    for st_id, sinfo in STATIONS_MAP.items():
        subbasin = sinfo.get("subbasin", "S1")
        base_intensity = CLIMATOLOGICAL_HOURLY_BASELINES.get(subbasin, 4.0)
        hours = np.arange(FORECAST_HOURS)
        diurnal = 1.0 + 0.4 * np.sin(2 * np.pi * (hours % 24 - 8) / 24)
        synth = np.maximum(0.0, base_intensity * diurnal)
        station_series[st_id] = {
            "precipitation_mm_hr": np.round(synth, 2).tolist(),
            "temperature_c": [24.0] * FORECAST_HOURS,
            "relative_humidity_pct": [80.0] * FORECAST_HOURS,
        }

    fetched_at = datetime.now(timezone.utc)
    warning = "SYNTHETIC climatological rainfall — NOT an Open-Meteo forecast."
    return {
        "tier": "tier3_climatology_synthetic",
        "is_live": False,
        "timestamp_utc": fetched_at.isoformat(),
        "run_dt": run_dt.astimezone(timezone.utc).isoformat(),
        "stations": station_series,
        "lead_hours": FORECAST_HOURS,
        "warning": warning,
        "provenance": _provenance(
            "tier3_climatology_synthetic",
            is_live=False,
            run_dt=run_dt,
            fetched_at=fetched_at,
            warning=warning,
        ),
    }


def get_weather_failsafe(run_dt: Optional[datetime] = None) -> Dict[str, Any]:
    """Return a trustworthy weather payload or raise ``WeatherDataUnavailable``."""
    if run_dt is None:
        run_dt = datetime.now(timezone.utc)

    live = fetch_tier1_open_meteo(run_dt)
    if live is not None:
        return live

    cached = fetch_tier2_predecessor_cache(run_dt)
    if cached is not None:
        return cached

    # Raises unless the operator explicitly enabled synthetic climatology.
    return fetch_tier3_climatology(run_dt)


__all__ = [
    "WeatherDataUnavailable",
    "STATIONS_MAP",
    "fetch_tier1_open_meteo",
    "fetch_tier2_predecessor_cache",
    "fetch_tier3_climatology",
    "get_weather_failsafe",
]
