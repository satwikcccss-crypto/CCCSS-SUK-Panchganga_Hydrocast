"""
HEC-DSS Writer
===============
Writes the selected 90-hour hyetographs to HEC-DSS binary format.
Uses pydsstools (pip install pydsstools) – wraps the official HEC-DSSVue Java lib.

DSS pathname convention:
  /BASIN/SUBBASIN/PRECIP-INC//1HOUR/ECMWF-GAUGE-SEL/
  e.g. /GODAVARI/SUB_01/PRECIP-INC//1HOUR/ECMWF-GAUGE-SEL/

One record per subbasin per cycle.  Old record for same subbasin+run_time
is OVERWRITTEN (HEC-HMS reads the latest interval matching its control spec).
"""

import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
from pydsstools.heclib.dss.HecDss import HecDss      # pip install pydsstools
from pydsstools.core import TimeSeriesContainer, UNDEFINED

from processing.station_selector import SubbasinRainfall

log = logging.getLogger(__name__)

# Configured in environment / system_config.json
DSS_FILE = Path("data/hms/rainfall_input.dss")
BASIN_NAME = "GODAVARI"     # top-level DSS A-part


def _hec_dtime(dt: datetime) -> str:
    """Convert UTC datetime to HEC time string '01JAN2025 06:00:00'."""
    return dt.strftime("%d%b%Y %H:%M:%S").upper()


def write_subbasin_to_dss(
    dss: HecDss,
    sub_id: str,
    result: SubbasinRainfall,
    run_time: datetime,
) -> str:
    """
    Write one subbasin hyetograph to an open DSS file.
    Returns the pathname written.
    """
    # DSS pathname: /A/B/C/D/E/F/
    # A=basin, B=subbasin, C=parameter, D=start_date, E=interval, F=version
    start_dt = run_time + timedelta(hours=1)   # first valid hour
    d_part   = start_dt.strftime("%d%b%Y").upper()
    pathname = (
        f"/{BASIN_NAME}/{sub_id}/PRECIP-INC/{d_part}/1HOUR/ECMWF-GAUGE-SEL/"
    )

    # Build TimeSeriesContainer
    tsc = TimeSeriesContainer()
    tsc.pathname      = pathname
    tsc.startDateTime = _hec_dtime(start_dt)
    tsc.numberValues  = 90
    tsc.units         = "MM"
    tsc.type          = "INST-VAL"
    tsc.interval      = 60          # minutes
    tsc.values        = [float(v) for v in result.hyetograph]

    dss.put(tsc)
    log.info("DSS written: %s  (%.1f mm total)", pathname, sum(result.hyetograph))
    return pathname


def write_all_subbasins(
    results: dict[str, SubbasinRainfall],
    run_time: datetime,
    dss_path: Optional[Path] = None,
) -> list[str]:
    """
    Write all selected subbasin hyetographs to DSS.
    Returns list of pathnames written.
    """
    dss_path = dss_path or DSS_FILE
    dss_path.parent.mkdir(parents=True, exist_ok=True)

    written = []
    with HecDss.Open(str(dss_path)) as dss:
        for sub_id, result in results.items():
            try:
                pn = write_subbasin_to_dss(dss, sub_id, result, run_time)
                written.append(pn)
            except Exception as exc:
                log.error("DSS write failed for %s: %s", sub_id, exc)
                raise

    log.info("DSS write complete: %d subbasins → %s", len(written), dss_path)
    return written


def verify_dss(dss_path: Path, expected_subbasins: list[str]) -> bool:
    """Read back each written record and verify non-zero values."""
    ok = True
    with HecDss.Open(str(dss_path)) as dss:
        for sub_id in expected_subbasins:
            catalog = dss.getPathnameList(f"/{BASIN_NAME}/{sub_id}/PRECIP-INC/*/1HOUR/ECMWF-GAUGE-SEL/")
            if not catalog:
                log.error("VERIFY FAIL: No DSS record found for %s", sub_id)
                ok = False
                continue
            tsc = dss.read(catalog[-1])   # most recent
            total = sum(v for v in tsc.values if v != UNDEFINED)
            if total <= 0:
                log.warning("VERIFY WARN: Zero rainfall in DSS for %s", sub_id)
            else:
                log.info("VERIFY OK: %s → %.1f mm total", sub_id, total)
    return ok
