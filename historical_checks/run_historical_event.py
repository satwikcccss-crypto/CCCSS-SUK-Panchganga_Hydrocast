"""
Historical Flood Event Runner (Backward-Compatibility Forwarder)
===============================================================
This file forwards to `historical_checks/scripts/run_historical_event.py`.
The historical validation framework is structured into:
  - `historical_checks/scripts/`: Runner and evaluation scripts
  - `historical_checks/results/`: Output JSON simulation records
  - `historical_checks/reports/`: Markdown accuracy benchmarks & parameter studies
  - `historical_checks/data/`   : Reference and benchmark observation datasets
"""
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from run_historical_event import *  # noqa: F401, F403
import run_historical_event as _mod

if __name__ == "__main__":
    _mod.main()