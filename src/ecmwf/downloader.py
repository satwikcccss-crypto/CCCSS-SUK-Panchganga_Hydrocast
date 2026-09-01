"""
ECMWF IFS 9km Rainfall Downloader
===================================
Downloads total precipitation from ECMWF IFS HRES forecast.
- Public path  : ecmwf-opendata (0.25° / 28km, free, no account)
- 9km HRES path: requires ECMWF MARS credentials → set USE_MARS=True

Output: /data/raw/ecmwf_<YYYYMMDD>_<HHz>.nc  (NetCDF, hourly TP mm/hr)
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import xarray as xr
import cfgrib                       # pip install cfgrib
from ecmwf.opendata import Client   # pip install ecmwf-opendata

# ── If you have ECMWF MARS credentials (for true 9km HRES) ──────────────────
USE_MARS = os.getenv("USE_MARS", "false").lower() == "true"
if USE_MARS:
    import ecmwfapi                 # pip install ecmwf-api-client

log = logging.getLogger(__name__)

# ── Study area bounding box (adjust to your catchment) ──────────────────────
BBOX = {
    "north": float(os.getenv("BBOX_N", "22.0")),
    "south": float(os.getenv("BBOX_S", "17.0")),
    "east":  float(os.getenv("BBOX_E", "78.5")),
    "west":  float(os.getenv("BBOX_W", "73.0")),
}

# 90-hour window at 1-hour steps → lead times 1..90
LEAD_HOURS = list(range(1, 91))          # hours 1–90

RAW_DIR = Path(os.getenv("RAW_DIR", "data/raw"))
RAW_DIR.mkdir(parents=True, exist_ok=True)


def latest_available_run() -> tuple[str, str]:
    """Return (YYYYMMDD, HHz) of latest complete ECMWF run available (6h lag)."""
    now_utc = datetime.now(timezone.utc) - timedelta(hours=6)
    # ECMWF runs at 00z and 12z
    run_hour = "00" if now_utc.hour < 12 else "12"
    return now_utc.strftime("%Y%m%d"), run_hour + "z"


def download_opendata(date: str, time: str, out_path: Path) -> Path:
    """
    Download ECMWF Open Data (free, 0.25°).
    param date: 'YYYYMMDD'
    param time: '00z' or '12z'
    Returns path to downloaded GRIB2 file.
    """
    grib_path = out_path.with_suffix(".grib2")
    if grib_path.exists():
        log.info("GRIB2 already cached: %s", grib_path)
        return grib_path

    client = Client(source="ecmwf")  # or source="azure" / "aws"
    log.info("Downloading ECMWF Open Data: date=%s time=%s steps=%s", date, time, LEAD_HOURS)

    client.retrieve(
        date=date,
        time=time.replace("z", ""),
        step=LEAD_HOURS,
        stream="oper",
        type="fc",
        levtype="sfc",
        param="tp",                  # total precipitation (m, accumulated)
        target=str(grib_path),
    )
    log.info("Downloaded: %s (%.1f MB)", grib_path, grib_path.stat().st_size / 1e6)
    return grib_path


def download_mars_9km(date: str, time: str, out_path: Path) -> Path:
    """
    Download true IFS HRES at 9km (~0.083°) via ECMWF MARS API.
    Requires: ~/.ecmwfapirc with KEY, EMAIL, URL
    """
    grib_path = out_path.with_suffix(".grib2")
    if grib_path.exists():
        return grib_path

    server = ecmwfapi.ECMWFService("mars")
    server.execute({
        "class":    "od",
        "date":     date[:4] + "-" + date[4:6] + "-" + date[6:],
        "expver":   "1",
        "grid":     "0.083/0.083",       # ~9km
        "levtype":  "sfc",
        "param":    "228.128",            # total precipitation MARS param
        "step":     "/".join(str(h) for h in LEAD_HOURS),
        "stream":   "oper",
        "time":     time.replace("z", "") + ":00:00",
        "type":     "fc",
        "area":     f"{BBOX['north']}/{BBOX['west']}/{BBOX['south']}/{BBOX['east']}",
        "format":   "grib2",
        "target":   str(grib_path),
    })
    return grib_path


def grib_to_hourly_nc(grib_path: Path, out_nc: Path) -> xr.Dataset:
    """
    Convert accumulated TP (m) GRIB2 → hourly intensity mm/hr NetCDF.
    ECMWF stores TP as accumulated from run start → diff to get hourly.
    """
    log.info("Decoding GRIB2: %s", grib_path)
    ds_list = cfgrib.open_datasets(str(grib_path))

    # Find TP dataset
    tp_ds = next(d for d in ds_list if "tp" in d)
    tp = tp_ds["tp"]                      # shape: (step, lat, lon), units: m

    # Crop to study bbox
    lat_mask = (tp.latitude >= BBOX["south"]) & (tp.latitude <= BBOX["north"])
    lon_mask = (tp.longitude >= BBOX["west"]) & (tp.longitude <= BBOX["east"])
    tp = tp.sel(latitude=lat_mask, longitude=lon_mask)

    # De-accumulate: hourly = current_accum - previous_accum
    # Step 1 has no previous → step 1 == accumulated from 0
    tp_vals = tp.values           # (90, nlat, nlon)
    hourly = np.zeros_like(tp_vals)
    hourly[0] = tp_vals[0]
    hourly[1:] = np.diff(tp_vals, axis=0)
    hourly = np.maximum(hourly, 0)        # clip small negatives from floating point

    # Convert m → mm/hr
    hourly_mm = hourly * 1000.0

    # Build valid_time coordinate
    run_dt = tp.time.values  # numpy datetime64
    valid_times = [run_dt + np.timedelta64(h, "h") for h in LEAD_HOURS]

    ds_out = xr.Dataset(
        {"tp_mm_hr": (["valid_time", "latitude", "longitude"], hourly_mm)},
        coords={
            "valid_time": valid_times,
            "latitude":   tp.latitude.values,
            "longitude":  tp.longitude.values,
            "run_time":   run_dt,
        },
        attrs={
            "source":     "ECMWF IFS HRES",
            "resolution": "0.083 deg (~9km)" if USE_MARS else "0.25 deg (Open Data)",
            "units":      "mm/hr",
            "lead_hours": "1-90",
        },
    )
    ds_out.to_netcdf(out_nc, encoding={"tp_mm_hr": {"zlib": True, "complevel": 4}})
    log.info("Saved hourly NetCDF: %s", out_nc)
    return ds_out


def run(date: str | None = None, time: str | None = None) -> xr.Dataset:
    """
    Main entry point.
    Returns xr.Dataset with tp_mm_hr(valid_time, lat, lon).
    """
    if date is None or time is None:
        date, time = latest_available_run()

    out_nc = RAW_DIR / f"ecmwf_{date}_{time.replace('z','z')}.nc"
    if out_nc.exists():
        log.info("Cache hit: %s", out_nc)
        return xr.open_dataset(out_nc)

    grib_path = RAW_DIR / f"ecmwf_{date}_{time}"
    if USE_MARS:
        grib_path = download_mars_9km(date, time, grib_path)
    else:
        grib_path = download_opendata(date, time, grib_path)

    return grib_to_hourly_nc(grib_path, out_nc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ds = run()
    print(ds)
    print(f"Shape: {ds.tp_mm_hr.shape}")
    print(f"Max intensity: {float(ds.tp_mm_hr.max()):.2f} mm/hr")
