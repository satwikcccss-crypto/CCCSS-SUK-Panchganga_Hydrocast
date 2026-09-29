# API Reference

HydroCast exposes two complementary API surfaces. Together they let you go from
"a district officer wants an answer" all the way down to "which NumPy function
computed the number in that answer".

<div class="grid cards" markdown>

-   :material-api: **Interactive REST Explorer**

    ---

    FastAPI's Swagger UI / ReDoc is generated directly from the running
    application. Every route is documented with live JSON schemas and a
    **Try it out** button — no client code required.

    [Launch Swagger UI :octicons-arrow-right-24:](../Backend.md#3-interactive-api-explorer)

-   :material-file-tree: **Python Source Reference**

    ---

    Every module, class and function in `src/` is rendered from its own
    docstring. Write a docstring in the code and it appears here — the
    reference can never drift from the implementation.

    [Browse the modules :octicons-arrow-right-24:](backend.md)

</div>

---

## 1. The two surfaces at a glance

```text
                     ┌──────────────────────────────────────────────┐
                     │            src/  (Python source of truth)    │
                     │                                              │
                     │   docstrings ──────────┐                      │
                     │                        ▼                      │
                     │              ┌─────────────────────┐          │
                     │              │   mkdocstrings      │          │
                     │              │   (build time)      │          │
                     │              └──────────┬──────────┘          │
                     └─────────────────────────┼─────────────────────┘
                                               │
                                               ▼
                     ┌──────────────────────────────────────────────┐
                     │        THIS SECTION (API Reference)          │
                     │  • signature   • parameters   • return type   │
                     │  • docstring   • source link  • call graph    │
                     └──────────────────────────────────────────────┘

                     ┌──────────────────────────────────────────────┐
                     │            src/api/main.py  (FastAPI)        │
                     │                                              │
                     │   route() metadata + type hints ──┐          │
                     │                                    ▼          │
                     │                    ┌───────────────────────┐  │
                     │                    │  /docs  (Swagger UI)  │  │
                     │                    │  /redoc (ReDoc)       │  │
                     │                    │  /openapi.json        │  │
                     │                    └───────────┬───────────┘  │
                     └────────────────────────────────┼──────────────┘
                                                      ▼
        ┌───────────────────────────────────────────────────────────────────┐
        │  Next.js dashboard  ·  Telegram bulletin bot  ·  District officers │
        └───────────────────────────────────────────────────────────────────┘
```

| | REST API | Python Reference |
|:---|:---|:---|
| **Audience** | Integrators, integrators' scripts, Postman users | Hydrologists, maintainers, reviewers |
| **Source of truth** | Type hints + `response_model` on each route | Docstrings in `src/**.py` |
| **Regenerate by** | Restarting the server — automatic | `mkdocs build` — automatic |
| **Can it go stale?** | No — schema is derived from the code | No — content is derived from the code |
| **Where** | `http://<host>:8000/docs` | This section, left-hand nav |

!!! tip "The rule we follow"
    Never hand-write an API description that the code already implies. Route
    schemas come from Pydantic models; reference pages come from docstrings.
    Prose belongs in `docs_src/*.md`, not duplicated into signatures.

---

## 2. Launching the interactive explorer

The Swagger UI is served by the FastAPI application itself — no extra tooling.

=== "Local (development)"

    ```bash
    # From the repository root, with dependencies installed
    pip install -r requirements.txt
    python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
    ```

    Then open:

    | Surface | URL | What you get |
    |:---|:---|:---|
    | **Swagger UI** | [`/docs`](http://localhost:8000/docs) | Interactive explorer with *Try it out* |
    | **ReDoc** | [`/redoc`](http://localhost:8000/redoc) | Three-panel reference, better for reading |
    | **Raw OpenAPI** | [`/openapi.json`](http://localhost:8000/openapi.json) | Machine-readable spec for codegen |

=== "Docker Compose"

    ```bash
    docker compose up -d backend
    docker compose exec backend uvicorn src.api.main:app --host 0.0.0.0 --port 8000
    ```

=== "In CI (generate a static spec)"

    ```bash
    # Emits openapi.json without ever binding a port — used to diff the
    # public contract in pull requests.
    python -c "import json; from src.api.main import app; \
               print(json.dumps(app.openapi(), indent=2))" > openapi.json
    ```

---

## 3. Authenticating in the explorer

Two independent mechanisms protect the API. Set them once under
**Authorize** in the Swagger UI, then every route works.

```text
                    ┌────────────────────────────────────────┐
                    │            request arrives              │
                    └───────────────────┬────────────────────┘
                                        │
                    ┌───────────────────▼────────────────────┐
                    │  /api/v1/**  and  /api/v1/admin/**      │
                    └───────────────────┬────────────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
              ▼                         ▼                         ▼
     ┌──────────────────┐      ┌───────────────────┐     ┌──────────────────┐
     │  REQUIRE_API_KEY │      │  /api/v1/admin/** │     │  /api/v1/health  │
     │     == "true"    │      │   (except /token)│     │  (always public) │
     └────────┬─────────┘      └─────────┬─────────┘     └──────────────────┘
              │                         │
              ▼                         ▼
     ┌──────────────────┐      ┌───────────────────┐
     │  X-API-Key hdr   │      │  Authorization:   │
     │  == API_KEY      │      │  Bearer <JWT>     │
     └────────┬─────────┘      └─────────┬─────────┘
              │                         │
              ▼                         ▼
        ┌───────────┐             ┌───────────┐
        │   401     │             │   401     │
        │  Unauthorized           │  Unauthorized
        └─────────────────────────┴───────────┘

     ALWAYS applied to every route, on top of the above:
       • slowapi per-IP rate limit  (default 100/minute)
       • CORS allow-list            (CORS_ORIGINS, default "*")
       • JWT expiry                 (JWT_EXPIRATION_MINUTES, default 1440)
```

Obtaining a JWT:

```bash
curl -X POST http://localhost:8000/api/v1/admin/auth/token \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"<ADMIN_PASSWORD>"}'
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in_seconds": 86400
}
```

Then reuse it:

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIs..."
curl http://localhost:8000/api/v1/admin/me -H "Authorization: Bearer $TOKEN"
```

!!! warning "Production defaults are deliberately strict"
    `JWT_SECRET` and `API_KEY` have **no** insecure fallback outside of
    `APP_ENV=test|dev` and under pytest. If either is missing in production the
    API starts but every authenticated route rejects the request — it will
    never silently accept traffic with an empty credential. See
    [Security](security.md).

---

## 4. Module map

The reference is grouped by the role each subsystem plays in the forecast.

| Group | Modules | What they do |
|:---|:---|:---|
| **FastAPI Service** | [`src.api.main`](backend.md) · [`src.api.admin`](backend.md#srcapiadminpy) · [`src.api.security`](security.md) · [`src.api.notifier`](backend.md) | HTTP surface, auth, rate limiting, WebSocket push |
| **Hydrology Engine** | [`src.hms.runner`](hms.md) · [`src.hms.basin_parser`](hms.md#srchmsbasin_parserpy) | SCS-CN loss, SCS-UH transform, Muskingum routing, baseflow recession |
| | [`src.hydrology.stage_converter`](hydrology.md) | Manning DCM + WRD-anchored PCHIP rating curves |
| | [`src.hydrology.ml_calibration`](calibration.md) | Levenberg–Marquardt adaptive recalibration |
| **Data Ingestion** | [`src.ecmwf.open_meteo`](ecmwf.md) · [`src.ecmwf.station_selector`](ecmwf.md) | ECMWF IFS QPF, soil moisture, dynamic gauge selection |
| | [`src.sensors.thingspeak_gauge`](sensors.md) | Live ultrasonic radar stage telemetry |
| | [`src.processing.*`](processing.md) | Gauge fetch, DSS conversion, pre-run QC |
| **Alerts & Delivery** | [`src.alerts.evaluator`](alerts.md) · [`src.alerts.telegram_bot`](alerts.md) | Threshold evaluation, priority de-duplication, Telegram bulletins |
| **Orchestration & Storage** | [`src.orchestrator`](orchestrator.md) | The 10-step cycle driver and `pipeline_step_log` writer |
| | [`src.dss.writer`](dss.md) | Canonical HEC-DSS `PRECIP-INC` record writer |
