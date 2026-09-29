"""
HEC-DSS Writer
==============
Writes the selected 90-hour hyetographs to HEC-DSS binary format.
Uses pydsstools (pip install pydsstools) – wraps the official HEC-DSSVue Java lib.

Convention (matches HMS_Automation_RJKT.gage / Met_1.met, 1HOUR modelling choice):
  //<GAGE>/PRECIP-INC/<start>/1HOUR/GAGE/
  e.g. //Radhanagari/PRECIP-INC/10SEP2026/1HOUR/GAGE/

The Gage Manager reads precipitation from the HEC-HMS project DSS
(HMS_Automation_RJKT.dss) at the above pathname template.  Subbasins are mapped
to gauges exactly as Met_1.met assigns them; gauges shared by several subbasins
(Salwan → S5/S6/S7) receive a single average hyetograph.  Old records for the
same gauge+run_time are OVERWRITTEN.
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Any

import numpy as np
try:
    from pydsstools.heclib.dss.HecDss import HecDss      # pip install pydsstools
    from pydsstools.core import TimeSeriesContainer, UNDEFINED
except ImportError:
    HecDss = None
    TimeSeriesContainer = None
    UNDEFINED = -9999.0

from src.ecmwf.station_selector import SubbasinRainfall

log = logging.getLogger(__name__)

# Subbasin → precipitation gauge assignment from Met_1.met (Specified Average).
SUBBASIN_TO_GAGE = {
    "S1": "Karvir",
    "S2": "Sangarul",
    "S3": "kotoli",
    "S4": "karanjphen",
    "S5": "Salwan",
    "S6": "Salwan",
    "S7": "Salwan",
    "S8": "Beed",
    "S9": "Radhanagari",
}

# Gauge → subbasins that share it (used to average shared-gauge hyetographs).
GAGE_SUBBASINS = {
    gage: [sid for sid, g in SUBBASIN_TO_GAGE.items() if g == gage]
    for gage in set(SUBBASIN_TO_GAGE.values())
}

# HMS Gage Manager reads from the HEC-HMS project DSS next to the .gage file.
DSS_FILE = Path(os.getenv("DSS_PATH", "data/hms/HMS_Automation_RJKT/HMS_Automation_RJKT.dss"))


def _hec_dtime(dt: datetime) -> str:
    """Convert UTC datetime to HEC time string '01JAN2025 06:00:00'."""
    return dt.strftime("%d%b%Y %H:%M:%S").upper()


def write_gage_to_dss(
    dss: Any,
    gage_name: str,
    hyetograph: list[float],
    run_time: datetime,
) -> str:
    """
    Write one gauge's 90-hour hyetograph to an open DSS file.
    Returns the pathname written.
    """
    # HEC-DSS pathname: /A/B/C/D/E/F/
    # A="", B=gauge, C=PRECIP-INC, D=start_date, E=1HOUR, F=GAGE
    start_dt = run_time + timedelta(hours=1)   # first valid hour
    d_part   = start_dt.strftime("%d%b%Y").upper()
    pathname = f"//{gage_name}/PRECIP-INC/{d_part}/1HOUR/GAGE/"

    # Build TimeSeriesContainer
    tsc = TimeSeriesContainer()
    tsc.pathname      = pathname
    tsc.startDateTime = _hec_dtime(start_dt)
    tsc.numberValues  = len(hyetograph)
    tsc.units         = "MM"
    tsc.type          = "INST-VAL"
    tsc.interval      = 60          # minutes
    tsc.values        = [float(v) for v in hyetograph]

    dss.put(tsc)
    log.info("DSS written: %s  (%.1f mm total)", pathname, sum(tsc.values))
    return pathname


def write_all_subbasins(
    results: dict[str, SubbasinRainfall],
    run_time: datetime,
    dss_path: Optional[Path] = None,
) -> list[str]:
    """
    Write all selected subbasin hyetographs to DSS, aggregated per gauge.
    Returns list of pathnames written.
    """
    if HecDss is None:
        raise RuntimeError("pydsstools not installed or Java JDK missing from system PATH")

    dss_path = dss_path or DSS_FILE
    dss_path.parent.mkdir(parents=True, exist_ok=True)

    # Aggregate per-subbasin hyetographs into per-gauge records.
    per_gage = {}
    for sub_id, result in results.items():
        gage = SUBBASIN_TO_GAGE.get(sub_id)
        if gage is None:
            log.warning("No gauge assignment for subbasin %s — skipped", sub_id)
            continue
        per_gage.setdefault(gage, []).append(np.asarray(result.hyetograph, dtype=np.float64))

    written = []
    with HecDss.Open(str(dss_path)) as dss:
        for gage, hyetos in per_gage.items():
            # Shared gauge (e.g. Salwan → S5/S6/S7): one representative record.
            agg = hyetos[0] if len(hyetos) == 1 else np.mean(hyetos, axis=0)
            try:
                pn = write_gage_to_dss(dss, gage, agg.tolist(), run_time)
                written.append(pn)
            except Exception as exc:
                log.error("DSS write failed for %s: %s", gage, exc)
                raise

    log.info("DSS write complete: %d gauges → %s", len(written), dss_path)
    return written


def verify_dss(dss_path: Path, expected_subbasins: list[str]) -> bool:
    """Read back each expected gauge record and verify non-zero values."""
    if HecDss is None:
        return False

    ok = True
    expected_gages = sorted({SUBBASIN_TO_GAGE.get(s) for s in expected_subbasins if s})
    with HecDss.Open(str(dss_path)) as dss:
        for gage in expected_gages:
            catalog = dss.getPathnameList(f"//{gage}/PRECIP-INC/*/1HOUR/GAGE/")
            if not catalog:
                log.error("VERIFY FAIL: No DSS record found for gauge %s", gage)
                ok = False
                continue
            tsc = dss.read(catalog[-1])   # most recent
            total = sum(v for v in tsc.values if v != UNDEFINED)
            if total <= 0:
                log.warning("VERIFY WARN: Zero rainfall in DSS for gauge %s", gage)
            else:
                log.info("VERIFY OK: %s → %.1f mm total", gage, total)
    return ok