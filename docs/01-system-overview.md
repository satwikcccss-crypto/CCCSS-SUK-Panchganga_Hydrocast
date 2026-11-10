# 01 — System Overview

## Mission

HydroCast is an operational flood forecasting and early warning system for the **Panchganga River Basin** in Kolhapur, Maharashtra, India. It provides real-time water level monitoring and 90-hour-ahead flood stage predictions to protect citizens, civic planners, and emergency responders.

The system is developed by the **Centre for Climate Change and Sustainability Studies (CCCSS)** at Shivaji University, Kolhapur, under a **DST-SERB** (Department of Science and Technology — Science and Engineering Research Board, Government of India) research grant.

## What It Does

1. **Ingests rainfall forecasts** from ECMWF (via Open-Meteo) for 9 delineated subbasins (S1–S9) of the Panchganga catchment.
2. **Runs a physics-based hydrological model** (SCS-CN rainfall-runoff + SCS unit hydrograph + Muskingum-Cunge flood routing) to simulate river discharge at the basin outlet.
3. **Converts discharge to river stage** using government-anchored PCHIP rating curves at two bridge sites (Shivaji Bridge and Rajaram Bridge).
4. **Classifies flood alerts** against CWC/DDMA thresholds (Normal → Alert → Warning → Danger → Extreme).
5. **Monitors live water levels** through a network of ultrasonic radar IoT sensors (ThingSpeak) at Shivaji Bridge, Nitawade RWLS, and Ichalkaranji.
6. **Serves a public dashboard** for citizens and a secured **operator console** for CCCSS staff and government officials.

## Architecture at a Glance

```
                    ┌─────────────────────────────────────┐
                    │         ECMWF / Open-Meteo           │
                    │    (Quantitative Precipitation        │
                    │     Forecast — 90 hr horizon)        │
                    └──────────────┬──────────────────────┘
                                   │
            ┌──────────────────────▼──────────────────────┐
            │            12-STEP FORECAST PIPELINE          │
            │                                              │
            │  1. Rainfall Download (Open-Meteo API)       │
            │  2. Station Selection (nearest-gauge)         │
            │  3. SCS-CN Loss (Effective Rainfall)         │
            │  4. SCS Unit Hydrograph (Direct Runoff)      │
            │  5. Baseflow Separation                       │
            │  6. Muskingum Flood Routing (R1–R5)          │
            │  7. Discharge Summation at Outlet            │
            │  8. Stage Conversion (PCHIP Rating Curve)    │
            │  9. Alert Classification (CWC Thresholds)    │
            │ 10. Telemetry Validation (ThingSpeak IoT)    │
            │ 11. Result Persistence (PostgreSQL)          │
            │ 12. WebSocket Broadcast (Live Dashboard)     │
            └──────────────────────┬──────────────────────┘
                                   │
     ┌─────────────────────────────┼─────────────────────────────┐
     │                             │                             │
     ▼                             ▼                             ▼
┌──────────┐              ┌──────────────┐              ┌──────────────┐
│ Public   │              │   Admin      │              │  PostgreSQL  │
│ Dashboard│              │   Console    │              │  16 + PostGIS│
│ :3000    │              │   :3001      │              │  :5432       │
└──────────┘              └──────────────┘              └──────────────┘
     │                             │
     │    ┌────────────────────────┤
     │    │                        │
     ▼    ▼                        ▼
┌──────────────┐          ┌──────────────┐
│  Public API  │          │  Admin API   │
│  :8000       │          │  :8001       │
└──────────────┘          └──────────────┘
```

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend Framework | FastAPI + Uvicorn | 0.115+ |
| Frontend Framework | Next.js (React) | 15.x |
| Database | PostgreSQL + PostGIS | 16.x |
| Language (Backend) | Python | 3.12 |
| Language (Frontend) | TypeScript | 5.x |
| IoT Platform | ThingSpeak (MathWorks) | REST API v2 |
| Weather Data | Open-Meteo ECMWF IFS | Free API |
| Authentication | JWT (HS256) + bcrypt | — |
| OS | Windows Server / Windows 11 | — |

## Dual-Port Architecture

The system runs two independent FastAPI applications:

- **Public API (Port 8000)**: Serves the citizen-facing dashboard. Read-only forecast data, rainfall, discharge, stage, and alerts. Protected by optional API key and rate limiting.
- **Admin API (Port 8001)**: Serves the operator console. Full control: user management, forecast triggers, database backup, ML recalibration, system health. Protected by JWT authentication with role-based access control.

Each API has its own CORS whitelist, security headers, anti-scraping middleware, and rate limits. They share the same PostgreSQL database.

## Sensor Network

Three IoT stations continuously monitor water levels:

| Station | ID | Location | ThingSpeak Channel | Capabilities |
|---------|-----|----------|-------------------|-------------|
| Shivaji Bridge | SS | Kolhapur (urban sink) | 3424513 | Distance, Voltage |
| Nitawade RWLS | NW | Upstream | 3417870 | Distance, Voltage |
| Ichalkaranji | IK | Downstream | 3417872 | Distance |

Each station uses an ultrasonic radar sensor that measures the distance from the sensor mounting point down to the water surface. The raw distance (in feet) is converted to water level (meters MSL) using the station-specific sensor datum.

## Forecast Cycle

The system runs a 12-step forecast pipeline on a 6-hourly cadence (00, 06, 12, 18 UTC), aligned with ECMWF synoptic hours. Each cycle:

1. Downloads the latest 90-hour quantitative precipitation forecast from Open-Meteo
2. Selects the governing rain gauge for each subbasin
3. Computes effective rainfall using SCS-CN with AMC-III curve numbers
4. Generates direct runoff hydrographs using SCS dimensionless unit hydrograph
5. Separates baseflow
6. Routes flood waves through 5 Muskingum-Cunge reaches (R1–R5)
7. Sums routed hydrographs at the outlet junction
8. Converts outlet discharge to river stage at each bridge site
9. Classifies alert levels against CWC thresholds
10. Validates forecasts against live IoT telemetry
11. Persists results to PostgreSQL
12. Broadcasts updates via WebSocket to connected dashboards

## Project Team

| Role | Name | Responsibility |
|------|------|---------------|
| Principal Investigator | Dr. Sachin S. Panhalkar | Project leadership and hydrology |
| Co-Principal Investigator | Dr. Ganesh S. Nhivekar | Electronics and IoT sensor network |
| System Architect | Er. Satwik K. Udupi | Full-stack development and deployment |
| Junior Research Fellow | Nikhil Pawar | Field operations and data collection |

## Partner Bodies

- **DST-SERB, Government of India** — Funding agency
- **Water Resources Department (WRD), Maharashtra** — Hydrological data and validation
- **Central Water Commission (CWC)** — Flood threshold standards
- **District Disaster Management Authority (DDMA), Kolhapur** — Alert dissemination
- **University Computer Centre, Shivaji University** — Infrastructure and hosting
