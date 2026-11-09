"""
scripts/suk_hydrocast_client.py
===============================
Shivaji University Kolhapur (SUK) Standalone Python Client & CLI tool.
Enables researchers, students, and emergency managers to fetch HydroCast
Panchganga flood intelligence in one Python line or command:

Functions:
    get_peak_summary()         -> peak stage, peak discharge, volume, arrival time
    get_stage_forecast(site)   -> 90-hr stage & discharge forecast for bridge
    get_hydrograph()           -> 90-hr basin discharge hydrograph
    get_station_rainfall()     -> 20 stations peak rainfall and peak time
    get_flood_arrival_time()   -> arrival time & confidence interval

CLI Usage:
    python scripts/suk_hydrocast_client.py
    python scripts/suk_hydrocast_client.py --summary
    python scripts/suk_hydrocast_client.py --stage SHIVAJI_BRIDGE
    python scripts/suk_hydrocast_client.py --rainfall
    python scripts/suk_hydrocast_client.py --hydrograph
"""

from __future__ import annotations

import argparse
import sys
from backend.client.suk_client import (
    get_complete_forecast,
    get_peak_summary,
    get_stage_forecast,
    get_hydrograph,
    get_station_rainfall,
    get_flood_arrival_time,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SUK HydroCast v1 Flood Intelligence Client"
    )
    parser.add_argument("--base-url", default="http://localhost:8000", help="API URL (default: http://localhost:8000)")
    parser.add_argument("--key", default="", help="Read-only API key (or set in HYDROCAST_READONLY_KEY)")
    parser.add_argument("--summary", action="store_true", help="Print executive peak flood summary")
    parser.add_argument("--stage", choices=["SHIVAJI_BRIDGE", "RAJARAM_BRIDGE", "ALL"], help="Print 90h stage forecast")
    parser.add_argument("--rainfall", action="store_true", help="Print station-wise rainfall peaks")
    parser.add_argument("--hydrograph", action="store_true", help="Print 90h basin outlet hydrograph")
    args = parser.parse_args()

    # If no flags passed, print full comprehensive dashboard view
    show_all = not (args.summary or args.stage or args.rainfall or args.hydrograph)

    try:
        if args.summary or show_all:
            summary = get_peak_summary(base_url=args.base_url, key=args.key or None)
            print("\n================================================================================")
            print(" SHIVAJI UNIVERSITY KOLHAPUR -- HYDROCAST v1 FLOOD PEAK SUMMARY")
            print("================================================================================")
            print(f"Cycle ID : {summary['cycle_id']}")
            print(f"Issued At: {summary['issued_at']}")
            print(f"Peak Basin Discharge : {summary['peak_discharge_m3s']:.2f} m³/s")
            print(f"Total Runoff Volume  : {summary['total_volume_mcm']:.2f} MCM")
            print(f"Lead Hours to Peak   : {summary['lead_hours_to_peak']} hours")
            print(f"Alert Status         : {summary['alert_level']}")
            print("\nCritical Bridge Water Levels:")
            for sid, b in summary["bridge_peaks"].items():
                print(f"  • {b['site_name']:<35}: Current={b['current_stage_m']:.2f} m | Peak={b['peak_stage_m']:.2f} m MSL | Alert={b['alert_level']}")

        if args.stage or show_all:
            target_site = args.stage or "SHIVAJI_BRIDGE"
            pts = get_stage_forecast(site=target_site, base_url=args.base_url, key=args.key or None)
            print("\n--------------------------------------------------------------------------------")
            print(f" 90-HOUR WATER LEVEL FORECAST: {target_site} (First 12 Hours)")
            print("--------------------------------------------------------------------------------")
            print(f"  {'Lead':<8} {'Forecast Time':<26} {'Stage (m MSL)':<16} {'Discharge (m³/s)':<18} {'Alert Level'}")
            print("  " + "-" * 80)
            for p in pts[:12]:
                print(f"  T+{p['lead_hours']:<6} {p['forecast_time']:<26} {p['stage_m']:<16.2f} {p['discharge_m3s']:<18.2f} {p['alert_level']}")

        if args.rainfall or show_all:
            stations = get_station_rainfall(base_url=args.base_url, key=args.key or None)
            print("\n--------------------------------------------------------------------------------")
            print(" STATION-WISE RAINFALL PEAKS & 90-HR TOTALS (Top Stations)")
            print("--------------------------------------------------------------------------------")
            print(f"  {'Station ID':<16} {'Station Name':<22} {'Peak Rate (mm/hr)':<20} {'Peak Time':<24} {'Total (mm)'}")
            print("  " + "-" * 90)
            for s in stations[:8]:
                print(f"  {s['station_id']:<16} {s['station_name']:<22} {s['peak_rainfall_mm_hr']:<20.2f} {str(s['peak_time'])[:23]:<24} {s['cumulative_90h_mm']:.2f}")

        if args.hydrograph:
            hg = get_hydrograph(base_url=args.base_url, key=args.key or None)
            print("\n--------------------------------------------------------------------------------")
            print(" 90-HOUR BASIN OUTLET HYDROGRAPH")
            print("--------------------------------------------------------------------------------")
            for p in hg[:12]:
                print(f"  T+{p.get('lead_hours', 0):<4} | Discharge: {p.get('discharge_m3s', 0.0):7.2f} m³/s | Stage: {p.get('stage_m', 0.0):6.2f} m")

        print("================================================================================\n")
        return 0
    except Exception as exc:
        print(f"\n[CLIENT ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
