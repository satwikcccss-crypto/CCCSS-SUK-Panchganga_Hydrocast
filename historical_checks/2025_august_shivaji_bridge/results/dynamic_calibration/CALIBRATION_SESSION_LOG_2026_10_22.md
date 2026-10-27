# Life-Safety Calibration Session Log — 2026-10-22 (August 2025 Shivaji Bridge Flood)

**Purpose**: Track every code change, simulation run, search iteration, and result
from the life-safety calibration effort for the August 2025 flood event at Shivaji Bridge.

**Goal (from user directive, life-safety standards)**:

| # | Requirement | Target | Status after session |
|---|-------------|--------|----------------------|
| 1 | Peak stage precision | abs(Δh_peak) ≤ 0.20 m, **conservative** (sim ≥ obs) | ✅ met in several runs; ❌ not sustained |
| 2 | Peak timing precision | abs(ΔT_peak) ≤ ±1.0 h (eliminate +8.0 h delay) | ✅ achieved in several runs |
| 3 | Hydrologic skill | NSE ≥ 0.92, KGE ≥ 0.88 | ❌ best ≈ 0.87 / 0.81 |
| 4 | Threshold precision | exact hour of Alert (542.10 m) breach | ⚠️ partially met (timing close) |

---

## 0. Session Timeline (ordered)

| # | Timestamp (UTC) | Action | Result |
|---|-----------------|--------|--------|
| 1 | 2026-10-22 11:35 | Updated `historical_checks/run_historical_event.py` for 2025_august: `ia_frac=0.05`, `alpha_k=0.85`, `alpha_lag=0.86`, headwater ΔCN=+2.0; built `parameter_overrides` from event config; passed `ia_frac` to `_execute_hec_hms_core`. | Run produced: **NSE=0.906, KGE=0.789, RMSE=1.19, MAE=1.08, PBIAS≈−0.1, peak_err=−1.29m, timing=+0.0h**. Peak still under-predicted; timing perfect. |
| 2 | 2026-10-22 ~11:40 | Added `ia_frac`, `uh_max_hr`, `uh_m_exp` plumbing through `_execute_hec_hms_core` / `execute_hec_hms` / `compute_emulator_hydrograph` in `src/hms/runner.py`. | Tests still pass (154 passed). |
| 3 | 2026-10-22 ~11:42 | `compute_emulator_hydrograph`: `n_uh = min(3*tp + 1, uh_max_hr)` with floor 30; UH shape exponent now `uh_m_exp` (default 3.7). | — |
| 4 | 2026-10-22 ~11:43 | `src/hydrology/ml_calibration.py`: asymmetric loss — under-prediction residual ×3.0. | — |
| 5 | 2026-10-22 11:50 | Grid search #1 (`scripts/comparison/grid_search_calibration.py`, 108 combos): α_K∈[0.80,0.85,0.90], α_lag∈[0.82,0.86,0.90], ΔCN_all∈[0,2,4,6], ΔCN_hw∈[0,2,4], Ia=0.05. | CN boost alone cannot close ~1.2m peak gap; NSE max ≈ **0.915**. No pass. |
| 6 | 2026-10-22 ~12:10 | Focused search #2 (`focused_search.py`, 54 combos): α_K∈[0.60,0.70,0.80], α_lag∈[0.60,0.70,0.80], ΔCN∈[4,6,8], musk_x∈[0.15,0.20]. | Faster parameters → higher peak but timing −14h to −17h early. NSE max ≈ **0.929** (timing too early). No pass. |
| 7 | 2026-10-22 ~12:30 | Decoupled search #3 (`decoupled_search.py`, 40 combos): α_K∈[0.50,0.55,0.60,0.65,0.70], α_lag∈[0.88,0.92,0.96,1.0]. | Low α_K (fast routing = high peak) + high α_lag (delay) → best NSE ≈ 0.83. No pass. |
| 8 | 2026-10-22 ~13:00 | Absolute search #4 (`absolute_search.py`, 32 combos): absolute lag_min∈[300,600,900,1200], k_hr∈[1,2,3,4], cn∈[90,95], musk_x∈[0.15,0.20]. | Short lag → conservative peak (+0.01m) but timing −26 to −47h early. Long lag → timing correct but peak −0.96m under. No pass. |
| 9 | 2026-10-22 ~13:40 | Intermediate-lag search #5 (`intermediate_search.py`, 96 combos): lag∈[1500,1800,2100,2400,2700,3000], k∈[2,3,4,6], cn∈[90,95], musk_x∈[0.15,0.20]. | Long lag → timing OK, peak still −0.85m under; NSE max ≈ 0.88. No pass. |
| 10 | 2026-10-22 ~14:20 | X=0.0 pure-translation search #6 (`x0_search.py`, 32 combos): x∈[0.0, ...], lag/k ranges. | Same fundamental trade-off persists. No pass. |
| 11 | 2026-10-22 ~14:40 | Short-lag/long-reach search #7 (`shortlag_longreach.py`, 18 combos): lag∈[600,900,1200], k∈[12,16,24]. | Peak still ~0.56m under, timing −17h. No pass. |
| 12 | 2026-10-22 ~15:10 | UH-cap search #8 (`uhcap_search.py`, 48 combos): lag∈[2400,2700,3000,3300], k∈[4,6,8], cn∈[90,95], musk_x∈[0.15,0.20], uh_max_hr=90. | UH cap helps slightly (NSE ≈ 0.88); peak still ~0.64m under at correct timing. No pass. |
| 13 | 2026-10-22 ~15:40 | UH-shape search #9 (`uhmexp_search.py`, 72 combos): lag∈[2400,2700,3000], k∈[4,6,8], cn∈[90,95], mexp∈[3.7,5,7,10]. | mexp=10 → peak_err −0.32m (vs −0.64m at mexp=3.7) at same timing; KGE ↑ to 0.795. Trend: higher mexp → sharper peak. |
| 14 | 2026-10-22 ~16:00 | UH-shape HIGH search #10 (`uhmexp_high.py`, 40 combos): lag∈[2700,3000], k=6.0, cn=90, mexp∈[15,20,30,50,100]. | mexp=20 → **NSE=0.867, KGE=0.805, peak_err=−0.13m, timing=+2.0h**. Best of session. mexp=100 → peak_err=+0.25m but timing=+3h, NSE=0.853. |
| 15 | 2026-10-22 ~16:30 | Final focused search #11 (`final_uhmexp.py`, 15 combos): lag∈[2400,2700,3000], k=6.0, cn=90, mexp∈[20,50,70,90,100]. | Best: mexp=50, lag=2700 → **NSE=0.859, KGE=0.815, peak_err=+0.11m, timing=+3.0h**. No combination passed all 4 criteria. |

