# 15 — Troubleshooting

## Scope

Common issues, diagnostics, and recovery procedures. Audience: **All**.

## Quick Diagnostics

Run the system diagnostics script:

```powershell
.\windows\system_diag.ps1
```

Or check individual components:

| Check | Command |
|-------|---------|
| Public API | `curl http://localhost:8000/api/v1/health` |
| Admin API | `curl http://localhost:8001/api/v1/admin/health` |
| PostgreSQL | `psql -U <db_user> -d rainfall_runoff -c "SELECT 1"` |
| Public Dashboard | Open `http://localhost:3000` in browser |
| Admin Console | Open `http://localhost:3001` in browser |

---

## Common Issues

### API Returns 502 / Connection Refused

**Symptoms**: Dashboard shows loading spinner or connection error.

**Causes and Fixes**:
1. **Service not running**: Check `.\windows\service_control.ps1 -Action status`
2. **Port conflict**: Another process using port 8000/8001. Check with `netstat -ano | findstr :8000`
3. **Python crash**: Check `data/logs/orchestrator.log` for traceback
4. **Fix**: Restart the service: `.\windows\service_control.ps1 -Action restart`

### Dashboard Shows Stale Data

**Symptoms**: Last cycle timestamp is hours old.

**Causes and Fixes**:
1. **Scheduler stopped**: Check if `HydroCast-Scheduler` service is running
2. **Pipeline stuck**: Check Pipeline & Diagnostics in admin console for stuck step
3. **Open-Meteo outage**: Check if rainfall download (step 1) is failing
4. **Fix**: Force a manual forecast from the admin console or CLI

### Login Fails with "Invalid Credentials"

**Symptoms**: Correct username/password rejected.

**Causes and Fixes**:
1. **Account deactivated**: Admin must check `is_active` flag
2. **Wrong username format**: Usernames are case-sensitive (e.g., `DEV.Satwikcccss@Adm1`)
3. **Password not changed**: If using initial password, check `must_change_password` flag
4. **Rate limited**: Login endpoint allows 5 attempts/minute. Wait and retry.

### Password Reset Code Not Working

**Symptoms**: Reset page says "Invalid or expired code".

**Causes and Fixes**:
1. **Code expired**: Codes are valid for 1 hour only. Generate a new one.
2. **Code already used**: Codes are single-use. Generate a new one.
3. **Wrong username**: The code is tied to a specific username.
4. **Typo in code**: The code is 6 digits, numeric only.

### Sensor Shows OFFLINE

**Symptoms**: Gauge panel shows OFFLINE for one or more stations.

**Causes and Fixes**:
1. **ThingSpeak API down**: Check https://thingspeak.com/channels/<channel_id>
2. **Network issue**: Server cannot reach ThingSpeak (check outbound HTTPS)
3. **Sensor hardware failure**: Contact field team (JRF) for physical inspection
4. **API key expired**: Verify the read API key in `.env`

### Sensor Shows NO_DATA

**Symptoms**: Gauge connected but stage is null.

**Causes and Fixes**:
1. **Sensor producing empty readings**: field1 in ThingSpeak is empty
2. **Data format changed**: Check ThingSpeak channel for field mapping changes
3. **Sensor obstruction**: Physical debris blocking ultrasonic beam

### High RMSE / Low NSE in Forecast Validation

**Symptoms**: Accuracy metrics degraded.

**Causes and Fixes**:
1. **Parameter drift**: Catchment conditions changed since last calibration
2. **Fix**: Trigger recalibration via admin console or API
3. **Unusual weather**: Extreme events outside model training range
4. **Sensor error**: Check if telemetry data quality is degraded

### PostgreSQL Connection Error

**Symptoms**: API returns 500 with database errors.

**Causes and Fixes**:
1. **PostgreSQL service stopped**: Check Windows Services
2. **Connection pool exhausted**: Restart the API to reset connections
3. **Disk full**: Check disk space on the PostgreSQL data directory
4. **Fix**: `.\windows\service_control.ps1 -Action restart`

### Pipeline Step 7 Fails (HMS/Twin Execution)

**Symptoms**: Pipeline stops at step 7.

**Causes and Fixes**:
1. **Java not installed**: HEC-HMS requires Java. System falls back to Python twin.
2. **HEC-HMS files missing**: Check `hms/` directory for basin model files
3. **Out of memory**: HMS simulation exceeds available RAM
4. **Fix**: The Python twin emulator is the default fallback; ensure it is operational

### WebSocket Not Connecting

**Symptoms**: Dashboard not receiving live updates.

**Causes and Fixes**:
1. **Wrong WebSocket URL**: Check `NEXT_PUBLIC_WS_URL` in `.env`
2. **CORS blocking**: WebSocket origin must be in the allowed list
3. **Firewall blocking WebSocket upgrade**: Ensure ws:// protocol is allowed
4. **Fix**: Dashboard will fall back to HTTP polling (30-60 second refresh)

---

## Recovery Procedures

### Full System Restart

```powershell
.\windows\service_control.ps1 -Action stop
# Wait 10 seconds
.\windows\service_control.ps1 -Action start
.\windows\system_diag.ps1
```

### Database Recovery from Backup

```powershell
# Stop all services first
.\windows\service_control.ps1 -Action stop

# Restore from backup
psql -U <db_user> -d rainfall_runoff < backup_file.sql

# Restart services
.\windows\service_control.ps1 -Action start
```

### Emergency Fallback Admin Login

If all database accounts are locked out, the system has an environment-variable-based fallback admin login configured via `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env`.

---

## Log File Locations

| Log | Path | Description |
|-----|------|-------------|
| Pipeline | `data/logs/orchestrator.log` | 12-step cycle execution log |
| API (stdout) | Windows Event Log / NSSM log | FastAPI request logs |
| PostgreSQL | `E:\PostgreSQL\16\data\log\` | Database server logs |

## Getting Help

- **System maintainer**: Er. Satwik K. Udupi (System Architect)
- **Field operations**: Nikhil Pawar (JRF)
- **Project leadership**: Dr. Sachin S. Panhalkar (PI)
- **IoT and electronics**: Dr. Ganesh S. Nhivekar (Co-PI)
