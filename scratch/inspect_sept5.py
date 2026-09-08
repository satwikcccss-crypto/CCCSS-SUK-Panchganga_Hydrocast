import json

with open('data/runs/CYC_20260905_18z.json', 'r') as f:
    d = json.load(f)

v = d.get('validation', {})
pts = v.get('scatter_points', [])
print(f"Total scatter points: {len(pts)}")
print(f"{'LeadH':<6} {'Obs Stage':<12} {'Pred Stage':<12} {'Delta(P-O)':<12}")
print("-" * 45)
for p in pts:
    obs = p.get('actual_stage')
    pred = p.get('predicted_stage')
    delta = round(pred - obs, 3) if obs is not None and pred is not None else '-'
    print(f"{p.get('lead_hours', '-'):<6} {obs:<12} {pred:<12} {delta:<12}")