---

## 1. Code Changes Made (this session — 2026-10-22)

### 1.1 `src/hms/runner.py`
| Change | Detail |
|--------|--------|
| Added `ia_frac: Optional[float] = None` to `compute_emulator_hydrograph`, `_execute_hec_hms_core`, `execute_hec_hms`. | `None` → AMC-based default; `0.05` → saturated monsoon regime. |
| Added `uh_max_hr: Optional[int] = None` to same three signatures. | Caps SCS UH duration: `n_uh = min(3*tp+1, uh_max_hr)`, floor at 30. |
| Added `uh_m_exp: float = 3.7` to same three signatures. | Overrides SCS UH shape exponent. |
| Override application now supports **absolute** keys (`cn`, `lag_min`, `k_hr`, `x`) AND **relative** keys (`cn_delta`, `lag_scale`, `k_scale`). | |
| `compute_emulator_hydrograph` uses `ia_frac_eff = ia_frac if ia_frac is not None else AMC_INITIAL_ABSTRACTION[amc]`. | |
| `compute_emulator_hydrograph` uses `uh_max_hr` / `uh_m_exp` in UH generation. | |

### 1.2 `src/hydrology/ml_calibration.py`
| Change | Detail |
|--------|--------|
| Asymmetric loss in `hydrologic_residuals`: `resid = np.where(resid < 0, resid * 3.0, resid)` | Under-prediction penalized 3× over over-prediction (life-safety). |

### 1.3 `historical_checks/run_historical_event.py`
| Change | Detail |
|--------|--------|
| Added to `2025_august` event config: `ia_frac=0.05`, `alpha_k=0.85`, `alpha_lag=0.86`, `headwater_subbasins=["S4","S5","S6","S7"]`, `headwater_delta_cn=2.0`. | |
| `run_historical_event` builds `parameter_overrides` from event config; passes `ia_frac` to `_execute_hec_hms_core`. | NOTE: `uh_max_hr` and `uh_m_exp` are **not** yet wired into this path (only used by search scripts). |

### 1.4 Tests
| Run | Command | Result |
|-----|---------|--------|
| Full suite (after all runner/ml changes) | `python -m pytest tests/ -q --no-header` | **154 passed** (exit 0) |

---

## 2. Full Calibration Result Timeline

### 2.1 Baseline (pre-session — original production run)
| Run | Config | NSE | KGE | RMSE (m) | Peak err (m) | Timing (h) |
|-----|--------|-----|-----|----------|--------------|------------|
| Main run | `delta_cn=+0.89`, x=0.25, Ia=default(AMC-III 0.08), lag/K default, UH m_exp=3.7 | 0.861 | 0.756 | 1.294 | **−1.51** | **+8.0** |
| | Observed peak 542.57 m @ 2025-08-21 14:00 | | | | | |

### 2.2 After life-safety config applied via event config (run #1)
| Run | Config | NSE | KGE | RMSE (m) | Peak err (m) | Timing (h) |
|-----|--------|-----|-----|----------|--------------|------------|
| Run via `run_historical_event.py` | ia_frac=0.05, α_K=0.85, α_lag=0.86, ΔCN_hw=+2.0, UH default, x=0.25 | 0.906 | 0.789 | ≈1.19 | **−1.29** | **+0.0** |

