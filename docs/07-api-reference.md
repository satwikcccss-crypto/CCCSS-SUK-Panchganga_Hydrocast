# 07 — API Reference

## Scope

This document provides a complete reference for all HTTP and WebSocket endpoints. Audience: **Maintainer**.

## Architecture

The system exposes two independent FastAPI applications:

| API | Port | Purpose | Authentication |
|-----|------|---------|---------------|
| Public API | 8000 | Citizen-facing dashboard data | API key (optional) + rate limiting |
| Admin API | 8001 | Operator console control plane | JWT bearer token (required) |

Both share the same PostgreSQL database.

---

## Public API (Port 8000)

### Health & Probes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Liveness check. Returns `{"status": "ok"}`. No auth required. |
| GET | `/api/v1/status` | System health + current cycle info |

### Visitor Counter

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/visits` | Persisted daily and total visitor counts |

### Hydrology (Rainfall)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/rainfall/ecmwf` | 90-hr ECMWF hyetograph per subbasin |
| GET | `/api/v1/rainfall/stations` | Station selection log for latest cycle |
| GET | `/api/v1/rainfall/gauges` | Raw gauge hyetographs (last cycle) |

### Runoff & Stage

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/runoff/hydrograph` | Outlet discharge hydrograph (90 points) |
| GET | `/api/v1/runoff/summary` | Peak Q, Tp, volume, stage per bridge |
| GET | `/api/v1/runoff/stage/{site_id}` | 90-hr stage forecast at bridge (shivaji/rajaram) |

### Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/integration/hydrosim/stage` | Water-level boundary conditions (JSON/CSV) |

### Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/alerts` | Active CWC alert classifications |
| GET | `/api/v1/alerts/bulletin` | Formatted flood bulletin (PDF-ready JSON) |

### Pipeline

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/pipeline` | Pipeline step status for current cycle |
| GET | `/api/v1/pipeline/history` | Last N cycle durations + status |

### Historical Runs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/runs` | Paginated list of computation runs |
| GET | `/api/v1/runs/{run_id}` | Retrieve computation run details |

### Accuracy

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/accuracy` | Validation metrics (NSE, RMSE, Spearman rho) |

### Sensor Network

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/sensors/live` | All stations live readings (SS, NW, IK) |
| GET | `/api/v1/sensors/{station_id}` | Single station by ID |
| GET | `/api/v1/sensors/registry` | Station metadata without live data |

### WebSocket

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WS | `/ws/live` | Push updates on each new cycle result |

---

## Admin API (Port 8001)

All endpoints require JWT authentication unless noted.

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/admin/auth/token` | None | Exchange credentials for JWT |
| POST | `/api/v1/admin/auth/reset-password` | None | Reset password with admin-issued code |
| GET | `/api/v1/admin/me` | JWT | Current identity and claims |

### User Management (admin role required)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/admin/users` | JWT (dev/admin) | List all users |
| POST | `/api/v1/admin/users` | JWT (admin) | Create new user (domain validated) |
| POST | `/api/v1/admin/users/{username}/generate-reset-code` | JWT (dev/admin) | Generate 6-digit reset code (valid 1 hr) |
| POST | `/api/v1/admin/users/{username}/toggle-active` | JWT (admin) | Activate/deactivate user |

### Operations (dev/admin role required)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/admin/trigger-run` | JWT | Manual pipeline cycle trigger |
| POST | `/api/v1/admin/archive` | JWT | Parquet cold-storage archival |
| POST | `/api/v1/admin/recalibrate` | JWT | Forced ML recalibration |
| POST | `/api/v1/admin/abort` | JWT | Emergency abort current run |
| POST | `/api/v1/admin/pause` | JWT | Pause/resume scheduler |
| POST | `/api/v1/admin/backup-db` | JWT | Manual database backup |
| GET | `/api/v1/admin/health` | JWT | Admin service health |
| GET | `/api/v1/admin/pipeline` | JWT | 12-step matrix with live status |

### WebSocket

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WS | `/ws/admin/logs` | Streaming operator logs |

---

## Authentication Model

### Public API (Port 8000)

| Credential | Grants |
|-----------|--------|
| None | `/api/v1/health` only |
| `X-API-Key` header | All public `/api/v1/*` reads (rate limited) |

### Admin API (Port 8001)

| Credential | Grants |
|-----------|--------|
| JWT bearer (HS256) | Full admin control per role |
| Master `X-API-Key` | Service-to-service automation |

### JWT Token Structure

```json
{
  "sub": "DEV.Satwikcccss@Adm1",
  "role": "admin",
  "exp": 1720000000,
  "iat": 1719913600,
  "iss": "hydrocast-api"
}
```

### Rate Limits

| Scope | Limit | Library |
|-------|-------|---------|
| Public API | 60 requests/minute per IP | slowapi |
| Login endpoint | 5 requests/minute per IP | slowapi |

---

## Response Conventions

- All timestamps are in **UTC** (ISO 8601)
- Discharge is in **m3/s**
- Rainfall is in **mm/hr**
- Stage is in **metres above mean sea level** (WRD datum)
- Rate-limited responses return HTTP 429 with `Retry-After` header

## Source Files

| File | Purpose |
|------|---------|
| `backend/api/main.py` | Public API application (port 8000) |
| `backend/api/admin_app.py` | Admin API application (port 8001) |
| `backend/api/admin.py` | Admin router (shared by both apps) |
| `backend/api/security.py` | JWT creation, verification, password hashing |
| `backend/api/limits.py` | Rate limiter configuration |
| `backend/api/keys.py` | API key verification |
| `backend/api/websocket_hub.py` | WebSocket broadcast hub |
| `backend/api/circuit_breaker.py` | Circuit breaker for external API calls |
