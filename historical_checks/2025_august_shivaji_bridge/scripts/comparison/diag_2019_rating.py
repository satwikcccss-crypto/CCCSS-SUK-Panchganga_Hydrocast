"""Diagnostic: is the 2019 reported (stage, Q) pair self-consistent on the WRD Rajaram rating?"""
import sys
from pathlib import Path

REPO = Path("E:/hydrocast_complete")
sys.path.insert(0, str(REPO))

from src.hydrology.stage_converter import (
    convert_stage_to_discharge_manning,
    convert_discharge_to_stage_manning,
    RAJARAM_ANCHORS_STAGE, RAJARAM_ANCHORS_Q,
)

print("=== WRD Rajaram rating anchors (top of range) ===")
for s, q in list(zip(RAJARAM_ANCHORS_STAGE, RAJARAM_ANCHORS_Q))[-6:]:
    print(f"  stage {s:.3f} m  <->  Q {q:.1f} m3/s")

print("\n=== 2019 reported pair checked against the rating ===")
rep_stage, rep_q = 546.97, 2111.0
q_at_rep_stage = convert_stage_to_discharge_manning(rep_stage, "RAJARAM_WEIR")
stage_at_rep_q = convert_discharge_to_stage_manning(rep_q, "RAJARAM_WEIR")
print(f"  Reported stage {rep_stage} m  ->  rating Q = {q_at_rep_stage:.1f} m3/s   (report says Q={rep_q})")
print(f"  Reported Q      {rep_q} m3/s ->  rating stage = {stage_at_rep_q:.3f} m   (report says stage={rep_stage})")
print(f"  => Inconsistency: stage implies ~{q_at_rep_stage:.0f} m3/s but report says {rep_q} m3/s "
      f"({q_at_rep_stage/rep_q:.1f}x). The pair is NOT self-consistent on the WRD rating.")

print("\n=== Our model's 2019 peak (from two_event run) ===")
sim_q, sim_stage = 3358.8, 544.36
print(f"  Model peak Q={sim_q} m3/s -> rating stage={convert_discharge_to_stage_manning(sim_q,'RAJARAM_WEIR'):.2f} m "
      f"(model reported {sim_stage})")
print(f"  Model sits BETWEEN the two reported interpretations:")
print(f"     trust Q  ({rep_q} m3/s)  -> stage {stage_at_rep_q:.2f} m")
print(f"     model                          -> stage {sim_stage:.2f} m")
print(f"     trust stage ({rep_stage} m) -> stage {rep_stage} m (Q~{q_at_rep_stage:.0f})")
