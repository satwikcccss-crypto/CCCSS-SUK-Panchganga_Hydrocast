"""Preprocess & clean the August 2025 Shivaji Bridge ultrasonic telemetry.

Reads ``data/Shivaji Bridge 2025 water levels.csv`` (ThingSpeak export),
filters ultrasonic echo artifacts, converts raw ultrasonic distance (ft) to
stage (m MSL) and resamples to 1-hour averages over
2025-08-08 00:00:00 - 2025-08-22 23:00:00.

Stage (m MSL) = 549.35 - (field1_ft * 0.3048)     (sensor datum = deck level)

Echo artifacts removed:
  * field1 <= 10 ft  -> the sensor dropped to ~3.69 ft (lost echo, water
                        reported as if right below the deck) — 10 readings.
  * field1 > 67.82 ft -> stage would fall below the surveyed river bed
                        (528.67 m MSL), i.e. max-range / lost-return garbage —
                        2 readings (106.33 ft, 106.66 ft).
"""
from pathlib import Path

import pandas as pd

RAW_CSV = Path("data/Shivaji Bridge 2025 water levels.csv")
OUT_CSV = Path("data/shivaji_bridge_2025_hourly_observed.csv")

SENSOR_DATUM_MSL_M = 549.35   # Shivaji Bridge deck level (m MSL)
FT_TO_M = 0.3048
BED_RL_M = 528.67             # surveyed Shivaji Bridge bed RL (m MSL)

# Field1 (ft) bounds for a physically possible stage [bed, deck]:
#   0 <= field1 <= (deck - bed) / 0.3048 = 67.82 ft
FIELD1_MIN_FT = 10.0          # echo-drop floor (catches the ~3.69 ft artifact)
FIELD1_MAX_FT = (SENSOR_DATUM_MSL_M - BED_RL_M) / FT_TO_M  # ≈ 67.82 ft

WINDOW_START = "2025-08-08 00:00:00"
WINDOW_END = "2025-08-22 23:00:00"


def preprocess(raw_csv: Path = RAW_CSV, out_csv: Path = OUT_CSV) -> pd.DataFrame:
    df = pd.read_csv(raw_csv)
    assert df["field1"].notna().all(), "raw field1 contains nulls"

    # Parse timestamps (source is IST, +05:30). Keep the wall-clock local time
    # as a naive timestamp so it lines up with the model's naive time axis
    # (control file time zone = Asia/Calcutta).
    ts = pd.to_datetime(df["created_at"], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.assign(timestamp=ts).sort_values("timestamp").reset_index(drop=True)

    n_raw = len(df)
    n_art_low = int((df["field1"] <= FIELD1_MIN_FT).sum())
    n_art_hi = int((df["field1"] > FIELD1_MAX_FT).sum())

    clean = df[(df["field1"] > FIELD1_MIN_FT) & (df["field1"] <= FIELD1_MAX_FT)].copy()
    clean["stage_m"] = SENSOR_DATUM_MSL_M - clean["field1"] * FT_TO_M

    # Floor each reading to its hour, average within the hour, then reindex to
    # the full event window (hours with no readings become NaN).
    clean["hour"] = clean["timestamp"].dt.floor("h")
    hourly_mean = clean.groupby("hour")["stage_m"].mean()
    hourly_count = clean.groupby("hour")["field1"].count()

    idx = pd.date_range(WINDOW_START, WINDOW_END, freq="h")
    hourly = pd.DataFrame({"stage_m": hourly_mean, "source_readings": hourly_count}, index=idx)
    hourly = hourly.reindex(idx)  # ensure every window hour present (NaN gaps)
    hourly.index.name = "timestamp"
    hourly = hourly.reset_index()

    # Report
    n_out = len(hourly)
    n_nan = int(hourly["stage_m"].isna().sum())
    valid = hourly.dropna(subset=["stage_m"])
    peak = valid.loc[valid["stage_m"].idxmax()]
    print(f"Raw readings            : {n_raw}")
    print(f"Artifacts removed (low  : {n_art_low}  (field1 <= {FIELD1_MIN_FT} ft))")
    print(f"Artifacts removed (high : {n_art_hi}  (field1 > {FIELD1_MAX_FT:.2f} ft, stage < bed))")
    print(f"Clean readings          : {len(clean)}")
    print(f"Hourly rows             : {n_out}  ({WINDOW_START} to {WINDOW_END})")
    print(f"Hours with no data      : {n_nan}")
    print(f"Valid stage range       : {valid['stage_m'].min():.3f} - {valid['stage_m'].max():.3f} m MSL")
    print(f"Peak observed stage     : {peak['stage_m']:.3f} m MSL at {peak['timestamp']}")
    print(f"Writing                 : {out_csv}")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    hourly.to_csv(out_csv, index=False, date_format="%Y-%m-%d %H:%M:%S")
    return hourly


if __name__ == "__main__":
    preprocess()
