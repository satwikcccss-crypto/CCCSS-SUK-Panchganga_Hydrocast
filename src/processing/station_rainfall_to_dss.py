"""
Open-Meteo Forecast v1 API — Station Rainfall Downloader & HEC-DSS Converter
=============================================================================
Downloads hourly precipitation forecasts from Open-Meteo API v1 for user-defined
rain gauge stations or subbasin centroids, exports to structured CSV time series,
and converts to HEC-DSS format (.dss) ready for HEC-HMS hydrological simulation.

Features:
  - Flexible CSV reader supporting custom column formats (e.g. 'Raingauge_Station', 'Longitude (X)', 'Latitude (Y)').
  - Direct Open-Meteo v1 Forecast API ingestion (ECMWF IFS / Best Match models).
  - Subbasin Centroid calculation option (--use-centroids).
  - Export individual and combined station rainfall CSVs.
  - Generates HEC-HMS subbasin max-cumulative hyetographs.
  - Converts to binary HEC-DSS (.dss) via pydsstools or DSSVue tabular/Jython scripts.

Usage:
  # Run with user's station CSV:
  python station_rainfall_to_dss.py --stations-csv data/stations/raingauge_stations.csv

  # Run with 90-hour forecast and custom output dir:
  python station_rainfall_to_dss.py --stations-csv data/stations/raingauge_stations.csv --hours 90 --output-dir data/output_rainfall

  # Run using Subbasin Centroid aggregation:
  python station_rainfall_to_dss.py --stations-csv data/stations/raingauge_stations.csv --use-centroids
"""

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Tuple

import numpy as np
import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("HydroCast.OpenMeteo")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass
class Station:
    station_id: str
    station_name: str
    subbasin_id: str
    latitude: float
    longitude: float
    elevation_m: float = 0.0


@dataclass
class StationForecast:
    station: Station
    timestamps: List[datetime]
    lead_hours: List[int]
    precipitation_mm_hr: List[float]
    cumulative_mm: List[float]
    total_precipitation_mm: float
    peak_intensity_mm_hr: float
    time_of_peak: datetime


