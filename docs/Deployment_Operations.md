# Production Deployment, Operations & Automation Manual

```
========================================================================================
             HYDROCAST PRODUCTION INFRASTRUCTURE & ORCHESTRATION
========================================================================================

                 [ 6-Hourly Cron / Task Scheduler (00z, 06z, 12z, 18z) ]
                                            │
                                            ▼
                    Python Orchestrator (system/src/ecmwf/open_meteo.py)
                    - 18-Station Rainfall Fetch
                    - HEC-HMS / SCS-CN Hydrologic Simulation
                    - Monotonic PCHIP Hydraulic Conversion
                    - Validation Engine & Runs Ledger Archiving
                                            │
                 ┌──────────────────────────┴──────────────────────────┐
                 ▼                                                     ▼
     [ FastAPI Backend Service ]                             [ Next.js 14 Web App ]
     Managed by systemd / PM2                                Managed by PM2
     Port: 8000 (ASGI / Uvicorn)                             Port: 3000 (Production Node)
     Reverse Proxy: NGINX / Cloudflare                       Reverse Proxy: NGINX / Cloudflare
```

---

## 1. Automated Cron Scheduling (ECMWF Operational Cycles)

The European Centre for Medium-Range Weather Forecasts releases operational IFS runs four times daily. HydroCast triggers automated forecast cycles 45 minutes after official model availability to allow for global numerical assimilation:

```
+---------------+---------------------+---------------------+-------------------------+
| ECMWF Cycle   | Global Model Time   | Indian Std Time(IST)| Automated Pipeline Run  |
+---------------+---------------------+---------------------+-------------------------+
| 00z Forecast  | 00:00 UTC           | 05:30 AM IST        | 06:45 AM IST (01:15 UTC)|
| 06z Forecast  | 06:00 UTC           | 11:30 AM IST        | 12:45 PM IST (07:15 UTC)|
| 12z Forecast  | 12:00 UTC           | 05:30 PM IST        | 06:45 PM IST (13:15 UTC)|
| 18z Forecast  | 18:00 UTC           | 11:30 PM IST        | 12:45 AM IST (19:15 UTC)|
+---------------+---------------------+---------------------+-------------------------+
```

### Linux Crontab Configuration:
```cron
# Edit with: crontab -e
15 1 * * *  cd /opt/hydrocast && /opt/hydrocast/venv/bin/python system/src/ecmwf/open_meteo.py >> system/data/logs/cron_00z.log 2>&1
15 7 * * *  cd /opt/hydrocast && /opt/hydrocast/venv/bin/python system/src/ecmwf/open_meteo.py >> system/data/logs/cron_06z.log 2>&1
15 13 * * * cd /opt/hydrocast && /opt/hydrocast/venv/bin/python system/src/ecmwf/open_meteo.py >> system/data/logs/cron_12z.log 2>&1
15 19 * * * cd /opt/hydrocast && /opt/hydrocast/venv/bin/python system/src/ecmwf/open_meteo.py >> system/data/logs/cron_18z.log 2>&1
```

---

## 2. Process Management: Systemd & PM2

### 2.1 Backend FastAPI Service Unit (`/etc/systemd/system/hydrocast-api.service`)
```ini
[Unit]
Description=HydroCast FastAPI Backend & WebSocket Service
After=network.target postgresql.service

[Service]
Type=simple
User=hydrocast
WorkingDirectory=/opt/hydrocast
ExecStart=/opt/hydrocast/venv/bin/uvicorn src.api.main:app --app-dir system --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5
EnvironmentFile=/opt/hydrocast/system/.env

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable hydrocast-api
sudo systemctl start hydrocast-api
sudo systemctl status hydrocast-api
```

### 2.2 Frontend Next.js Process via PM2
```bash
cd /opt/hydrocast/system/frontend
npm run build
pm2 start npm --name "hydrocast-frontend" -- start -- -p 3000
pm2 save
pm2 startup
```

---

## 3. Environment Variable Configuration (`system/.env`)

```ini
# Database (Leave blank to use standalone JSON ledger mode)
DATABASE_URL=postgresql://postgres:password@localhost:5432/hydrocast
SUPABASE_DB_URL=

# Pipeline Security
INTERNAL_KEY=your_secure_internal_broadcast_key_here

# Catchment Geographical Envelope
BBOX_N=17.20
BBOX_S=16.20
BBOX_E=74.50
BBOX_W=73.70

# Hydrologic Baseflow Calibration
MONSOON_BASEFLOW=91.1
HEC_HMS_CMD="C:\Program Files\HEC\HEC-HMS-4.10\hec-hms.cmd"
```

---

## 4. NGINX Reverse Proxy & SSL Configuration

```nginx
server {
    listen 80;
    server_name hydrocast.kolhapur.gov.in;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name hydrocast.kolhapur.gov.in;

    ssl_certificate /etc/letsencrypt/live/hydrocast.kolhapur.gov.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hydrocast.kolhapur.gov.in/privkey.pem;

    # Frontend Next.js Web App
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend FastAPI REST Endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket Live Push Stream
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## 5. Health Monitoring & Disaster Recovery

- **Health Check Endpoint:** `curl -s http://localhost:8000/health | jq`
  - Returns `{"status": "healthy", "database": "connected", "last_cycle": "CYC_..."}`.
- **Log Rotation:** Logs are kept under `system/data/logs/` and automatically rotated using `logrotate` with 14-day retention.
- **Zero-Dependency Fallback:** If PostgreSQL or internet APIs fail, HydroCast defaults to the pre-cached static dataset and physical SCS-CN emulator, guaranteeing that emergency centers always have active flood projections.
