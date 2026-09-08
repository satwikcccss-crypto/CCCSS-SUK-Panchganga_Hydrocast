import json

with open('data/telemetry/thingspeak_hourly_cache.json', 'r') as f:
    cache = json.load(f)

timestamps = sorted(cache.keys())
print(f"Total cached hourly timestamps: {len(timestamps)}")
print(f"From {timestamps[0]} to {timestamps[-1]}")

stages = [cache[t]['observed_stage_m'] for t in timestamps if 'observed_stage_m' in cache[t] and cache[t]['observed_stage_m'] is not None]
print(f"Observed Stage Range: {min(stages):.2f} m to {max(stages):.2f} m MSL")
print(f"Mean Observed Stage: {sum(stages)/len(stages):.2f} m MSL")

print("\nSampled Every 24 Hours:")
for t in timestamps[::24]:
    entry = cache[t]
    print(f"{t}: Stage = {entry.get('observed_stage_m', 0):.2f} m, Dist = {entry.get('observed_distance_ft', 0):.2f} ft")
