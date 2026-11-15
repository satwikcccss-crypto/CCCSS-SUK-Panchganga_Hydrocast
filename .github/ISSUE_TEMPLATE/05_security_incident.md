---
name: 🔒 Security Advisory & Incident
about: Report a security anomaly, access control breach, or operational vulnerability
title: "[Security]: <Component or Vector Affected>"
labels: ["security", "needs-triage"]
assignees: []
---

<!-- ======================================================================= -->
<!-- HYDROCAST RESPONSIBLE DISCLOSURE & SECURITY ADVISORY                    -->
<!-- IMPORTANT: If this is an actively exploitable vulnerability, please DO   -->
<!-- NOT file a public issue. Email: satwikcccss@gmail.com directly.         -->
<!-- ======================================================================= -->

> [!WARNING]
> **Responsible Disclosure Policy:**  
> If this issue exposes live database credentials, JWT keys, or active remote code execution vectors, **do not post sensitive details publicly**. Email the Lead Developer directly at **`satwikcccss@gmail.com`** or consult [SECURITY.md](../../SECURITY.md).

---

## 🛡️ Vulnerability Category

<!-- Select applicable category -->
- [ ] **Role-Based Access Control (RBAC):** Official viewer bypassing operator restriction
- [ ] **Authentication / JWT:** Token validation flaw, spoofing, or expiration bypass
- [ ] **API Security:** Injection, unauthenticated WebSocket handshake, or rate-limit evasion
- [ ] **Data Integrity:** Unauthorized manipulation of hydrological forecast records
- [ ] **Secret Exposure:** Accidental inclusion of sensitive keys in logs or client bundles
- [ ] **Network & Reverse Proxy:** Caddy proxy, TLS misconfiguration, or port leakage

---

## 📍 Affected Endpoint or Module
- **File / Route:** (e.g. `/ws/admin/telemetry`, `backend/api/admin_routes/`, Next.js proxy)
- **Deployment Edition:** Windows Server On-Premises

---

## 🔍 Vulnerability Summary
<!-- Clear description of the vulnerability without disclosing active live attack vectors -->


---

## 🛠️ Proposed Remediation & Hardening Steps
<!-- Suggest defensive patches, role gates, or configuration adjustments -->
