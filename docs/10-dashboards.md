# 10 — Dashboards

## Scope

This document describes the two web dashboards: the public citizen-facing dashboard and the admin operator console. Audience: **Operator**.

## Public Dashboard (Port 3000)

The public dashboard at `frontend-public/` is a Next.js 15 application providing real-time flood information to citizens, government officials, and media.

### Navigation Panels

| Panel | Description |
|-------|-------------|
| Executive Dashboard | System status, latest forecast summary, alert level, peak discharge, bridge stages |
| River Stages & Hydrograph | 90-hour discharge and stage forecast charts with live IoT overlay |
| Cross Section View | Bridge cross-section visualization with current water level |
| Rainfall & Rain Gauges | ECMWF rainfall forecast distribution across 9 subbasins |
| Open Data & Alerts | Active CWC alert classifications, Data Sharing panel, Telegram bot integration |
| Project Information | About page with Shivaji University logo and acknowledgements |

### Live Data Features

- **SWR polling**: Dashboard data refreshes every 30-60 seconds
- **WebSocket**: Live push updates when new forecast cycle completes
- **Alert classification**: Colour-coded NORMAL/ALERT/WARNING/DANGER/EXTREME bands
- **Visitor counter**: Tracks daily and cumulative dashboard visits

### Data Sharing Panel

The public dashboard includes a Data Sharing panel for data access:
- Links to public API endpoints
- Python client SDK (`backend/client/suk_client.py`) download
- Telegram bot integration for alert notifications

### Security Features

- Content Security Policy (CSP) headers
- Anti-copy protection (select-none, right-click prevention)
- robots.txt allows indexing of `/dashboard` only
- PWA support with offline fallback page

---

## Admin Console (Port 3001)

The admin console at `frontend-admin/` is a Next.js 15 application styled after the Windows 11 Settings interface, providing full operational control.

### Category Groups and Panels

#### System & Basin

| Category | Description | Operator Only |
|----------|-------------|:------------:|
| Overview | Executive dashboard with live bridge stages, peak discharge, alert status | No |
| Gauge Stations | Rain gauge network status and selection log | No |

#### River & Hydrology

| Category | Description | Operator Only |
|----------|-------------|:------------:|
| Routing Parameters | Muskingum-Cunge reach configuration | No |
| Governing Station | Dynamic precipitation weighting and station selection | No |

#### Meteorology & Ingestion

| Category | Description | Operator Only |
|----------|-------------|:------------:|
| Ingestion Pipeline | ECMWF forecast download status and failsafe tier | No |
| Cross-Section | Bridge geometry and rating curve anchor points | No |
| Hydrograph | 90-hr discharge and stage forecast visualization | No |
| Rainfall | Subbasin rainfall distribution and areal computation | No |
| Basin Map | Interactive catchment GIS contours and station network | No |

#### Intelligence & Audit

| Category | Description | Operator Only |
|----------|-------------|:------------:|
| ML Recalibration | Physics-informed Levenberg-Marquardt optimization parameters | Yes |
| Run Ledger & Accuracy | Spearman rank correlation, NSE, RMSE and historical runs | No |

#### Windows Host & DB

| Category | Description | Operator Only |
|----------|-------------|:------------:|
| Pipeline & Diagnostics | 12-stage automation workflow, live runtime logs, SLA status | Yes |
| Database & Host Health | PostgreSQL 16 tablespace, hardware meters, DST-SERB info | Yes |

### RBAC Enforcement

- Categories marked "Operator Only" are hidden from `govt` (viewer) role accounts
- Action buttons (Force Forecast, DB Test, DB Backup, Message Dispatch) show only for `dev`/`admin` roles
- Read-only badge shown for viewer accounts

### Authentication Flow

1. User navigates to `/login`
2. Enters username and password
3. POST to `/api/v1/admin/auth/token` (Admin API on port 8001)
4. JWT stored in browser session (httpOnly cookie or localStorage)
5. AuthGate component validates token on every protected route
6. `/login`, `/login/forgot`, `/login/reset` are exempt from auth gate

### Password Reset Flow

1. User clicks "Forgot password?" on login page
2. `/login/forgot` — instruction page: contact admin for reset code
3. Admin generates 6-digit code via console or API
4. Admin shares code out-of-band (WhatsApp, phone, in-person)
5. User enters code on `/login/reset` page with new password
6. Code expires after 1 hour; single-use

---

## PWA Support

Both dashboards are Progressive Web Apps:

| Feature | Public | Admin |
|---------|--------|-------|
| manifest.json | Yes | Yes |
| Service worker | Yes | Yes |
| Offline fallback | Yes | Yes |
| Install prompt | Yes | Yes |
| Apple touch icon | Yes | Yes |

## Source Files

### Public Dashboard

| File | Purpose |
|------|---------|
| `frontend-public/app/dashboard/page.tsx` | Main dashboard with 6 navigation panels |
| `frontend-public/components/DataSharingPanel.tsx` | Data access and Telegram integration |
| `frontend-public/components/ProjectInfoPanel.tsx` | About page with acknowledgements |
| `frontend-public/next.config.js` | CSP headers and security configuration |
| `frontend-public/public/manifest.json` | PWA manifest |
| `frontend-public/public/sw.js` | Service worker |

### Admin Console

| File | Purpose |
|------|---------|
| `frontend-admin/components/WindowsSettingsConsole.tsx` | Main console with category navigation |
| `frontend-admin/app/login/page.tsx` | Login page |
| `frontend-admin/app/login/forgot/page.tsx` | Forgot password instructions |
| `frontend-admin/app/login/reset/page.tsx` | Reset password form |
| `frontend-admin/components/AuthGate.tsx` | Auth guard for protected routes |
| `frontend-admin/lib/auth.ts` | JWT session management and role helpers |
| `frontend-admin/next.config.js` | CSP headers and security configuration |
