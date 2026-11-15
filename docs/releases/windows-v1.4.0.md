# 📡 windows-v1.4.0 — IoT Sensor Unit Corrections & Telemetry Integrity (Windows Server)

**Tag:** `windows-v1.4.0`  
**Target branch:** `windows-server-production`  
**Release date:** 2026-11-15  
**Edition:** Windows Server (on-premises) — Shivaji University, Kolhapur

> 🌊 Critical IoT telemetry physics correction release resolving unit conversion discrepancies across the multi-station sensor network, surfacing SIM signal telemetry, eliminating pipeline exception halts, harmonizing environment configurations, and aligning runtime metadata across all services.

---

## ✨ Highlights

- 🎯 **Critical Sensor Unit Conversion Fix (Physics Bug):** Corrected unit conversion logic in `backend/thingspeak/multi_station.py`. Shivaji Bridge sends distance in **feet**, while Nitawade (NW) and Ichalkaranji (IK) send distance in **meters**. Inverted stage calculations (which previously computed Nitawade at 4.16 m MSL) now correctly calculate live river stages across all three stations.
- 📶 **SIM Signal Strength Telemetry:** Channel 3424513 `field3` ("SS") surfaced as GSM/SIM signal percentage across backend, public dashboard (`SensorNetworkPanel`), and operator console (`LiveTelemetryPanel`).
- 🔋 **Nitawade Sensor Field Mapping Correction:** Separated precomputed stage (`field2`, ~548.16 m MSL) from sensor battery voltage, preventing physically impossible voltage readouts (548.16 V).
- 🛠️ **Pipeline Exception Safety:** Added missing logger definition to `backend/service/pipeline/steps.py:110`, preventing `NameError` from masking root-cause telemetry anomalies during validation.
- 📧 **Multi-Recipient Disaster Alert Fix:** Updated `backend/alerts/admin_notifier.py` to correctly parse comma-separated administrator email lists without delivery rejection.
- ⚙️ **Telemetry Environment Harmonization:** Reconciled `THINGSPEAK_READ_API_KEY` and `THINGSPEAK_API_KEY` across `thingspeak_gauge.py`, `failsafe_telemetry.py`, and `realtime_telemetry_validator.py`, pinning `field1` extraction to avoid voltage/signal cross-reading.
- 🏷️ **Version Metadata Alignment:** Backend runtime (`main.py`, `admin_app.py`, `observability.py`, `health.py`) and frontends (`frontend-public`, `frontend-admin`) bumped to **`1.4.0`**.

---

## 🌊 Multi-Station IoT Sensor Network Architecture

| Station | Location | Channel ID | Field 1 (Raw) | Field 2 | Field 3 | Sensor Unit | Sensor Datum | Verified Live Stage |
|:---|:---|:---:|:---|:---|:---|:---:|:---:|:---:|
| **Shivaji Bridge** (`SS`) | Kolhapur City | `3424513` | Ultrasonic Distance | Sensor Voltage (V) | SIM Signal Strength (%) | **Feet** | `549.35 m MSL` | **531.63 m MSL** |
| **Nitawade RWLS** (`NW`) | Bhogavati River | `3417870` | Radar Distance | Precomputed Stage (m MSL) | Sensor Altitude (m MSL) | **Meters** | `552.80 m MSL` | **548.16 m MSL** |
| **Ichalkaranji** (`IK`) | Panchganga Downstream | `3417872` | Radar Distance | — | — | **Meters** | `543.71 m MSL` | **527.84 m MSL** |

---

## 📦 Closed Issues in this Release

- [#21](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/21) — `[Bug]: Critical physics bug — incorrect sensor unit conversion for Nitawade and Ichalkaranji`
- [#22](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/22) — `[Bug]: ThingSpeak multi-station telemetry returns NOT_CONFIGURED without .env auto-load`
- [#23](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/23) — `[Bug]: Nitawade sensor voltage misinterprets precomputed stage as 548.16 V`
- [#24](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/24) — `[Feature]: Surface SIM Signal Strength (SS) for Shivaji Bridge IoT station`
- [#25](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/25) — `[Bug]: Critical pipeline crash due to undefined logger in steps.py:110`
- [#26](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/26) — `[Bug]: Lead admin email alert failure on comma-separated recipient lists`
- [#46](https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/issues/46) — `[Telemetry]: Standardize THINGSPEAK_API_KEY vs THINGSPEAK_READ_API_KEY across modules`

---

## ⚠️ Upgrade Notes

- **Deployment:** Restart the API, admin API, and both frontend services after deployment, then run the post-deploy smoke tests.
- **Pending Domain Cutover:** Domain assignment is pending from Shivaji University IT (`hydrocast.unishivaji.ac.in` and `hydrocast-admin.unishivaji.ac.in`).

---

## ✅ Verification & Validation

| Test / Gate | Target | Result | Notes |
|:---|:---|:---:|:---|
| Backend Test Suite | `py -m pytest tests/ -q --no-header` | **325 passed, 3 skipped** | Includes new unit regression tests (`tests/test_thingspeak_units.py`) |
| Ruff Code Quality | `py -m ruff check backend tests scripts` | **Clean (0 errors)** | Full lint passing |
| Frontend Public Portal | `npm run build` (`frontend-public`) | **8/8 routes passed** | Next.js 14 production export clean |
| Frontend Operator Console | `npm run build` (`frontend-admin`) | **11/11 routes passed** | Next.js 14 operator console clean |
| Live IoT Telemetry Fetch | `fetch_all_stations()` | **3/3 returned readings** | All three stations returned valid stage values; freshness status was `STALE` at release check, so confirm sensor uplink before deploy |
