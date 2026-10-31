"""
scripts/fetch_hydrocast_levels.py
=================================
Download the HydroCast water-level forecast in one step.

In plain English
----------------
HydroCast predicts the river water level (in metres) for two bridges for the
next ~90 hours. This script asks HydroCast for that forecast and saves it as a
file. Your flood model can then read the file.

You do NOT need to understand HTTP or headers. The key is already inside the
URL. Just run:

    python scripts/fetch_hydrocast_levels.py

That creates ``hydrocast_water_levels.json`` in the current folder.

Useful options
--------------
    python scripts/fetch_hydrocast_levels.py --out my_levels.json
    python scripts/fetch_hydrocast_levels.py --format csv --out levels.csv
    python scripts/fetch_hydrocast_levels.py --site SHIVAJI_BRIDGE
    python scripts/fetch_hydrocast_levels.py --base-url http://localhost:8000

The key is read from ``.env`` (``HYDROCAST_READONLY_KEY``; the old
``HYDROSIM_API_KEY`` name still works). If you keep the key
somewhere else, pass it with ``--key hydrocast_PS_V1_...``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is a declared dependency
    pass


DEFAULT_BASE = os.getenv("HYDROCAST_BASE_URL", "http://localhost:8000")
DEFAULT_OUT = {"json": "hydrocast_water_levels.json", "csv": "hydrocast_water_levels.csv"}


def _key_from_env() -> str:
    key = os.getenv("HYDROCAST_READONLY_KEY", "").strip()
    if key:
        return key
    # Legacy name used by earlier builds.
    key = os.getenv("HYDROSIM_API_KEY", "").strip()
    if key:
        return key
    # Fallback: read .env directly if python-dotenv was unavailable.
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(("HYDROCAST_READONLY_KEY=", "HYDROSIM_API_KEY=")):
                return line.split("=", 1)[1].strip()
    return ""


def _print_summary_json(data: dict) -> None:
    print()
    print("HydroCast forecast downloaded")
    print(f"  Forecast cycle : {data.get('cycle_id', 'unknown')}")
    print(f"  Issued at      : {data.get('issued_at', 'unknown')}")
    sites = data.get("sites") or []
    if not sites:
        print("  (No bridge data in this cycle.)")
        return
    print()
    print("Peak water level per bridge:")
    for site in sites:
        series = site.get("series") or []
        if not series:
            continue
        peak = max(series, key=lambda row: float(row.get("stage_m") or -1e9))
        print(
            f"  {site.get('site_id'):<18} "
            f"{float(peak['stage_m']):7.2f} m  "
            f"at {peak.get('forecast_time')}  "
            f"[{peak.get('alert_level')}]"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Download HydroCast water levels.")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="HydroCast server URL")
    parser.add_argument("--key", default="", help="Hydrosim key (default: from .env)")
    parser.add_argument("--site", default="", help="Only one bridge, e.g. SHIVAJI_BRIDGE")
    parser.add_argument(
        "--format", choices=["json", "csv"], default="json", help="File type to save"
    )
    parser.add_argument("--out", default="", help="Output file name")
    parser.add_argument("--timeout", type=int, default=30, help="Seconds to wait")
    args = parser.parse_args()

    key = args.key.strip() or _key_from_env()
    if not key:
        print("ERROR: no Hydrosim key found.", file=sys.stderr)
        print("  Put HYDROCAST_READONLY_KEY=hydrocast_PS_V1_... in .env,", file=sys.stderr)
        print("  or run with --key hydrocast_PS_V1_...", file=sys.stderr)
        return 2

    url = args.base_url.rstrip("/") + "/api/v1/hydrocast/water-levels"
    params = {"key": key, "format": args.format}
    if args.site:
        params["site_id"] = args.site

    out = Path(args.out or DEFAULT_OUT[args.format])

    try:
        response = requests.get(url, params=params, timeout=args.timeout)
    except requests.exceptions.ConnectionError:
        print(f"ERROR: could not reach {args.base_url}", file=sys.stderr)
        print("  Is HydroCast running? Start it first, then try again.", file=sys.stderr)
        return 3
    except requests.exceptions.Timeout:
        print("ERROR: HydroCast took too long to answer.", file=sys.stderr)
        return 3

    if response.status_code == 401:
        print("ERROR: the key was rejected.", file=sys.stderr)
        print("  Copy HYDROCAST_READONLY_KEY from .env, or pass --key.", file=sys.stderr)
        return 4
    if response.status_code == 404:
        print("ERROR: no forecast cycle exists yet.", file=sys.stderr)
        print("  Run the HydroCast pipeline once, then try again.", file=sys.stderr)
        return 5
    if not response.ok:
        print(f"ERROR: HydroCast returned {response.status_code}", file=sys.stderr)
        print(response.text[:300], file=sys.stderr)
        return 6

    if args.format == "json":
        data = response.json()
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _print_summary_json(data)
    else:
        out.write_text(response.text, encoding="utf-8")
        rows = max(len(response.text.strip().splitlines()) - 1, 0)
        print()
        print("HydroCast forecast downloaded")
        print(f"  Saved {rows} hourly rows to {out}")

    print()
    print(f"Saved file: {out.resolve()}")
    print("Your flood model can now read this file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
