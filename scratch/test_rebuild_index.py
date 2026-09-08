import json
import glob
import os
from pathlib import Path

runs = sorted(glob.glob('data/runs/CYC_*.json'), reverse=True)
index = []
for r in runs:
    with open(r, 'r', encoding='utf-8') as f:
        d = json.load(f)
    cid = d.get('cycle_id', os.path.basename(r).replace('.json', ''))
    summary = d.get('summary', {})
    val = d.get('validation', {})
    m = val.get('metrics', {})
    entry = {
        "cycle_id": cid,
        "run_date": summary.get("forecast_date") or cid,
        "cycle_time": summary.get("cycle_time") or (cid.split("_")[-1] if "_" in cid else "06z"),
        "peak_discharge_m3s": summary.get("peak_discharge_m3s", 0),
        "lead_hours_to_peak": summary.get("lead_hours_to_peak", 0),
        "total_volume_mcm": summary.get("total_volume_mcm", 0.0),
        "total_rainfall_mm": summary.get("total_rainfall_mm", 0.0),
        "shivaji_peak_stage_m": summary.get("bridges", {}).get("shivaji", {}).get("peak_stage_m", 0),
        "rajaram_peak_stage_m": summary.get("bridges", {}).get("rajaram", {}).get("peak_stage_m", 0),
        "alert_level": summary.get("bridges", {}).get("shivaji", {}).get("alert_level", "NORMAL"),
        "status": "completed",
        "has_validation": bool(val),
        "spearman_rho": m.get("spearman_rho"),
        "nse": m.get("nse_stage"),
        "rmse": m.get("rmse_stage_m"),
        "lifecycle_status": val.get("lifecycle_status", "IN_PROGRESS"),
        "verified_hours": val.get("verified_hours", m.get("sample_size_hours", 0)),
    }
    index.append(entry)

print(f"Total entries indexed: {len(index)}")
for e in index:
    print(f"{e['cycle_id']} | {e['run_date']} | verified={e['verified_hours']}h | status={e['lifecycle_status']} | MAE={m.get('mae_stage_m')}")
