# HydroCast — Complete Server Setup Instructions (for automated agent)

**Release:** `windows-v2.0.0` (target: `windows-server-production` tag)  
**Package:** `Hydrocast-src-windows-v2.0.0-with-env.zip`  
**Primary goal:** install and run the HydroCast application stack on this Windows Server from the provided package, with no missed prerequisites or steps.

> **Hard constraints (must follow):**
> - **Database is on another system and is ON HOLD.** Do **not** run migrations (`-Migrate`), do **not** try to “fix” DB connectivity, and do **not** change DB-related values. The lead developer will configure the database later.
> - **Do not change secrets/credentials now.** `.env` and frontend `.env.local` files are included as provided; leave them as-is (secrets will be rotated/changed later). **Never print, log, or exfiltrate env file contents.**
> - Use **`-SkipHealthCheck`** during this setup because full health may depend on the database handover. Services/builds/dependencies must still be installed and registered.
> - Run commands from the **extracted install folder**. The location is portable (any drive, including inside `Documents`) — do **not** assume `E:\`.

---

## 1) Mission checklist (definition of done for this phase)

Complete every applicable item and report status for each:

- [ ] Package extracted to the chosen `<INSTALL_PATH>` (correct structure, not nested)
- [ ] Prerequisites verified (or installed where possible): Windows admin, Python 3.12, Node 20+, internet, disk space, permissions
- [ ] Port/service conflicts checked (8000/3000/3001 and `Hydrocast-*` services) and resolved/reported
- [ ] `windows\deploy_release.ps1 -SkipHealthCheck` executed successfully (or `-SkipFrontend -SkipHealthCheck` if Node unavailable, with note)
- [ ] `.venv` created and backend dependencies installed
- [ ] Frontend builds produced (`frontend-public\.next`, `frontend-admin\.next`) when Node available
- [ ] NSSM services registered (`Hydrocast-Backend`, `Hydrocast-Scheduler`, `Hydrocast-Watchdog`, `Hydrocast-PublicWeb`, `Hydrocast-OperatorConsole`)
- [ ] `data\deployed_revision.txt` recorded
- [ ] Service statuses and any errors/log tails captured and reported (degraded health due to DB-on-hold is expected)
- [ ] Handover items and external/on-hold dependencies clearly reported

---

## 2) What is included in the package (ready to use)

| Included | Details |
|---|---|
| Application source | Full `windows-v2.0.0` codebase (`backend/`, `frontend-public/`, `frontend-admin/`, `scripts/`, `windows/`, `alembic/`, docs, etc.) |
| One-command deploy | `windows\deploy_release.ps1` (pre-flight, `.venv` + `pip install -r requirements.lock`, backend import smoke test, `npm ci && npm run build`, service register/restart, revision record) |
| Service management | `windows\install_services.ps1`, `windows\service_control.ps1` (NSSM-based; auto-downloads NSSM if missing when internet is available) |
| Locked dependencies | `requirements.lock`, `frontend-public\package-lock.json`, `frontend-admin\package-lock.json` (packages downloaded on-server during deploy) |
| Environment files (included as provided) | `.env`, `frontend-public\.env.local`, `frontend-admin\.env.local` **and** `.example` templates |
| Reverse proxy config | `Caddyfile` (included; Caddy installation/runtime is separate) |
| Instructions | `AGENT_SERVER_SETUP.md` (this file) |

**Not included (by design):** `node_modules/`, `.next/`, `.venv/`, wheelhouse/offline package cache, Python/Node installers, PostgreSQL, HEC-HMS, Caddy binary, TLS certificates. These are installed/built on the server or provided by the environment.

---

## 3) Server prerequisites — verify everything (do not skip)

### 3.1 Required on the server now
| Requirement | How to check | Action if missing |
|---|---|---|
| Windows Server with **Administrator** PowerShell | Session is elevated | Re-open PowerShell as Administrator |
| **Python 3.12.x (x64)** on `PATH` | `python --version` | Install Python 3.12 x64 and add to PATH before deploy (deploy will fail without it) |
| **Node.js 20+ LTS** (includes npm) on `PATH` | `node -v` ; `npm -v` | Install Node 20+ LTS for frontend builds. If unavailable now, run deploy with `-SkipFrontend` and report frontends pending |
| **Internet access** (first run) | Can reach package registries | Required for `pip install -r requirements.lock` and `npm ci` (and NSSM auto-download if needed). If offline, report blocker — no offline bundle is included |
| **Disk space** | Sufficient free space on install drive | Need room for `.venv`, `node_modules`, `.next` builds, logs, and runtime data |
| **Write/execute permissions** | Can write under `<INSTALL_PATH>` and create services | Run as Administrator; ensure path is not read-only/restricted |

### 3.2 Ports and service-name conflicts (must check before deploy)
| Resource | Used by HydroCast | Check | Action |
|---|---|---|---|
| TCP **8000** | Backend API | `Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue` | If in use by another system, stop/conflict-resolve or **stop and ask** before deploying |
| TCP **3000** | Public frontend | `Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue` | Same |
| TCP **3001** | Admin frontend | `Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue` | Same |
| Windows services `HydroCast-Backend`, `HydroCast-Scheduler`, `HydroCast-Watchdog`, `HydroCast-PublicWeb`, `HydroCast-OperatorConsole` | App services | `Get-Service HydroCast-* -ErrorAction SilentlyContinue` | Deploy will stop/re-register/replace these names. If another system depends on them, **stop and ask**. If side-by-side coexistence is required (different ports/service names), **stop and ask** for alternate config before deploying |

### 3.3 External systems / environment dependencies (not installed by this package)

| Dependency | Status for this phase | Agent action |
|---|---|---|
| **PostgreSQL 16 + PostGIS** (on another system) | **ON HOLD** | Do **not** migrate or troubleshoot DB. `.env` contains DB settings but lead dev will finalize connectivity later. Expect DB-related degradation until handover |
| **HEC-HMS 4.13** (`C:\Program Files\HEC\HEC-HMS-4.13\HEC-HMS.exe` or `HEC_HMS_PATH` in `.env`) | Environment-specific / optional | Do not install/change now unless explicitly available; report if missing. Runtime behavior depends on env (emulator fallback may apply) |
| **Caddy / reverse proxy & TLS** | Not automated | `Caddyfile` is included, but Caddy binary/service, certificates, and domain binding must be installed/configured separately if public HTTPS is required |
| **DNS, firewall, inbound/outbound rules** | Environment-specific | Ensure required ports/hosts can be reached as per deployment; do not change network policy without instruction |
| **Third-party integrations** (ThingSpeak, Telegram, SMTP, etc.) | Config present, not validated | Values are in `.env`; reachability/validity is environment-specific. Do not modify now; report as pending validation at handover |

---

## 4) Install location (portable)

1. Choose `<INSTALL_PATH>` on any drive/folder (spaces allowed), e.g. `C:\Users\<user>\Documents\Hydrocast Windows Server` or `D:\Hydrocast Windows Server`.
2. Extract the zip so `<INSTALL_PATH>` **directly** contains: `backend\`, `frontend-public\`, `frontend-admin\`, `windows\`, `requirements.lock`, `.env`, `AGENT_SERVER_SETUP.md`.
3. **Do not** nest (avoid `<INSTALL_PATH>\Hydrocast...\Hydrocast...`). **Do not** copy `node_modules/` or `.next/` from another machine.
4. Ensure `.env`, `frontend-public\.env.local`, `frontend-admin\.env.local` are present (they are included). **Leave them unchanged.** Only adjust if the install cannot run due to a path issue specific to this machine — and report any such adjustment.

---

## 5) Execute setup (one command)

Open **PowerShell as Administrator**:

```powershell
cd "<INSTALL_PATH>"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Primary (DB on hold: no -Migrate, skip health checks)
.\windows\deploy_release.ps1 -SkipHealthCheck
```

**What it does:** pre-flight checks → creates `.venv` and installs `requirements.lock` → backend import smoke test → `npm ci` + `npm run build` for both frontends → (re)registers and restarts NSSM services → writes `data\deployed_revision.txt`.

**Fallbacks (only if necessary):**
- Node/npm not available now: `.\windows\deploy_release.ps1 -SkipFrontend -SkipHealthCheck` (frontends pending until built).
- Do **not** use `-Migrate` during this phase.

**Notes:** First run may take time downloading/installing dependencies. NSSM may be auto-downloaded if missing. Re-running the script is idempotent/safe.

---

## 6) Verify and collect evidence

Run and record results:

```powershell
cd "<INSTALL_PATH>"