# ── Flexible CSV Loader ───────────────────────────────────────────────────────
def load_stations_from_csv(csv_path: Path) -> List[Station]:
    """
    Load stations from CSV supporting diverse column naming conventions:
      - Name/ID: 'Raingauge_Station', 'Station', 'station_id', 'station_name', 'Name'
      - Longitude: 'Longitude (X)', 'Longitude', 'lon', 'x', 'Long'
      - Latitude:  'Latitude (Y)', 'Latitude', 'lat', 'y', 'Lat'
      - Subbasin:  'Subbasin_ID', 'subbasin_id', 'Subbasin', 'Basin'
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Stations CSV not found at: {csv_path}")

    # Try comma, tab, or semicolon separated
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        df = pd.read_csv(csv_path, sep=r"\s+")

    # Standardize column mapping
    cols = {c.strip().lower(): c for c in df.columns}

    # Find Name / ID column
    name_col = None
    for candidate in ["raingauge_station", "station_id", "station_name", "station", "name", "stn_name"]:
        if candidate in cols:
            name_col = cols[candidate]
            break
    if not name_col:
        name_col = df.columns[0]

    # Find Longitude column
    lon_col = None
    for candidate in ["longitude (x)", "longitude", "lon", "long", "x", "longitude_x", "longitude_deg"]:
        if candidate in cols:
            lon_col = cols[candidate]
            break

    # Find Latitude column
    lat_col = None
    for candidate in ["latitude (y)", "latitude", "lat", "y", "latitude_y", "latitude_deg"]:
        if candidate in cols:
            lat_col = cols[candidate]
            break

    if not lon_col or not lat_col:
        raise ValueError(
            f"Could not identify Longitude and Latitude columns in {csv_path}. Columns present: {list(df.columns)}"
        )

    # Find Subbasin column (optional)
    subbasin_col = None
    for candidate in ["subbasin_id", "subbasin", "sub_basin", "basin_id", "basin", "watershed"]:
        if candidate in cols:
            subbasin_col = cols[candidate]
            break

    # Find Elevation column (optional)
    elev_col = None
    for candidate in ["elevation_m", "elevation", "elev", "z", "altitude"]:
        if candidate in cols:
            elev_col = cols[candidate]
            break

    stations: List[Station] = []
    seen_ids = set()

    for idx, row in df.iterrows():
        raw_name = str(row[name_col]).strip()
        if not raw_name or raw_name.lower() == "nan":
            continue

        # Deduplicate duplicate rows if any
        if raw_name in seen_ids:
            continue
        seen_ids.add(raw_name)

        lat = float(row[lat_col])
        lon = float(row[lon_col])
        sub = str(row[subbasin_col]).strip() if subbasin_col else f"SUB_{idx + 1:02d}"
        elev = float(row[elev_col]) if elev_col and pd.notna(row[elev_col]) else 0.0

        st_id = raw_name.replace(" ", "_").upper()
        stations.append(
            Station(
                station_id=st_id,
                station_name=raw_name,
                subbasin_id=sub,
                latitude=lat,
                longitude=lon,
                elevation_m=elev,
            )
        )

    log.info("Loaded %d unique precipitation stations from %s", len(stations), csv_path.name)
    return stations


def compute_subbasin_centroids(stations: List[Station]) -> List[Station]:
    """
    Group stations by subbasin_id and calculate the centroid (mean lat, mean lon).
    Returns a list of synthetic Station objects representing subbasin centroids.
    """
    sub_groups: Dict[str, List[Station]] = {}
    for st in stations:
        sub_groups.setdefault(st.subbasin_id, []).append(st)

    centroids: List[Station] = []
    for sub_id, st_list in sub_groups.items():
        mean_lat = float(np.mean([s.latitude for s in st_list]))
        mean_lon = float(np.mean([s.longitude for s in st_list]))
        mean_elev = float(np.mean([s.elevation_m for s in st_list]))
        centroids.append(
            Station(
                station_id=f"{sub_id}_CENTROID",
                station_name=f"{sub_id} Subbasin Centroid",
                subbasin_id=sub_id,
                latitude=round(mean_lat, 4),
                longitude=round(mean_lon, 4),
                elevation_m=round(mean_elev, 1),
            )
        )
    log.info("Computed %d Subbasin Centroids from %d stations", len(centroids), len(stations))
    return centroids


# ── Open-Meteo API v1 Downloader ──────────────────────────────────────────────
def fetch_station_rainfall(
    station: Station,
    forecast_hours: int = 90,
    model: Optional[str] = "ecmwf_ifs",
    max_retries: int = 4,
) -> StationForecast:
    """
    Download hourly precipitation forecast from Open-Meteo Forecast v1 API.
    """
    forecast_days = int(np.ceil(forecast_hours / 24)) + 1

    params = {
        "latitude": round(station.latitude, 4),
        "longitude": round(station.longitude, 4),
        "hourly": "precipitation",
        "timezone": "UTC",
        "forecast_days": forecast_days,
    }

    if model and model.lower() not in ["default", "best_match"]:
        params["models"] = model

    log.info(
        "Fetching %s (%s) at (%.4f, %.4f) [forecast_days=%d]...",
        station.station_id,
        station.station_name,
        station.latitude,
        station.longitude,
        forecast_days,
    )

    data = None
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(OPEN_METEO_URL, params=params, timeout=25)
            if resp.status_code == 400 and "models" in params:
                log.warning("Model '%s' returned 400. Falling back to default best_match model...", model)
                params.pop("models", None)
                resp = requests.get(OPEN_METEO_URL, params=params, timeout=25)

            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            last_err = e
            log.warning("Attempt %d/%d for %s failed: %s. Retrying in %ds...", attempt, max_retries, station.station_id, e, attempt * 2)
            time.sleep(attempt * 2)

    if not data or "hourly" not in data:
        raise RuntimeError(f"Failed to fetch rainfall for {station.station_id}: {last_err}")

    hourly = data["hourly"]
    times_raw = hourly.get("time", [])
    precip_raw = hourly.get("precipitation", [])

    # Parse and trim to forecast_hours
    parsed_times: List[datetime] = []
    for t_str in times_raw:
        dt = datetime.fromisoformat(t_str.replace("Z", "+00:00")).astimezone(timezone.utc)
        parsed_times.append(dt)

    precip_vals: List[float] = [max(0.0, float(p)) if p is not None else 0.0 for p in precip_raw]

    # Select the requested number of forecast hours
    times = parsed_times[:forecast_hours]
    precip = precip_vals[:forecast_hours]
    lead_hrs = list(range(len(times)))

    cum_precip = list(np.cumsum(precip))
    total_precip = float(cum_precip[-1]) if cum_precip else 0.0

    peak_intensity = float(np.max(precip)) if precip else 0.0
    peak_idx = int(np.argmax(precip)) if precip else 0
    time_of_peak = times[peak_idx] if times else datetime.now(timezone.utc)

    log.info(
        "✓ %s (%s): %d-hr Total = %.2f mm | Peak Intensity = %.2f mm/hr at T+%dh",
        station.station_id,
        station.station_name,
        len(precip),
        total_precip,
        peak_intensity,
        peak_idx,
    )

    return StationForecast(
        station=station,
        timestamps=times,
        lead_hours=lead_hrs,
        precipitation_mm_hr=precip,
        cumulative_mm=cum_precip,
        total_precipitation_mm=total_precip,
        peak_intensity_mm_hr=peak_intensity,
        time_of_peak=time_of_peak,
    )


# ── CSV Exporter ──────────────────────────────────────────────────────────────
def export_to_csv(
    forecasts: List[StationForecast],
    output_dir: Path,
) -> Dict[str, Path]:
    """
    Save rainfall datasets to structured CSV files:
      1. output/csv/stations/<station_id>_hyetograph.csv
      2. output/csv/all_stations_timeseries.csv
      3. output/csv/stations_summary.csv
      4. output/csv/subbasin_selected_hyetographs.csv
    """
    csv_dir = output_dir / "csv"
    stations_dir = csv_dir / "stations"
    stations_dir.mkdir(parents=True, exist_ok=True)

    exported_files = {}

    # 1. Individual station files
    for fc in forecasts:
        st = fc.station
        df_st = pd.DataFrame({
            "timestamp_utc": [dt.strftime("%Y-%m-%d %H:%M:%S") for dt in fc.timestamps],
            "lead_hour": fc.lead_hours,
            "station_id": st.station_id,
            "station_name": st.station_name,
            "subbasin_id": st.subbasin_id,
            "precipitation_mm_hr": [round(v, 2) for v in fc.precipitation_mm_hr],
            "cumulative_mm": [round(v, 2) for v in fc.cumulative_mm],
        })
        st_path = stations_dir / f"{st.station_id}_hyetograph.csv"
        df_st.to_csv(st_path, index=False)

    # 2. Combined wide matrix CSV
    if forecasts:
        timestamps = [dt.strftime("%Y-%m-%d %H:%M:%S") for dt in forecasts[0].timestamps]
        lead_hrs = forecasts[0].lead_hours
        wide_dict = {
            "timestamp_utc": timestamps,
            "lead_hour": lead_hrs,
        }
        for fc in forecasts:
            wide_dict[f"{fc.station.station_id}_mm_hr"] = [round(v, 2) for v in fc.precipitation_mm_hr]

        df_all = pd.DataFrame(wide_dict)
        all_path = csv_dir / "all_stations_timeseries.csv"
        df_all.to_csv(all_path, index=False)
        exported_files["all_stations_csv"] = all_path

    # 3. Stations summary CSV
    summary_rows = []
    for fc in forecasts:
        st = fc.station
        summary_rows.append({
            "station_id": st.station_id,
            "station_name": st.station_name,
            "subbasin_id": st.subbasin_id,
            "latitude": st.latitude,
            "longitude": st.longitude,
            "elevation_m": st.elevation_m,
            "total_precipitation_mm": round(fc.total_precipitation_mm, 2),
            "peak_intensity_mm_hr": round(fc.peak_intensity_mm_hr, 2),
            "time_of_peak_utc": fc.time_of_peak.strftime("%Y-%m-%d %H:%M:%S"),
        })
    df_summary = pd.DataFrame(summary_rows)
    summary_path = csv_dir / "stations_summary.csv"
    df_summary.to_csv(summary_path, index=False)
    exported_files["summary_csv"] = summary_path

    # 4. Subbasin Selected Hyetographs (HEC-HMS Subbasin Mapping)
    subbasin_groups: Dict[str, List[StationForecast]] = {}
    for fc in forecasts:
        subbasin_groups.setdefault(fc.station.subbasin_id, []).append(fc)

    subbasin_selected = {}
    subbasin_summary_rows = []
    for sub_id, group in subbasin_groups.items():
        best_fc = max(group, key=lambda x: x.total_precipitation_mm)
        subbasin_selected[sub_id] = best_fc
        subbasin_summary_rows.append({
            "subbasin_id": sub_id,
            "selected_station_id": best_fc.station.station_id,
            "selected_station_name": best_fc.station.station_name,
            "total_rainfall_mm": round(best_fc.total_precipitation_mm, 2),
            "candidate_stations": ", ".join([f.station.station_id for f in group]),
        })

    df_sub_summary = pd.DataFrame(subbasin_summary_rows)
    sub_summary_path = csv_dir / "subbasin_station_selection.csv"
    df_sub_summary.to_csv(sub_summary_path, index=False)
    exported_files["subbasin_selection_csv"] = sub_summary_path

    if subbasin_selected and forecasts:
        sub_dict = {
            "timestamp_utc": [dt.strftime("%Y-%m-%d %H:%M:%S") for dt in forecasts[0].timestamps],
            "lead_hour": forecasts[0].lead_hours,
        }
        for sub_id, fc in subbasin_selected.items():
            sub_dict[f"{sub_id}_mm_hr"] = [round(v, 2) for v in fc.precipitation_mm_hr]
        df_sub = pd.DataFrame(sub_dict)
        sub_path = csv_dir / "subbasin_selected_hyetographs.csv"
        df_sub.to_csv(sub_path, index=False)
        exported_files["subbasin_hyetographs_csv"] = sub_path

    log.info("Exported CSV files to: %s", csv_dir.resolve())
    return exported_files


# ── HEC-DSS Exporter ──────────────────────────────────────────────────────────
def export_to_dss(
    forecasts: List[StationForecast],
    output_dir: Path,
    basin_name: str = "PANCHGANGA",
    export_all_stations: bool = True,
) -> Path:
    """
    Convert rainfall hyetographs to HEC-DSS (.dss).
    If pydsstools is installed, directly writes native binary DSS.
    Also produces standard HEC-DSS CSV table and HEC-DSSVue Jython importer script.
    """
    dss_dir = output_dir / "dss"
    dss_dir.mkdir(parents=True, exist_ok=True)
    dss_path = dss_dir / "rainfall_input.dss"

    # Targets to export (both subbasin mappings and station records)
    targets: List[Tuple[str, StationForecast]] = []
    if export_all_stations:
        for fc in forecasts:
            targets.append((fc.station.station_id, fc))

    # Also include subbasin representative records
    subbasin_groups: Dict[str, List[StationForecast]] = {}
    for fc in forecasts:
        subbasin_groups.setdefault(fc.station.subbasin_id, []).append(fc)
    for sub_id, group in subbasin_groups.items():
        best_fc = max(group, key=lambda x: x.total_precipitation_mm)
        targets.append((sub_id, best_fc))

    pydss_written = False
    try:
        from pydsstools.heclib.dss.HecDss import HecDss
        from pydsstools.core import TimeSeriesContainer

        with HecDss.Open(str(dss_path)) as dss:
            for b_part, fc in targets:
                start_dt = fc.timestamps[0]
                d_part = start_dt.strftime("%d%b%Y").upper()
                pathname = f"/{basin_name}/{b_part}/PRECIP-INC/{d_part}/1HOUR/OPENMETEO-V1/"

                tsc = TimeSeriesContainer()
                tsc.pathname = pathname
                tsc.startDateTime = start_dt.strftime("%d%b%Y %H:%M:%S").upper()
                tsc.numberValues = len(fc.precipitation_mm_hr)
                tsc.units = "MM"
                tsc.type = "INST-VAL"
                tsc.interval = 60
                tsc.values = [float(v) for v in fc.precipitation_mm_hr]

                dss.put(tsc)
                log.info("✓ Binary DSS written: %s", pathname)
        log.info("Native HEC-DSS file successfully saved: %s", dss_path)
        pydss_written = True
    except ImportError:
        log.info("pydsstools not installed. Generating DSS tabular files and Jython import automation script...")
    except Exception as e:
        log.warning("Binary DSS write encountered an issue: %s", e)

    # ── Fallback / Auxiliary: HEC-DSSVue Table & Jython Script ─────────────────
    dss_table_path = dss_dir / "hec_dss_rainfall_table.csv"
    with open(dss_table_path, "w") as f:
        f.write("# HEC-DSSVue Tabular Rainfall Import Format\n")
        f.write(f"# Basin: {basin_name} | Generated: {datetime.now(timezone.utc).isoformat()}\n")
        for b_part, fc in targets:
            start_dt = fc.timestamps[0]
            d_part = start_dt.strftime("%d%b%Y").upper()
            f.write(f"\nPATHNAME: /{basin_name}/{b_part}/PRECIP-INC/{d_part}/1HOUR/OPENMETEO-V1/\n")
            f.write("UNITS: MM\nTYPE: INST-VAL\nINTERVAL: 1HOUR\n")
            f.write("DATE,TIME,VALUE\n")
            for dt, val in zip(fc.timestamps, fc.precipitation_mm_hr):
                f.write(f"{dt.strftime('%d%b%Y').upper()},{dt.strftime('%H:%M:%S')},{val:.2f}\n")

    jython_path = dss_dir / "import_rainfall_to_dss.jy"
    jython_code = f"""# Jython script to create/populate {dss_path.name} in HEC-DSSVue
