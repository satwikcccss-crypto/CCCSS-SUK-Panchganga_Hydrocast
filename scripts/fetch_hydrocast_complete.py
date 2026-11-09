"""
scripts/fetch_hydrocast_complete.py
===================================
Open-Meteo style CLI & Python client for HydroCast Panchganga flood forecasts.

Usage:
    python scripts/fetch_hydrocast_complete.py
    python scripts/fetch_hydrocast_complete.py --key <HYDROCAST_READONLY_KEY>
    python scripts/fetch_hydrocast_complete.py --out forecast.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
import urllib.request
import urllib.parse
import urllib.error

DEFAULT_BASE = os.getenv("HYDROCAST_BASE_URL", "http://localhost:8000")


def _key_from_env() -> str:
    key = os.getenv("HYDROCAST_READONLY_KEY", "").strip()
    if key:
        return key
    key = os.getenv("HYDROSIM_API_KEY", "").strip()
    if key:
        return key
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(("HYDROCAST_READONLY_KEY=", "HYDROSIM_API_KEY=")):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch full HydroCast flood intelligence forecast.")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="HydroCast API base URL (default: http://localhost:8000)")
    parser.add_argument("--key", default="", help="Read-only API key (Open-Meteo style)")
    parser.add_argument("--out", default="", help="Optional JSON file path to save full forecast payload")
    args = parser.parse_args()

    key = args.key.strip() or _key_from_env()
    url = f"{args.base_url.rstrip('/')}/api/v1/hydrocast/complete"
    if key:
        url += f"?key={urllib.parse.quote(key)}"

    print("================================================================================")
    print(" HYDROCAST PANCHGANGA -- REAL-TIME FLOOD INTELLIGENCE FEED")
    print(" Shivaji University Kolhapur (SUK) Production Server")
    print("================================================================================")
    print(f"Connecting to: {args.base_url}/api/v1/hydrocast/complete")

    req = urllib.request.Request(url, headers={"User-Agent": "HydroCast-Client/1.0"})
    if key:
        req.add_header("X-API-Key", key)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"\n[ERROR] HTTP {e.code}: {e.reason}", file=sys.stderr)
        if e.code == 401:
            print("  Unauthorized: Pass a valid key with --key or set HYDROCAST_READONLY_KEY in .env", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[ERROR] Connection failed: {exc}", file=sys.stderr)
        return 1

    summary = data.get("summary", {})
    bridges = data.get("bridges", {})
    stations = data.get("stations_rainfall", [])
    outlet_hg = data.get("outlet_hydrograph_90h", [])

    print(f"\nCycle ID : {data.get('cycle_id')}")
    print(f"Issued At: {data.get('issued_at')}")

    print("\n--------------------------------------------------------------------------------")
    print(" 1. BASIN RUNOFF & FLOOD PEAK SUMMARY")
    print("--------------------------------------------------------------------------------")
    print(f"  • Peak Discharge (Sink) : {summary.get('peak_discharge_m3s', 0.0):.2f} m³/s")
    print(f"  • Total Runoff Volume   : {summary.get('total_volume_mcm', 0.0):.2f} MCM")
    print(f"  • Lead Hours to Peak    : {summary.get('lead_hours_to_peak', 0)} hours")
    print(f"  • Alert Level           : {summary.get('alert_level', 'NORMAL')}")

    pa = summary.get("peak_arrival", {})
    if isinstance(pa, dict):
        sh_pa = pa.get("shivaji", {})
        rj_pa = pa.get("rajaram", {})
        if sh_pa.get("peak_arrival_time"):
            print(f"  • Shivaji Bridge Arrival : {sh_pa.get('peak_arrival_time')}")
        if rj_pa.get("peak_arrival_time"):
            print(f"  • Rajaram Weir Arrival   : {rj_pa.get('peak_arrival_time')}")

    print("\n--------------------------------------------------------------------------------")
    print(" 2. CRITICAL BRIDGE MONITORING (90-HR PEAKS & GAUGE DATUM)")
    print("--------------------------------------------------------------------------------")
    print(f"  {'Site / Bridge':<35} {'Current (m)':<12} {'Peak (m MSL)':<14} {'Peak Q (m³/s)':<14} {'Thresholds (Alert/Warn/Danger)'}")
    print("  " + "-" * 95)
    for sid, b in bridges.items():
        sname = b.get("site_name", sid)[:34]
        curr = f"{b.get('current_stage_m', 0.0):.2f}"
        pk_st = f"{b.get('peak_stage_m', 0.0):.2f}"
        pk_q = f"{b.get('peak_discharge_m3s', 0.0):.2f}"
        th = b.get("thresholds", {})
        th_str = f"{th.get('alert_m', 0):.1f} / {th.get('warning_m', 0):.1f} / {th.get('danger_m', 0):.1f} m"
        print(f"  {sname:<35} {curr:<12} {pk_st:<14} {pk_q:<14} {th_str}")

    print("\n--------------------------------------------------------------------------------")
    print(" 3. STATION-WISE RAINFALL PEAKS (TOP GOVERNING GAUGES)")
    print("--------------------------------------------------------------------------------")
    print(f"  {'Station ID':<16} {'Station Name':<22} {'Peak (mm/hr)':<14} {'Peak Time':<24} {'Total 90h (mm)'}")
    print("  " + "-" * 90)
    for st in stations[:10]:
        sid = st.get("station_id", "")[:15]
        sname = st.get("station_name", sid)[:21]
        p_rate = f"{st.get('peak_rainfall_mm_hr', 0.0):.2f}"
        p_time = str(st.get("peak_time", ""))[:23]
        tot = f"{st.get('cumulative_90h_mm', 0.0):.2f}"
        print(f"  {sid:<16} {sname:<22} {p_rate:<14} {p_time:<24} {tot}")

    print("\n--------------------------------------------------------------------------------")
    print(" 4. 90-HOUR HYDROGRAPH SNAPSHOT (FIRST 12 HOURS PREVIEW)")
    print("--------------------------------------------------------------------------------")
    sh_pts = bridges.get("SHIVAJI_BRIDGE", {}).get("series_90h", [])
    rj_pts = bridges.get("RAJARAM_BRIDGE", {}).get("series_90h", [])
    print(f"  {'Lead (h)':<10} {'Forecast Time':<26} {'Shivaji Stage (m)':<20} {'Rajaram Stage (m)':<20} {'Outlet Q (m³/s)'}")
    print("  " + "-" * 90)
    limit = min(12, len(sh_pts), len(rj_pts))
    for i in range(limit):
        sh = sh_pts[i]
        rj = rj_pts[i]
        out_q = outlet_hg[i].get("discharge_m3s", 0.0) if i < len(outlet_hg) else sh.get("discharge_m3s", 0.0)
        print(f"  T+{sh.get('lead_hours', i):<7} {sh.get('forecast_time', ''):<26} {sh.get('stage_m', 0.0):<20.2f} {rj.get('stage_m', 0.0):<20.2f} {out_q:<10.2f}")

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"\n[OK] Full 90-hour complete forecast saved to: {out_path.resolve()}")

    print("================================================================================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
