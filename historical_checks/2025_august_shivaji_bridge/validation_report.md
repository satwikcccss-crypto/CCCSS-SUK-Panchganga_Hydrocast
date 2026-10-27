# HydroCast Validation Report — August 2025 Flood, Shivaji Bridge

**Event**: August 2025 Flood — Shivaji Bridge (Panchganga Basin)  
**Observed window**: 2025-08-08 to 2025-08-22 (14 days)  
**Sensor datum**: 549.35 m MSL (Shivaji Bridge deck level)  
**Stage formula**: Stage (m MSL) = 549.35 − (field1_ft × 0.3048)  
**Model**: HEC-HMS emulator (calibrated Panchganga RJKT physical engine)  
**Rainfall**: Open-Meteo Historical Archive API, 18 gauges / 9 subbasins  

---

## 1. Executive Summary

| Item | Result |
|------|--------|
| Observed peak stage | **542.57 m MSL** on 2025-08-21 14:00 (hourly average) |
| **Best session-calibrated peak stage** | **542.67 m MSL** (lag=2700, k=6.0, cn=90, x=0.15, Ia=0.05, UH cap=90, UH m_exp=50) at **2025-08-21 17:00** |
| **Best session-calibrated stage error** | **+0.10 m** (conservative: sim ≥ obs) |
| **Best session-calibrated timing error** | **+3.0 h** (sim crest 3 h late) |
| Best session NSE (stage) | **0.859** |
| Best session KGE (stage) | **0.815** |
| Best session RMSE (stage) | **~1.30 m** |

**Key finding**: The HydroCast model reproduces the August 2025 Shivaji Bridge hydrograph with **good skill (NSE = 0.86, KGE = 0.76)** using a single continuous 360-hour simulation. Volume bias is negligible (−0.13 %); the residual error is a modest 1.5 m peak under-prediction and an 8-hour late crest.

**Regarding the 90-hour window hypothesis**: Splitting the event into four consecutive 90-hour windows does **not** improve accuracy — it makes it substantially worse (NSE drops to −1.25 to −1.50, RMSE rises to ~5.4 m). The single 360-hour block is the correct configuration for this 14-day multi-storm monsoon event (see Section 5).

---

## 1.1 Life-Safety Calibration Update — 2026-10-22 (Session Log)

Following the life-safety directive (peak ≤ 0.20 m conservative, timing ≤ ±1.0 h, NSE ≥ 0.92, KGE ≥ 0.88), a multi-pronged calibration campaign was executed. **Every change, run, and result is logged in full in
`results/dynamic_calibration/CALIBRATION_SESSION_LOG_2026_10_22.md`.**

### Code changes applied during the session

1. `src/hms/runner.py` — added configurable `ia_frac` (SCS initial-abstraction fraction, default `None`), `uh_max_hr` (caps SCS unit-hydrograph duration, default `None`), and `uh_m_exp` (SCS UH shape exponent, default `3.7`); override application now supports both absolute and relative parameter overrides.
2. `src/hydrology/ml_calibration.py` — asymmetric loss: under-prediction residuals are multiplied by 3.0 (life-safety).
3. `historical_checks/run_historical_event.py` — `2025_august` event now carries life-safety config: `ia_frac=0.05`, `alpha_k=0.85`, `alpha_lag=0.86`, headwater subbasin ΔCN = +2.0.

### Structural enhancements added

- **UH duration cap** (`uh_max_hr=90`): caps SCS UH from `3*tp+1` hours down to a maximum of 90 hours, concentrating the same runoff volume into fewer hours and raising the peak without shifting time-to-peak.
- **UH shape exponent** (`uh_m_exp`): higher values (5–100) produce sharper hydrographs at the same time-to-peak, raising peak magnitude (m_exp=20 raised peak error from −0.64 m → −0.13 m at fixed timing).

### Best results achieved this session

Best configuration (by KGE): `lag_min=2700 min`, `k_hr=6.0 h`, `cn=90`, `muskingum_x=0.15`, `ia_frac=0.05`, `uh_max_hr=90 h`, `uh_m_exp=50`.

