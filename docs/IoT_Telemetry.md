# Real-Time IoT Telemetry & Sensor Integration

```
====================================================================================================
                PANCHGANGA RIVER LEVEL IOT TELEMETRY PROCESSING PIPELINE
====================================================================================================

      Chhatrapati Shivaji Maharaj Bridge (Panchganga Ghat, Kolhapur)
      Ultrasonic Distance Telemetry Transducer (ThingSpeak Channel 3424513)
                               |
                               | (5-Minute Cellular Uplink)
                               v
               +-------------------------------+
               | REST Telemetry Polling Engine |
               | - Field1: Distance to Water   |
               | - Field2: Temperature / Status|
               +-------------------------------+
                               |
                               v
               +-------------------------------------------------------+
               | Physical Elevation Conversion                         |
               | H_water (m MSL) = Sensor_Datum (549.35m) - Distance_m |
               +-------------------------------------------------------+
                               |
                               v
               +-------------------------------------------------------+
               | Quality Control & Outlier Rejection                   |
               | - Range Check: 528.0m <= H_water <= 548.0m MSL        |
               | - 1-Hour Rolling Median Window                        |
               | - Rate of Change Guard: |dh/dt| <= 2.0 m/hr           |
               +-------------------------------------------------------+
                               |
                               +-----------------------------------+
                               |                                   |
                               v                                   v
             +-------------------------------+   +-------------------------------+
             | Active Cycle Verification     |   | Real-Time Adaptive Calibrator |
             | Compares live H_obs to        |   | Detects wave timing offset    |
             | forecast H_pred(t)            |   | Triggers L-BFGS-B optimization|
             +-------------------------------+   +-------------------------------+
```

---

## 1. Hardware Specification & Installation

- **Location:** Chhatrapati Shivaji Maharaj Bridge, Kolhapur City (Chainage 6+257).
- **Sensor Type:** High-precision Industrial Ultrasonic Distance Transducer.
- **Mounting Datum:** Affixed to bridge girder at **549.35 m MSL**.
- **River Bed Thalweg:** **528.670 m MSL** (Chainage 6+257).
- **Measurement Span:** 0.50 m to 25.0 m distance.
- **Reporting Interval:** 5 minutes via cellular IoT gateway to ThingSpeak Channel 3424513.

---

## 2. Ingestion & Quality Control Engine

The ingestion pipeline (`src/sensors/thingspeak_gauge.py` and `src/hydrology/realtime_telemetry_validator.py`) applies strict physical filters:

```python
# Elevation conversion and physical validation
datum_msl = 549.35  # Official surveyed bridge mounting level
distance_m = distance_ft * 0.3048
water_stage_msl = datum_msl - distance_m

# Physical boundary gate:
# Panchganga thalweg is 528.67m, historical 2019 HFL is 545.33m
if 528.0 <= water_stage_msl <= 548.0:
    valid_observations.append((timestamp, water_stage_msl))
```
