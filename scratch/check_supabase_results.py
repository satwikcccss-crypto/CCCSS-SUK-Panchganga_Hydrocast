"""
HydroCast Panchganga: Supabase PostgreSQL Inspector & Data Verification Tool
============================================================================
Checks and displays all data stored in your Supabase PostgreSQL database:
- Table inventory and row counts
- All simulation runs in `simulation_runs`
- All accuracy metrics in `forecast_validation_metrics`
- Sample 90-hr hydrographs in `hydrograph_results`
- Bridge stage projections in `bridge_stage_forecasts`
"""

import sys
import os
import getpass
from urllib.parse import quote_plus
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("psycopg2 is required. Run: pip install psycopg2-binary")
    sys.exit(1)


def build_conn_url():
    """Constructs connection URI from env or interactive prompt."""
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("Usage:")
        print("  python scratch/check_supabase_results.py [PASSWORD_OR_URI]")
        print("Examples:")
        print("  python scratch/check_supabase_results.py")
        print("  python scratch/check_supabase_results.py MySecretPass123")
        print("  python scratch/check_supabase_results.py 'postgresql://postgres.oaranobpxwstubkxrzuu:pass@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require'")
        sys.exit(0)

    url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SUPABASE_DB_URL")
        or os.getenv("SUPABASE_DATABASE_URL")
    )
    if len(sys.argv) > 1 and sys.argv[1].startswith("postgres"):
        return sys.argv[1]

    if url and "password" not in url.lower():
        return url

    print("=" * 75)
    print(" HydroCast Panchganga - Supabase PostgreSQL Database Inspector")
    print("=" * 75)
    print("Host:     aws-0-ap-south-1.pooler.supabase.com")
    print("Port:     6543")
    print("Database: postgres")
    print("User:     postgres.oaranobpxwstubkxrzuu")
    print("-" * 75)

    # If password passed as CLI argument
    if len(sys.argv) > 1:
        pwd = sys.argv[1]
    else:
        pwd = getpass.getpass("Enter your Supabase Database Password: ")

    encoded_pwd = quote_plus(pwd.strip())
    conn_url = f"postgresql://postgres.oaranobpxwstubkxrzuu:{encoded_pwd}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
    return conn_url


