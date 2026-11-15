---
name: 📡 Sensor & Telemetry Incident
about: Report an RTDAS / IoT river gauge anomaly, telemetry outage, or physical sensor drift
title: "[Telemetry Incident]: <Station Name> - <Nature of Anomaly>"
labels: ["telemetry", "needs-triage"]
assignees: []
---

<!-- ======================================================================= -->
<!-- HYDROCAST RTDAS / IOT TELEMETRY INCIDENT REPORT                        -->
<!-- Standards: WMO-No. 168 (Guide to Hydrological Practices) & WRD Datum   -->
<!-- ======================================================================= -->

## 📍 Station Identification

- **Station Name:** 
  - [ ] Shivaji Bridge (`SS` - Kolhapur City)
  - [ ] Nitawade RWLS (`NW` - Bhogavati River)
  - [ ] Ichalkaranji (`IK` - Downstream Panchganga)
  - [ ] Rajaram Weir (WRD Gauge Reach)
  - [ ] Other / Rain Gauge Station: `...`
- **ThingSpeak Channel ID:** (e.g. `3424513`, `3417870`, `3417872`)
- **Sensor Technology:** Ultrasonic Distance / Microwave Radar / Pressure Transducer / Tipping Bucket

---

## ⚠️ Nature of Telemetry Incident

<!-- Select applicable incident types -->
- [ ] **Physical Unit Discrepancy:** Raw value unit mismatch (feet vs. meters)
- [ ] **Sensor Telemetry Outage:** No new data received for > 2 hours
- [ ] **Physically Impossible Reading:** Negative water level or stage exceeding bridge crest
- [ ] **Battery / Power Anomaly:** Voltage dropping below threshold or misread as stage
- [ ] **GSM / SIM Signal Degradation:** Signal strength dropped to 0% or fluctuating wildly
- [ ] **Sensor Drift / Bio-fouling:** Steady unphysical creep in water surface elevation
- [ ] **WRD Benchmark Deviation:** Discrepancy against physical staff gauge reading

---

## 📊 Telemetry Data Evidence

| Metric | Raw Telemetry Value | Expected Ground Truth | Physical Unit |
|:---|:---:|:---:|:---:|
| **Field 1 (Distance to Water)** | `...` | `...` | Feet / Meters |
| **Field 2 (Secondary Parameter)** | `...` | `...` | Volts / m MSL |
| **Field 3 (Tertiary Parameter)** | `...` | `...` | SIM % / Datum |
| **Computed River Stage** | `...` m MSL | `...` m MSL | m MSL |
| **Timestamp of First Anomaly** | `YYYY-MM-DD HH:MM IST` | — | IST |

---

## 🛟 Fail-Safe & Model Continuity Status

<!-- What action did the pipeline orchestrator take? -->
- **Antecedent Cycle Fallback:** Activated / Failed
- **Seasonal Baseflow Fallback:** Activated / Failed
- **Downstream Hydraulic Impact:** Peak stage overestimation / Underestimation / No drift

---

## 🔧 Action Requested / Field Intervention
<!-- Does this require physical on-site cleaning, battery replacement, SIM recharge, or software recalibration? -->
- [ ] Physical inspection of transducer mounting at bridge girder
- [ ] Solar battery / power management intervention
- [ ] SIM card recharge / APN network reconfiguration
- [ ] Software field-mapping adjustment in `backend/thingspeak/multi_station.py`
- [ ] Sensor elevation datum recalibration
