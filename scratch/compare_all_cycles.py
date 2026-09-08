import json
import glob
import os

runs = sorted(glob.glob('data/runs/CYC_*.json'))
print(f"{'Cycle ID':<18} {'Start Stage':<12} {'Peak Pred':<12} {'Peak Obs':<12} {'Obs Range':<18} {'Pred Range'}")
print("-" * 85)
for r in runs:
    with open(r, 'r') as f:
        d = json.load(f)
    cid = d.get('cycle_id', os.path.basename(r))
    summary = d.get('summary', {})
    val = d.get('validation', {})
    pts = val.get('scatter_points', [])
    start_stg = summary.get('bridges', {}).get('shivaji', {}).get('current_stage_m', '-')
    peak_pred = summary.get('bridges', {}).get('shivaji', {}).get('peak_stage_m', '-')
    
    if pts:
        obs_vals = [p['actual_stage'] for p in pts if 'actual_stage' in p and p['actual_stage'] is not None]
        pred_vals = [p['predicted_stage'] for p in pts if 'predicted_stage' in p and p['predicted_stage'] is not None]
        obs_min_max = f"{min(obs_vals):.2f}-{max(obs_vals):.2f}" if obs_vals else "-"
        pred_min_max = f"{min(pred_vals):.2f}-{max(pred_vals):.2f}" if pred_vals else "-"
        peak_obs = f"{max(obs_vals):.2f}" if obs_vals else "-"
    else:
        obs_min_max = "-"
        pred_min_max = "-"
        peak_obs = "-"
    
    print(f"{cid:<18} {str(start_stg):<12} {str(peak_pred):<12} {str(peak_obs):<12} {obs_min_max:<18} {pred_min_max}")