# Environment/build artifacts
python --version
node -v
npm -v
Test-Path .\.venv\Scripts\python.exe
Test-Path .\frontend-public\.next
Test-Path .\frontend-admin\.next

# Services and revision
Get-Service HydroCast-* | Format-Table Name, Status, StartType
Get-Content .\data\deployed_revision.txt

# Ports (if relevant)
Get-NetTCPConnection -LocalPort 8000,3000,3001 -State Listen -ErrorAction SilentlyContinue | Format-Table LocalPort,OwningProcess,State
```

If a service is stopped/unhealthy, capture logs (degraded state due to DB-on-hold can be expected):
```powershell
Get-Content .\data\logs\service_HydroCast-Backend_err.log -Tail 80
Get-Content .\data\logs\service_HydroCast-Backend.log -Tail 80
Get-Content .\data\logs\service_HydroCast-PublicWeb_err.log -Tail 80
Get-Content .\data\logs\service_HydroCast-OperatorConsole_err.log -Tail 80
```

---

## 7) Handover (lead developer, later — not the agent’s job now)

- Finalize DB connectivity/credentials in `.env` (and any related settings) once the other system is ready; then run `.\windows\deploy_release.ps1 -Migrate` (or `.\.venv\Scripts\python -m alembic upgrade head`) and restart services: `.\windows\service_control.ps1 -Action restart` (or re-run deploy).
- Rotate/change secrets as planned. If `NEXT_PUBLIC_*` values change, rebuild frontends (`npm run build` in each frontend or re-run deploy).
- Install/configure HEC-HMS, Caddy/TLS, DNS, firewall, and validate third-party integrations as required by the environment.

---

## 8) Final report format (agent must provide)

Report clearly:
1. **Install path** used and confirmation of correct extraction
2. **Prerequisites:** Python/Node/npm versions, admin/internet/disk status, any missing items
3. **Conflicts:** ports/services checked and outcome
4. **Actions taken:** exact deploy command(s) run and result (success/failure)
5. **Artifacts:** `.venv`, `.next` presence, `data\deployed_revision.txt` value
6. **Services:** name/status/start type for all `HydroCast-*`
7. **Issues:** errors, log tails, and what is **expected due to DB-on-hold** vs actual blockers
8. **Pending/on-hold/environment items:** DB migration/connectivity, HEC-HMS, Caddy/TLS/DNS/firewall, integration validation
9. **Confirmation:** env files were not modified and no secrets were exposed
