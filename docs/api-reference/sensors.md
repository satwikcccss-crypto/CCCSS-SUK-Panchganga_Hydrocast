---
title: Sensors Reference
---

# Sensors Reference

The ThingSpeak channel, the datum arithmetic, and the live-stage contract.

---

## Stage derivation


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

The fetcher keeps a rolling window of 800 pings per channel, rejects values
outside 1.5 interquartile ranges, and requires a minimum number of surviving
samples before it will publish a stage. On a timeout or a rejected window it
returns the last good value with an explicit staleness flag; it never substitutes
a zero. If the channel has been stale for longer than the configured horizon, the
cycle proceeds on the WRD default rather than on the dead sensor.


---

## Status contract

`fetch_shivaji_live_telemetry()` returns a status string with every payload, and
callers branch on it rather than on a nullable stage.

| Status | Meaning | Stage / raw value |
|:---|:---|:---|
| `OK` | 200 with a numeric field | populated |
| `AWAITING_CHANNEL_ID` | Channel id not configured | `None` |
| `SENSOR_ABNORMAL` | 200 but the field is non-numeric | `None` |
| `RATE_LIMITED` | 429 from ThingSpeak | last known value |
| `HTTP_ERROR` | 5xx or transport failure | last known value |

The raw field is `raw_feet`, the distance from the radar head to the water
surface. Stage is derived as `549.35 − raw_feet × 0.3048` metres MSL, then
converted to discharge against the WRD PICHIP rating for the forecast comparison.

On a failed fetch `open_meteo.py` logs a warning and proceeds with the last known
value (532.60 m / 54.83 ft at the time of writing) rather than a zero. The API key
is never echoed back in the returned payload.


## `src/sensors/thingspeak_gauge.py`

::: src.sensors.thingspeak_gauge