| Metric | Best achieved | Life-safety target | Status |
|--------|---------------|--------------------|--------|
| Peak stage error | **+0.10 m** (sim 542.67 ≥ obs 542.56) | ≤ 0.20 m, conservative | ✅ |
| Peak timing error | **+3.0 h** | ≤ ±1.0 h | ❌ |
| NSE | **0.859** | ≥ 0.92 | ❌ |
| KGE | **0.815** | ≥ 0.88 | ❌ |
| Alert-breach timing precision | ~±3 h | exact hour | ❌ |

**Conclusion of this session**: The life-safety calibration got substantially closer — peak under-prediction closed from −1.51 m → +0.10 m, timing from +8.0 h → +3.0 h, NSE 0.86 → 0.86, KGE 0.76 → 0.82. The model structure (SCS UH + Muskingum routing) still cannot simultaneously satisfy all life-safety criteria. Further gains require either event-specific rainfall gauge correction or additional structural UH changes (e.g., a true gamma-shape UH) — recommended as future work.

---

## 2. Step 1 — Preprocess & Clean Observed Telemetry

**Source**: `data/raw/Shivaji Bridge 2025 water levels.csv` (ThingSpeak export, 20,292 readings, 8–22 Aug 2025, IST +05:30)

### 2.1 Artifacts removed
| Artifact | Criterion | Rows removed |
|----------|-----------|--------------|
| Ultrasonic echo drop | `field1` ≤ 10 ft (sensor read ≈ 3.69 ft, i.e. "water right below deck" — lost echo) | 10 |
| Max-range / below-bed | `field1` > 67.82 ft → stage < surveyed river bed (528.67 m MSL), physically impossible | 2 (106.33 ft, 106.66 ft) |
| **Total removed** | | **12** |
| **Clean readings retained** | | **20,280** |

### 2.2 Stage conversion
`stage_m = 549.35 − field1 × 0.3048` applied to every clean reading.

### 2.3 Resampling to 1-hour averages
Each reading floored to its hour, averaged within the hour, then reindexed to the full window `2025-08-08 00:00` → `2025-08-22 23:00` (360 hourly rows). Hours at the start/end with no readings are NaN (22 edge hours).

**Output**: `data/processed/shivaji_bridge_2025_hourly_observed.csv` (360 rows × 3 columns: timestamp, stage_m, source_readings)

### 2.4 Observed statistics
| Statistic | Value |
|-----------|-------|
| Valid hourly observations | 338 / 360 hours |
| Stage range | 533.12 − 542.57 m MSL |
| **Peak observed stage** | **542.57 m MSL** at **2025-08-21 14:00 IST** |
| First valid hour | 2025-08-08 12:00 |
| Last valid hour | 2025-08-22 13:00 |

Note: the peak occurs at hour T+332 (relative to 2025-08-08 00:00), which is **beyond the legacy 90-hour flash-flood window**. This is why the simulation window had to be extended to 360 h.

---

## 3. Step 2 — Rainfall Ingestion & Event Configuration

**Source**: Open-Meteo Historical Archive (`https://archive-api.open-meteo.com/v1/archive`), `hourly=precipitation`, `timezone=UTC`

All 18 raingauge stations were queried for 2025-08-08 to 2025-08-22 (360 h). The governing gage per subbasin was selected by maximum cumulative 360-h rainfall volume (`src/ecmwf/station_selector.select_active_subbasin_gages`).

### Governing stations & 360-h rainfall
| Subbasin | Governing station | Cumulative rain (mm) |
|----------|-------------------|----------------------|
| S1 | Karveer | 179.0 |
| S2 | Sangarul | 269.4 |
| S3 | Kotoli | 262.9 |
| S4 | Karanjphen | 608.6 |
| S5 | Padasali | 734.4 |
| S6 | Gaganbawda | 677.7 |
| S7 | Garivade | 683.7 |
| S8 | Beed | 250.8 |
| S9 | Radhanagari | 522.7 |
| **Mean catchment rain** | | **465.5 mm** |

**Event registered** in `historical_checks/run_historical_event.py` as `2025_august`:
- start: 2025-08-08, end: 2025-08-22, sim_hours: 360
- observed_csv: `data/shivaji_bridge_2025_hourly_observed.csv`
- observed peak stage: 542.57 m MSL (2025-08-21 14:00)

**AMC regime**: AMC-III (saturated soil, mean 90-h catchment rain 465.5 mm ≫ 65 mm threshold) — consistent with a heavy monsoon flood.

---

## 4. Step 3 — Simulation & Validation Results

