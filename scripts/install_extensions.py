import urllib.request
import re
import json

# 1. PostGIS check
print("Checking PostGIS binaries for PG16...")
postgis_url = "https://download.osgeo.org/postgis/windows/pg16/"
try:
    req = urllib.request.Request(postgis_url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=10).read().decode()
    bundles = re.findall(r'href=["\'](postgis-bundle-pg16-[^"\']+\.zip)["\']', html)
    print("Found PostGIS bundles:", bundles[-5:] if bundles else "None")
except Exception as e:
    print("PostGIS check failed:", e)

# 2. TimescaleDB check
print("\nChecking TimescaleDB for PG16...")
ts_url = "https://api.github.com/repos/timescale/timescaledb/releases/latest"
try:
    req = urllib.request.Request(ts_url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
    print("TimescaleDB latest release:", data.get("tag_name"))
    assets = [a["browser_download_url"] for a in data.get("assets", []) if "windows" in a["name"].lower() and "16" in a["name"]]
    print("TimescaleDB PG16 assets:", assets)
except Exception as e:
    print("TimescaleDB check failed:", e)

