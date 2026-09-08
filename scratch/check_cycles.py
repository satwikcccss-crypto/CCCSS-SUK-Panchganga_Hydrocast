import json
import glob
import os

runs = sorted(glob.glob('data/runs/CYC_*.json'))
print(f"Total run files found: {len(runs)}")
print(f"{'Cycle ID':<20} {'Hours':<8} {'Stage MAE':<12} {'Stage RMSE':<12} {'NSE Stage':<12} {'Grade':<22} {'Status'}")
print("-" * 95)
for r in runs:
    with open(r, 'r') as f:
        d = json.load(f)
    cid = d.get('cycle_id', os.path.basename(r))
    v = d.get('validation', {})
    m = v.get('metrics', {})
    status = v.get('lifecycle_status', d.get('status', 'UNKNOWN'))
    hours = m.get('sample_size_hours', '-')
    mae = m.get('mae_stage_m', '-')
    rmse = m.get('rmse_stage_m', '-')
    nse = m.get('nse_stage', '-')
    grade = m.get('performance_grade', '-')
    print(f"{cid:<20} {str(hours):<8} {str(mae):<12} {str(rmse):<12} {str(nse):<12} {str(grade):<22} {status}")
