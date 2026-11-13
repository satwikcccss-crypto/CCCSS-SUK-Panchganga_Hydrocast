"""
HydroCast Panchganga — Production Start Script (Windows Server)
===============================================================
Starts all four services for the complete HydroCast deployment:

  Port 8000  Backend Public API      (uvicorn backend.api.main:app)
  Port 8001  Backend Admin API       (uvicorn backend.api.admin_app:app)
  Port 3000  Frontend Public Portal  (next start -p 3000)
  Port 3001  Frontend Admin Console  (next start -p 3001)

Usage:
  python start_production.py          # Start all services
  python start_production.py --check  # Health check only
"""

import os
import sys
import time
import signal
import subprocess
import json
import urllib.request
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("PROJECT_ROOT", str(PROJECT_ROOT))

SERVICES = {
    "backend": {
        "name": "Backend Public API",
        "port": 8000,
        "cmd": [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.api.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--workers",
            "4",
        ],
        "cwd": str(PROJECT_ROOT),
        "health": "http://localhost:8000/healthz/live",
    },
    "backend-admin": {
        "name": "Backend Admin API",
        "port": 8001,
        "cmd": [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.api.admin_app:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8001",
            "--workers",
            "2",
        ],
        "cwd": str(PROJECT_ROOT),
        "health": "http://localhost:8001/healthz/live",
    },
    "frontend-public": {
        "name": "Frontend Public Dashboard",
        "port": 3000,
        "cmd": ["npm", "run", "start"],
        "cwd": str(PROJECT_ROOT / "frontend-public"),
        "health": "http://localhost:3000",
    },
    "frontend-admin": {
        "name": "Frontend Admin Console",
        "port": 3001,
        "cmd": ["npm", "run", "start"],
        "cwd": str(PROJECT_ROOT / "frontend-admin"),
        "health": "http://localhost:3001",
    },
}

processes: dict[str, subprocess.Popen] = {}


def check_health(url: str, timeout: int = 5) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HydroCast-HealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def start_service(key: str, svc: dict) -> subprocess.Popen:
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    stdout_log = open(log_dir / f"{key}.log", "a", encoding="utf-8")
    stderr_log = open(log_dir / f"{key}.err", "a", encoding="utf-8")

    print(f"  Starting {svc['name']} on port {svc['port']}...")
    proc = subprocess.Popen(
        svc["cmd"],
        cwd=svc["cwd"],
        stdout=stdout_log,
        stderr=stderr_log,
        env={**os.environ},
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    return proc


def wait_for_health(svc: dict, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if check_health(svc["health"]):
            return True
        time.sleep(1)
    return False


def health_check_all():
    print("\n=== HydroCast Health Check ===\n")
    all_ok = True
    for key, svc in SERVICES.items():
        ok = check_health(svc["health"])
        status = "HEALTHY" if ok else "OFFLINE"
        marker = "+" if ok else "!"
        print(f"  [{marker}] {svc['name']:30s} port {svc['port']}  {status}")
        if not ok:
            all_ok = False

    # Extra: check specific API endpoints (best-effort; may require API key)
    print()
    api_checks = [
        ("Backend /api/v1/health", "http://localhost:8000/api/v1/health"),
        ("Backend /healthz/ready", "http://localhost:8000/healthz/ready"),
        ("Admin /api/v1/admin/health", "http://localhost:8001/api/v1/admin/health"),
    ]
    for name, url in api_checks:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "HydroCast-HealthCheck/1.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
                print(f"  [+] {name:35s} OK")
        except Exception as e:
            print(f"  [~] {name:35s} skipped/failed ({e})")

    print()
    if all_ok:
        print("  === ALL SERVICES HEALTHY ===")
    else:
        print("  === SOME SERVICES OFFLINE ===")
    return all_ok


def shutdown_all(signum=None, frame=None):
    print("\n  Shutting down all services...")
    for key, proc in processes.items():
        try:
            if sys.platform == "win32":
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                proc.terminate()
            proc.wait(timeout=10)
            print(f"  Stopped {SERVICES[key]['name']}")
        except Exception:
            proc.kill()
            print(f"  Force-killed {SERVICES[key]['name']}")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="HydroCast Production Server Manager")
    parser.add_argument("--check", action="store_true", help="Health check only, don't start")
    parser.add_argument(
        "--backend-only", action="store_true", help="Start backend services only (ports 8000, 8001)"
    )
    args = parser.parse_args()

    if args.check:
        ok = health_check_all()
        sys.exit(0 if ok else 1)

    print("=" * 60)
    print("  HydroCast Panchganga — Production Server")
    print("  Windows Server Deployment")
    print("=" * 60)
    print()

    signal.signal(signal.SIGINT, shutdown_all)
    signal.signal(signal.SIGTERM, shutdown_all)

    services_to_start = SERVICES
    if args.backend_only:
        services_to_start = {k: v for k, v in SERVICES.items() if k.startswith("backend")}

    # Start all services
    for key, svc in services_to_start.items():
        processes[key] = start_service(key, svc)

    # Wait for health
    print()
    print("  Waiting for services to become healthy...")
    print()
    time.sleep(3)

    all_healthy = True
    for key, svc in services_to_start.items():
        healthy = wait_for_health(svc, timeout=30)
        status = "HEALTHY" if healthy else "STARTING (check logs)"
        marker = "+" if healthy else "~"
        print(f"  [{marker}] {svc['name']:30s} port {svc['port']}  {status}")
        if not healthy:
            all_healthy = False

    print()
    if all_healthy:
        print("  === ALL SERVICES STARTED SUCCESSFULLY ===")
    else:
        print("  === SOME SERVICES STILL STARTING (check logs/ directory) ===")

    print()
    print("  Public Dashboard:   http://localhost:3000")
    print("  Admin Console:      http://localhost:3001")
    print("  API (Public):       http://localhost:8000/docs")
    print("  API (Admin):        http://localhost:8001/docs")
    print()
    print("  Press Ctrl+C to stop all services.")
    print()

    # Keep running and monitor
    try:
        while True:
            time.sleep(5)
            for key, proc in list(processes.items()):
                if proc.poll() is not None:
                    svc = services_to_start[key]
                    print(f"  [!] {svc['name']} exited (code {proc.returncode}). Restarting...")
                    processes[key] = start_service(key, svc)
    except KeyboardInterrupt:
        shutdown_all()


if __name__ == "__main__":
    main()
