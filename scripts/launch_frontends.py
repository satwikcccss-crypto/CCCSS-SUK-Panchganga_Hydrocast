"""
Launch HydroCast Next.js frontends in production mode on ports 3000 and 3001.
"""
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(r"E:\Hydrocast Windows Server")
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)

DETACHED_FLAGS = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

public_out = open(LOGS / "frontend-public.log", "w", encoding="utf-8")
public_err = open(LOGS / "frontend-public.err", "w", encoding="utf-8")
p_public = subprocess.Popen(
    ["node", str(ROOT / "frontend-public" / "node_modules" / "next" / "dist" / "bin" / "next"), "start", "-p", "3000"],
    cwd=str(ROOT / "frontend-public"),
    stdout=public_out,
    stderr=public_err,
    creationflags=DETACHED_FLAGS
)
print(f"frontend-public launched with PID {p_public.pid}")

admin_out = open(LOGS / "frontend-admin.log", "w", encoding="utf-8")
admin_err = open(LOGS / "frontend-admin.err", "w", encoding="utf-8")
p_admin = subprocess.Popen(
    ["node", str(ROOT / "frontend-admin" / "node_modules" / "next" / "dist" / "bin" / "next"), "start", "-p", "3001"],
    cwd=str(ROOT / "frontend-admin"),
    stdout=admin_out,
    stderr=admin_err,
    creationflags=DETACHED_FLAGS
)
print(f"frontend-admin launched with PID {p_admin.pid}")

# Give them a few seconds to start
print("Waiting for servers to bind ports...")
time.sleep(5)

def check(url, name):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HydroCast-Launcher/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            print(f"[{r.status}] {name} is active at {url}")
            return True
    except Exception as e:
        print(f"[FAILED] {name} at {url}: {e}")
        return False

check("http://localhost:3000", "Frontend Public")
check("http://localhost:3001", "Frontend Admin")
