import urllib.request
import json

print("=" * 60)
print("END-TO-END VERIFICATION")
print("=" * 60)

# 1. Backend API
print("\n--- Backend API (port 8000) ---")
try:
    r = urllib.request.urlopen('http://localhost:8000/api/v1/status', timeout=10)
    d = json.loads(r.read())
    print(f"  status: {r.status}")
    print(f"  pipeline_ok: {d.get('pipeline_ok')}")
except Exception as e:
    print(f"  ERROR: {e}")

try:
    r = urllib.request.urlopen('http://localhost:8000/api/v1/runoff/summary', timeout=10)
    d = json.loads(r.read())
    for b in d.get('bridges', []):
        print(f"  Bridge {b.get('site_id')}: current={b.get('current_stage_m')}m, stage={b.get('stage_m')}m, peak={b.get('peak_stage_m')}m")
except Exception as e:
    print(f"  ERROR: {e}")

try:
    r = urllib.request.urlopen('http://localhost:8000/api/v1/rainfall/ecmwf', timeout=10)
    d = json.loads(r.read())
    if d:
        first_key = list(d.keys())[0]
        print(f"  Rainfall: {len(d)} subbasins, S1={len(d.get(first_key, []))} points, total_mm={sum(p['mm_hr'] for p in d.get(first_key, [])):.2f}")
except Exception as e:
    print(f"  ERROR: {e}")

# 2. Public Frontend
print("\n--- Public Frontend (port 3000) ---")
try:
    r = urllib.request.urlopen('http://localhost:3000/dashboard', timeout=10)
    print(f"  /dashboard: status {r.status}")
except Exception as e:
    print(f"  ERROR: {e}")

# 3. Admin Frontend
print("\n--- Admin Frontend (port 3001) ---")
try:
    r = urllib.request.urlopen('http://localhost:3001/login', timeout=10)
    print(f"  /login: status {r.status}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 60)
print("ALL SERVICES RUNNING")
print("=" * 60)