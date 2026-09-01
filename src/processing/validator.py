"""
src/processing/validator.py
============================
QC checks on each forecast cycle before DSS write + HMS execution.
Fails fast on critical issues, logs warnings for degraded data.
"""

import logging
from datetime import datetime, timezone, timedelta

log = logging.getLogger(__name__)

MAX_VALID_MM_HR  = 500.0   # physical upper bound (mm/hr)
MIN_COVERAGE_PCT = 50.0    # minimum % of 90 expected hours present
MAX_LAG_MINUTES  = 60      # gauge data older than this → degraded
ECMWF_MAX_AGE_HR = 8       # ECMWF data must be fresher than this


def validate_cycle(conn, run_dt: datetime) -> dict:
    """
    Run all QC checks. Returns report dict with:
      critical_failures: int  (> 0 → abort pipeline)
      warnings:          int
      details:           list[str]
    """
    report = {"critical_failures": 0, "warnings": 0, "details": []}

    _check_ecmwf_freshness(conn, run_dt, report)
    _check_gauge_coverage(conn, run_dt, report)
    _check_gauge_range(conn, run_dt, report)
    _check_gauge_lag(conn, run_dt, report)

    log.info(
        "QC report: %d critical, %d warnings",
        report["critical_failures"], report["warnings"],
    )
    for d in report["details"]:
        log.info("QC: %s", d)

    return report


def _check_ecmwf_freshness(conn, run_dt: datetime, report: dict):
    """ECMWF data must be available and recent."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT MAX(forecast_run_time) FROM subbasin_rainfall_ts
            WHERE source_id='ecmwf_ifs'
        """)
        row = cur.fetchone()

    latest = row[0]
    if latest is None:
        report["critical_failures"] += 1
        report["details"].append("CRITICAL: No ECMWF data in subbasin_rainfall_ts")
        return

    age_hr = (run_dt - latest.replace(tzinfo=timezone.utc)).total_seconds() / 3600
    if age_hr > ECMWF_MAX_AGE_HR:
        report["critical_failures"] += 1
        report["details"].append(
            f"CRITICAL: ECMWF data age {age_hr:.1f}h > {ECMWF_MAX_AGE_HR}h threshold"
        )
    else:
        report["details"].append(f"OK: ECMWF data age {age_hr:.1f}h")


def _check_gauge_coverage(conn, run_dt: datetime, report: dict):
    """Each gauge must have ≥ MIN_COVERAGE_PCT of expected 90 hourly records."""
    start = run_dt
    end   = run_dt + timedelta(hours=90)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT gauge_id, COUNT(*) AS n
            FROM rainfall_data
            WHERE timestamp >= %s AND timestamp < %s AND is_active IS DISTINCT FROM FALSE
            GROUP BY gauge_id
        """, (start, end))
        rows = cur.fetchall()

    gauge_counts = {r[0]: r[1] for r in rows}
    for gid, count in gauge_counts.items():
        pct = count / 90 * 100
        if pct < MIN_COVERAGE_PCT:
            report["warnings"] += 1
            report["details"].append(f"WARN: {gid} coverage {pct:.0f}% < {MIN_COVERAGE_PCT}%")
        else:
            report["details"].append(f"OK: {gid} coverage {pct:.0f}%")

    if not gauge_counts:
        report["warnings"] += 1
        report["details"].append("WARN: No gauge records in rainfall_data for this cycle window")


def _check_gauge_range(conn, run_dt: datetime, report: dict):
    """Rainfall values must be 0 ≤ x ≤ MAX_VALID_MM_HR."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT gauge_id, MAX(rainfall_mm) AS max_mm, MIN(rainfall_mm) AS min_mm
            FROM rainfall_data
            WHERE timestamp >= %s AND timestamp < %s
            GROUP BY gauge_id
        """, (run_dt, run_dt + timedelta(hours=90)))
        rows = cur.fetchall()

    for gid, max_mm, min_mm in rows:
        if min_mm < 0:
            report["warnings"] += 1
            report["details"].append(f"WARN: {gid} has negative rainfall ({min_mm:.1f}mm) — clipped to 0")
        if max_mm > MAX_VALID_MM_HR:
            report["warnings"] += 1
            report["details"].append(
                f"WARN: {gid} max {max_mm:.1f} mm/hr > physical limit {MAX_VALID_MM_HR} — suspect"
            )


def _check_gauge_lag(conn, run_dt: datetime, report: dict):
    """Latest gauge record should not be older than MAX_LAG_MINUTES."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT gauge_id, MAX(timestamp) AS latest
            FROM rainfall_data
            WHERE timestamp >= %s
            GROUP BY gauge_id
        """, (run_dt - timedelta(hours=6),))
        rows = cur.fetchall()

    now = datetime.now(timezone.utc)
    for gid, latest in rows:
        if latest is None:
            continue
        lag_min = (now - latest.replace(tzinfo=timezone.utc)).total_seconds() / 60
        if lag_min > MAX_LAG_MINUTES:
            report["warnings"] += 1
            report["details"].append(f"WARN: {gid} lag {lag_min:.0f}min > {MAX_LAG_MINUTES}min")
