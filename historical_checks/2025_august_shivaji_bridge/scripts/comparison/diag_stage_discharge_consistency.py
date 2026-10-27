"""
Stage<->discharge consistency for 2019 and 2021 now that BOTH discharges are known.
User: 2019 Q = 2111 m3/s (accurate), 2021 Q = 2162 m3/s.
Backwater bounded at <=1 m (user). Rajaram rating = official WRD sheet.
"""
import sys
from pathlib import Path
REPO = Path("E:/hydrocast_complete")
sys.path.insert(0, str(REPO))
from src.hydrology.stage_converter import (
    convert_stage_to_discharge_manning, convert_discharge_to_stage_manning,
    RAJARAM_ANCHORS_STAGE, RAJARAM_ANCHORS_Q, RAJARAM_BED_RL_M,
)

print("WRD Rajaram rating top anchors:")
for s, q in list(zip(RAJARAM_ANCHORS_STAGE, RAJARAM_ANCHORS_Q))[-4:]:
    print(f"   stage {s:.3f} -> Q {q:.1f}")

rows = [
    ("2019", 2111.0, 546.97, 3360.0),   # (event, obs_Q, obs_stage, model_Q @baseline routing)
    ("2021", 2162.0, 547.83, 1705.0),   # model_Q baseline; ~1801 at CN ceiling / faster routing
]
print("\n=== Stage<->discharge consistency at Rajaram (bed %.3f) ===" % RAJARAM_BED_RL_M)
for ev, obs_q, obs_stage, mq in rows:
    q_from_stage = convert_stage_to_discharge_manning(obs_stage, "RAJARAM_WEIR")
    stage_from_q = convert_discharge_to_stage_manning(obs_q, "RAJARAM_WEIR")
    gap = obs_stage - stage_from_q
    print(f"\n{ev}:")
    print(f"   reported DISCHARGE {obs_q:.0f} -> free-outflow stage {stage_from_q:.2f} m")
    print(f"   reported STAGE     {obs_stage:.2f} -> rating discharge {q_from_stage:.0f} m3/s")
    print(f"   stage-vs-discharge gap = {gap:.2f} m  (backwater <=1 m explains at most 1 m)")
    print(f"   model peak Q (baseline) {mq:.0f} -> {100*(mq-obs_q)/obs_q:+.1f}% vs reported Q")

print("\n=== If DISCHARGE is the truth, model accuracy vs it (recommended fast routing raises model Q) ===")
print("2021 model Q: ~1705 (baseline) to ~1801 (CN/fast) vs obs 2162  ->  -21% to -17% (GOOD)")
print("2019 model Q: ~3360 (baseline) vs obs 2111                      ->  +59% (Open-Meteo 2019 too wet)")
