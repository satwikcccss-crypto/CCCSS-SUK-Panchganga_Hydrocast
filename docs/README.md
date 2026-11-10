# HydroCast Panchganga — Technical Documentation Suite

**IoT and Geoinformatics-Based Flood Monitoring & Prediction System**  
Centre for Climate Change and Sustainability Studies (CCCSS)  
Shivaji University, Kolhapur — DST-SERB Funded Project

---

## Documentation Index

### Domain & Science

| Document | Audience | Description |
|----------|----------|-------------|
| [01 System Overview](01-system-overview.md) | All | High-level architecture, mission, and operational summary |
| [02 Hydrology](02-hydrology.md) | Maintainer | SCS-CN loss model, unit hydrograph, subbasin delineation |
| [03 Hydraulics](03-hydraulics.md) | Maintainer | Muskingum-Cunge routing, stage-discharge, rating curves |
| [04 Meteorology](04-meteorology.md) | Maintainer | ECMWF/Open-Meteo forecast ingestion, areal rainfall |
| [05 Station Network](05-station-network.md) | Operator | ThingSpeak IoT sensors, station selection algorithm |
| [06 Machine Learning](06-machine-learning.md) | Maintainer | Physics-based recalibration, Levenberg-Marquardt, parameter nudging |

### Technical Reference

| Document | Audience | Description |
|----------|----------|-------------|
| [07 API Reference](07-api-reference.md) | Maintainer | Public API (port 8000) and Admin API (port 8001) endpoints |
| [08 Architecture](08-architecture.md) | Maintainer | Dual-port FastAPI, Next.js frontends, PostgreSQL, tech stack |
| [09 Database](09-database.md) | Maintainer | Schema, tables, indexes, migrations, PostGIS |
| [10 Dashboards](10-dashboards.md) | Operator | Public dashboard panels and Admin console sections |
| [11 Security](11-security.md) | Maintainer | JWT auth, RBAC, CORS, CSP, anti-scraping, rate limiting |
| [12 Deployment](12-deployment.md) | Maintainer | Windows Server setup, services, backup, environment config |

### Operations Guides

| Document | Audience | Description |
|----------|----------|-------------|
| [13 Operator Guide](13-operator-guide.md) | Operator | Day-to-day console use: login, monitoring, forecast triggers |
| [14 Maintainer Guide](14-maintainer-guide.md) | Maintainer | Code walkthrough, debugging, adding sensors, redeployment |
| [15 Troubleshooting](15-troubleshooting.md) | All | Common issues, diagnostics, recovery procedures |

---

## Audience Definitions

- **General**: Anyone who needs to understand what the system does (officials, stakeholders)
- **Operator**: Personnel who use the admin console to monitor and trigger forecasts (CCCSS staff, JRFs)
- **Maintainer**: Developers who modify, debug, or redeploy the system (system architects, future developers)

## Quick Reference

| Component | Port | Technology |
|-----------|------|------------|
| Public API | 8000 | FastAPI + Uvicorn |
| Admin API | 8001 | FastAPI + Uvicorn |
| Public Dashboard | 3000 | Next.js 15 |
| Admin Console | 3001 | Next.js 15 |
| Database | 5432 | PostgreSQL 16 + PostGIS |
| IoT Telemetry | — | ThingSpeak REST API |

## Version

- **System Version**: 2.0.0
- **Documentation Date**: November 2026
- **Authors**: Er. Satwik K. Udupi (System Architecture & Development)
- **Institution**: CCCSS, Shivaji University, Kolhapur
