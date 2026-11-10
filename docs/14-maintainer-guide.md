# 14 — Maintainer Guide

## Scope

Code walkthrough, debugging procedures, adding new components, and redeployment guide for developers. Audience: **Maintainer**.

## Code Organization

```
backend/
  api/                 FastAPI applications and routes
    main.py            Public API (port 8000)
    admin_app.py       Admin API (port 8001)
    admin.py           Admin router (shared endpoints)
    security.py        JWT, bcrypt, auth verification
    limits.py          Rate limiter configuration
    keys.py            API key verification
    websocket_hub.py   WebSocket broadcast
    circuit_breaker.py External API circuit breaker
  service/             Pipeline and scheduling
    pipeline_worker.py 12-step forecast cycle
    orchestrator.py    Pipeline entry point
    scheduler_daemon.py 6-hourly cron
    watchdog.py        Process health monitor
  rainfall/            Meteorological data
    open_meteo.py      ECMWF download
    open_meteo_failsafe.py 3-tier failsafe
    station_selector.py Station registry and selection
    downloader.py      HTTP utilities
    retry_utils.py     Retry logic
  hms/                 Hydrologic modelling
    runner.py          HEC-HMS execution / Python twin
    basin_parser.py    Basin parameter parsing
  stage_conversion/    Hydraulics
    stage_converter.py PCHIP rating curves
    post_process.py    Alert classification
  hydraulics/
    rating_physics.py  Physics-based rating utilities
  ml/                  Machine learning
    ml_calibration.py  Levenberg-Marquardt optimizer
    ml_parameter_predictor.py Gated ML predictor
  thingspeak/          IoT telemetry
    multi_station.py   Multi-station fetcher (SS, NW, IK)
    thingspeak_gauge.py Single-station fetcher
    failsafe_telemetry.py Spike filtering
  validation/          Forecast validation
    validation_metrics.py NSE, RMSE, Spearman
    realtime_telemetry_validator.py Forecast vs observed
    telemetry_metrics.py Telemetry quality metrics
  alerts/              Alert system
    evaluator.py       CWC threshold evaluation
    telegram_bot.py    Telegram notification dispatch
  db/                  Database layer
    connection.py      Connection config
    resilient_pool.py  Async connection pool
    store_results.py   Forecast persistence
    archive_runs.py    Parquet cold storage
  dss/
    writer.py          HEC-DSS time-series generation
  processing/
    gauge_fetcher.py   Gauge data collection
  client/
    suk_client.py      Python client SDK
  scripts/
    manage_users.py    CLI user management
    seed_adm1.py       Admin user seeder
```

## Adding a New Sensor Station

1. **Add channel to `.env`**:
   Add `THINGSPEAK_<NAME>_CHANNEL_ID` and `THINGSPEAK_<NAME>_READ_API_KEY` environment variables.

2. **Register in `backend/thingspeak/multi_station.py`**:
   Add an entry to the `STATIONS` list with:
   - `station_id`: 2-letter code (e.g., "XY")
   - `name`: Short display name
   - `full_name`: Full location name
   - `channel_id_env`: Environment variable name for channel ID
   - `api_key_env`: Environment variable name for API key
   - `sensor_datum_m`: Height of sensor transducer (m MSL)
   - `zero_level_m`: Gauge zero reference (m MSL)
   - `has_voltage`: Whether the station reports battery voltage
   - `field_map`: ThingSpeak field mapping

3. **Restart the backend** to pick up the new station.

The new station will automatically appear in:
- `/api/v1/sensors/live`
- `/api/v1/sensors/{station_id}`
- `/api/v1/sensors/registry`

4. **Update frontend** to display the new station (add to dashboard panels).

## Adding a New API Endpoint

### Public API (port 8000)

Add the route to `backend/api/main.py`:

```python
@app.get("/api/v1/your-endpoint", tags=["YourTag"])
@limiter.limit(RATE_LIMIT_PUBLIC)
async def your_endpoint(request: Request):
    ...
```

### Admin API (port 8001)

Add the route to `backend/api/admin.py`:

```python
@router.post("/your-endpoint", summary="Description")
async def your_endpoint(claims=Depends(verify_admin_auth)):
    role = claims.get("role", "")
    if role not in ("admin", "dev"):
        raise HTTPException(403, "Insufficient role")
    ...
```

## Debugging the Pipeline

### Check Pipeline Status

```powershell
# Via API
curl http://localhost:8000/api/v1/pipeline

# Via admin console
# Navigate to Pipeline & Diagnostics
```

### Live Logs

Connect to the WebSocket log stream:
```
ws://localhost:8001/ws/admin/logs
```

Or check the log file: `data/logs/orchestrator.log`

### Single-Step Retry

If one step fails, you can retry it without re-running the entire cycle:

```python
from backend.service.orchestrator import run_pipeline
result = run_pipeline(single_step=7)  # Re-run only step 7
```

### Common Pipeline Failures

| Step | Common Issue | Fix |
|------|-------------|-----|
| 1 (Weather) | Open-Meteo API timeout | Will fall through to Tier 2/3 automatically |
| 7 (HMS/Twin) | Java not found (HEC-HMS) | System falls back to Python twin emulator |
| 9 (Stage) | Rating curve out of range | Check if discharge exceeds HFL bounds |
| 10 (DB) | PostgreSQL connection lost | Check `resilient_pool.py` reconnection |
| 12 (Broadcast) | No WebSocket clients | Not an error; broadcast succeeds silently |

## Database Maintenance

### Run a Manual Migration

```powershell
psql -U <db_user> -d rainfall_runoff -f database/auth/your_migration.sql
```

### Check Table Sizes

```sql
SELECT relname, pg_size_pretty(pg_total_relation_size(oid))
FROM pg_class WHERE relkind = 'r'
ORDER BY pg_total_relation_size(oid) DESC LIMIT 10;
```

### Archive Old Runs

```powershell
curl -X POST http://localhost:8001/api/v1/admin/archive -H "Authorization: Bearer <token>"
```

## Redeployment Checklist

1. Pull latest code
2. Run any new database migrations
3. `pip install -r requirements.txt` (if dependencies changed)
4. `npm install && npm run build` in both frontend directories (if changed)
5. Restart Windows services: `.\windows\service_control.ps1 -Action restart`
6. Verify: `.\windows\system_diag.ps1`
7. Check API health: `curl http://localhost:8000/api/v1/health`

## Source Files

All source files are listed in the Code Organization section above.