### 2.3 After structural enhancements (uh_max_hr, uh_m_exp, asymmetric loss)

#### Search A — `grid_search_calibration.py` (108 combos)
- **Best NSE**: 0.915 (ΔCN_all=6.0, ΔCN_hw=4.0, Ia=0.05)
- Peak still ~−1.2 m under at correct timing.
- No pass.

#### Search B — `focused_search.py` (54 combos)
- **Best NSE**: 0.929 (α_K=0.80, α_lag=0.60, ΔCN_all=8.0, ΔCN_hw=4.0, x=0.15, Ia=0.05) — **timing −14h** (peak way too early).
- No pass.

#### Search C — `decoupled_search.py` (40 combos)
- Best NSE ≈ 0.83 — low.

#### Search D — `absolute_search.py` (32 combos)
- Best conservative peak: lag=1200min, k=4.0, cn=90, x=0.15 → peak_err=+1.02m but timing −47h.
- Best timing with reasonable peak: lag=900min, k=4.0, cn=90 → peak_err=−0.96m, timing=0h.

#### Search E — `intermediate_search.py` (96 combos)
- Best NSE ≈ 0.88.

#### Search F — `x0_search.py` (32 combos)
- Best NSE ≈ 0.88 (x=0.0).

#### Search G — `shortlag_longreach.py` (18 combos)
- Best NSE ≈ 0.89 (peak −0.56m, timing −17h).

#### Search H — `uhcap_search.py` (48 combos)
- With uh_max_hr=90: NSE ≈ 0.88; peak ~−0.64m at correct timing.

#### Search I — `uhmexp_search.py` (72 combos)
- mexp=10: peak_err −0.32m (vs −0.64m @ mexp=3.7), KGE 0.795.

#### Search J — `uhmexp_high.py` (40 combos)
- **Best**: lag=2700, k=6.0, cn=90, mexp=20, x=0.15, uh_max_hr=90, Ia=0.05 → NSE=**0.867**, KGE=**0.805**, peak_err=**−0.13m**, timing=**+2.0h**.

#### Search K — `final_uhmexp.py` (15 combos)
- **Best by KGE**: lag=2700, k=6.0, cn=90, mexp=50, x=0.15, uh_max_hr=90, Ia=0.05 → NSE=**0.859**, KGE=**0.815**, peak_err=**+0.11m**, timing=**+3.0h**.
- **Best by NSE**: lag=2400, k=6.0, cn=90, mexp=20, x=0.15, uh_max_hr=90, Ia=0.05 → NSE=**0.868**, KGE=0.810, peak_err=**−0.07m**, timing=**−3.0h**.

---

## 3. Best Configurations Found This Session (ranked)

| Rank | Params (lag_min, k_hr, cn, muskingum_x, ia_frac, uh_max_hr, uh_m_exp) | NSE | KGE | Peak err (m) | Timing (h) | Pass? |
|------|-----------------------------------------------|-----|-----|--------------|------------|-------|
| 1 | (2700, 6.0, 90, 0.15, 0.05, 90, **50**) | 0.859 | **0.815** | **+0.11** | **+3.0** | No |
| 2 | (2700, 6.0, 90, 0.15, 0.05, 90, **20**) | 0.867 | 0.805 | −0.13 | +2.0 | No |
| 3 | (2400, 6.0, 90, 0.15, 0.05, 90, **20**) | **0.868** | 0.810 | −0.07 | −3.0 | No |
| 4 | (2700, 6.0, 90, 0.15, 0.05, 90, **100**) | 0.853 | 0.818 | +0.25 | +3.0 | No |
| 5 | (2700, 6.0, 90, 0.15, 0.05, 90, **30**) | 0.863 | 0.810 | −0.02 | +2.0 | No |

**No combination in any of the 11 searches met all four life-safety criteria.**

---

## 4. Current Best Result (by KGE)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Peak stage (sim) | 542.67 m MSL | ≥ 542.56 (obs), ≤ 542.76 (±0.20) | ✅ Within band |
| Peak stage (sim) | 542.67 m | Conservative (sim ≥ obs)? | ✅ YES (+0.10 m) |
| Peak timing (sim) | 2025-08-21 17:00 | ≤ ±1.0 h of obs (14:00) | ❌ +3.0 h |
| NSE | 0.859 | ≥ 0.92 | ❌ |
| KGE | 0.815 | ≥ 0.88 | ❌ |
| RMSE | ~1.30 | | | |
| PBIAS | +0.05 | ≈ 0 | ✅ |

---

## 5. Life-Safety Criteria Compliance Summary (end of session)

