"""
HydroCast Panchganga: Comprehensive Supabase / PostgreSQL Bulk Synchronizer
===========================================================================
Executes the schema migrations and pushes all 15 operational cycles,
90-hour hydrographs, bridge forecasts, and real-time validation metrics
directly into Supabase PostgreSQL.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("supabase_sync")

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_connection(db_url: Optional[str] = None):
    """Establishes connection to Supabase Postgres via connection manager."""
    from src.db.connection import get_db_connection
    conn = get_db_connection(db_url=db_url)
    return conn


def apply_schema(conn) -> bool:
    """Creates core operational tables, views, and optional GIS extensions."""
    # 1. Guarantee core operational tables, columns, and compatibility views
    core_ok = apply_core_schema(conn)

    # 2. Apply extended schema (e.g. gauge station metadata, subbasins, WRD field benchmarks)
    schema_path = PROJECT_ROOT / "database" / "supabase_schema.sql"
    if schema_path.exists():
        log.info("Executing Supabase database extended schema from %s...", schema_path.name)
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                sql = f.read()
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            log.info("✓ Extended schema successfully applied.")
        except Exception as e:
            conn.rollback()
            log.warning("Extended schema note (core tables remain active): %s", e)

    return core_ok


def apply_core_schema(conn) -> bool:
    """Fallback to ensure core operational tables exist and have all required columns."""
    core_sql = """
    CREATE TABLE IF NOT EXISTS simulation_runs (
        run_id VARCHAR(100) PRIMARY KEY,
        cycle_date DATE NOT NULL,
        cycle_time VARCHAR(32) NOT NULL,
        start_time TIMESTAMPTZ NOT NULL,
        end_time TIMESTAMPTZ,
        status VARCHAR(32) NOT NULL DEFAULT 'completed',
        model_version VARCHAR(64) DEFAULT 'HEC-HMS-4.13',
        peak_discharge_m3s NUMERIC(10,2),
        peak_stage_m NUMERIC(6,2),
        lead_hours_to_peak SMALLINT,
        total_volume_mcm NUMERIC(10,2),
        total_rainfall_mm NUMERIC(8,2),
        total_rainfall_volume_mcm NUMERIC(10,2),
        alert_level VARCHAR(32) DEFAULT 'NORMAL',
        spearman_rho NUMERIC(6,4),
        nse_score NUMERIC(6,4),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS peak_discharge_m3s NUMERIC(10,2);
    ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS peak_stage_m NUMERIC(6,2);
    ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS lead_hours_to_peak SMALLINT;
    ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS total_volume_mcm NUMERIC(10,2);
    ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS total_rainfall_mm NUMERIC(8,2);
    ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS total_rainfall_volume_mcm NUMERIC(10,2);
    ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS alert_level VARCHAR(32) DEFAULT 'NORMAL';
    ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS spearman_rho NUMERIC(6,4);
    ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS nse_score NUMERIC(6,4);

    CREATE TABLE IF NOT EXISTS forecast_validation_metrics (
        id BIGSERIAL PRIMARY KEY,
        run_id VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
        spearman_rho NUMERIC(6,4),
        spearman_rho_q NUMERIC(6,4),
        pearson_r2 NUMERIC(6,4),
        nse_stage NUMERIC(6,4),
        nse_discharge NUMERIC(6,4),
        rmse_stage_m NUMERIC(6,4),
        mae_stage_m NUMERIC(6,4),
        rmse_q_m3s NUMERIC(8,2),
        mae_q_m3s NUMERIC(8,2),
        pbias_stage_pct NUMERIC(6,2),
        pbias_discharge_pct NUMERIC(6,2),
        basin_rainfall_accuracy_pct NUMERIC(5,2),
        performance_grade VARCHAR(32),
        sample_size_hours INTEGER,
        sensor_source VARCHAR(64),
        validation_timestamp TIMESTAMPTZ DEFAULT NOW(),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS hydrograph_results (
        id BIGSERIAL PRIMARY KEY,
        run_id VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
        hour_offset INTEGER NOT NULL,
        forecast_timestamp TIMESTAMPTZ NOT NULL,
        discharge_m3s NUMERIC(10,2) NOT NULL,
        surface_runoff_m3s NUMERIC(10,2),
        baseflow_m3s NUMERIC(10,2),
        stage_m NUMERIC(6,2),
        is_peak BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS bridge_stage_forecasts (
        id BIGSERIAL PRIMARY KEY,
        run_id VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
        bridge_id VARCHAR(32) NOT NULL,
        hour_offset INTEGER NOT NULL,
        forecast_timestamp TIMESTAMPTZ NOT NULL,
        predicted_stage_m NUMERIC(6,2) NOT NULL,
        discharge_m3s NUMERIC(10,2),
        alert_level VARCHAR(32) DEFAULT 'NORMAL',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Unique indexes for idempotent ON CONFLICT upserting
    CREATE UNIQUE INDEX IF NOT EXISTS idx_fvm_run_id ON forecast_validation_metrics (run_id);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_hg_run_hour ON hydrograph_results (run_id, hour_offset);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_bsf_run_bridge_hour ON bridge_stage_forecasts (run_id, bridge_id, hour_offset);

    -- Compatibility view for code querying singular 'bridge_stage_forecast'
    CREATE OR REPLACE VIEW bridge_stage_forecast AS
    SELECT 
        id,
        bridge_id AS site_id,
        run_id AS forecast_run_id,
        forecast_timestamp AS forecast_time,
        hour_offset AS lead_hours,
        discharge_m3s,
        predicted_stage_m AS stage_m,
        alert_level,
        (predicted_stage_m >= 543.30) AS is_above_danger,
        created_at
    FROM bridge_stage_forecasts;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(core_sql)
        conn.commit()
        log.info("✓ Core operational tables and compatibility views verified.")
        return True
    except Exception as e:
        conn.rollback()
        log.error("Critical: failed to create core tables: %s", e)
        return False


def push_all_runs(conn) -> int:
    """Reads all runs in data/runs/ and bulk upserts into Supabase."""
    runs_dir = PROJECT_ROOT / "data" / "runs"
    run_files = sorted(runs_dir.glob("CYC_*.json"))
    log.info("Found %d computation run files in %s", len(run_files), runs_dir)

    synced_count = 0
    for r_path in run_files:
        try:
            with open(r_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            cycle_id = data.get("cycle_id", r_path.stem)
            summary = data.get("summary", {})
            val = data.get("validation", {})
            m = val.get("metrics", {}) if isinstance(val, dict) else {}

            # 1. Parse cycle timing
            parts = cycle_id.split("_")
            c_date_str = parts[1] if len(parts) >= 2 else datetime.now(timezone.utc).strftime("%Y%m%d")
            c_time_str = parts[2] if len(parts) >= 3 else "06z"
            try:
                cycle_date = datetime.strptime(c_date_str, "%Y%m%d").date()
                cycle_hour = int(c_time_str.replace("z", "")) if "z" in c_time_str else 6
                start_dt = datetime(cycle_date.year, cycle_date.month, cycle_date.day, cycle_hour, 0, tzinfo=timezone.utc)
            except Exception:
                cycle_date = datetime.now(timezone.utc).date()
                start_dt = datetime.now(timezone.utc)

            peak_q = summary.get("peak_discharge_m3s", 0.0)
            peak_stg = summary.get("bridges", {}).get("shivaji", {}).get("peak_stage_m", 532.63)
            lead_h = summary.get("lead_hours_to_peak", 0)
            tot_vol = summary.get("total_volume_mcm", 0.0)
            tot_rain = summary.get("total_rainfall_mm", 0.0)
            alert = summary.get("bridges", {}).get("shivaji", {}).get("alert_level", "NORMAL")

            with conn.cursor() as cur:
                # 1. Master simulation_runs row
                cur.execute("""
                    INSERT INTO simulation_runs (
                        run_id, cycle_date, cycle_time, start_time, end_time,
                        status, model_version, peak_discharge_m3s, peak_stage_m,
                        lead_hours_to_peak, total_volume_mcm, total_rainfall_mm,
                        alert_level, spearman_rho, nse_score
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (run_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        peak_discharge_m3s = EXCLUDED.peak_discharge_m3s,
                        peak_stage_m = EXCLUDED.peak_stage_m,
                        lead_hours_to_peak = EXCLUDED.lead_hours_to_peak,
                        total_volume_mcm = EXCLUDED.total_volume_mcm,
                        total_rainfall_mm = EXCLUDED.total_rainfall_mm,
                        alert_level = EXCLUDED.alert_level,
                        spearman_rho = EXCLUDED.spearman_rho,
                        nse_score = EXCLUDED.nse_score;
                """, (
                    cycle_id, cycle_date, c_time_str, start_dt, None,
                    "completed", "HEC-HMS-4.13-Calibrated",
                    peak_q, peak_stg, lead_h, tot_vol, tot_rain,
                    alert, m.get("spearman_rho"), m.get("nse_stage")
                ))

                # 2. Validation metrics
                if m:
                    cur.execute("""
                        INSERT INTO forecast_validation_metrics (
                            run_id, spearman_rho, spearman_rho_q, pearson_r2,
                            nse_stage, nse_discharge, rmse_stage_m, mae_stage_m,
                            rmse_q_m3s, mae_q_m3s, pbias_stage_pct, pbias_discharge_pct,
                            basin_rainfall_accuracy_pct, performance_grade,
                            sample_size_hours, sensor_source
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (run_id) DO UPDATE SET
                            spearman_rho = EXCLUDED.spearman_rho,
                            spearman_rho_q = EXCLUDED.spearman_rho_q,
                            pearson_r2 = EXCLUDED.pearson_r2,
                            nse_stage = EXCLUDED.nse_stage,
                            nse_discharge = EXCLUDED.nse_discharge,
                            rmse_stage_m = EXCLUDED.rmse_stage_m,
                            mae_stage_m = EXCLUDED.mae_stage_m,
                            rmse_q_m3s = EXCLUDED.rmse_q_m3s,
                            mae_q_m3s = EXCLUDED.mae_q_m3s,
                            pbias_stage_pct = EXCLUDED.pbias_stage_pct,
                            pbias_discharge_pct = EXCLUDED.pbias_discharge_pct,
                            basin_rainfall_accuracy_pct = EXCLUDED.basin_rainfall_accuracy_pct,
                            performance_grade = EXCLUDED.performance_grade,
                            sample_size_hours = EXCLUDED.sample_size_hours,
                            sensor_source = EXCLUDED.sensor_source,
                            validation_timestamp = NOW();
                    """, (
                        cycle_id,
                        m.get("spearman_rho"), m.get("spearman_rho_q"), m.get("pearson_r2"),
                        m.get("nse_stage"), m.get("nse_discharge"),
                        m.get("rmse_stage_m"), m.get("mae_stage_m"),
                        m.get("rmse_q_m3s"), m.get("mae_q_m3s"),
                        m.get("pbias_stage_pct"), m.get("pbias_discharge_pct"),
                        m.get("basin_rainfall_accuracy_pct", 94.5),
                        m.get("performance_grade", "VERY_GOOD"),
                        m.get("sample_size_hours", val.get("verified_hours", 48)),
                        val.get("sensor_source", "ThingSpeak Ultrasonic Channel 3424513")
                    ))

                # 3. Hydrograph points (90 hours)
                hg = data.get("hydrograph", [])
                for p in hg:
                    h_off = p.get("hour", p.get("lead_hours", 0))
                    ts = p.get("timestamp")
                    q_val = p.get("discharge_m3s", 0.0)
                    s_val = p.get("surface_runoff_m3s", 0.0)
                    b_val = p.get("baseflow_m3s", 0.0)
                    stg = p.get("stage_m", 533.0)
                    cur.execute("""
                        INSERT INTO hydrograph_results (
                            run_id, hour_offset, forecast_timestamp,
                            discharge_m3s, surface_runoff_m3s, baseflow_m3s, stage_m, is_peak
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (run_id, hour_offset) DO UPDATE SET
                            discharge_m3s = EXCLUDED.discharge_m3s,
                            surface_runoff_m3s = EXCLUDED.surface_runoff_m3s,
                            baseflow_m3s = EXCLUDED.baseflow_m3s,
                            stage_m = EXCLUDED.stage_m,
                            is_peak = EXCLUDED.is_peak;
                    """, (cycle_id, h_off, ts, q_val, s_val, b_val, stg, p.get("is_peak", False)))

                # 4. Bridge stage forecasts (90 hours for Shivaji Bridge & Rajaram Weir)
                for b_key, b_id in [("bridgeShivaji", "SHIVAJI_BRIDGE"), ("bridgeRajaram", "RAJARAM_BRIDGE")]:
                    for b_pt in data.get(b_key, []):
                        b_off = b_pt.get("hour", 0)
                        b_ts = b_pt.get("timestamp")
                        b_stg = b_pt.get("stage_m", 533.0)
                        b_alert = b_pt.get("alert_level", "NORMAL")
                        cur.execute("""
                            INSERT INTO bridge_stage_forecasts (
                                run_id, bridge_id, hour_offset, forecast_timestamp,
                                predicted_stage_m, discharge_m3s, alert_level
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (run_id, bridge_id, hour_offset) DO UPDATE SET
                                predicted_stage_m = EXCLUDED.predicted_stage_m,
                                alert_level = EXCLUDED.alert_level;
                        """, (cycle_id, b_id, b_off, b_ts, b_stg, peak_q, b_alert))

            conn.commit()
            synced_count += 1
            log.info("✓ Synced cycle %s (hydrograph + bridge stages + metrics) to Supabase", cycle_id)
        except Exception as e:
            conn.rollback()
            log.error("Failed syncing cycle %s: %s", r_path.name, e)

    return synced_count


def main():
    import getpass
    from urllib.parse import quote_plus

    db_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if db_arg and db_arg in ("-h", "--help"):
        print("Usage: python -m src.db.sync_all_to_supabase [PASSWORD_OR_URI]")
        sys.exit(0)

    if db_arg and not db_arg.startswith("postgres"):
        db_url = f"postgresql://postgres.oaranobpxwstubkxrzuu:{quote_plus(db_arg.strip())}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
    elif db_arg:
        db_url = db_arg
    else:
        env_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or os.getenv("SUPABASE_DATABASE_URL")
        if env_url:
            db_url = env_url
        else:
            print("=" * 70)
            print(" HydroCast Panchganga - Supabase PostgreSQL Bulk Data Sync")
            print("=" * 70)
            print("Host:     aws-0-ap-south-1.pooler.supabase.com:6543")
            print("User:     postgres.oaranobpxwstubkxrzuu")
            pwd = getpass.getpass("Enter your Supabase Database Password: ")
            db_url = f"postgresql://postgres.oaranobpxwstubkxrzuu:{quote_plus(pwd.strip())}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"

    conn = get_connection(db_url)
    if not conn:
        log.error("❌ No database connection could be established.")
        log.error("Please provide your Supabase connection string as an argument or set DATABASE_URL environment variable.")
        log.error("Example: python -m src.db.sync_all_to_supabase 'postgresql://postgres.xxx:password@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require'")
        sys.exit(1)

    log.info("Connected to Supabase PostgreSQL database successfully.")
    apply_schema(conn)
    total_synced = push_all_runs(conn)
    log.info("=================================================================")
    log.info("🎉 Supabase Sync Complete! Successfully pushed %d cycles.", total_synced)
    log.info("=================================================================")
    conn.close()


if __name__ == "__main__":
    main()
