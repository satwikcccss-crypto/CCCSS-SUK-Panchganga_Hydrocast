# Changelog

All notable changes to the **HydroCast** platform are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-11-02 — Production Release: Operations Control & Digital Twin

### 🚀 Highlights & Architectural Milestones
* **Edge & Serverless Presentation Layer:** Deployed Next.js 14 App Router frontend to Vercel with serverless API route proxying, zero mixed-content issues, and automatic edge scaling.
* **Vectorized Digital Twin Simulation Engine:** Introduced pure-Python kinematic wave and Muskingum-Cunge routing (`src/models/vectorized_engine.py`) providing instantaneous, zero-dependency hydrologic modeling alongside official USACE HEC-HMS 4.13 runtime execution.
* **Operator Control Room (`/admin`):** Integrated operational control dashboard with live 12-step pipeline inspection, runtime telemetry metrics, and asynchronous cloud pipeline dispatch via GitHub Actions.
* **Enterprise Dual-Auth Architecture:** 
  * Supabase Google OAuth with strict project allowlist verification (`satwikcccss@gmail.com`, `panhalkarsachin@gmail.com`, `gonioelect@gmail.com`, `nikhilpawar6297@gmail.com`).
  * Bcrypt salted operational passkeys for offline and field operator access (`Dev@Adm1`, `PI@Adm1`, `COPI@Adm1`, `JRF@Adm1`).
* **Live Mechanical Odometer & Telemetry:** Real-time visitor counter with persistent database synchronization (Supabase/PostgreSQL) and fallback ledger preventing stale or zero-count anomalies.

### 🌊 Hydrologic Modeling & Stage Calibration
* **Dynamic Rating Curves:** Re-calibrated Manning's stage-discharge equations for critical Panchganga basin checkpoints (**Chhatrapati Shivaji Maharaj Bridge** and **Rajaram K.T. Weir**), validated against 2005, 2019, and 2021 historical flood records.
* **12-Stage Automated Forecast Pipeline:** Automated 90-hour cyclical rainfall ingestion (Open-Meteo 1km + ECMWF IFS), gridded sub-basin hyetograph mapping, unit hydrograph runoff convolution, and stage alert classification.

### 🛡️ Security, Reliability & Compliance
* **Fail-Closed Security Posture:** Cryptographically salted visitor IP hashing (`VISIT_HASH_SALT`), tight rate limiting on public and auth endpoints (`RATE_LIMIT_LOGIN=5/minute`), and fail-closed secret verification.
* **Multi-Channel Emergency Alerting:** Direct integrations with DDMA Kolhapur, CWC telemetry, and Telegram bot notification channels (`TELEGRAM_ALLOWED_CHAT_IDS`).
* **Zero-Warning Strict Documentation:** 100% compliant MkDocs Material documentation built with `--strict` gating in CI/CD.
* **Comprehensive Test Suite:** 286+ unit, integration, and security tests passing.

---

## [1.0.0] - 2026-05-15 — Baseline Release
* Initial HEC-HMS 4.13 automation via Jython script runner.
* Offline DSS boundary reading and manual runoff hydrograph export.
* Basic FastAPI server with static JSON outputs.
