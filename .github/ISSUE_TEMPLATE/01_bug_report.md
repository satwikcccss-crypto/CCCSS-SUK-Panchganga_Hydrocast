---
name: 🐛 Bug Report
about: Create a report to help us identify, reproduce, and fix an anomaly in HydroCast
title: "[Bug]: <Concise description of the anomaly>"
labels: ["bug", "needs-triage"]
assignees: []
---

<!-- ======================================================================= -->
<!-- HYDROCAST DEFECT & BUG REPORT TEMPLATE                                 -->
<!-- Standards: ISO/IEC/IEEE 29119-3 & Shivaji University CCCSS Benchmark    -->
<!-- ======================================================================= -->

## 📌 Problem Description
<!-- Clear and concise description of what the bug is. -->


---

## 🧩 Affected Component
<!-- Select the component(s) affected by marking [x] -->
- [ ] **IoT Telemetry & Sensors** (`backend/thingspeak/`, units, datums, GSM signal)
- [ ] **Hydrological Engine & Model** (HEC-HMS, HEC-DSS, rating curves, baseflow derivation)
- [ ] **FastAPI Core & APIs** (`backend/api/`, routing, ETag, PDF bulletin generation)
- [ ] **Public Portal** (`frontend-public/`, dashboards, gauge visualization, maps)
- [ ] **Operator Console** (`frontend-admin/`, RBAC, system dispatch, telemetry panel)
- [ ] **Database & Migrations** (`PostgreSQL 16`, PostGIS, Alembic migrations)
- [ ] **Windows Services & Deployment** (NSSM daemons, Watchdog, Caddy reverse proxy)

---

## 🔁 Reproduction Steps
<!-- Steps to reproduce the anomaly -->
1. Navigate to / execute: `...`
2. Input parameters / configuration: `...`
3. Trigger action: `...`
4. Observe unexpected error or anomaly.

---

## 🔍 Expected vs. Actual Behavior

### Expected Behavior
<!-- What should have happened according to hydrological or system specification? -->


### Actual Behavior
<!-- What actually occurred? Include wrong water level, HTTP error code, or process crash. -->


---

## 🌊 Hydrologic & Operational Impact Assessment
<!-- Does this issue affect river water levels, flood alert warnings, or emergency decisions? -->
- **Impact Level:** 🔴 Critical Physics/Safety | 🟠 High Operational | 🟡 Medium Functional | 🟢 Low/Cosmetic
- **Flood Safety Impact:**
  - [ ] No impact on water elevation or flood warning thresholds
  - [ ] Affects stage calculation (m MSL) or discharge ($m^3/s$)
  - [ ] Affects official disaster bulletin or Telegram alert generation

---

## 🖥️ System & Environment Details
<!-- Please provide environment configuration if relevant -->
- **Operating System:** Windows Server 2022 / Windows Server 2025 / Windows 11
- **Service Deployment:** Native NSSM Services / Docker Compose / Standalone
- **Python Version:** `python --version` (e.g. 3.12.7)
- **Node.js Version:** `node --version` (e.g. 20.18.0)
- **Database:** PostgreSQL 16.5 + PostGIS 3.4
- **Software Version:** (e.g. `windows-v1.4.0`)

---

## 📋 Logs, Error Traces & Screenshots
<!-- Paste error logs, traceback, or terminal output below. Redact passwords or secrets. -->
```text
<Paste traceback or log output here>
```

---

## ✅ Pre-Submission Checklist
- [ ] I have verified this is not a duplicate of an existing issue in [ISSUES.md](../../ISSUES.md).
- [ ] I have verified that no private API keys, database passwords, or JWT secrets are included in this report.
- [ ] If this involves sensitive security vulnerabilities, I have reported directly to `satwikcccss@gmail.com` as per [SECURITY.md](../../SECURITY.md).
