import urllib.request
import zipfile
import os
import shutil
import subprocess

PG_DIR = r"E:\PostgreSQL\16"
PG_DATA = r"E:\PostgreSQL\16\data"
TEMP_DIR = r"E:\pg_extensions_temp"
os.makedirs(TEMP_DIR, exist_ok=True)

def reporthook(blocknum, blocksize, totalsize):
    read = blocknum * blocksize
    if totalsize > 0 and blocknum % 1000 == 0:
        print(f"  Downloaded: {read / (1024*1024):.1f} MB / {totalsize / (1024*1024):.1f} MB ({read*100/totalsize:.1f}%)")

# ── 1. Install PostGIS ────────────────────────────────────────────────────────
postgis_url = "https://download.osgeo.org/postgis/windows/pg16/postgis-bundle-pg16-3.6.2x64.zip"
postgis_zip = os.path.join(TEMP_DIR, "postgis-bundle-pg16-3.6.2x64.zip")

print("=== Step 1: Downloading PostGIS 3.6.2 for PG16 ===")
if not os.path.exists(postgis_zip):
    urllib.request.urlretrieve(postgis_url, postgis_zip, reporthook)
    print("PostGIS download complete.")
else:
    print(f"PostGIS zip already present: {os.path.getsize(postgis_zip)} bytes")

print("\n=== Step 2: Extracting PostGIS into E:\\PostgreSQL\\16 ===")
with zipfile.ZipFile(postgis_zip, "r") as zf:
    # PostGIS bundle usually has a root folder or bin/, lib/, share/ directly
    # Check top-level dirs
    names = zf.namelist()
    prefix = ""
    first = names[0].split("/")[0]
    if first.startswith("postgis-bundle"):
        prefix = first + "/"

    print(f"Archive prefix detected: '{prefix}'")
    file_count = 0
    for member in zf.infolist():
        rel = member.filename
        if prefix and rel.startswith(prefix):
            rel = rel[len(prefix):]
        if not rel or rel.endswith("/"):
            continue
        dest = os.path.join(PG_DIR, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with zf.open(member) as src, open(dest, "wb") as dst:
            shutil.copyfileobj(src, dst)
        file_count += 1
    print(f"Extracted {file_count} PostGIS files into {PG_DIR}")

# ── 2. Install TimescaleDB ────────────────────────────────────────────────────
timescale_url = "https://github.com/timescale/timescaledb/releases/download/2.31.0/timescaledb-postgresql-16-windows-amd64.zip"
timescale_zip = os.path.join(TEMP_DIR, "timescaledb-pg16.zip")

print("\n=== Step 3: Downloading TimescaleDB 2.31.0 for PG16 ===")
if not os.path.exists(timescale_zip):
    req = urllib.request.Request(timescale_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(timescale_zip, "wb") as out_file:
        totalsize = int(resp.headers.get("Content-Length", 0))
        blocksize = 1024 * 64
        read = 0
        blocknum = 0
        while True:
            chunk = resp.read(blocksize)
            if not chunk:
                break
            out_file.write(chunk)
            read += len(chunk)
            blocknum += 1
            if blocknum % 200 == 0 and totalsize > 0:
                print(f"  Downloaded: {read / (1024*1024):.1f} MB / {totalsize / (1024*1024):.1f} MB ({read*100/totalsize:.1f}%)")
    print("TimescaleDB download complete.")
else:
    print(f"TimescaleDB zip already present: {os.path.getsize(timescale_zip)} bytes")

print("\n=== Step 4: Extracting TimescaleDB into E:\\PostgreSQL\\16 ===")
with zipfile.ZipFile(timescale_zip, "r") as zf:
    file_count = 0
    for member in zf.infolist():
        rel = member.filename
        if not rel or rel.endswith("/"):
            continue
        # If files are inside a subfolder or root
        dest = os.path.join(PG_DIR, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with zf.open(member) as src, open(dest, "wb") as dst:
            shutil.copyfileobj(src, dst)
        file_count += 1
    print(f"Extracted {file_count} TimescaleDB files into {PG_DIR}")

print("\n=== Step 5: Updating postgresql.conf for TimescaleDB ===")
conf_path = os.path.join(PG_DATA, "postgresql.conf")
if os.path.exists(conf_path):
    conf_text = open(conf_path, "r", encoding="utf-8").read()
    if "timescaledb" not in conf_text:
        # Append shared_preload_libraries
        with open(conf_path, "a", encoding="utf-8") as f:
            f.write("\n# TimescaleDB Extension\nshared_preload_libraries = 'timescaledb'\n")
        print("Added shared_preload_libraries = 'timescaledb' to postgresql.conf")
    else:
        print("shared_preload_libraries already contains timescaledb in postgresql.conf")
else:
    print("postgresql.conf not found at:", conf_path)

print("\n=== PostGIS and TimescaleDB installation finished successfully! ===")

