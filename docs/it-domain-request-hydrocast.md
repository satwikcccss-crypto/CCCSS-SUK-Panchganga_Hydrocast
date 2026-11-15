# IT Request: Domain/Subdomain Provisioning & Reverse Proxy Setup (HydroCast)

**Project:** HydroCast — Panchganga River Flood Monitoring & Forecasting System  
**Institution:** CCCSS, Shivaji University, Kolhapur  
**Deployment:** Windows Server (on-premises), internal services on localhost (not publicly exposed)  
**Document purpose:** Ready-to-send request for IT Director/team to issue domains and configure reverse proxy/DNS (and TLS if feasible)

---

## 1) Email draft (copy/paste)

**Subject:** Request for Domain/Subdomain Provisioning and Reverse Proxy Configuration — HydroCast (Panchganga Flood Monitoring & Forecasting System)

Dear [IT Director’s Name / Sir/Madam],

I am writing to request the provisioning of domain/subdomain entries and the required reverse proxy (and SSL, if feasible) configuration for **HydroCast**, the Panchganga River flood monitoring and forecasting system developed/deployed under **CCCSS, Shivaji University, Kolhapur**. The application is ready for deployment on the university Windows server; to make it accessible to authorized users, we require public URLs mapped securely to internal services (without exposing application ports directly to the internet).

### 1) Requested URLs (to be issued/provisioned)
| Purpose | Requested URL | Intended users/access |
|---|---|---|
| **Public Portal (Dashboard & Public Information)** | `http://Hydrocast.unishivaji.ac.in` | Public / general users |
| **Public API (Base URL)** | `http://Hydrocast.unishivaji.ac.in/api/v1` | Public portal & authorized integrations |
| **Operator Console (Admin Interface)** | `http://Hydrocast-admin.unishivaji.ac.in` | Authorized operators only (**restricted access recommended**) |
| **Admin API (Base URL)** | `http://Hydrocast-admin.unishivaji.ac.in/api/v1` | Operator console / authorized admin operations (**restricted access recommended**) |

*Note:* Application endpoints are served under the path **`/api/v1`** (lowercase). Kindly configure routing/proxying accordingly (or add a rewrite if `/API/V1` must also be supported).

### 2) Internal service mapping (server-local only; not to be exposed publicly)
The reverse proxy should forward traffic from the above public URLs to the following **localhost/internal** services on the application server:

| Public endpoint | Internal upstream (localhost) | Notes |
|---|---|---|
| `http://Hydrocast.unishivaji.ac.in/` | `http://127.0.0.1:3000` | Public web portal (Next.js) |
| `http://Hydrocast.unishivaji.ac.in/api/v1/*` | `http://127.0.0.1:8000/api/v1/*` | Public backend API (FastAPI) |
| `ws://Hydrocast.unishivaji.ac.in/ws/*` (e.g. `/ws/live`) | `ws://127.0.0.1:8000/ws/*` | **WebSocket upgrade required** (live updates) |
| `http://Hydrocast-admin.unishivaji.ac.in/` | `http://127.0.0.1:3001` | Operator console (Next.js), **restricted** |
| `http://Hydrocast-admin.unishivaji.ac.in/api/v1/*` | `http://127.0.0.1:8001/api/v1/*` | Admin backend API (FastAPI), **restricted** |
| `ws://Hydrocast-admin.unishivaji.ac.in/ws/admin/telemetry` | `ws://127.0.0.1:8001/ws/admin/telemetry` | **WebSocket upgrade required** (if proxied via admin host) |

**Important:** Ports **3000, 3001, 8000, 8001, and 5432 (PostgreSQL)** must **not** be directly exposed to the public internet; only the reverse-proxied public URLs should be accessible.

### 3) Required proxy/DNS configuration details
Kindly arrange the following:
1. **DNS records:** Create/point subdomains `Hydrocast.unishivaji.ac.in` and `Hydrocast-admin.unishivaji.ac.in` to the designated server/reverse proxy as per university policy.
2. **Reverse proxy rules:** Route paths as per the mapping above (preserve request paths/headers as applicable).
3. **WebSocket support:** Enable HTTP upgrade/connection forwarding for `/ws/*` endpoints with appropriate proxy timeouts.
4. **Forwarded headers:** Pass `Host`, `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Forwarded-Host` to upstream services.
5. **Access control (recommended):** Restrict `Hydrocast-admin.unishivaji.ac.in` (and its `/api/v1`/WS paths) to authorized networks/users (e.g., campus/VPN/IP allowlist), in addition to application-level authentication.
6. **HTTPS/SSL (strongly recommended):** If possible, please provision TLS certificates and serve over **`https://`** (with **`wss://`** for WebSockets) and redirect HTTP to HTTPS. This is important for protecting login sessions, administrative actions, and API traffic. If HTTPS cannot be enabled immediately, we can proceed with HTTP as requested, but we recommend enabling HTTPS at the earliest.

### 4) Coordination / next steps
Once the domains and proxy configuration are in place (or if you require any server-side details such as internal IP/hostname, preferred proxy technology, or firewall rules), I will coordinate with your team to perform connectivity testing (portal access, API routing, WebSocket telemetry, and admin console access).

Could you please confirm the feasibility, expected timeline, and any prerequisites or approvals required from our side for issuing these subdomains and completing the configuration?

Thank you for your support.

Sincerely,  
[Your Full Name]  
[Your Designation/Role]  
[Department / CCCSS, Shivaji University, Kolhapur]  
[Phone Number] | [Email Address]  
[Project: HydroCast — Panchganga Flood Monitoring & Forecasting System]

---

## 2) Technical checklist for IT / implementation team

- [ ] **DNS:** `Hydrocast.unishivaji.ac.in` and `Hydrocast-admin.unishivaji.ac.in` created and resolvable
- [ ] **TLS (recommended):** certificates installed for both subdomains; HTTP→HTTPS redirect; WS upgraded to `wss://`
- [ ] **Reverse proxy:** path-based routing to localhost upstreams as specified
- [ ] **WebSockets:** upgrade headers forwarded; read/write/idle timeouts configured
- [ ] **Headers:** `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host`, `Host` forwarded
- [ ] **Firewall:** public access limited to 80/443 (or 443 only); internal app ports not exposed
- [ ] **Access restriction:** admin host/API/WS limited to authorized networks/users (VPN/IP allowlist) where possible
- [ ] **Path compatibility:** `/api/v1` supported (and optional `/API/V1` rewrite if required)

## 3) Post-provisioning smoke tests (application team)

- [ ] Public portal loads at public URL (assets, navigation, dashboard data)
- [ ] Public API reachable: `/api/v1/health`, `/api/v1/dashboard`, `/api/v1/runoff/summary`, `/api/v1/alerts/bulletin.pdf`
- [ ] WebSocket live updates connect (`ws://` or `wss://` as configured)
- [ ] Operator console login and admin actions work (restricted access path)
- [ ] Conditional requests (ETag/304) and PDF responses behave correctly through proxy
- [ ] Rate limiting and client IPs behave correctly (forwarded headers trusted appropriately)

## 4) Current local pre-configuration status (repo)

- Local gitignored env files have been pre-configured for the above target URLs (not committed/pushed).
- Domains are **not yet issued** at the time of this request; final activation requires DNS/proxy/TLS provisioning by IT.
- If HTTPS is enabled, application/browser-facing URLs and WebSocket schemes must be updated to `https://` / `wss://` and frontends rebuilt with updated public env vars.