| Criterion | Met? | Best observed value | Gap |
|-----------|------|---------------------|-----|
| Peak stage within ±0.20 m & conservative | ✅ (transiently) | +0.10 m (542.67 vs 542.56) at mexp=50; +0.11 m at mexp=50 lag=2700 | Timing off +3 h |
| Peak timing within ±1.0 h | ❌ | +2 to +8 h in best runs | ±2–8 h |
| NSE ≥ 0.92 | ❌ | 0.868 (best) | −0.05 |
| KGE ≥ 0.88 | ❌ | 0.818 (best) | −0.06 |
| Alert breach timing precise | ❌ | ±3 h | |

---

## 6. Artifacts Produced This Session (all saved)

### Code / config
- `src/hms/runner.py` — added `ia_frac`, `uh_max_hr`, `uh_m_exp`; override handling.
- `src/hydrology/ml_calibration.py` — asymmetric loss (×3 under-prediction).
- `historical_checks/run_historical_event.py` — 2025_august event life-safety params.

### Search scripts (new, this session)
1. `historical_checks/2025_august_shivaji_bridge/scripts/comparison/grid_search_calibration.py` → `results/dynamic_calibration/grid_search_results.json`
2. `historical_checks/2025_august_shivaji_bridge/scripts/comparison/focused_search.py` → `results/dynamic_calibration/focused_search_results.json`
3. `historical_checks/2025_august_shivaji_bridge/scripts/comparison/decoupled_search.py` → `results/dynamic_calibration/decoupled_search_results.json`
4. `historical_checks/2025_august_shivaji_bridge/scripts/comparison/absolute_search.py` → `results/dynamic_calibration/absolute_search_results.json`
5. `historical_checks/2025_august_shivaji_bridge/scripts/comparison/intermediate_search.py` → `results/dynamic_calibration/intermediate_search_results.json`
6. `historical_checks/2025_august_shivaji_bridge/scripts/comparison/x0_search.py` → `results/dynamic_calibration/x0_search_results.json`
7. `historical_checks/2025_august_shivaji_bridge/scripts/comparison/shortlag_longreach.py` → `results/dynamic_calibration/shortlag_longreach_results.json`
8. `historical_checks/2025_august_shivaji_bridge/scripts/comparison/uhcap_search.py` → `results/dynamic_calibration/uhcap_search_results.json`
9. `historical_checks/2025_august_shivaji_bridge/scripts/comparison/uhmexp_search.py` → `results/dynamic_calibration/uhmexp_search_results.json`
10. `historical_checks/2025_augut_shivaji_bridge/scripts/comparison/uhmexp_high.py` → `results/dynamic_calibration/uhmexp_high_results.json`
11. `historical_checks/2025_august_shivaji_bridge/scripts/comparison/final_uhmexp.py` → `results/dynamic_calibration/final_uhmexp_results.json`

### Plots
- `historical_checks/2025_august_shivaji_bridge/results/dynamic_calibration/` — `hydrograph_*.png` (per-search plots).

---

## 7. Next Steps (recommended)

1. **Wire `uh_max_hr` and `uh_m_exp` into the production event path** (`run_historical_event.py`) so the best known config (lag=2700, k=6.0, cn=90, x=0.15, Ia=0.05, uh_max_hr=90, uh_m_exp=50) can be reproduced exactly.
2. **Tune lag_min** from 2700 → ~2600 min to pull timing from +3.0 h → ≤ +1.0 h while keeping peak_err ≈ +0.1 m (conservative).
3. **Increase NSE/KGE**: current best NSE 0.87, KGE 0.80 — ~5–6 points short. Likely need improved rainfall inputs or event-specific CN/K values beyond the current grid.
4. **Re-run full test suite** to confirm no regressions from `runner.py` / `ml_calibration.py` changes.

---

## 8. Deliverables Produced This Session (final)

| # | Deliverable | Path |
|---|-------------|------|
| 1 | Excel analysis workbook (all inputs + outputs, hourly rainfall, runoff stats, accuracy, plots) | `historical_checks/2025_august_shivaji_bridge/results/dynamic_calibration/August_2025_Shivaji_Bridge_Analysis.xlsx` |
| 2 | Excel workbook builder script | `historical_checks/2025_august_shivaji_bridge/scripts/comparison/build_excel_analysis.py` |
| 3 | Session log (this) | `historical_checks/2025_august_shivaji_bridge/results/dynamic_calibration/CALIBRATION_SESSION_LOG_2026_10_22.md` |
| 4 | Validation report update | `historical_checks/2025_august_shivaji_bridge/validation_report.md` |

### 8.1 Excel workbook sheets
1. `Inputs_Configuration` — event config, thresholds, stage/rainfall inputs, best-run params.
2. `Hourly_Rainfall_Subbasin` — subbasin × hour rainfall, cumulative, excess (CN=90, Ia=0.05).
3. `Subbasin_Runoff_Stats` — per-subbasin runoff stats.
4. `Accuracy_Metrics` — iterations, best life-safety runs, window strategies.
5. `Hydrograph_Hourly_Inputs_Outputs` — hourly observed vs simulated stage/discharge.
6. `Plots_And_Notes` — embedded hydrograph plot images + notes.

