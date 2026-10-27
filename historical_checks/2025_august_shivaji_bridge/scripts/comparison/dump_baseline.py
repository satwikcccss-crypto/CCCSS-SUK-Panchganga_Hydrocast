import sys
from pathlib import Path

REPO = Path("E:/hydrocast_complete")
sys.path.insert(0, str(REPO))

from src.hms.basin_parser import load_immutable_baseline

sub_models, reaches = load_immutable_baseline()

print("=== BASELINE PER-SUBBASIN (cn, lag_min, area_km2) ===")
for sid in sorted(sub_models.keys()):
    s = sub_models[sid]
    print(f"{sid}: name={s.get('name')}, cn={s.get('cn')}, lag_min={s.get('lag_min')}, area_km2={s.get('area_km2')}")

print("\n=== BASELINE PER-REACH (k_hr, x) ===")
for rid in sorted(reaches.keys()):
    r = reaches[rid]
    print(f"{rid}: k_hr={r.get('k_hr')}, x={r.get('x')}")