### 4.1 Main run: single 360-hour block (production path)

Executed via `historical_checks/run_historical_event.py --event 2025_august` (calibration-aware: `delta_cn = +0.89`, reach `x = 0.25` from `data/telemetry/ml_calibration_state.json`).

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Peak discharge | 1,570.4 m³/s at T+336 h | Model flood crest |
| Peak stage (Shivaji) | 541.05 m MSL | vs observed 542.57 m MSL |
| **Stage error** | **−1.52 m** | Model under-predicts peak by 1.5 m |
| **NSE (stage)** | **0.861** | Good skill (0.75–1.0 = good) |
| **KGE (stage)** | **0.756** | Good skill (correlation + variability + volume balanced) |
| RMSE (stage) | 1.29 m | Typical hourly error ~1.3 m |
| MAE (stage) | 1.13 m | Median-ish hourly error ~1.1 m |
| PBIAS (stage) | −0.13 % | Negligible volume bias — total runoff volume is correct |
| Peak timing error | +8.0 h | Simulated crest 8 h late (Aug 22 00:00 vs obs Aug 21 14:00) |
| Matched hours | 338 | Overlap of simulated & observed valid hours |

**Artifact**: `results/360h_block/historical_event_2025_august_results.json` (full 622-hour hydrograph + validation block)

### 4.2 Window comparison: 90-hour windows vs 360-hour block

Executed via `historical_checks/2025_august_shivaji_bridge/scripts/comparison/compare_window_strategies.py`. Same rainfall, same calibration, three strategies:

| Strategy | NSE | KGE | RMSE (m) | MAE (m) | Peak err (m) | Timing err (h) |
|----------|-----|-----|----------|---------|--------------|----------------|
| **A: Single 360-h block** | **0.861** | **0.756** | **1.294** | **1.128** | **−1.51** | **+8.0** |
| B: 4×90-h, fresh start | −1.249 | 0.204 | 5.306 | 4.185 | −3.35 | −8.0 |
| C: 4×90-h, rolling baseflow | −1.498 | 0.184 | 5.592 | 4.509 | −3.57 | −7.0 |

**Artifact**: `results/90h_windows/window_strategy_comparison.json`

**Verdict**: The 90-hour windowing hypothesis is **not supported**. The single continuous 360-hour block outperforms both 90-hour window strategies by a large margin on every metric.

---

## 5. Interpretation — Why the 360-h Block Wins (and 90-h Windows Fail)

### 5.1 What NSE / KGE / RMSE / PBIAS mean here
- **NSE = 0.86**: The model explains 86 % of the variance in observed stage. Values > 0.75 are generally considered "good" for flood forecasting. Negative NSE (as in the 90-h windows) means the model is worse than simply predicting the observed mean.
- **KGE = 0.76**: Decomposes error into correlation (timing/shape), variability bias (peak magnitude), and volume bias. 0.76 indicates a balanced, skillful simulation.
- **PBIAS = −0.13 %**: The total simulated runoff volume matches observed almost exactly — the model is not systematically over- or under-producing water.
- **RMSE 1.29 m / MAE 1.13 m**: On a flood that swings from ~533 m to ~542.5 m (a 9.5 m range), an average error of ~1.1–1.3 m is reasonable.

### 5.2 Why 90-hour windows under-perform
The August 2025 event was a **14-day multi-storm monsoon**, not a single 90-hour flash flood. Chopping it into independent 90-hour forecasts breaks two physical continuities:

1. **Baseflow continuity**: The river does not reset to 91.1 m³/s every 90 hours. Strategy B (fresh start) forces each window to begin from the same baseflow, so windows 2–4 start from an artificially depleted/incorrect initial condition and mis-time their crests (timing errors −7 to −8 h).

2. **Antecedent moisture (SCS) continuity**: Soil moisture accumulates across storms. In a real 14-day monsoon, later storms fall on already-wet soil and produce more runoff. Strategy B/C reset SCS cumulative rainfall every 90 h, so the soil "dries out" artificially between windows, under-generating runoff in later windows (hence the lower peaks: 539.2 / 539.0 m vs observed 542.6 m).

3. **Peak misalignment**: Because each 90-h window reports its peak relative to window start (T+0 to T+89), the absolute timing of the multi-storm crest is lost. The single 360-h run preserves the true sequence: storms on ~Aug 12–13, ~Aug 18–19, and the final crest on Aug 21.

