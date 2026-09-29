---
title: Sensors Reference
---

# Sensors Reference

The ThingSpeak channel, the datum arithmetic, and the live-stage contract.

---

## Stage derivation

```text
  Ultrasonic radar sensor (Chhatrapati Shivaji Maharaj Bridge)
  mounted at  549.35 m MSL
        │
        │  raw_feet  (distance from sensor head to water surface)
        ▼
  ┌──────────────────────────────────────────────────┐
  │  stage_m = 549.35 − (raw_feet × 0.3048)          │
  └──────────────────┬───────────────────────────────┘
                     ▼
             observed_stage_m  (m MSL)
                     │
        ┌────────────┴─────────────┐
        │                          │
        ▼                          ▼
  forecast comparison       stage → discharge
  (stage error, m)          via WRD PCHIP rating
                            ⇒ RATING_IMPLIED_DERIVED
```

```text
  raw_feet = 54.83 ft
      │
      ├── × 0.3048 = 16.712 m
      │
      └── 549.35 − 16.712 = 532.64 m MSL
```

!!! info "Datum chain, in one place"
    - **549.35 m MSL** — elevation of the sensor mount (the radar head).
    - **528.670 m MSL** — Shivaji Bridge bed level (X-Section survey).
    - **529.318 m MSL** — Rajaram weir bed / thalweg level, `0.648 m` higher.
    - **542.10 m** — Shivaji **ALERT** stage (WRD), recorded at the same
      `1 800 m³/s` as the Rajaram **WARNING** — exactly the `0.648 m` separation,
      which is what validates the downstream-shift transform
      `Shivaji_stage = WRD_Rajaram_stage − 0.648`.

---

## Resilience behaviour

```text
  fetch_shivaji_live_telemetry()
            │
   ┌────────┴─────────┐
   │ channel id set?  │──no──► status = "AWAITING_CHANNEL_ID"
   │                   │         stage_m = None, raw_feet = None
   │ yes                              │
   │                                  ▼
   ▼                        open_meteo.py logs a WARN and uses
  HTTP fetch to ThingSpeak          last-known 532.60 m / 54.83 ft
   │
   ├── 200 + sane value ──► stage_m, raw_feet populated
   ├── 200 + non-numeric ──► status = "SENSOR_ABNORMAL", values None
   ├── 429 / 5xx           ──► status = "RATE_LIMITED" | "HTTP_ERROR"
   └── timeout             ──► status = "TIMEOUT"
            │
            ▼
   NOTE: the API key is never echoed back in the returned payload.
```

---

## `src/sensors/thingspeak_gauge.py`

::: src.sensors.thingspeak_gauge