def main():
    conn_url = build_conn_url()

    print("\nConnecting to Supabase PostgreSQL (IPv4 Pooler)...")
    try:
        conn = psycopg2.connect(conn_url, connect_timeout=10)
        print("✓ Connected successfully to Supabase PostgreSQL!\n")
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Verify your database password in Supabase Dashboard (Project Settings -> Database).")
        print("2. If your password has special characters, they are auto-encoded.")
        print("3. Ensure Supabase project is active (not paused).")
        sys.exit(1)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1. Table inventory and row counts
    print("=" * 75)
    print(" 1. TABLE INVENTORY & RECORD COUNTS")
    print("=" * 75)
    target_tables = [
        "simulation_runs",
        "forecast_validation_metrics",
        "hydrograph_results",
        "bridge_stage_forecasts",
        "rating_curves",
        "subbasins",
        "gauge_stations"
    ]

    for tbl in target_tables:
        try:
            cur.execute(f"SELECT COUNT(*) AS cnt FROM {tbl};")
            cnt = cur.fetchone()["cnt"]
            status = f"✓ {cnt} rows" if cnt > 0 else "⚠ 0 rows (Empty)"
            print(f"  - {tbl:<32} : {status}")
        except Exception:
            conn.rollback()
            print(f"  - {tbl:<32} : ✖ Table does not exist yet")

    # 2. Master simulation runs
    print("\n" + "=" * 75)
    print(" 2. RECORDED SIMULATION RUNS (simulation_runs)")
    print("=" * 75)
    try:
        cur.execute("""
            SELECT run_id, cycle_date, cycle_time, peak_discharge_m3s, 
                   peak_stage_m, lead_hours_to_peak, alert_level, 
                   spearman_rho, nse_score, created_at
            FROM simulation_runs
            ORDER BY created_at DESC
            LIMIT 20;
        """)
        runs = cur.fetchall()
        if not runs:
            print("  (No simulation runs recorded in database yet)")
        else:
            print(f"  {'Run ID':<20} {'Date':<12} {'Time':<6} {'Peak Q (m3/s)':<14} {'Peak Stg':<10} {'LeadH':<6} {'Spearman':<10} {'NSE'}")
            print("  " + "-" * 88)
            for r in runs:
                rho = f"{float(r['spearman_rho']):.3f}" if r['spearman_rho'] is not None else "-"
                nse = f"{float(r['nse_score']):.3f}" if r['nse_score'] is not None else "-"
                print(f"  {r['run_id']:<20} {str(r['cycle_date']):<12} {r['cycle_time']:<6} {str(r['peak_discharge_m3s']):<14} {str(r['peak_stage_m']):<10} {str(r['lead_hours_to_peak']):<6} {rho:<10} {nse}")
    except Exception as e:
        conn.rollback()
        print(f"  Error reading simulation_runs: {e}")

    # 3. Forecast validation metrics
    print("\n" + "=" * 75)
    print(" 3. FORECAST ACCURACY & VALIDATION METRICS (forecast_validation_metrics)")
    print("=" * 75)
    try:
        cur.execute("""
            SELECT run_id, sample_size_hours, mae_stage_m, rmse_stage_m, 
                   nse_stage, spearman_rho, pbias_stage_pct, performance_grade
            FROM forecast_validation_metrics
            ORDER BY id DESC
            LIMIT 20;
        """)
        metrics = cur.fetchall()
        if not metrics:
            print("  (No validation metrics recorded in database yet)")
        else:
            print(f"  {'Run ID':<20} {'Hours':<6} {'MAE (m)':<10} {'RMSE (m)':<10} {'NSE Stage':<12} {'Spearman':<10} {'PBIAS %':<10} {'Grade'}")
            print("  " + "-" * 90)
            for m in metrics:
                mae = f"{float(m['mae_stage_m']):.3f}" if m['mae_stage_m'] is not None else "-"
                rmse = f"{float(m['rmse_stage_m']):.3f}" if m['rmse_stage_m'] is not None else "-"
                nse = f"{float(m['nse_stage']):.3f}" if m['nse_stage'] is not None else "-"
                rho = f"{float(m['spearman_rho']):.3f}" if m['spearman_rho'] is not None else "-"
                pbias = f"{float(m['pbias_stage_pct']):.2f}%" if m['pbias_stage_pct'] is not None else "-"
                print(f"  {m['run_id']:<20} {str(m['sample_size_hours']):<6} {mae:<10} {rmse:<10} {nse:<12} {rho:<10} {pbias:<10} {m.get('performance_grade', '-')}")
    except Exception as e:
        conn.rollback()
        print(f"  Error reading forecast_validation_metrics: {e}")

    # 4. Hydrograph sample
    print("\n" + "=" * 75)
    print(" 4. HYDROGRAPH FLOW TIME-SERIES SAMPLE (hydrograph_results)")
    print("=" * 75)
    try:
        cur.execute("""
            SELECT run_id, hour_offset, forecast_timestamp, discharge_m3s, stage_m, is_peak
            FROM hydrograph_results
            ORDER BY id DESC
            LIMIT 10;
        """)
        hgs = cur.fetchall()
        if not hgs:
            print("  (No hydrograph records recorded in database yet)")
        else:
            print(f"  {'Run ID':<20} {'Hour':<6} {'Timestamp':<25} {'Discharge (m3/s)':<18} {'Stage (m)':<10} {'Peak'}")
            print("  " + "-" * 88)
            for h in hgs:
                print(f"  {h['run_id']:<20} {str(h['hour_offset']):<6} {str(h['forecast_timestamp']):<25} {str(h['discharge_m3s']):<18} {str(h['stage_m']):<10} {'★ YES' if h['is_peak'] else 'No'}")
    except Exception as e:
        conn.rollback()
        print(f"  Error reading hydrograph_results: {e}")

    print("\n" + "=" * 75)
    cur.close()
    conn.close()
    print("Inspection complete.")


if __name__ == "__main__":
    main()
