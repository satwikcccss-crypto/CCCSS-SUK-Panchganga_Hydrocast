# Dataflow Pipeline — HydroCast

> **Current build:** v2.0.0 · Panchganga Basin · 90-h forecast · 4 cycles/day  
> **Status:** the five-stage flow below is the production path, not the design intent.

---

## Interactive Dataflow Console

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 02</span>
      <strong>Rainfall to Alert Dataflow (Five Operational Stages)</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/02-dataflow.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/02-dataflow.html?embed=1" title="Rainfall to Alert Dataflow Console"></iframe>
</div>

---


## Dataflow Artifact Map

Every artifact appears exactly once:


---

## Dataflow — Stage by Stage

| Stage | Components | Scripts | Output |
|:---|:---|:---|:---|
| **01 · Sources** | ECMWF IFS HRES 9 km, ThingSpeak Ch. 3424513 | `src/ecmwf/open_meteo.py`, `src/sensors/thingspeak_gauge.py` | 90-h hyetographs, observed stage |
| **02 · Ingest** | Open-Meteo SDK Client, Station Selector, DSS Writer | `src/ecmwf/open_meteo.py`, `src/ecmwf/station_selector.py`, `src/dss/writer.py` | HEC-DSS boundary write |
| **03 · Process** | Orchestrator, HEC-HMS Emulator, WRD PCHIP, ML Recalibration | `src/orchestrator.py`, `src/hms/runner.py`, `src/hydrology/stage_converter.py`, `src/hydrology/ml_calibration.py` | Q_total, stage h, peak arrival |
| **04 · Store** | PostgreSQL 15, Parquet, JSON Ledger | `src/db/archive_runs.py`, `src/db/store_results.py` | Parquet partitions, run JSON |
| **05 · Consume** | FastAPI REST, WebSocket, Next.js 14, Telegram Bot | `src/api/main.py`, `src/api/notifier.py`, `src/alerts/telegram_bot.py` | Dashboard, Telegram alerts |

---

## Data Contracts

| Flow | From → To | Payload | Unit |
|:---|:---|:---|:---|
| `ecmwf → openmeteo` | External → Ingest | 90-h QPF | mm/hr |
| `thingspeak → orchestrator` | External → Process | observed stage | m MSL |
| `openmeteo → station_selector` | Ingest → Ingest | hyetographs | mm/hr |
| `station_selector → dss_writer` | Ingest → Ingest | governing gage | station ID |
| `dss_writer → orchestrator` | Ingest → Process | DSS boundary write | HEC-DSS pathname |
| `orchestrator → hms_emulator` | Process → Process | 12 steps | Q_total, Q_surface, baseflow |
| `hms_emulator → stage_converter` | Process → Process | discharge Q | m³/s |
| `stage_converter → postgres` | Process → Store | stage h | m MSL |
| `ml_calibration → orchestrator` | Process → Process | α_K · α_lag · ΔCN · X ↩ | parameters |
| `postgres → parquet` | Store → Store | 90-day pruning | Parquet |
| `orchestrator → json_ledger` | Process → Store | CYC_*.json | JSON |
| `postgres → fastapi` | Store → Consume | asyncpg reads | — |
| `fastapi → websocket` | Consume → Consume | /ws/live | — |
| `websocket → nextjs` | Consume → Consume | push | — |
| `stage_converter → telegram_bot` | Process → Consume | alert tier | — |
| `telegram_bot → nextjs` | Consume → Consume | bulletin | — |

---

## Data Integrity

| Check | Implementation | Location |
|:---|:---|:---|
| Physical range check | ≤ 250 mm/hr | `src/processing/validator.py` |
| Coverage floor | ≥ 50% of 90 h | `src/processing/validator.py` |
| Gauge lag | ≤ 60 min | `src/processing/validator.py` |
| NWP freshness | ≤ 8 h | `src/processing/validator.py` |
| Mass conservation | C₀ + C₁ + C₂ ≡ 1 | `src/hms/runner.py` |
| Monotonicity | dQ/dh > 0 | `src/hydrology/stage_converter.py` |
| Atomic write-back | `.bak` + `os.replace()` | `src/hydrology/ml_calibration.py` |
