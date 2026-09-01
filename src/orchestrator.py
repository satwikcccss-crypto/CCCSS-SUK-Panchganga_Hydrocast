"""
HydroCast Pipeline Orchestrator
================================
Runs the full 12-step prediction pipeline for one forecast cycle.

Usage:
    python -m src.orchestrator                    # uses current UTC time
    python -m src.orchestrator --date 20250822 --hour 6
    python -m src.orchestrator --cycle_id CYC_20250822_06

Designed to run:
  - Via GitHub Actions (each step as a separate job)
  - OR directly on Windows Server as a scheduled task (all steps inline)
"""

import argparse
import json
import logging
import os
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import psycopg2
import psycopg2.extras

log = logging.getLogger(__name__)

DB_URL   = os.getenv("DATABASE_URL", "postgresql://hms_app:password@localhost:5432/rainfall_runoff")
DSS_PATH = Path(os.getenv("DSS_PATH", "data/hms/rainfall_input.dss"))


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def step_start(conn, cycle_id: str, step_num: int, step_name: str):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO pipeline_step_log (cycle_id, step_number, step_name, status, start_time)
            VALUES (%s, %s, %s, 'running', NOW())
            ON CONFLICT (cycle_id, step_number)
            DO UPDATE SET status='running', start_time=NOW(), error_message=NULL
        """, (cycle_id, step_num, step_name))
    conn.commit()


def step_done(conn, cycle_id: str, step_num: int, details: dict | None = None):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE pipeline_step_log
            SET status='success', end_time=NOW(), details_json=%s
            WHERE cycle_id=%s AND step_number=%s
        """, (json.dumps(details) if details else None, cycle_id, step_num))
    conn.commit()


def step_fail(conn, cycle_id: str, step_num: int, error: str):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE pipeline_step_log
            SET status='failed', end_time=NOW(), error_message=%s
            WHERE cycle_id=%s AND step_number=%s
        """, (error[:2000], cycle_id, step_num))
        cur.execute("""
            UPDATE simulation_runs SET status='failed', end_time=NOW(), error_message=%s
            WHERE run_id=%s
        """, (error[:2000], cycle_id))
    conn.commit()


@contextmanager
def timed_step(conn, cycle_id, step_num, step_name):
    step_start(conn, cycle_id, step_num, step_name)
    t0 = time.perf_counter()
    try:
        yield
        elapsed = time.perf_counter() - t0
        log.info("Step %02d [%s] OK  %.1fs", step_num, step_name, elapsed)
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        log.error("Step %02d [%s] FAILED (%.1fs): %s", step_num, step_name, elapsed, exc)
        step_fail(conn, cycle_id, step_num, traceback.format_exc())
        raise


# ── Pipeline steps ────────────────────────────────────────────────────────────

def step1_download_weather(conn, cycle_id, run_dt):
    with timed_step(conn, cycle_id, 1, "Open-Meteo Download"):
        from src.ecmwf.open_meteo import run as om_run
        ds = om_run(run_dt)
        step_done(conn, cycle_id, 1, {
            "grid_points": int(ds.latitude.size * ds.longitude.size),
            "lead_hours": 90,
            "max_intensity_mm_hr": float(ds.tp_mm_hr.max()),
        })
        return ds


def step2_fetch_gauges(conn, cycle_id, run_dt):
    with timed_step(conn, cycle_id, 2, "Gauge Station Fetch"):
        from src.processing.gauge_fetcher import fetch_all_gauges
        n_records = fetch_all_gauges(conn, run_dt)
        step_done(conn, cycle_id, 2, {"records_inserted": n_records})


def step3_validate(conn, cycle_id, run_dt):
    with timed_step(conn, cycle_id, 3, "Data Validation"):
        from src.processing.validator import validate_cycle
        report = validate_cycle(conn, run_dt)
        step_done(conn, cycle_id, 3, report)
        if report.get("critical_failures", 0) > 0:
            raise ValueError(f"Critical QC failures: {report}")


def step4_select_stations(conn, cycle_id, run_dt, ds_ecmwf):
    with timed_step(conn, cycle_id, 4, "Station Selection"):
        from src.processing.station_selector import load_stations, select_stations, store_selection
        stations = load_stations(conn)
        results = select_stations(ds_ecmwf, stations, conn, run_dt)
        store_selection(conn, results, run_dt, cycle_id)
        step_done(conn, cycle_id, 4, {
            "subbasins": list(results.keys()),
            "selections": {k: v.selected_station for k, v in results.items()},
        })
        return results


def step5_write_dss(conn, cycle_id, run_dt, results):
    with timed_step(conn, cycle_id, 5, "DSS Write"):
        from src.dss.writer import write_all_subbasins, verify_dss
        pathnames = write_all_subbasins(results, run_dt)
        ok = verify_dss(DSS_PATH, list(results.keys()))
        if not ok:
            raise RuntimeError("DSS verification failed")
        step_done(conn, cycle_id, 5, {"pathnames": pathnames})


def step6_check_params(conn, cycle_id, results):
    with timed_step(conn, cycle_id, 6, "HMS Parameter Check"):
        from src.hms.runner import check_basin_parameters
        check_basin_parameters(conn, list(results.keys()))
        step_done(conn, cycle_id, 6, {"subbasins_checked": len(results)})


def step7_run_hms(conn, cycle_id, run_dt, results):
    with timed_step(conn, cycle_id, 7, "HEC-HMS Execute"):
        from src.hms.runner import run_hms
        run_hms(run_dt, list(results.keys()))
        step_done(conn, cycle_id, 7, {})


def step8_extract_results(conn, cycle_id, run_dt):
    with timed_step(conn, cycle_id, 8, "Result Extraction"):
        from src.hms.runner import read_outlet_hydrograph
        hg = read_outlet_hydrograph(run_dt)
        step_done(conn, cycle_id, 8, {
            "peak_q_m3s":       hg["peak_q"],
            "time_of_peak":     hg["time_of_peak"].isoformat(),
            "total_volume_m3":  hg["total_volume_m3"],
        })
        return hg


def step9_stage_conversion(conn, cycle_id, run_dt, hg):
    with timed_step(conn, cycle_id, 9, "Stage Conversion"):
        from src.hydrology.post_process import convert_and_store_stages
        bridge_forecasts = convert_and_store_stages(conn, hg, cycle_id, run_dt)
        step_done(conn, cycle_id, 9, {
            "bridges": list(bridge_forecasts.keys()),
        })
        return bridge_forecasts


def step10_store_db(conn, cycle_id, run_dt, hg, bridge_forecasts):
    with timed_step(conn, cycle_id, 10, "Postgres Write"):
        from src.db.store_results import store_all
        counts = store_all(conn, cycle_id, run_dt, hg, bridge_forecasts)
        step_done(conn, cycle_id, 10, counts)


def step11_alerts(conn, cycle_id, bridge_forecasts):
    with timed_step(conn, cycle_id, 11, "Alert Evaluation"):
        from src.alerts.evaluator import evaluate_and_notify
        issued = evaluate_and_notify(conn, cycle_id, bridge_forecasts)
        step_done(conn, cycle_id, 11, {"alerts_issued": issued})


def step12_broadcast(conn, cycle_id):
    with timed_step(conn, cycle_id, 12, "Dashboard Broadcast"):
        from src.api.notifier import broadcast_cycle_complete
        broadcast_cycle_complete(cycle_id)
        step_done(conn, cycle_id, 12, {})


# ── Entry point ───────────────────────────────────────────────────────────────

def create_cycle(conn, cycle_id: str, run_dt: datetime):
    """Register this cycle as a simulation run."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO simulation_runs
                (run_id, basin_id, run_name, hms_project_path,
                 control_spec_name, meteorologic_model,
                 sim_start, sim_end, timestep_minutes,
                 forecast_run_time, start_time, status)
            VALUES
                (%s, 'MAIN_BASIN', %s,
                 %s, 'ForecastControl', 'ECMWFMetModel',
                 %s, %s, 60, %s, NOW(), 'running')
            ON CONFLICT (run_id) DO UPDATE SET status='running', start_time=NOW()
        """, (
            cycle_id,
            f"Forecast {run_dt.strftime('%Y-%m-%d %Hz')}",
            str(os.getenv("HMS_PROJECT_DIR", "data/hms/project")),
            run_dt,
            run_dt + timedelta(hours=90),
            run_dt,
        ))
    conn.commit()


def mark_complete(conn, cycle_id: str):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE simulation_runs
            SET status='completed', end_time=NOW()
            WHERE run_id=%s
        """, (cycle_id,))
    conn.commit()


