---
title: FastAPI Service Reference
---

# FastAPI Service Reference

Rendered from the docstrings in `src/api/`. Every route below is also visible in the
live [Swagger UI](../backend.md#3-interactive-api-explorer).

## Interactive diagram consoles

The console below is the rendered reference for this page: it carries the same structure, tier boundaries and failure branches that the prose describes.

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 11</span>
      <strong>Backend API Map</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../../diagrams/11-backend-api.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../../diagrams/11-backend-api.html?embed=1" title="Backend API Map Console"></iframe>
</div>

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 04</span>
      <strong>API Gateway & Auth Sequence</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../../diagrams/04-sequence-auth-api.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../../diagrams/04-sequence-auth-api.html?embed=1" title="API Gateway & Auth Sequence Console"></iframe>
</div>

---

## Request lifecycle

A request passes through four stages before it reaches a route handler: CORS
negotiation, API-key or bearer-token authentication, per-client rate limiting, and
response-model validation. Failures short-circuit at the stage that rejected them,
so an unauthenticated request never consumes the rate-limit budget and a
rate-limited request never touches the database.


---

## `src/api/main.py`

The application object, public data endpoints and the live WebSocket.

::: src.api.main

---

## `src/api/admin.py`

Administrative router mounted at `/api/v1/admin`. Every route except
`/auth/token` requires a valid admin JWT bearer token.


::: src.api.admin

---

## `src/api/notifier.py`

Lightweight push helper used when a cycle completes and the dashboard must
refresh without polling.

::: src.api.notifier
