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

# Safe run ID pattern: CYC_YYYYMMDD_HHz only
_RUN_ID_RE = re.compile(r"^CYC_\d{8}_\d{2}z$")


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


def list_computation_runs() -> list[str]:
    """List all stored computation run IDs."""
    if not RUNS_DIR.exists():
        return []
    return sorted(
        p.stem for p in RUNS_DIR.glob("CYC_*.json") if _RUN_ID_RE.match(p.stem)
    )


__all__ = ["RUNS_DIR", "_run_path", "get_computation_run", "save_computation_run", "list_computation_runs"]