def run_pipeline(run_dt: Optional[datetime] = None, cycle_id: Optional[str] = None):
    if run_dt is None:
        now = datetime.now(timezone.utc)
        h6  = (now.hour // 6) * 6
        run_dt = now.replace(hour=h6, minute=0, second=0, microsecond=0)

    if cycle_id is None:
        cycle_id = f"CYC_{run_dt.strftime('%Y%m%d_%H%M')}"

    log.info("=" * 60)
    log.info("HYDROCAST PIPELINE — cycle %s", cycle_id)
    log.info("Forecast start: %s UTC", run_dt.isoformat())
    log.info("=" * 60)

    t_total = time.perf_counter()
    conn = get_conn()

    try:
        create_cycle(conn, cycle_id, run_dt)

        ds      = step1_download_weather(conn, cycle_id, run_dt)
        step2_fetch_gauges(conn, cycle_id, run_dt)
        step3_validate(conn, cycle_id, run_dt)
        results = step4_select_stations(conn, cycle_id, run_dt, ds)
        step5_write_dss(conn, cycle_id, run_dt, results)
        step6_check_params(conn, cycle_id, results)
        step7_run_hms(conn, cycle_id, run_dt, results)
        hg      = step8_extract_results(conn, cycle_id, run_dt)
        bfcasts = step9_stage_conversion(conn, cycle_id, run_dt, hg)
        step10_store_db(conn, cycle_id, run_dt, hg, bfcasts)
        step11_alerts(conn, cycle_id, bfcasts)
        step12_broadcast(conn, cycle_id)

        mark_complete(conn, cycle_id)
        elapsed = time.perf_counter() - t_total
        log.info("PIPELINE COMPLETE — cycle %s  total=%.1fs", cycle_id, elapsed)

    except Exception:
        log.error("PIPELINE FAILED — cycle %s", cycle_id, exc_info=True)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/pipeline.log"),
        ],
    )
    ap = argparse.ArgumentParser()
    ap.add_argument("--date",     help="YYYYMMDD")
    ap.add_argument("--hour",     type=int, default=0, choices=[0, 6, 12, 18])
    ap.add_argument("--cycle_id", help="Override cycle ID")
    args = ap.parse_args()

    dt = None
    if args.date:
        dt = datetime.strptime(f"{args.date}{args.hour:02d}", "%Y%m%d%H").replace(tzinfo=timezone.utc)

    run_pipeline(dt, args.cycle_id)
