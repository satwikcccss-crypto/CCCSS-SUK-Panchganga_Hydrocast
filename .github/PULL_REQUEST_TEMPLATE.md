## 🌊 HydroCast Pull Request Benchmark

<!-- ======================================================================= -->
<!-- HYDROCAST ENGINEERING & SCIENTIFIC CONTRIBUTIONS TEMPLATE               -->
<!-- Standards: Shivaji University CCCSS Flood Intelligence Platform         -->
<!-- ======================================================================= -->

### 📋 Executive Summary
<!-- Provide a clear, concise summary of the rationale, architecture, and behavioral impact of this change -->


---

### 🔗 Related Issues & Tracking
<!-- Link related issues from ISSUES.md or GitHub issue tracker. Use keywords: Closes #XX, Fixes #XX, Resolves #XX -->
- Closes #
- References [ISSUES.md](../ISSUES.md) entry:

---

### 🧩 Scope & Categorization
<!-- Select all applicable change types by marking [x] -->
- [ ] 🐛 **Bug Fix:** Non-breaking defect correction (logic, routing, error recovery)
- [ ] 📡 **IoT Telemetry:** Sensor field mappings, units (feet/meters), or ThingSpeak sync
- [ ] 🌊 **Hydrology & Physics:** Rating curves, Manning survey, baseflow derivation, HEC-HMS
- [ ] ✨ **New Feature:** Non-breaking functionality or architectural extension
- [ ] 🔒 **Security & RBAC:** Auth hardening, JWT claims, role boundary, credential protection
- [ ] 🖥️ **Public Portal (`frontend-public`):** Citizen dashboard, flood maps, RTDAS displays
- [ ] 🛡️ **Operator Console (`frontend-admin`):** SRE controls, dispatch, database health, audit log
- [ ] 🗄️ **Database & Migrations:** PostgreSQL schema change, Alembic migration, PostGIS
- [ ] ⚙️ **Windows Server & Ops:** NSSM daemon, Watchdog service, Caddy reverse proxy, backups
- [ ] 📝 **Documentation:** System architecture, scientific manuals, API guides

---

### 🌊 Hydrologic Safety & Operational Assessment
<!-- Critical: HydroCast governs municipal flood warnings for the Panchganga Basin -->
- **Does this change alter simulated water levels or peak discharge?**
  - [ ] **No:** Strictly operational/UI/infrastructure change.
  - [ ] **Yes:** Hydrological simulation or hydraulic rating equations modified.
    - *Explanation of hydrologic validation:* 
    - *Nash-Sutcliffe Efficiency ($NSE$) / Peak Stage deviation ($cm$):* 

- **Does this change alter sensor datums or physical units?**
  - [ ] **No:** Datums preserved (Shivaji: `549.35 m MSL`, Nitawade: `552.80 m MSL`, Ichalkaranji: `543.71 m MSL`).
  - [ ] **Yes:** Requires explicit WRD GTS survey cross-check.

---

### 🧪 Verification, Testing & Quality Gates

#### 1. Backend Test Suite (`pytest`)
```powershell
# Run backend test suite
pytest tests/ -q --no-header
```
- [ ] **All tests passing:** `... passed, ... skipped, 0 failures`

#### 2. Static Analysis & Linting (`ruff`)
```powershell
# Verify syntax, undefined variables, and imports
ruff check backend tests scripts
```
- [ ] **Ruff clean:** Zero fatal errors (`F821`, `F822`, `F823`)

#### 3. Frontend Production Builds (`Next.js 14`)
```powershell
# Public Portal Verification
cd frontend-public; npm run build; cd ..

# Operator Console Verification
cd frontend-admin; npm run build; cd ..
```
- [ ] `frontend-public` production build passed cleanly (8/8 routes)
- [ ] `frontend-admin` production build passed cleanly (11/11 routes)

---

### 📸 Visual Evidence (Frontend / Dashboard Changes)
<!-- If this PR modifies visual dashboard components, please include screenshots or before/after comparison -->

| Prior Baseline | Proposed Enhancement |
|:---:|:---:|
| _(Attach Screenshot)_ | _(Attach Screenshot)_ |

---

### 🗄️ Database & Environment Impact
- [ ] **Requires Alembic Migration:** New migration added under `alembic/versions/`
- [ ] **Requires Environment Variables:** Documented in `.env.example`
- [ ] **Windows Services Restart Required:** List affected NSSM services (`hydrocast-api`, `hydrocast-admin`, etc.)

---

### ✅ Contributor Quality & Security Checklist
- [ ] **No Committed Secrets:** Verified that `.env`, passwords, JWT secrets, and private keys are NOT committed.
- [ ] **Data Honesty:** No fabricated synthetic mock responses or fake DB health payloads.
- [ ] **RBAC Enforced:** Privileged administrative actions strictly require `role == "admin"`.
- [ ] **Changelog Updated:** Entry added to [CHANGELOG.md](../CHANGELOG.md) under the active release.
- [ ] **Issues Register Updated:** Corresponding entry updated in [ISSUES.md](../ISSUES.md).
- [ ] **Self-Reviewed:** I have conducted an end-to-end self-review of all changed lines.
