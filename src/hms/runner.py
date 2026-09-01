"""
HEC-HMS Automation Runner
==========================
Two-part automation:
  1. Python patches .control, .met, .basin files for the current run.
  2. Invokes HEC-HMS in headless/batch mode via subprocess.
  3. Post-run: reads DSS results → extracts Peak Q, Time of Peak, Total Volume.

HEC-HMS Commander (batch mode):
  Windows: HEC-HMS.exe -Dstudy=<path>.hms -Dscript=run.jy
  Linux:   hec-hms.sh  -Dstudy=<path>.hms -Dscript=run.jy
  → run.jy is a Jython script placed inside the HMS project dir.

Requires HEC-HMS 4.10+ installed.
Env vars: HMS_HOME, HMS_PROJECT_DIR, HMS_CONTROL_SPEC, HMS_RUN_NAME
"""

import logging
import os
import re
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
from pydsstools.heclib.dss.HecDss import HecDss
from pydsstools.core import TimeSeriesContainer, UNDEFINED

log = logging.getLogger(__name__)

HMS_HOME        = Path(os.getenv("HMS_HOME",        r"C:\HEC\HEC-HMS-4.11"))
HMS_PROJECT_DIR = Path(os.getenv("HMS_PROJECT_DIR", "data/hms/project"))
HMS_PROJECT_HMS = HMS_PROJECT_DIR / os.getenv("HMS_PROJECT_NAME", "GodavariBasin.hms")
HMS_DSS_IN      = Path(os.getenv("HMS_DSS_IN",  "data/hms/rainfall_input.dss"))
HMS_DSS_OUT     = HMS_PROJECT_DIR / "GodavariBasin.dss"   # HMS writes here
SINK_NODE       = os.getenv("HMS_SINK_NODE", "J_Outlet")

# ── 1. Patch HMS control spec ─────────────────────────────────────────────────

def patch_control_spec(run_time: datetime, duration_hours: int = 90):
    """
    Update the .control file so HMS simulates exactly [run_time, run_time+90h].
    Preserves all other control spec settings.
    """
    ctrl_file = next(HMS_PROJECT_DIR.glob("*.control"))
    text = ctrl_file.read_text()

    start_str = run_time.strftime("%d %B %Y, %H:%M")           # e.g. '22 August 2025, 06:00'
    end_dt    = run_time + timedelta(hours=duration_hours)
    end_str   = end_dt.strftime("%d %B %Y, %H:%M")

    text = re.sub(r"(Start Date:\s*).*",  rf"\g<1>{start_str}", text)
    text = re.sub(r"(End Date:\s*).*",    rf"\g<1>{end_str}",   text)
    text = re.sub(r"(Start Time:\s*).*",  rf"\g<1>{run_time.strftime('%H:%M')}", text)
    text = re.sub(r"(End Time:\s*).*",    rf"\g<1>{end_dt.strftime('%H:%M')}",   text)
    text = re.sub(r"(Time Interval:\s*).*", r"\g<1>60",         text)   # 60-min step

    ctrl_file.write_text(text)
    log.info("Patched control spec: %s → %s", start_str, end_str)


def patch_met_model(subbasin_ids: list[str]):
    """
    Update the .met file to point each subbasin at the correct DSS pathname.
    DSS pathnames must match what dss/writer.py wrote:
      /GODAVARI/<sub_id>/PRECIP-INC/<date>/1HOUR/ECMWF-GAUGE-SEL/
    """
    met_file = next(HMS_PROJECT_DIR.glob("*.met"))
    text = met_file.read_text()

    for sub_id in subbasin_ids:
        # Replace DSS file path and pathname for each subbasin rain gage entry
        pattern = rf"(Subbasin:\s+{re.escape(sub_id)}.*?DSS Pathname:\s*)\"[^\"]*\""
        replacement = rf'\g<1>"/{sub_id.upper()}/PRECIP-INC//1HOUR/ECMWF-GAUGE-SEL/"'
        text = re.sub(pattern, replacement, text, flags=re.DOTALL)

        # Also update DSS file path reference
        pattern_file = rf"(Subbasin:\s+{re.escape(sub_id)}.*?DSS File:\s*)\"[^\"]*\""
        text = re.sub(pattern_file, rf'\g<1>"{str(HMS_DSS_IN)}"', text, flags=re.DOTALL)

    met_file.write_text(text)
    log.info("Patched met model for %d subbasins", len(subbasin_ids))


# ── 2. Run HMS ────────────────────────────────────────────────────────────────

def _hms_executable() -> Path:
    if os.name == "nt":
        return HMS_HOME / "bin" / "HEC-HMS.exe"
    else:
        return HMS_HOME / "bin" / "hec-hms.sh"


