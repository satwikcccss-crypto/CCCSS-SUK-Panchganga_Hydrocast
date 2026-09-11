"""
tests/test_archival.py
======================
Unit tests for the Parquet archival and time-series pruning logic.
"""

import shutil
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pyarrow.parquet as pq

from src.db.archive_runs import get_cutoff_date, archive_table_to_parquet


class TestArchival(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_cutoff_date(self):
        now = datetime.now(timezone.utc)
        cutoff = get_cutoff_date(30)
        diff = now - cutoff
        self.assertAlmostEqual(diff.total_seconds(), 30 * 86400, delta=5)

    @patch("pandas.read_sql_query")
    def test_archive_table_to_parquet_creates_partitioned_parquet(self, mock_read_sql):
        cutoff = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        # Mock sample rows from hydrograph_results
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "run_id": ["CYC_01", "CYC_01", "CYC_02"],
            "timestamp": [
                "2025-11-15T12:00:00Z",
                "2025-11-15T13:00:00Z",
                "2025-12-01T06:00:00Z",
            ],
            "discharge_m3s": [120.5, 145.0, 98.2],
        })
        mock_read_sql.return_value = df

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        # Mock table exists = True, count = 3
        mock_cur.fetchone.side_effect = [(True,), (3,)]
        mock_cur.rowcount = 3
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        stats = archive_table_to_parquet(
            conn=mock_conn,
            table_name="hydrograph_results",
            time_col="timestamp",
            cutoff=cutoff,
            archive_root=self.test_dir,
            dry_run=False,
        )

        self.assertEqual(stats["status"], "archived_and_pruned")
        self.assertEqual(stats["rows_archived"], 3)
        self.assertEqual(len(stats["files_written"]), 2)  # Nov and Dec partitions

        # Verify reading back the generated Parquet files
        for f in stats["files_written"]:
            table = pq.read_table(f)
            self.assertGreater(table.num_rows, 0)
            self.assertIn("discharge_m3s", table.column_names)

    @patch("pandas.read_sql_query")
    def test_archive_dry_run_does_not_prune_or_write(self, mock_read_sql):
        cutoff = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.side_effect = [(True,), (100,)]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        stats = archive_table_to_parquet(
            conn=mock_conn,
            table_name="rainfall_data",
            time_col="timestamp",
            cutoff=cutoff,
            archive_root=self.test_dir,
            dry_run=True,
        )

        self.assertEqual(stats["status"], "dry_run")
        self.assertEqual(stats["rows_identified"], 100)
        self.assertEqual(len(stats["files_written"]), 0)
        mock_read_sql.assert_not_called()


if __name__ == "__main__":
    unittest.main()
