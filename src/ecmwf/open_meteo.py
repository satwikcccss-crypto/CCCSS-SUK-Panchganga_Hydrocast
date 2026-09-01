"""
Open-Meteo Rainfall Downloader
================================
Free, no API key, up to 16-day hourly forecast.
Model: "ecmwf_ifs" (same underlying NWP, served via Open-Meteo API).
Resolution: 0.1° (~11km) — closest free option to IFS 9km.

Fetches precipitation for every station location + ECMWF grid points
within the catchment bounding box, building a 90-hr gridded dataset.

Install:
    pip install openmeteo-requests requests-cache retry-requests

API docs: https://open-meteo.com/en/docs
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests
import requests_cache
import xarray as xr
from retry_requests import retry

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BBOX = {
    "north": float(os.getenv("BBOX_N", "22.0")),
    "south": float(os.getenv("BBOX_S", "17.0")),
    "east":  float(os.getenv("BBOX_E", "78.5")),
    "west":  float(os.getenv("BBOX_W", "73.0")),
}
GRID_STEP = 0.1          # °, Open-Meteo native resolution
FORECAST_DAYS = 4        # gives 96 hours; we take first 90
RAW_DIR = Path(os.getenv("RAW_DIR", "data/raw"))
RAW_DIR.mkdir(parents=True, exist_ok=True)

OM_URL = "https://api.open-meteo.com/v1/forecast"

# Cached session: avoids re-downloading if run twice within 1 hour
_session = retry(
    requests_cache.CachedSession(str(RAW_DIR / ".om_cache"), expire_after=3600),
    retries=5,
    backoff_factor=0.4,
)


# ── Grid generation ───────────────────────────────────────────────────────────
def build_grid_points() -> list[tuple[float, float]]:
    """Generate lat/lon pairs covering the catchment at GRID_STEP resolution."""
    lats = np.arange(BBOX["south"], BBOX["north"] + GRID_STEP, GRID_STEP)
    lons = np.arange(BBOX["west"],  BBOX["east"]  + GRID_STEP, GRID_STEP)
    return [(round(lat, 2), round(lon, 2)) for lat in lats for lon in lons]


# ── Single-point fetch ────────────────────────────────────────────────────────
def fetch_point(lat: float, lon: float, start_dt: datetime) -> np.ndarray:
    """
    Fetch 90-hr hourly precipitation (mm/hr) for one lat/lon.
    Returns np.ndarray shape (90,).
    """
    params = {
        "latitude":      lat,
        "longitude":     lon,
        "hourly":        "precipitation",
        "models":        "ecmwf_ifs",        # Open-Meteo re-serves ECMWF IFS
        "forecast_days": FORECAST_DAYS,
        "timezone":      "UTC",
        "start_date":    start_dt.strftime("%Y-%m-%d"),
        "end_date":      (start_dt + timedelta(days=FORECAST_DAYS)).strftime("%Y-%m-%d"),
    }
    resp = _session.get(OM_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    hourly = data.get("hourly", {})
    times  = hourly.get("time", [])
    precip = hourly.get("precipitation", [])

    # Align to start_dt and take 90 hours
    df = pd.DataFrame({"time": pd.to_datetime(times, utc=True), "precip": precip})
    df = df[df["time"] >= start_dt].head(90)

    if len(df) < 90:
        log.warning("Incomplete data for (%.2f, %.2f): got %d of 90 hours", lat, lon, len(df))
        # Pad with 0
        arr = np.zeros(90, dtype=np.float32)
        arr[: len(df)] = df["precip"].fillna(0).values
        return arr

    return df["precip"].fillna(0).values.astype(np.float32)


# ── Batch fetch (all grid points) ────────────────────────────────────────────
def fetch_all_grid(start_dt: datetime) -> xr.Dataset:
    """
    Download precipitation for all catchment grid points.
    Returns xr.Dataset with tp_mm_hr(valid_time, latitude, longitude).
    """
    nc_path = RAW_DIR / f"openmeteo_{start_dt.strftime('%Y%m%d_%H%M')}.nc"
    if nc_path.exists():
        log.info("Cache hit: %s", nc_path)
        return xr.open_dataset(nc_path)

    grid = build_grid_points()
    lats_u = sorted({p[0] for p in grid})
    lons_u = sorted({p[1] for p in grid})
    nlat, nlon = len(lats_u), len(lons_u)

    log.info("Open-Meteo: fetching %d grid points (%dx%d) …", len(grid), nlat, nlon)
    data = np.zeros((90, nlat, nlon), dtype=np.float32)

    lat_idx = {v: i for i, v in enumerate(lats_u)}
    lon_idx = {v: i for i, v in enumerate(lons_u)}

    for lat, lon in grid:
        arr = fetch_point(lat, lon, start_dt)
        data[:, lat_idx[lat], lon_idx[lon]] = arr

    valid_times = [start_dt + timedelta(hours=h) for h in range(1, 91)]

    ds = xr.Dataset(
        {"tp_mm_hr": (["valid_time", "latitude", "longitude"], data)},
        coords={
            "valid_time": valid_times,
            "latitude":   lats_u,
            "longitude":  lons_u,
            "run_time":   np.datetime64(start_dt.replace(tzinfo=None)),
        },
        attrs={
            "source":     "Open-Meteo ECMWF IFS",
            "resolution": "0.1 deg (~11km)",
            "units":      "mm/hr",
            "bbox":       str(BBOX),
        },
    )
    ds.to_netcdf(nc_path, encoding={"tp_mm_hr": {"zlib": True, "complevel": 4}})
    log.info("Saved: %s  (%.1f MB)", nc_path, nc_path.stat().st_size / 1e6)
    return ds


# ── Per-station fetch (for station_selector.py) ──────────────────────────────
def fetch_station_forecast(lat: float, lon: float, start_dt: datetime) -> np.ndarray:
    """
    Fetch 90-hr hourly precipitation for a single gauge station.
    Called by station_selector when no observed data is available.
    """
    return fetch_point(lat, lon, start_dt)


# ── Historical backfill (for calibration / missing cycle) ───────────────────
def fetch_historical(lat: float, lon: float, start: datetime, end: datetime) -> pd.DataFrame:
    """
    Fetch historical ERA5 reanalysis precipitation via Open-Meteo Historical API.
    Use for model calibration and gap-filling observed data.
    Returns DataFrame(time, precip_mm_hr).
    """
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "hourly":     "precipitation",
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date":   end.strftime("%Y-%m-%d"),
        "timezone":   "UTC",
        # Historical endpoint uses ERA5
    }
    url = "https://archive-api.open-meteo.com/v1/archive"
    resp = _session.get(url, params=params, timeout=60)
    resp.raise_for_status()
    d = resp.json()
    return pd.DataFrame({
        "time":         pd.to_datetime(d["hourly"]["time"], utc=True),
        "precip_mm_hr": d["hourly"]["precipitation"],
    })


def run(start_dt: Optional[datetime] = None) -> xr.Dataset:
    """Entry point. If start_dt is None uses current UTC time truncated to 6h."""
    if start_dt is None:
        now = datetime.now(timezone.utc)
        h6  = (now.hour // 6) * 6
        start_dt = now.replace(hour=h6, minute=0, second=0, microsecond=0)
    return fetch_all_grid(start_dt)


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYYMMDD")
    ap.add_argument("--hour", type=int, default=0, help="Run hour: 0, 6, 12, 18")
    args = ap.parse_args()
    if args.date:
        dt = datetime.strptime(f"{args.date}{args.hour:02d}", "%Y%m%d%H").replace(tzinfo=timezone.utc)
    else:
        dt = None
    ds = run(dt)
    print(ds)
    print(f"Max: {float(ds.tp_mm_hr.max()):.2f} mm/hr")
