# HydroCast Panchganga — System Verification & Operational Architecture Guide
**Centre for Climate Change and Sustainability Studies (CCCSS), Shivaji University, Kolhapur**  
**Funding Agency:** Science and Engineering Research Board (DST-SERB), Govt. of India  
**Last Updated:** November 2026 | **Version:** 2.0.0 Production Windows Server Edition

---

## ⚠️ Mandatory Institutional & Academic Research Framing

> [!IMPORTANT]
> **HydroCast is strictly an academic, scientific research and predictive simulation system** developed by researchers at Shivaji University Kolhapur (CCCSS) under DST-SERB sponsorship.
> 
> - HydroCast **does NOT publish or issue official civil flood alerts or evacuation orders**.
> - HydroCast does not claim official operational collaboration or joint authority with the Kolhapur District Disaster Management Authority (DDMA), Kolhapur Municipal Corporation (KMC), or Central Water Commission (CWC).
> - All outputs, Telegram bot feeds (`@Hydrocast_SUK_bot`), and APIs are research telemetry for scientific evaluation.
> - **Mandatory Public Disclaimer:**  
>   *"Academic & Scientific Research Simulation by CCCSS, Shivaji University Kolhapur. For official flood warnings, evacuation notices, and civil alerts, consult District Administration / DDMA."*  
>   *(मराठी: "शिवाजी विद्यापीठ कोल्हापूर (CCCSS) व DST-SERB अंतर्गत केवळ शैक्षणिक व वैज्ञानिक संशोधनात्मक अभ्यास. अधिकृत पूर सूचना व आपत्कालीन मार्गदर्शक सूचनांसाठी जिल्हा प्रशासनाशी संपर्क साधावा.")*

---

## 1. System Architecture & Topology

HydroCast operates on a 4-tier autonomous architecture on Windows Server:

| Component | Port | Technology | Process / Command |
| :--- | :--- | :--- | :--- |
| **PostgreSQL 16 + PostGIS** | `5432` | Relational & Geo DB | `E:\PostgreSQL\16\bin\postgres.exe` (DB: `rainfall_runoff`) |
| **FastAPI Operational Hub** | `8000` | Python 3.12 / Async | `python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000` |
| **Citizen Public Portal** | `3000` | Next.js 14 / React 18 | `node node_modules/next/dist/bin/next start -p 3000` |
| **Operator Control Room** | `3001` | Next.js 14 / React 18 | `node node_modules/next/dist/bin/next start -p 3001` |

---

## 2. Seasonal Hydrological Flow Specifications (9.1 vs 91 m³/s)

A historical discrepancy previously existed where post-monsoon baseflow was mistakenly displayed as monsoon runoff (91.10 m³/s) due to stale database benchmark caches. This has been resolved and synchronized across all system tiers:

### 2.1 Post-Monsoon Season (November through May)
- **Baseflow Discharge:** Exactly **`9.10 m³/s`** (derived from surveyed WRD rating tables and baseflow regression).
- **Shivaji Bridge Stage:** **`531.54 m MSL`** (Safe / Normal; below Alert level 542.10m).
- **Rajaram K.T. Weir Stage:** **`532.19 m MSL`** (Safe / Normal; below Solid Crest 535.77m).
- **IoT Ultrasonic Sensor (Shivaji Bridge):** Physically unpowered during non-monsoon months by university design.
  - Telemetry validator marks status as `SEASONAL_STANDBY` (`"Seasonal Dormant (Active June–October)"`).
  - Error metrics (NSE, RMSE, Spearman rho) are set to clean JSON `null` (zero NaN/division-by-zero crashes).
  - Admin and public interfaces show: `📡 IoT Sensor: Seasonal Standby (Operates June–Oct) · Calibrated Hydrodynamic Baseline Active`.

### 2.2 Monsoon Season (June through October)
- **Discharge Range:** `90 m³/s` to `3,500+ m³/s`.
- **Warning Thresholds:**
  - Alert Stage: `542.10 m` (Shivaji) / `541.50 m` (Rajaram)
  - Warning Stage: `542.70 m` (Shivaji) / `542.07 m` (Rajaram)
  - Danger Stage: `543.30 m` (Shivaji & Rajaram)
  - 2019/2021 High Flood Level (HFL): `545.33 m`
- **Manning Open-Channel Extrapolation Beyond HFL:**
  - If simulated discharges exceed surveyed rating curve maximums (`4,183.5 m³/s`), the system **never flatlines, caps, or produces NaN**.
  - It applies Manning's open-channel hydraulic power-law:
    $$h = h_{\text{bed}} + \Delta h_{\max} \cdot \left(\frac{Q}{q_{\max}}\right)^{1 / \beta}$$
    where $\beta \approx 1.67$ (wide-channel Manning exponent), continuing monotonic and physically sound flood stage predictions up to extreme super-floods (550m+ MSL).

---

## 3. Database Administration & Audit Logging

### 3.1 Audit Log Schema (`admin_audit_log`)
Every administrative action triggered in the Operator Console (`:3001`) writes an immutable record to PostgreSQL:

