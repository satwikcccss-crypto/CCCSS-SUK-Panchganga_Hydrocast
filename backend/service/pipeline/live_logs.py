"""In-memory + on-disk live log stream for the operator console."""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOGS_DIR = PROJECT_ROOT / "data" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
ORCH_LOG_FILE = LOGS_DIR / "orchestrator.log"

MAX_MEMORY_LOGS = 500
_LOG_STREAM_BUFFER: List[Dict[str, Any]] = []
_LOG_STREAM_LOCK = threading.Lock()

def emit_live_log(level: str, message: str, step: Optional[int] = None) -> None:
    """Record a log message to both file and WebSocket memory buffer."""
    ts = datetime.now(timezone.utc).isoformat()
    entry = {
        "timestamp": ts,
        "level": level.upper(),
        "step": step,
        "message": message,
    }

    # 1. Write to memory ring-buffer
    with _LOG_STREAM_LOCK:
        _LOG_STREAM_BUFFER.append(entry)
        if len(_LOG_STREAM_BUFFER) > MAX_MEMORY_LOGS:
            _LOG_STREAM_BUFFER.pop(0)

    # 2. Write to disk log file
    line = f"[{ts}] [{level.upper()}] [Step {step or '-'}] {message}\n"
    try:
        with open(ORCH_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

    # 3. Print to stdout
    if level.upper() in ("ERROR", "CRITICAL"):
        log.error(message)
    elif level.upper() == "WARNING":
        log.warning(message)
    else:
        log.info(message)

def get_live_logs(since_ts: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve in-memory logs for the operator console."""
    with _LOG_STREAM_LOCK:
        if since_ts is None:
            return list(_LOG_STREAM_BUFFER[-100:])
        return [entry for entry in _LOG_STREAM_BUFFER if entry["timestamp"] > since_ts]
