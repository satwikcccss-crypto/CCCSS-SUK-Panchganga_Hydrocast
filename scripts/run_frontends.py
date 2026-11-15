"""
HydroCast Frontends Daemon Runner
Starts frontend-public on port 3000 and frontend-admin on port 3001 and keeps them running.
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"E:\Hydrocast Windows Server")
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)

SERVICES = {
    "frontend-public": {
        "name": "Frontend Public Dashboard",
        "port": 3000,
        "cmd": ["node", str(ROOT / "frontend-public" / "node_modules" / "next" / "dist" / "bin" / "next"), "start", "-p", "3000"],
        "cwd": str(ROOT / "frontend-public"),
    },
    "frontend-admin": {
        "name": "Frontend Admin Console",
        "port": 3001,
        "cmd": ["node", str(ROOT / "frontend-admin" / "node_modules" / "next" / "dist" / "bin" / "next"), "start", "-p", "3001"],
        "cwd": str(ROOT / "frontend-admin"),
    },
}

processes = {}

def start_svc(key):
    svc = SERVICES[key]
    out = open(LOGS / f"{key}.log", "a", encoding="utf-8")
    err = open(LOGS / f"{key}.err", "a", encoding="utf-8")
    proc = subprocess.Popen(
        svc["cmd"],
        cwd=svc["cwd"],
        stdout=out,
        stderr=err,
    )
    print(f"Started {svc['name']} on port {svc['port']} with PID {proc.pid}", flush=True)
    return proc

for key in SERVICES:
    processes[key] = start_svc(key)

try:
    while True:
        time.sleep(5)
        for key, proc in list(processes.items()):
            if proc.poll() is not None:
                print(f"[!] {key} exited with code {proc.returncode}. Restarting...", flush=True)
                processes[key] = start_svc(key)
except KeyboardInterrupt:
    print("Shutting down frontends...", flush=True)
    for key, proc in processes.items():
        try:
            proc.terminate()
        except Exception:
            pass