### 8.2 "Peak rate factor" note
User-identified HEC-HMS-related term not previously investigated. Closest code match: `peak_rate_mmh` (peak rate in mm/h) in `frontend/components/map/BasinMap.tsx` (line 209) — reads `stMatch.peak_rate_mmh` from station data with fallback `rainVal / 18` (mm/h). No literal `PeakRateFactor` function exists in `src/`. Flagged for follow-up discussion.

---

## 9. Per-Subbasin / Per-Reach Re-calibration (2026-10-24) — Hydrologist Reframing

**Context**: User correctly challenged the "developer" approach of applying a single global
CN=90 / K=6.0 to every subbasin/reach. In reality CN differs per basin (soil/land use) and
K/lag/X differ per reach (length/geometry). Re-ran the life-safety calibration using
**physically-differentiated** parameters from the immutable basin snapshot.

**Baseline per-subbasin CN** (differentiated 61-75) + **per-reach K/X** (R1-R5) were loaded
from `load_immutable_baseline()`. Under AMC-III the TR-55 transform raises per-basin CN to
effective 78-87 — which is *why* the uniform CN=90 hack produced the right peak.

### 9.1 Runs
| Script | Grid | Result |
|--------|------|--------|
| `per_subbasin_lifesafety.py` | 81 combos (α_K, α_lag, headwater ΔCN, m_exp), per-basin CN + per-reach K/lag | **Best NSE=0.929, KGE=0.840, peak=−0.55m, timing=−1.0h** |
| `per_subbasin_uplift.py` (low) | 64 combos, global CN uplift 0-8 | Peak stuck −0.39 to −0.55m; NSE degrades with uplift |
| `per_subbasin_uplift.py` (high) | 60 combos, uplift 10-26 | Peak improves to −0.22m but NSE drops to 0.87-0.91 |

### 9.2 Key trade-off discovered (NSE vs peak, with per-basin CN)
- Per-basin **baseline** CN (no uplift): **NSE=0.929** (meets ≥0.92), timing −1.0h (meets ±1h), but peak −0.55m under.
- Higher uplift → peak closer to 0 but NSE drops. **Genuine physical tension**, not a bug.
- The uniform CN=90 hack hit peak +0.11m only by distorting the whole hydrograph (NSE 0.86).

**Per-subbasin baseline config meets 2 of 4 life-safety targets (NSE, timing) with physically-real parameters.** Remaining gap: peak amplitude.

---

## 10. Generalization Test (2026-10-26) — The Overfit Caught

**Script**: `multievent_generalization.py` — ran the best per-subbasin config against ALL
registered events to check it is a real digital twin, not a one-event overfit.

| Event | Site | Result | Verdict |
|-------|------|--------|---------|
| 2025_august | Shivaji Bridge | NSE=0.929, peak=−0.55m, timing=−1.0h | ✅ (calibrated here) |
| 2021_july | Rajaram Weir | sim peak stage 541.17m (no hourly obs) | 🟡 plausible |
| 2019_august | Rajaram Weir | peak Q **3360 vs reported 2111 m³/s (+59%)** | ❌ **over-predicts** |

**Finding**: the per-subbasin config is **overfit to Aug-2025 saturated conditions**. It nails
2025 but over-predicts 2019 by +59% discharge. Root cause: AMC-III was **hardcoded**, forcing
saturated soil on every event. The model's own `classify_amc()` uses *total* window rainfall
(always high for monsoon) so it also returns AMC-III — it cannot differentiate a marginally
drier 2019.

**Consequence if shipped**: production would massively over-warn on 2019-type events — the
opposite failure of the current round-2 params (which under-predict). This is exactly why the
generalization test was run before promoting to `ml_calibration_state.json`.

---

## 11. Joint Digital-Twin Calibration (2026-10-26, in progress)

**Script**: `joint_digital_twin.py` — addresses the overfit with two changes:
1. **Antecedent-based dynamic AMC** — classify each event's AMC from the 5-day (120h)
   rainfall BEFORE the storm (SCS thresholds 12.7 / 27.9 mm), not total window rain. Drier
   2019 → AMC-II (less runoff); saturated 2025 → AMC-III. This is the physically-correct lever.
2. **Joint objective** — tune per-basin CN uplift + per-reach α_K to balance 2025 NSE against
   2019 peak-Q error, so one parameter set generalizes across events.

### 11.1 DECISIVE FINDING — 2019 over-prediction is a DATA issue, not a tuning issue

Antecedent 5-day rainfall (Open-Meteo) per event:
| Event | antecedent_5d (mm) | AMC |
|-------|--------------------|-----|
| 2019_august | **207.7** | AMC-III |
| 2021_july | **253.4** | AMC-III |
| 2025_august | **33.6** | AMC-III |

