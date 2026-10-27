"""
Run the August 2025 Shivaji Bridge flood as a SINGLE 360-hour block.

This is the production validation path used by run_historical_event.py:
  * fetches 360 h of Open-Meteo archive rainfall for all 18 gauges,
  * selects the governing gage per subbasin (max 90-h rain volume),
  * runs the HEC-HMS emulator over the full 2025-08-08 to 2025-08-22 window,
  * converts discharge -> Shivaji Bridge stage via the WRD rating curve,
  * validates hourly against the cleaned observed telemetry (NSE, KGE, RMSE,
    MAE, PBIAS, peak-stage error, peak-timing error).

Usage:
    python scripts/simulation/run_360h_block.py

Artifacts:
    results/360h_block/historical_event_2025_august_results.json
"""
import shutil
from pathlib import Path
import sys

# Resolve repo root (this file lives in historical_checks/2025_august_shivaji_bridge/scripts/simulation/)
HERE = Path(__file__).resolve()
BRIDGE_DIR = HERE.parents[3]          # .../2025_august_shivaji_bridge
REPO = HERE.parents[4]                # repo root

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "historical_checks"))

from run_historical_event import main   # noqa: E402

if __name__ == "__main__":
    # Simulate: python run_historical_event.py --event 2025_august
    sys.argv = ["run_historical_event.py", "--event", "2025_august"]
    main()
    # Copy the artifact into the organized results folder
    src = REPO / "historical_checks" / "historical_event_2025_august_results.json"
    dst = BRIDGE_DIR / "results" / "360h_block" / "historical_event_2025_august_results.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"\n[run_360h_block] Results -> {dst}")

