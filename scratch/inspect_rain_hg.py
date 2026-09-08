import json

with open('data/runs/CYC_20260905_18z.json', 'r') as f:
    d = json.load(f)

hg = d.get('hydrograph', [])
print(f"{'Hour':<6} {'Total Q (m3/s)':<16} {'Runoff Q':<12} {'Baseflow':<12} {'Stage (m)':<12}")
print("-" * 60)
for p in hg[::3]:
    print(f"{p.get('hour', '-'):<6} {p.get('discharge_m3s', '-'):<16} {p.get('surface_runoff_m3s', '-'):<12} {p.get('baseflow_m3s', '-'):<12} {p.get('stage_m', '-'):<12}")