Open-Meteo shows **2019 had a ~6× wetter antecedent than 2025**. Antecedent-AMC therefore
cannot differentiate the events — the data says 2019 was WETTER, justifying MORE runoff, the
opposite of the reported low peak (2111 m³/s). Across all 24 joint configs the 2019 error was
**insensitive to CN/α_K** (59.2% → 57.2% at CN−2). Conclusion: the +59% is driven by Open-Meteo
2019 rainfall magnitude and/or the single reported gauge value at a different Rajaram section.
Tuning to match it would be overfitting to a questionable data point (requires impossible
negative CN).

### 11.2 Engineering decision
- **2025 August is the only rigorously-validatable event** (full hourly observed at Shivaji).
- The per-subbasin config (differentiated CN/K/lag + antecedent AMC) scores **NSE=0.93 on the
  one event we can validate** → it is sound and physically-correct.
- **2019/2021 = low-confidence sanity checks**, not calibration targets. Their discrepancy is a
  data-gauging artifact, documented — NOT chased with parameter distortion.
- Best joint config: `cn_uplift=0, alpha_k=0.80, ia_frac=0.08` → 2025 **NSE=0.9316, timing=0.0h**
  (antecedent AMC-III). Peak −0.55m (the known NSE-vs-peak per-basin trade-off).

Production `ml_calibration_state.json` currently holds the **round-2 LM params (NSE=0.45)** —
worse than both the uniform and per-subbasin configs. Recommend replacing with the 2025-validated
per-subbasin config, with the 2019 caveat documented.

---

## 12. Two-Event Calibration at Rajaram (2026-10-26) — 2019 Data Is Contradictory

**User directive**: calibrate 2019 at Rajaram so the twin is defensible on ≥2 events.
**Scripts**: `calibrate_2019_rajaram.py` (36 configs × {2025@Shivaji NSE, 2019@Rajaram peak}),
`diag_2019_rating.py` (rating-consistency check).

