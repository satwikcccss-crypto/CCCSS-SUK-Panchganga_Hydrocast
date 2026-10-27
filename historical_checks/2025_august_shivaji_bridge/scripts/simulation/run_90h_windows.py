"""
Compare simulation-window strategies for the August 2025 Shivaji Bridge flood.

Tests the hypothesis: "Does splitting the 14-day (360-h) monsoon event into four
consecutive 90-hour windows improve accuracy vs. one continuous 360-h block?"

Strategies (all calibration-aware, same rainfall & parameters):
  A) Single 360-h block — continuous baseflow & SCS antecedent moisture.
  B) Four 90-h windows, fresh start — baseflow reset to 91.1 m3/s each window.
  C) Four 90-h windows, rolling — baseflow carried between windows.

Each strategy converts discharge -> Shivaji Bridge stage (WRD rating curve),
aligns to observed hourly telemetry, and reports NSE, KGE, RMSE, MAE, PBIAS,
peak-stage error, and peak-timing error.

Usage:
    python scripts/simulation/run_90h_windows.py

Artifacts:
    results/90h_windows/window_strategy_comparison.json
"""
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve()
BRIDGE_DIR = HERE.parents[3]          # .../2025_august_shivaji_bridge
REPO = HERE.parents[4]                # repo root

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "historical_checks"))
sys.path.insert(0, str(BRIDGE_DIR / "scripts"))

from comparison.compare_window_strategies import main   # noqa: E402

if __name__ == "__main__":
    sys.argv = ["compare_window_strategies.py"]
    main()
    # Move/copy the artifact into the organized results folder
    src = BRIDGE_DIR / "results" / "comparison" / "window_strategy_comparison.json"
    dst = BRIDGE_DIR / "results" / "90h_windows" / "window_strategy_comparison.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dst)
    print(f"\n[run_90h_windows] Comparison -> {dst}")
