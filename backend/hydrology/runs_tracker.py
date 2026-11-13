"""
backend/hydrology/runs_tracker.py
==================================
Compatibility shim for legacy runs_tracker module.

Provides minimal run ledger tracking used by security tests and legacy
orchestrator code. All run data persists in PostgreSQL in production;
this shim provides the file-system fallback used by tests.
"""

import logging
import re
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = PROJECT_ROOT / "data" / "runs"

# Safe run ID pattern. Scheduler emits CYC_YYYYMMDD_HHMM; legacy runs use
# CYC_YYYYMMDD_HHz and manual triggers append _MANUAL. The 8-digit date is
# mandatory, so path traversal via the run ID is impossible.
_RUN_ID_RE = re.compile(r"^CYC_\d{8}_(\d{2}z|\d{4}(_MANUAL)?)$")


def _run_path(runs_dir: Path, run_id: str) -> Path:
    """Return the filesystem path for a run ID, preventing path traversal."""
    if not run_id or not _RUN_ID_RE.match(run_id):
        raise ValueError(f"Unsafe run ID: {run_id!r}")
    return runs_dir / f"{run_id}.json"


def get_computation_run(run_id: str) -> Optional[dict[str, Any]]:
    """Look up a computation run by ID. Returns None for invalid IDs."""
    if not run_id or not _RUN_ID_RE.match(run_id):
        return None
    try:
        p = _run_path(RUNS_DIR, run_id)
    except ValueError:
        return None
    if p.exists():
        try:
            import json
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_computation_run(run_id: str, data: dict[str, Any]) -> None:
    """Persist a computation run record."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    p = _run_path(RUNS_DIR, run_id)
    p.write_text(__import__("json").dumps(data, indent=2, default=str), encoding="utf-8")


def list_computation_runs(limit: Optional[int] = None) -> list[dict[str, Any]]:
    """List all stored computation runs from data/runs ledger.
    
    Returns newest-first list of run records with KPIs and summary metadata.
    """
    if not RUNS_DIR.exists():
        return []
    
    index_file = RUNS_DIR / "runs_index.json"
    if index_file.exists():
        try:
            import json
            raw = json.loads(index_file.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                # Ensure each record has summary and cycle_id
                for r in raw:
                    if isinstance(r, dict):
                        r.setdefault("summary", {
                            "peak_arrival": r.get("lead_hours_to_peak", 0),
                            "peak_discharge_m3s": r.get("peak_discharge_m3s", 0),
                            "total_volume_mcm": r.get("total_volume_mcm", 0),
                            "alert_level": r.get("alert_level", "NORMAL"),
                        })
                return raw[:limit] if limit is not None else raw
        except Exception as e:
            log.warning("Failed to parse runs_index.json: %s", e)

    # Fallback to scanning individual CYC_*.json files
    runs = []
    cyc_files = sorted(RUNS_DIR.glob("CYC_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if limit is not None:
        cyc_files = cyc_files[:limit]

    import json
    for p in cyc_files:
        if _RUN_ID_RE.match(p.stem):
            try:
                run_data = json.loads(p.read_text(encoding="utf-8"))
                runs.append({
                    "cycle_id": p.stem,
                    "run_date": run_data.get("summary", {}).get("run_date", ""),
                    "start_time": run_data.get("summary", {}).get("start_time", ""),
                    "duration_seconds": run_data.get("summary", {}).get("duration_seconds", 0),
                    "peak_discharge_m3s": run_data.get("summary", {}).get("peak_discharge_m3s", 0),
                    "lead_hours_to_peak": run_data.get("summary", {}).get("peak_arrival", 0),
                    "total_volume_mcm": run_data.get("summary", {}).get("total_volume_mcm", 0),
                    "alert_level": run_data.get("summary", {}).get("alert_level", "NORMAL"),
                    "status": run_data.get("status", "completed"),
                    "summary": run_data.get("summary", {}),
                    "validation": run_data.get("validation", {}),
                })
            except Exception:
                continue
    return runs


__all__ = ["RUNS_DIR", "_run_path", "get_computation_run", "save_computation_run", "list_computation_runs"]