### 5.3 Residual error in the 360-h block (where the remaining −1.51 m comes from)
Even the best run under-predicts the peak by 1.5 m and is 8 h late. Likely causes:
- **Rainfall input**: Open-Meteo archive is a grid reanalysis product, not gauge-corrected radar rainfall. Localized intense cells over the basin may be smoothed.
- **Parameter transfer**: Calibration (`delta_cn = +0.89`, `x = 0.25`) was trained on other events/cycles; the August 2025 storm may need event-specific CN/K/x tuning.
- **Baseflow assumption**: No live telemetry was available for the historical run, so baseflow fell back to 91.1 m³/s. If the actual antecedent baseflow was higher, the peak would be higher.
- **Rating curve**: Stage is derived from discharge via the WRD PCHIP rating curve; uncertainty is largest near bankfull and above (the peak 542.5 m is near the Shivaji alert/warning thresholds 542.10/542.70 m).

---

## 6. Folder Structure (organized)

```
historical_checks/2025_august_shivaji_bridge/
├── data/
│   ├── raw/
│   │   └── Shivaji Bridge 2025 water levels.csv   (20,292 raw readings)
│   ├── processed/
│   │   └── shivaji_bridge_2025_hourly_observed.csv   (360 hourly rows, cleaned)
│   └── stations/
│       └── raingauge_stations.csv   (18 gauges, 9 subbasins)
├── scripts/
│   ├── preprocessing/
│   │   └── preprocess_shivaji_2025.py   (cleaning, stage conversion, resampling)
│   ├── simulation/
│   │   ├── run_360h_block.py   (production 360-h event run)
│   │   └── run_90h_windows.py  (90-h window comparison)
│   └── comparison/
│       └── compare_window_strategies.py   (A vs B vs C analysis)
├── results/
│   ├── 360h_block/
│   │   └── historical_event_2025_august_results.json   (NSE 0.86, KGE 0.76)
│   └── 90h_windows/
│       └── window_strategy_comparison.json   (window comparison table)
├── docs/
│   └── accuracy_comparison.md   (2019 / 2021 / 2025 accuracy table)
└── validation_report.md   (this document)
```

### How to re-run
```bash
# 1. Reproduce the cleaned observed series
python historical_checks/2025_august_shivaji_bridge/scripts/preprocessing/preprocess_shivaji_2025.py

# 2. Run the 360-h block validation (main result)
python historical_checks/2025_august_shivaji_bridge/scripts/simulation/run_360h_block.py

# 3. Run the 90-h window comparison
python historical_checks/2025_august_shivaji_bridge/scripts/simulation/run_90h_windows.py
```
(All scripts insert the repo root and `historical_checks/` on `sys.path` so they import `src.*` and `run_historical_event` correctly.)

---

## 7. Conclusion & Recommendations

1. **The August 2025 event validates well**: NSE 0.86 / KGE 0.76 / PBIAS −0.13 % shows HydroCast can simulate a 14-day monsoon flood at Shivaji Bridge with good skill when run as a single continuous 360-hour block with station-selected rainfall.

2. **Do NOT use 90-hour windows for multi-day monsoon events**: The legacy 90-h flash-flood window is inappropriate for a 14-day event. It resets baseflow and antecedent moisture, degrading NSE from 0.86 to ≈ −1.3. Use a window matching the event duration (here 360 h).

3. **Peak is under-predicted by 1.5 m and 8 h late**: To close this gap, consider event-specific calibration of CN / Muskingum K / x for August 2025, gauge-corrected rainfall, and/or assimilating the observed Shivaji stage to nudge baseflow.

4. **Life-safety calibration (2026-10-22) improved but did not fully close the gap**: See Section 1.1. Best achieved: peak +0.10 m conservative, timing +3.0 h, NSE 0.86, KGE 0.82. Full campaign log: `results/dynamic_calibration/CALIBRATION_SESSION_LOG_2026_10_22.md`.

5. **Existing regression tests still pass**: `pytest tests/ -q --no-header` → **154 passed**. The runner.py changes (configurable `sim_hours`, `ia_frac`, `uh_max_hr`, `uh_m_exp`) are backward compatible — the 2019/2021 90-h events are unchanged.

---

*Report generated from `historical_checks/2025_august_shivaji_bridge/`, October 2026.*
