import urllib.request
import json

# Public dashboard
try:
    r = urllib.request.urlopen('http://localhost:3000/dashboard', timeout=10)
    print(f'Public /dashboard: status {r.status}')
except Exception as e:
    print(f'Public /dashboard: {e}')

# Admin login page
try:
    r = urllib.request.urlopen('http://localhost:3001/login', timeout=10)
    print(f'Admin /login: status {r.status}')
except Exception as e:
    print(f'Admin /login: {e}')

# Verify API still working
try:
    r = urllib.request.urlopen('http://localhost:8000/api/v1/status', timeout=10)
    d = json.loads(r.read())
    print(f'API pipeline_ok: {d.get("pipeline_ok")}')
except Exception as e:
    print(f'API: {e}')