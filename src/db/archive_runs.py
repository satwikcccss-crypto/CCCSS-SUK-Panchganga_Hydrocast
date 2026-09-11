"""
src/db/archive_runs.py
======================
Cold storage & telemetry archival engine for HydroCast.
Exports high-frequency time-series data older than the retention threshold
(default 90 days) into compressed Apache Parquet columnar partitions, then
prunes PostgreSQL tables to maintain sub-second query performance while
preserving executive KPIs and simulation_runs records indefinitely.

Usage:
    python -m src.db.archive_runs --retention-days 90
    python -m src.db.archive_runs --dry-run
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import psycopg2
import psycopg2.extras

from src.db.connection import get_db_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("hydrocast.archival")

DEFAULT_ARCHIVE_DIR = Path(os.getenv("ARCHIVE_DIR", "data/archives"))
DEFAULT_RETENTION_DAYS = int(os.getenv("ARCHIVE_RETENTION_DAYS", "90"))

# Granular tables targeted for cold storage archival
# Format: table_name -> timestamp_column
ARCHIVE_TARGETS = {
    "hydrograph_results": "timestamp",
    "bridge_stage_forecast": "forecast_time",
    "rainfall_data": "timestamp",
    "station_rainfall_telemetry": "created_at",
    "subbasin_rainfall_ts": "valid_time",
}


def get_cutoff_date(retention_days: int) -> datetime:
    """Calculate UTC cutoff timestamp based on retention days."""
    return datetime.now(timezone.utc) - timedelta(days=retention_days)


def archive_table_to_parquet(
    conn,
    table_name: str,
    time_col: str,
    cutoff: datetime,
    archive_root: Path,
    dry_run: bool = False,
    batch_size: int = 50000,
) -> Dict[str, Any]:
    """
    Export rows older than cutoff to Parquet files partitioned by year/month,
    and delete pruned rows from PostgreSQL.
    """
    stats = {
        "table": table_name,
        "rows_identified": 0,
        "rows_archived": 0,
        "files_written": [],
        "bytes_written": 0,
        "status": "skipped",
    }

    # First, count matching records
    with conn.cursor() as cur:
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, (table_name,))
        exists = cur.fetchone()[0]
        if not exists:
            log.info("Table '%s' does not exist in database — skipping", table_name)
            stats["status"] = "table_not_found"
            return stats

        cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {time_col} < %s", (cutoff,))
        total_rows = cur.fetchone()[0]

    stats["rows_identified"] = total_rows
    if total_rows == 0:
        log.info("No records older than %s found in '%s'", cutoff.strftime('%Y-%m-%d'), table_name)
        stats["status"] = "no_data_to_archive"
        return stats

    log.info("Identified %d records in '%s' older than %s to archive", total_rows, table_name, cutoff.strftime('%Y-%m-%d'))
    if dry_run:
        log.info("[DRY RUN] Would export %d records from '%s' to Parquet", total_rows, table_name)
        stats["status"] = "dry_run"
        return stats

    # Query and stream into DataFrame
    query = f"SELECT * FROM {table_name} WHERE {time_col} < %s ORDER BY {time_col} ASC"
    df = pd.read_sql_query(query, conn, params=(cutoff,))

    if df.empty:
        stats["status"] = "empty"
        return stats

    # Ensure datetime format on time_col
    df[time_col] = pd.to_datetime(df[time_col], utc=True)
    df["_year"] = df[time_col].dt.year
    df["_month"] = df[time_col].dt.month

    # Write partitioned Parquet files
    total_bytes = 0
    written_files = []

    for (year, month), group in df.groupby(["_year", "_month"]):
        partition_dir = archive_root / table_name / f"year={year}" / f"month={month:02d}"
        partition_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{table_name}_{year}{month:02d}_{timestamp_str}.parquet"
        file_path = partition_dir / filename

        # Drop temporary partition helper columns
        clean_group = group.drop(columns=["_year", "_month"])
        table = pa.Table.from_pandas(clean_group)
        pq.write_table(table, file_path, compression="SNAPPY")

        file_bytes = file_path.stat().st_size
        total_bytes += file_bytes
        written_files.append(str(file_path))
        log.info("Archived %d rows of '%s' to %s (%.2f KB)", len(clean_group), table_name, file_path, file_bytes / 1024)

    # Prune rows from DB inside transaction
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {table_name} WHERE {time_col} < %s", (cutoff,))
        deleted_count = cur.rowcount
    conn.commit()

    stats["rows_archived"] = deleted_count
    stats["files_written"] = written_files
    stats["bytes_written"] = total_bytes
    stats["status"] = "archived_and_pruned"
    log.info("Pruned %d records from '%s' in PostgreSQL", deleted_count, table_name)
    return stats


def run_archival(
    retention_days: int = DEFAULT_RETENTION_DAYS,
    archive_dir: Path = DEFAULT_ARCHIVE_DIR,
    target_tables: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Master archival runner across all designated time-series tables.
    """
    cutoff = get_cutoff_date(retention_days)
    log.info("=" * 65)
    log.info("HYDROCAST COLD STORAGE TELEMETRY ARCHIVAL")
    log.info("Retention period : %d days (Cutoff: %s UTC)", retention_days, cutoff.strftime("%Y-%m-%d %H:%M:%S"))
    log.info("Archive Root     : %s", archive_dir.resolve())
    log.info("Dry Run Mode     : %s", dry_run)
    log.info("=" * 65)

    conn = get_db_connection()
    if conn is None:
        log.error("Could not establish database connection for archival")
        return {"status": "error", "message": "Database connection unavailable"}

    results = {}
    selected_targets = target_tables or list(ARCHIVE_TARGETS.keys())

    t0 = time.perf_counter()
    try:
        for tbl in selected_targets:
            if tbl not in ARCHIVE_TARGETS:
                log.warning("Table '%s' is not in configured archive targets — skipping", tbl)
                continue
            time_col = ARCHIVE_TARGETS[tbl]
            stats = archive_table_to_parquet(conn, tbl, time_col, cutoff, archive_dir, dry_run=dry_run)
            results[tbl] = stats

        elapsed = time.perf_counter() - t0
        total_archived = sum(r.get("rows_archived", 0) for r in results.values())
        log.info("Archival completed in %.2fs: %d total rows compressed to Parquet", elapsed, total_archived)
        return {
            "status": "success",
            "retention_days": retention_days,
            "cutoff_utc": cutoff.isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "tables": results,
        }
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="HydroCast Telemetry Cold Storage Archival Tool")
    parser.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS, help="Number of days of data to retain in PostgreSQL")
    parser.add_argument("--archive-dir", type=str, default=str(DEFAULT_ARCHIVE_DIR), help="Root directory for Parquet archives")
    parser.add_argument("--tables", type=str, default=None, help="Comma-separated list of tables to archive")
    parser.add_argument("--dry-run", action="store_true", help="Inspect and report without writing parquet or deleting rows")
    args = parser.parse_args()

    tables = [t.strip() for t in args.tables.split(",")] if args.tables else None
    res = run_archival(
        retention_days=args.retention_days,
        archive_dir=Path(args.archive_dir),
        target_tables=tables,
        dry_run=args.dry_run,
    )
    print(f"\nArchival Summary: {res.get('status')}")


if __name__ == "__main__":
    main()
