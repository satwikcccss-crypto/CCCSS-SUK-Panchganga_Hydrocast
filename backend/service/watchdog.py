"""
backend/service/watchdog.py
===========================
Host supervisor and hardware-telemetry provider for the Operator Console.

Responsibilities
----------------
* Sample real CPU / RAM / disk counters (``psutil`` when available, stdlib
  fallbacks otherwise) — never invented or randomised values.
* Track how long the FastAPI admin service and the scheduler have been up.
* Expose a single supervision cycle that the console polls; it reports
  ``HEALTHY`` / ``DEGRADED`` plus any concrete issues it found.

The module has no import-time side effects and never raises: if a counter
cannot be read it is reported as ``None`` so the UI can render a dash instead
of a fabricated number.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:  # psutil is present on the Windows server image; keep it optional for CI.
    import psutil  # type: ignore
except Exception:  # pragma: no cover - exercised only on minimal installs
    psutil = None  # type: ignore

log = logging.getLogger(__name__)

# CPU above this for a sustained sample is worth flagging to the operator.
_CPU_WARN_PCT = 90.0
_RAM_WARN_PCT = 90.0
_DISK_WARN_PCT = 90.0


def _round(value: Optional[float], digits: int = 1) -> Optional[float]:
    return None if value is None else round(float(value), digits)


def _disk_usage(path: str) -> Optional[Dict[str, Any]]:
    """Usage for one mount point, or ``None`` when it does not exist."""
    if not path or not os.path.exists(path):
        return None
    try:
        usage = shutil.disk_usage(path)
    except OSError as exc:
        log.debug("disk_usage(%s) failed: %s", path, exc)
        return None
    total_gb = usage.total / (1024 ** 3)
    used_gb = usage.used / (1024 ** 3)
    free_gb = usage.free / (1024 ** 3)
    percent = (used_gb / total_gb * 100.0) if total_gb else None
    return {
        "path": path,
        "total_gb": _round(total_gb),
        "used_gb": _round(used_gb),
        "free_gb": _round(free_gb),
        "percent": _round(percent),
    }


class Watchdog:
    """Long-lived supervisor used by ``GET /api/v1/admin/system/health``."""

    def __init__(self) -> None:
        self._started_at = time.time()
        self._started_iso = datetime.now(timezone.utc).isoformat()
        self._checks = 0
        self._last_check_utc: Optional[str] = None
        self._last_status = "UNKNOWN"

    # ── Hardware sampling ────────────────────────────────────────────────────

    def get_hardware_telemetry(self) -> Dict[str, Any]:
        """Return a JSON-safe hardware snapshot. Missing values are ``None``."""
        cpu_percent: Optional[float] = None
        cpu_count: Optional[int] = None
        cpu_model: Optional[str] = None
        ram_percent: Optional[float] = None
        ram_used_gb: Optional[float] = None
        ram_total_gb: Optional[float] = None
        load_average: Optional[List[float]] = None

        if psutil is not None:
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                cpu_count = psutil.cpu_count(logical=True)
            except Exception as exc:  # pragma: no cover - platform specific
                log.debug("psutil CPU sample failed: %s", exc)
            try:
                vm = psutil.virtual_memory()
                ram_percent = float(vm.percent)
                ram_total_gb = vm.total / (1024 ** 3)
                ram_used_gb = vm.used / (1024 ** 3)
            except Exception as exc:  # pragma: no cover
                log.debug("psutil memory sample failed: %s", exc)
        else:
            try:
                cpu_count = os.cpu_count()
                load_average = list(os.getloadavg())  # type: ignore[attr-defined]
                if cpu_count and load_average:
                    cpu_percent = min(100.0, load_average[0] / cpu_count * 100.0)
            except Exception:
                load_average = None

        # CPU model: portable only via /proc on Linux. Windows reports it through
        # the environment/WMI instead; leave it ``None`` rather than invent one.
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.lower().startswith("model name"):
                        cpu_model = line.split(":", 1)[1].strip()
                        break
        except OSError:
            cpu_model = None

        # Windows server: the stack lives on E:; keep C: for completeness.
        drives: Dict[str, Optional[Dict[str, Any]]] = {
            "C:": _disk_usage("C:\\"),
            "E:": _disk_usage("E:\\"),
        }
        disk_c = drives.get("C:")
        disk_e = drives.get("E:")

        process: Dict[str, Any] = {
            "pid": os.getpid(),
            "uptime_seconds": _round(time.time() - self._started_at, 0),
        }
        if psutil is not None:
            try:
                proc = psutil.Process(os.getpid())
                process["rss_mb"] = _round(proc.memory_info().rss / (1024 ** 2))
                process["threads"] = proc.num_threads()
            except Exception:
                pass

        return {
            "sampled_at": datetime.now(timezone.utc).isoformat(),
            "cpu_percent": _round(cpu_percent),
            "cpu_count": cpu_count,
            "cpu_model": cpu_model,
            "load_average": load_average,
            "ram_percent": _round(ram_percent),
            "ram_used_gb": _round(ram_used_gb),
            "ram_total_gb": _round(ram_total_gb),
            "disks": drives,
            "disk_c_used_gb": (disk_c or {}).get("used_gb"),
            "disk_c_total_gb": (disk_c or {}).get("total_gb"),
            "disk_e_used_gb": (disk_e or {}).get("used_gb"),
            "disk_e_total_gb": (disk_e or {}).get("total_gb"),
            "process": process,
        }

    # Compatibility alias used by the WebSocket hub.
    def get_hardware(self) -> Dict[str, Any]:  # pragma: no cover - thin alias
        return self.get_hardware_telemetry()

    # ── Supervision ──────────────────────────────────────────────────────────

    def run_supervision_cycle(self) -> Dict[str, Any]:
        """Sample the host, evaluate thresholds, and return a health report."""
        self._checks += 1
        now_iso = datetime.now(timezone.utc).isoformat()
        self._last_check_utc = now_iso

        hardware = self.get_hardware_telemetry()
        issues: List[str] = []

        cpu = hardware.get("cpu_percent")
        if cpu is not None and cpu >= _CPU_WARN_PCT:
            issues.append(f"CPU utilisation {cpu}% is above {_CPU_WARN_PCT:.0f}%")

        ram = hardware.get("ram_percent")
        if ram is not None and ram >= _RAM_WARN_PCT:
            issues.append(f"RAM utilisation {ram}% is above {_RAM_WARN_PCT:.0f}%")

        for name, disk in (hardware.get("disks") or {}).items():
            pct = (disk or {}).get("percent")
            if pct is not None and pct >= _DISK_WARN_PCT:
                issues.append(f"Disk {name} is {pct}% full")

        # Surface scheduler state without importing it at module load (avoids a
        # circular import: websocket_hub imports both modules).
        scheduler_state: Dict[str, Any] = {}
        try:
            from backend.service.scheduler_daemon import scheduler_instance

            status = scheduler_instance.get_status()
            scheduler_state = {
                "status": status.get("status"),
                "is_paused": status.get("is_paused"),
                "active_cycle_id": (status.get("active_run") or {}).get("cycle_id"),
                "next_scheduled_cycle_utc": status.get("next_scheduled_cycle_utc"),
            }
        except Exception as exc:  # pragma: no cover - defensive
            log.debug("Scheduler status unavailable in watchdog: %s", exc)

        status = "HEALTHY" if not issues else "DEGRADED"
        self._last_status = status

        return {
            "status": status,
            "sampled_at": now_iso,
            # Flat fields consumed directly by SystemHealthCards.tsx
            "cpu_percent": hardware.get("cpu_percent"),
            "ram_percent": hardware.get("ram_percent"),
            "ram_used_gb": hardware.get("ram_used_gb"),
            "ram_total_gb": hardware.get("ram_total_gb"),
            "disk_c_used_gb": hardware.get("disk_c_used_gb"),
            "disk_c_total_gb": hardware.get("disk_c_total_gb"),
            "disk_e_used_gb": hardware.get("disk_e_used_gb"),
            "disk_e_total_gb": hardware.get("disk_e_total_gb"),
            # Structured detail
            "hardware": hardware,
            "scheduler": scheduler_state,
            "watchdog": {
                "state": "RUNNING",
                "started_at": self._started_iso,
                "last_check_utc": self._last_check_utc,
                "checks_completed": self._checks,
                "last_status": self._last_status,
                "issues": issues,
                "thresholds": {
                    "cpu_percent": _CPU_WARN_PCT,
                    "ram_percent": _RAM_WARN_PCT,
                    "disk_percent": _DISK_WARN_PCT,
                },
            },
        }


# Process-wide singleton imported by the admin/WebSocket routers.
watchdog_instance = Watchdog()


def get_hardware_telemetry() -> Dict[str, Any]:
    """Module-level accessor retained for ``websocket_hub`` compatibility."""
    return watchdog_instance.get_hardware_telemetry()


__all__ = ["Watchdog", "watchdog_instance", "get_hardware_telemetry"]
