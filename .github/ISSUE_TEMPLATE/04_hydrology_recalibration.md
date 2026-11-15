---
name: 🌊 Hydrologic Model Recalibration
about: Propose recalibration of river rating curves, cross-section survey data, or HEC-HMS parameters
title: "[Recalibration]: <Basin/Reach/Subbasin> - <Parameter or Rating Shift>"
labels: ["hydrology", "needs-triage"]
assignees: []
---

<!-- ======================================================================= -->
<!-- HYDROCAST HYDROLOGIC CALIBRATION & RATING CURVE RFC                     -->
<!-- Standards: HEC-HMS 4.13 / WRD Maharashtra Hydrographic Survey Protocols -->
<!-- ======================================================================= -->

## 🏞️ Basin & Reach Identification

- **Target Subbasin / Reach:**
  - [ ] Panchganga Main Stem (Shivaji Bridge to Rajaram Weir)
  - [ ] Kasari River Catchment (Subbasin S1-S3)
  - [ ] Kumbhi River Catchment (Subbasin S4-S5)
  - [ ] Tulshi River Catchment (Subbasin S6)
  - [ ] Bhogavati River Catchment (Subbasin S7-S8)
  - [ ] Lower Panchganga to Confluence (Subbasin S9 - Shirol / Narsobawadi)
- **Monitoring Reach / Cross-Section:** Cross-Section #17 (Shivaji) / Cross-Section #29 (Rajaram)

---

## 📐 Nature of Recalibration

<!-- Mark applicable recalibration categories -->
- [ ] **Stage-Discharge Rating Curve Update:** WRD current-metering survey shift
- [ ] **Sensor Datum Adjustment:** Benchmark elevation recalibration (GTS Datum)
- [ ] **SCS-CN Runoff Curve Number:** Land-use change or Antecedent Moisture Condition (AMC) tuning
- [ ] **Clark Unit Hydrograph:** Time of Concentration ($T_c$) or Storage Coefficient ($R$)
- [ ] **Manning's Roughness Coefficient ($n$):** Channel bed or floodplain vegetation shift
- [ ] **Baseflow Parameters:** Recalibration of recession constant or monsoon baseflow floor

---

## 📊 Survey & Calibration Data Comparison

| Parameter | Current Operational Model | Proposed Calibrated Value | Calibration Source / Survey Reference |
|:---|:---:|:---:|:---|
| **Warning Threshold** | `542.10 m MSL` | `... m MSL` | WRD Official / KMC Flood Order |
| **Danger Threshold** | `543.30 m MSL` | `... m MSL` | WRD Official / KMC Flood Order |
| **Sensor Elevation Datum** | `549.35 m MSL` | `... m MSL` | GTS Survey 2024 / Total Station |
| **Manning's Roughness $n$** | `0.035` | `...` | Field Survey / Channel Inspection |
| **Curve Number (AMC-II)** | `...` | `...` | LULC Remote Sensing Analysis |

---

## 🧪 Historical Event Validation Results

<!-- Did you validate this change against historical Panchganga flood events (e.g., 2019 or 2021 floods)? -->
- **Nash-Sutcliffe Efficiency ($NSE$):** `...` (Benchmark $\ge 0.85$)
- **Kling-Gupta Efficiency ($KGE$):** `...` (Benchmark $\ge 0.80$)
- **Peak Discharge Timing Error ($\Delta t$):** `...` hours
- **Peak Stage Deviation ($\Delta h$):** `...` cm

---

## 📑 Supporting Documents & Approvals
<!-- Attach WRD survey reports, cross-section coordinates, or academic peer-reviewed references -->