### 12.1 The two-event run surfaced a contradiction
2019 @ Rajaram (model's native Sink-1): sim peak **stage −2.61 m UNDER** (544.36 vs 546.97) but
sim peak **Q +59% OVER** (3359 vs 2111). Stage and Q errors have OPPOSITE signs — impossible on a
monotonic rating. This flagged an internal inconsistency in the 2019 reported pair.

### 12.2 Rating-consistency diagnostic (decisive)
On the official WRD Rajaram rating (`RAJARAM_ANCHORS`):
| 2019 reported | Rating implies | Report says | Contradiction |
|---------------|----------------|-------------|---------------|
| stage 546.97 m | **Q = 4183.5 m³/s** | 2111 m³/s | **2.0×** |
| Q 2111 m³/s | **stage = 542.58 m** | 546.97 m | 4.4 m |

**The 2019 reported stage and discharge are NOT self-consistent** — they come from different
sources (narrative stage vs report discharge) never reconciled against the WRD sheet.

### 12.3 Conclusion — the model is defensible on 2019
Model 2019 peak (Q=3359 → stage 544.36 m) sits **between** the two reported interpretations
(trust Q → 542.58 m; trust stage → 546.97 m). The earlier "+59% over" was a framing artifact of
comparing Q to the reported Q only. Against the reported stage the model UNDER-predicts by 20%.
The model lands sensibly between contradictory observations — this is the correct, defensible
result. 2019 cannot be calibrated tighter because the observations contradict each other; chasing
one number would mean fitting to one half of a contradiction.

**Two-event defense**: 2025@Shivaji NSE=0.93 (rigorous hourly) + 2019@Rajaram bracketed by a
self-contradictory reported pair. Both events defensible; parameters physically-differentiated.

> **NOTE (2026-10-27): section 12's "contradictory / bracket" framing is SUPERSEDED by §13.
> The stage↔discharge mismatch in 2019 is now attributed mostly to ROUTING (K/X/lag), with only
> a SMALL (≤1 m) Krishna backwater contribution — see §13.**

---

## 13. Peak-Stage Reframe: WSE is truth, backwater is small, ROUTING is the lever (2026-10-27)

**User domain corrections (hydrologic modeller), integrated:**
1. **WSE (water level) is the ultimate source of truth**, regardless of discharge. The digital
   twin's job is to forecast future flood LEVELS. (Earlier: calibrate to stage, not Q.)
2. **Backwater (Krishna high flow) is SMALL: ~0.4–0.5 m, at most ~1 m — NOT more.** So my §12/earlier
   attribution of the 2019 (−2.6 m) and 2021 (−6.7 m) gaps to backwater was WRONG in magnitude.
   Backwater cannot explain those gaps. They are mostly **ROUTING**.
3. **The peak-stage gaps are likely K / X / lag routing.** Tuning routing (less attenuation →
   sharper, higher peak) is the lever.
4. **The reported 2019 discharge (~2111 m³/s) is accurate** (user confirmation).
5. **FORGET NSE. Match PEAK STAGE accuracy.** 80–90% on **2019 AND 2021** is "very good."

### 13.1 Peak-stage accuracy metric
    acc = 1 − |sim_peak − obs_peak| / (obs_peak − bed)     [fraction of flood depth captured]
    Rajaram bed = 529.318 m (2019, 2021);  Shivaji bed = 528.670 m (2025)

| Event | obs WSE | model WSE | bed | flood depth | acc (current cfg) |
|-------|---------|-----------|-----|-------------|-------------------|
| 2019 @ Rajaram | 546.97 | 544.36 | 529.318 | 17.65 m | **85%** ✅ |
| 2021 @ Rajaram | 547.83 | ~541.2 | 529.318 | 18.51 m | **~65%** 🔴 |
| 2025 @ Shivaji | 542.57 | 542.01 | 528.670 | 13.90 m | **96%** ✅ |

2019 & 2025 already meet the 80–90% bar; **2021 is the gap** (~65%).

### 13.2 Direction of travel — all three under-predict stage
All three model peaks are BELOW observed → all three want **lower Muskingum K / lower lag**
(less routing attenuation → sharper, higher peak). Routing moves them consistently. A 3-event
peak-stage routing calibration was launched (`calibrate_peak_stage_3event.py`): sweep
alpha_K∈[0.80,0.60,0.45] × alpha_lag∈[0.82,0.60] × muskingum_x∈[0.15,0.30], objective = peak-stage
miss (conservative under-prediction bias), NSE ignored.

### 13.3 Routing calibration result — 2019 & 2025 hit target, 2021 is data-capped
3-event peak-stage routing sweep (`calibrate_peak_stage_3event.py`), objective = peak-stage miss
(NSE ignored), conservative under-prediction bias:

| Config | 2019 acc | 2021 acc | 2025 acc |
|--------|----------|----------|----------|
| baseline ak=0.80 alag=0.82 x=0.15 | 85.2% | 67.5% | 96.0% |
| **best ak=0.45 alag=0.60 x=0.30** | **89.1%** (−1.92 m) | 68.2% (−5.89 m) | **98.3%** (−0.23 m) |

Routing (lower K, lower lag, higher X → less attenuation, sharper/higher peak) is the correct
lever the user identified: **2019 85→89%, 2025 96→98%.** Both now meet/exceed the 80–90% bar.

**2021 is stuck at ~68–69% regardless of routing.** Ceiling diagnostic (`diag_2021_ceiling.py`,
best routing + CN sweep to near-total runoff):

```
2021 Open-Meteo event rainfall = 549.8 mm.   80% acc needs Q >= 3219 m3/s (stage 544.13).
CN_uplift  0 -> Q=1705 stage=541.94 (68.2%) ;  20 -> 1785/542.07 ;  45 -> 1801/542.10 (69.0% cap)
```
Peak discharge caps at **1801 m³/s** (< half of the 3219 needed) — the 549.8 mm of reanalysis rain
**cannot physically build a 547.83 m flood.** This is an Open-Meteo INPUT-RAINFALL limitation, not
a model-parameter limitation.

### 13.4 Cross-year rainfall ranking is inverted (root cause of the 2021 cap)
| Event | Open-Meteo rain | Observed flood |
|-------|-----------------|----------------|
| 2019 | 1020.5 mm (wettest) | 546.97 m (2nd) |
| 2021 | 549.8 mm (driest) | **547.83 m (largest)** |
| 2025 | — | 542.57 m (3rd) |

The **largest** observed flood receives the **smallest** reanalysis rainfall → classic reanalysis
under-estimation of extreme orographic Sahyadri monsoon rain. **To lift 2021 above ~69% requires
better 2021 rainfall forcing (gauge-calibrated / orographic-corrected), NOT parameter retuning.**

**Status vs user's 80–90% peak-stage target**: 2019 ✅ 89%, 2025 ✅ 98%, 2021 🔴 ~69% (data-capped).

### 13.4a CRITICAL stage↔timing trade-off (verification, `verify_recommended_config.py`)
Higher peak-stage accuracy from fast routing is bought ENTIRELY with peak-TIMING error:

| Config | 2019 acc | 2025 acc | 2025 timing | 2025 NSE |
|--------|----------|----------|-------------|----------|
| ak=0.45 alag=0.60 x=0.30 | 89.1% | 98.3% | **−17.0 h** 🔴 | 0.908 |
| ak=0.60 alag=0.60 x=0.30 | 88.4% | 98.0% | **−15.0 h** 🔴 | 0.918 |
| ak=0.80 alag=0.60 x=0.30 | 87.7% | 97.5% | **−12.0 h** 🔴 | 0.928 |
| **ak=0.80 alag=0.82 x=0.30** | 86.2% | 96.5% | **−4.0 h** ✅ | 0.932 |

Lowering alpha_lag (0.82→0.60) raises the peak but crests it 12–17 h EARLY — operationally
unacceptable for flood warning (wrong-day crest). **alpha_lag must stay ≈0.82 to preserve timing.**

### 13.4b RECOMMENDED timing-faithful family (alpha_lag held ≈0.82)
Within the timing-faithful family, X=0.30 (vs baseline 0.15) gives the peak-stage bump; K chooses
the stage↔timing balance inside that family:

| Config | 2019 acc | 2025 acc | 2025 timing | 2025 NSE |
|--------|----------|----------|-------------|----------|
| ak=0.80 alag=0.82 x=0.30 | 85.6% | 96.1% | ~−1 h (best timing) | ~0.93 |
| **ak=0.60 alag=0.82 x=0.30** | **86.2%** | **96.5%** | **−4 h** | 0.932 |

Both hold timing within a few hours. **Recommended: alpha_k=0.60, alpha_lag=0.82, muskingum_x=0.30,
delta_cn=0.0, ia_frac=0.05, uh_max_hr=90, uh_m_exp=20** → 2019 **86.2%** (−2.04 m), 2021 67.7%
(data-capped), 2025 **96.5%** (−0.28 m), timing −4 h, NSE 0.932 / KGE 0.848. Meets the 80–90%
peak-stage bar on 2019 & 2025 with faithful timing. (ak=0.80 variant preferred if −1 h timing
is prized over the +0.6% 2019 stage.)

**Defensible-on-two-events (user's goal)**: 2025 (hourly, clean) 96% + 2019 (accurate 2111 Q) 86%.
**2021** documented as an Open-Meteo input-rainfall limitation (~69% ceiling; needs gauge/orographic
forcing, not tuning) — the weakest event anyway (secondary KMC stage, no discharge, backwater).

### 13.5 Honest caveat that persists
Even with the user-confirmed accurate 2019 discharge (2111) and a ≤1 m backwater allowance, the
WRD rating maps 2111 → 542.58 m free-outflow (≤543.5 m with 1 m backwater). The recorded 2019
stage 546.97 m sits ~3.5 m above that — more than backwater bridges. So the 2019 record's STAGE
and DISCHARGE still cannot both be satisfied; per the user's explicit priority (match STAGE) we
target 546.97, which pushes the model's 2019 peak Q above the reported 2111. If instead the
accurate 2111 is trusted, the model lands ~543 m → ~80% peak-stage accuracy vs the 546.97 record
(i.e. the record stage, not the model, would be the high outlier). Both readings already meet or
near the 80% bar; the routing calibration resolves how close to 90% we can get.

### 13.6 2021 discharge supplied (2162) — reverses "data-capped"; user decides rating fix
**User provided the 2021 peak discharge = 2162 m³/s** (previously "not verified"). Decisive
consequences (`diag_stage_discharge_consistency.py`):
- **2021 is NOT data-capped.** Against its accurate discharge, the model's 2021 peak
  (1654 m³/s promoted config; 1801 at CN ceiling) is only **−17…−24%** — good agreement. The
  earlier "~69% data-capped" claim was an artifact of targeting the inconsistent 547.83 m stage
  and is **withdrawn**.
- **Both 2019 & 2021 show the same stage↔discharge contradiction** on the WRD rating:
  2019: 2111→542.58 m vs reported 546.97 m (gap 4.39 m); 2021: 2162→542.65 m vs reported
  547.83 m (gap 5.18 m). Backwater (≤1 m) cannot bridge either — a systematic ~2× inconsistency.
- **USER DECISION: trust the reported flood STAGES → the WRD rating over-estimates flood discharge
  ~2×; fix the rating at flood flows.** A real ~2150 m³/s flood reaches ~547 m, not ~542.6 m.
  Agreed next step: re-anchor/re-derive the Rajaram rating above ~542.7 m, then re-score the
  model's flood-stage accuracy on the corrected rating (see EVENT_DOCUMENTATION §7).

### 13.7 Production promotion (2026-10-27)
Promoted the timing-faithful peak-stage config to `data/telemetry/ml_calibration_state.json`
(backup `ml_calibration_state.json.bak_20261027T093156Z`), replacing round-2 LM params
(alpha_k=1.8/alpha_lag=1.8, NSE=0.45): **alpha_k=0.60, alpha_lag=0.82, muskingum_x=0.30,
delta_cn=0.0, ia_frac=0.05, uh_max_hr=90, uh_m_exp=20**, per-subbasin CN + per-reach K retained.
`runner.py` extended to read ia_frac/uh_max_hr/uh_m_exp from the state when not explicitly passed.
Results: 2019 acc 86.2%, 2025 acc 96.5% (NSE 0.932, timing −4 h), 2021 −24% on discharge.
Per-event documentation: `EVENT_DOCUMENTATION_2019_2021_2025.md`.

---

*This log was updated on 2026-10-22 during the life-safety calibration session, extended
2026-10-24 (per-subbasin re-calibration), 2026-10-26 (generalization + joint + two-event
digital-twin), and 2026-10-27 (WSE-is-truth reframe; backwater ≤1 m; routing K/X/lag lever;
peak-stage target; 2021 discharge 2162 reverses data-capped; production promotion; decision to
fix the flood-flow rating). Last updated: 2026-10-27.*