def write_jython_script(run_name: str) -> Path:
    """
    Generate the Jython (*.jy) script HMS will execute in headless mode.
    This uses the HEC-HMS internal API.
    """
    jy_path = HMS_PROJECT_DIR / "autorun.jy"
    jy_path.write_text(f"""\
# HEC-HMS Jython automation script
from hms.model.Project import Project
from hms.hecmath.HecMath import HecMath

# Open project
p = Project.open("{HMS_PROJECT_HMS}")
rm = p.getRunManager()

# Compute named run
run = rm.getElement("{run_name}")
if run is None:
    raise Exception("Run not found: {run_name}")

print "Starting HMS compute: " + run.getName()
run.compute()
print "HMS compute finished."

# Close
p.close()
""")
    return jy_path


def run_hms(run_time: datetime, subbasin_ids: list[str], timeout: int = 600) -> str:
    """
    Patch files, execute HMS, return run_id.
    timeout: seconds before giving up.
    """
    cycle_tag = run_time.strftime("%Y%m%d_%H%M")
    run_name  = os.getenv("HMS_RUN_NAME", "ForecastRun")

    patch_control_spec(run_time)
    patch_met_model(subbasin_ids)
    jy_path = write_jython_script(run_name)

    exe = _hms_executable()
    cmd = [
        str(exe),
        f"-Dstudy={HMS_PROJECT_HMS}",
        f"-Dscript={jy_path}",
        "-headless",
    ]
    log.info("Launching HMS: %s", " ".join(cmd))

    t0 = time.perf_counter()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(HMS_PROJECT_DIR),
    )
    elapsed = time.perf_counter() - t0

    if result.returncode != 0:
        log.error("HMS STDERR:\n%s", result.stderr[-3000:])
        raise RuntimeError(f"HEC-HMS exited with code {result.returncode}")

    log.info("HMS completed in %.1fs", elapsed)
    return cycle_tag


# ── 3. Extract Results ────────────────────────────────────────────────────────

def read_outlet_hydrograph(run_time: datetime, outlet_node: str = SINK_NODE) -> dict:
    """
    Read the discharge time series at the sink node from HMS output DSS.
    Returns:
      {
        'hydrograph':  [(timestamp, q_m3s), ...],   # length 90
        'peak_q':      float,                        # m³/s
        'time_of_peak': datetime (UTC),
        'total_volume_m3': float,                    # m³
        'surface_runoff_volume_m3': float,
      }
    """
    # HMS DSS pathname for flow at outlet:
    # /GODAVARI/J_OUTLET/FLOW//1HOUR/RUN:<name>/
    # Try to find automatically by scanning the catalog
    with HecDss.Open(str(HMS_DSS_OUT)) as dss:
        catalog = dss.getPathnameList(f"//{outlet_node.upper()}/FLOW/*/1HOUR/*/")
        if not catalog:
            raise FileNotFoundError(f"No FLOW record for {outlet_node} in {HMS_DSS_OUT}")

        # Take most recent record
        pathname = sorted(catalog)[-1]
        log.info("Reading: %s", pathname)
        tsc: TimeSeriesContainer = dss.read(pathname)

    q_vals = np.array([v if v != UNDEFINED else np.nan for v in tsc.values], dtype=np.float64)
    q_vals = np.nan_to_num(q_vals, nan=0.0)

    start_dt  = datetime.strptime(tsc.startDateTime, "%d%b%Y %H:%M:%S").replace(tzinfo=timezone.utc)
    timestamps = [start_dt + timedelta(hours=i) for i in range(len(q_vals))]

    # Peak
    peak_idx    = int(np.argmax(q_vals))
    peak_q      = float(q_vals[peak_idx])
    time_of_peak = timestamps[peak_idx]

    # Total volume: Q (m³/s) × 3600 s/hr × sum over 90 hours
    total_vol = float(np.sum(q_vals) * 3600.0)

    log.info(
        "Outlet %s → Peak Q=%.1f m³/s at %s | Vol=%.2e m³",
        outlet_node, peak_q, time_of_peak.isoformat(), total_vol,
    )

    return {
        "hydrograph":              list(zip(timestamps, q_vals.tolist())),
        "peak_q":                  peak_q,
        "time_of_peak":            time_of_peak,
        "lead_hours_to_peak":      peak_idx + 1,
        "total_volume_m3":         total_vol,
    }


def check_basin_parameters(conn, subbasin_ids: list[str]):
    """
    Read CN, Lag, K, X, Ia from model_calibration table.
    Logs a warning if any parameter is missing or stale (> 365 days).
    """
    from datetime import date
    with conn.cursor() as cur:
        params = ["CN", "Lag", "K", "X", "Ia"]
        for sub in subbasin_ids:
            for param in params:
                cur.execute("""
                    SELECT parameter_value, calibration_date, is_current
                    FROM model_calibration
                    WHERE basin_id=%s AND parameter_name=%s AND is_current=TRUE
                    ORDER BY calibration_date DESC LIMIT 1
                """, (sub, param))
                row = cur.fetchone()
                if row is None:
                    log.warning("MISSING PARAM: %s / %s — HMS will use default!", sub, param)
                elif (date.today() - row[1]).days > 365:
                    log.warning("STALE PARAM: %s / %s last calibrated %s", sub, param, row[1])
                else:
                    log.debug("PARAM OK: %s / %s = %.4f", sub, param, row[0])