```sql
CREATE TABLE IF NOT EXISTS admin_audit_log (
    audit_id SERIAL PRIMARY KEY,
    action VARCHAR(64) NOT NULL,
    performed_by VARCHAR(128) NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(64),
    status VARCHAR(32) DEFAULT 'SUCCESS',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.2 Flat Access Across All 5 Administrative Accounts
All five institutional accounts have full operator rights for all actions (Force Run, DB Test, DB Backup, Threshold Save, Alert Dispatch):
1. `DEV.Satwikcccss@Adm1`
2. `PI.Panhalkarsachin@Adm1`
3. `COPI.Nivhekarganesh@Adm1`
4. `JRF.PawarNikhil@Adm1`
5. `Dev.Arunbaby@Adm1`

### 3.3 Database Backup Engine
When **DB Backup** is triggered:
1. Executes `pg_dump.exe -F c` into:
   `E:\Hydrocast Windows Server\data\backups\db_backup_YYYYMMDD_HHMM.dump`
2. Writes an entry to `admin_audit_log` with absolute file path and byte size.
3. Frontend immediately reports:
   `"Backup created: db_backup_...dump (X.X MB) saved to E:\Hydrocast Windows Server\data\backups"`

---

## 4. Autonomous Windows Watchdog Service

File: `windows/watchdog_service.ps1`  
Installer: `windows/install_nssm_services.bat`

- **Execution:** Runs continuously every 30 seconds as a background supervisory process.
- **Monitored Ports:**
  - `5432`: PostgreSQL
  - `8000`: FastAPI Backend
  - `3000`: Public Portal
  - `3001`: Operator Mission Control Console
- **Self-Healing:** If any port fails TCP connection check, the watchdog automatically issues a service restart / process relaunch command and logs the event in `data/logs/watchdog_service.log`.

**Manual Health Verification:**
```powershell
powershell -ExecutionPolicy Bypass -File .\windows\watchdog_service.ps1 -Once
```

---

## 5. Playwright E2E & Concurrency Test Verification

### 5.1 Playwright E2E Suite (`tests/playwright/`)
Due to drive C: having limited free storage (0.11 GB), Playwright browsers are installed on drive E: (76.7 GB free) via `PLAYWRIGHT_BROWSERS_PATH`.

**Run Command:**
```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = "E:\ms-playwright"
cd tests\playwright
npx playwright test
```

**Test Coverage (10/10 Tests Passed):**
1. `admin_console.spec.ts`:
   - Admin console login & dashboard initialization.
   - "DB Test" button execution & audit log confirmation.
   - "DB Backup" button execution (`pg_dump`) & file path confirmation.
2. `api_consistency.spec.ts`:
   - Full data sync between `/api/v1/dashboard` and `/api/SUK_hydrocast_v1` (9.10 m³/s).
   - Verification of `/api/v1/research/hydrological-summary` academic disclaimer.
   - PWA Web App manifest verification.
3. `public_dashboard.spec.ts`:
   - 100% Light Mode validation (slate-50 background).
   - Post-monsoon normal flow (9.10 m³/s) and strict zero-NaN validation.
   - Interactive Marathi | English language toggle.
   - Open Data panel and 90-hour Forecast CSV download.

**Artifacts Generated:**
- Screenshots: `tests/playwright/results/screenshots/`
  - `admin_console.png`
  - `admin_backup_success.png`
  - `public_dashboard_en.png`
  - `public_dashboard_mr.png`
- HTML Report: `tests/playwright/results/html-report/index.html`

### 5.2 Flood Concurrency Stress Test (`tests/flood_concurrency_test.py`)
Simulates distributed concurrent citizen and agency query traffic against `/api/SUK_hydrocast_v1` and `/api/v1/dashboard`.

**Run Command:**
```powershell
python -m unittest tests.flood_concurrency_test
```
- **Concurrency Result:** 12/12 concurrent requests completed in **61.14ms average** (P50: 63.62ms), safely below the 100ms threshold.
- **Rate Limiting:** Enforces HTTP 429 Too Many Requests with standard `Retry-After: 60` header when query quota is exceeded.

---

## 6. Standard Operating Procedures (SOPs)

### SOP-01: System Cold Startup
1. Start PostgreSQL: Ensure Windows service `postgresql-x64-16` is running on port 5432.
2. Launch Watchdog: Run `windows/watchdog_service.ps1`, which automatically verifies and spawns ports 8000, 3000, and 3001.
3. Verify Endpoints:
   - Public: `http://localhost:3000/dashboard`
   - Admin: `http://localhost:3001/admin`
   - API Docs: `http://localhost:8000/docs`

### SOP-02: Triggering Manual Forecast Cycle
1. Navigate to Operator Console (`http://localhost:3001/admin`).
2. Click **Force Forecast Run**.
3. Live pipeline status streams step-by-step progress.
4. On completion, WebSocket broadcasts `NEW_CYCLE_READY` event, instantly refreshing both public and admin dashboards without page reload.
