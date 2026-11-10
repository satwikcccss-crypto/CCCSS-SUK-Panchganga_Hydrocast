# 05 — Station Network

## Scope

This document covers the IoT sensor network and ThingSpeak telemetry integration. Audience: **Operator**.

## Sensor Network Overview

Three ultrasonic radar water level stations continuously monitor the Panchganga River:

| Station | ID | Location | ThingSpeak Channel | Sensor Datum (m MSL) | Zero Level (m MSL) | Capabilities |
|---------|-----|----------|-------------------|---------------------|--------------------|----|
| Shivaji Bridge | SS | Kolhapur (urban sink) | 3424513 | 549.35 | 530.18 | Distance, Voltage |
| Nitawade RWLS | NW | Upstream | 3417870 | 545.00 | 528.00 | Distance, Voltage |
| Ichalkaranji | IK | Downstream | 3417872 | 540.00 | 525.00 | Distance |

## How the Sensors Work

Each station uses an **ultrasonic radar** sensor mounted above the river surface. The sensor measures the air distance from its transducer face down to the water surface.

### Stage Calculation

```
Stage (m MSL) = Sensor_Datum_m - (raw_distance_feet * 0.3048)
```

For example, at Shivaji Bridge:
- Sensor datum = 549.35 m MSL
- If raw distance = 20 ft, then stage = 549.35 - (20 * 0.3048) = 543.25 m MSL

### Data Fields

| Field | Description | Unit |
|-------|-------------|------|
| field1 | Distance from sensor to water surface | feet |
| field2 | Battery/solar voltage (SS and NW only) | volts |

## ThingSpeak Integration

The system fetches live readings from ThingSpeak's REST API:

```
GET https://api.thingspeak.com/channels/{channel_id}/feeds/last.json?api_key={key}
```

Each station has its own channel ID and read API key, configured via environment variables:

| Station | Channel ID Env Var | API Key Env Var |
|---------|-------------------|-----------------|
| SS | `THINGSPEAK_CHANNEL_ID` | `THINGSPEAK_READ_API_KEY` |
| NW | `THINGSPEAK_NITAWADE_CHANNEL_ID` | `THINGSPEAK_NITAWADE_READ_API_KEY` |
| IK | `THINGSPEAK_ICHALKARANJI_CHANNEL_ID` | `THINGSPEAK_ICHALKARANJI_READ_API_KEY` |

## Sensor Status Codes

| Status | Meaning |
|--------|---------|
| ONLINE | Live data available, stage computed |
| OFFLINE | ThingSpeak API unreachable or timeout |
| NO_DATA | Channel responded but field1 is empty/null |
| NOT_CONFIGURED | Channel ID environment variable not set |

## API Endpoints

The sensor network is exposed through three public API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/sensors/live` | GET | All stations with live readings |
| `/api/v1/sensors/{station_id}` | GET | Single station (SS, NW, or IK) |
| `/api/v1/sensors/registry` | GET | Station metadata without live data |

### Example Response (GET /api/v1/sensors/live)

```json
[
  {
    "station_id": "SS",
    "name": "Shivaji Bridge",
    "full_name": "Chhatrapati Shivaji Maharaj Bridge, Kolhapur",
    "river": "Panchganga",
    "type": "ultrasonic_radar",
    "sensor_datum_m": 549.35,
    "zero_level_m": 530.18,
    "latitude": 16.695,
    "longitude": 74.2275,
    "has_voltage": true,
    "status": "ONLINE",
    "stage_m": 531.42,
    "raw_distance_ft": 58.83,
    "voltage": 12.45,
    "timestamp": "2026-07-15T06:30:00Z",
    "entry_id": 12345
  }
]
```

## Outlier Filtering

The failsafe telemetry module (`backend/thingspeak/failsafe_telemetry.py`) applies physical bounds checking:

- **Minimum air distance**: 15.0 ft (rejects readings above bridge deck submergence)
- **Maximum air distance**: 80.0 ft (rejects readings below surveyed bedrock floor)
- **Rate-of-change filter**: Rejects spikes where stage changes more than physically possible between readings
- **Physical bounds**: Stage must fall within 530-565 m MSL for Shivaji Bridge

## Reporting Cadence

- ThingSpeak uploads: every 5 minutes
- Dashboard polling: every 15-30 seconds (SWR refresh interval)
- Hourly resampling: raw 5-minute pings aggregated into UTC hourly bins for validation

## Source Files

| File | Purpose |
|------|---------|
| `backend/thingspeak/multi_station.py` | Multi-station fetcher (SS, NW, IK) |
| `backend/thingspeak/thingspeak_gauge.py` | Original single-station fetcher (SS only) |
| `backend/thingspeak/failsafe_telemetry.py` | Spike filtering and cached fallback |
| `backend/validation/realtime_telemetry_validator.py` | Forecast vs observed comparison |
| `backend/validation/telemetry_metrics.py` | NSE, RMSE, Spearman validation |