from hec.script import *
from hec.heclib.dss import HecDss
from hec.heclib.util import HecTime
from hec.io import TimeSeriesContainer

dss = HecDss.open("{dss_path.resolve().as_posix()}")

"""
    for b_part, fc in targets:
        start_dt = fc.timestamps[0]
        d_part = start_dt.strftime("%d%b%Y").upper()
        vals_str = ", ".join([f"{v:.2f}" for v in fc.precipitation_mm_hr])
        jython_code += f"""
# Record for {b_part}
tsc = TimeSeriesContainer()
tsc.fullName = "/{basin_name}/{b_part}/PRECIP-INC/{d_part}/1HOUR/OPENMETEO-V1/"
tsc.interval = 60
tsc.units = "MM"
tsc.type = "INST-VAL"
tsc.startTime = HecTime("{start_dt.strftime('%d%b%Y %H:%M:%S').upper()}").value()
tsc.values = [{vals_str}]
tsc.numberValues = len(tsc.values)
dss.put(tsc)
print "Written: " + tsc.fullName
"""
    jython_code += '\ndss.close()\nprint "DSS Import Completed Successfully."\n'

    with open(jython_path, "w") as f:
        f.write(jython_code)

    log.info("DSS Table File  : %s", dss_table_path)
    log.info("HEC-DSSVue Jython: %s", jython_path)
    return dss_path if pydss_written else dss_table_path


# ── Pipeline Runner ───────────────────────────────────────────────────────────
def run_pipeline(
    stations_csv: Optional[Path] = None,
    output_dir: Path = Path("data/openmeteo_dss"),
    forecast_hours: int = 90,
    model: str = "ecmwf_ifs",
    basin_name: str = "PANCHGANGA",
    use_centroids: bool = False,
) -> Dict[str, any]:
    """
    Main workflow:
      1. Load / Parse Station CSV.
      2. Compute Centroids if specified.
      3. Download hourly rainfall from Open-Meteo v1.
      4. Save individual & combined CSV time series.
      5. Convert to HEC-DSS format for HEC-HMS.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if stations_csv and Path(stations_csv).exists():
        stations = load_stations_from_csv(Path(stations_csv))
    else:
        log.info("No CSV specified. Looking for default raingauge_stations.csv...")
        default_csv = Path("data/stations/raingauge_stations.csv")
        if default_csv.exists():
            stations = load_stations_from_csv(default_csv)
        else:
            raise FileNotFoundError("Please provide a valid stations CSV via --stations-csv")

    if use_centroids:
        log.info("Aggregating stations to Subbasin Centroids...")
        stations = compute_subbasin_centroids(stations)

    log.info("=" * 75)
    log.info("HYDROCAST OPEN-METEO V1 FORECAST & HEC-DSS PIPELINE")
    log.info("Forecast Horizon : %d Hours (Hourly Resolution)", forecast_hours)
    log.info("Model Engine     : %s", model or "Open-Meteo Best Match")
    log.info("Basin Identifier : %s", basin_name)
    log.info("Stations Count   : %d stations/centroids", len(stations))
    log.info("Output Directory : %s", output_dir.resolve())
    log.info("=" * 75)

    forecasts: List[StationForecast] = []
    for st in stations:
        fc = fetch_station_rainfall(
            station=st,
            forecast_hours=forecast_hours,
            model=model,
        )
        forecasts.append(fc)

    csv_files = export_to_csv(forecasts, output_dir)
    dss_file = export_to_dss(forecasts, output_dir, basin_name=basin_name)

    log.info("=" * 75)
    log.info("PIPELINE COMPLETED SUCCESSFULLY!")
    log.info("  ✓ Stations Processed    : %d", len(forecasts))
    log.info("  ✓ All Stations CSV      : %s", csv_files.get("all_stations_csv"))
    log.info("  ✓ Stations Summary CSV  : %s", csv_files.get("summary_csv"))
    log.info("  ✓ Subbasin Hyetographs  : %s", csv_files.get("subbasin_hyetographs_csv"))
    log.info("  ✓ HEC-DSS Target File   : %s", dss_file)
    log.info("=" * 75)

    return {
        "status": "success",
        "forecasts": forecasts,
        "csv_files": csv_files,
        "dss_file": dss_file,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download Open-Meteo v1 station precipitation forecasts to CSV and convert to HEC-DSS for simulation."
    )
    parser.add_argument(
        "--stations-csv",
        type=str,
        default="data/stations/raingauge_stations.csv",
        help="Path to CSV containing station coordinates.",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=90,
        help="Number of forecast hours to download (default: 90).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="ecmwf_ifs",
        help="Forecast model (e.g. ecmwf_ifs, best_match, gfs_seamless).",
    )
    parser.add_argument(
        "--basin",
        type=str,
        default="PANCHGANGA",
        help="HEC-DSS top-level basin A-part (default: PANCHGANGA).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/openmeteo_dss",
        help="Output directory for CSV and DSS files (default: data/openmeteo_dss).",
    )
    parser.add_argument(
        "--use-centroids",
        action="store_true",
        help="Calculate and fetch rainfall for Subbasin Centroids instead of individual stations.",
    )

    args = parser.parse_args()

    run_pipeline(
        stations_csv=Path(args.stations_csv),
        output_dir=Path(args.output_dir),
        forecast_hours=args.hours,
        model=args.model,
        basin_name=args.basin,
        use_centroids=args.use_centroids,
    )
