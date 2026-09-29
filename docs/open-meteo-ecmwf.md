# Open-Meteo & ECMWF Meteorological Data Pipeline

```
========================================================================================
             HYDROCAST METEOROLOGICAL INGESTION & FORECAST ENGINE
========================================================================================

           ECMWF Integrated Forecasting System (IFS HRES 9km / 0.1° Grid)
                                       │
                                       ▼
                       Open-Meteo High-Performance REST API
                                       │
     ┌─────────────────────────────────┴─────────────────────────────────┐
     ▼                                                                   ▼
[ 90-Hour Forward Hyetograph ]                          [ Soil-Moisture Capture ]
Hourly precipitation (mm/hr)                             Fetch-and-log ONLY:
Horizon: T+0 to T+89h                                    IFS 90h VWC + ERA5-Land 5-day
Resolution: 1 hour                                       antecedent (0-7 to 100-255 cm).
      │                                                  Stored for FUTURE AMC refinement;
      │                                                  never alters CN/K/routing today.
      ▼
[ AMC Classification (90h Rain Signal) ]
Cumulative mean 90h forecast rain (mm)
Evaluates Soil Moisture:
AMC-I (Dry) / AMC-II / AMC-III (Wet)
      │                                                   │
      └─────────────────────────────────┬─────────────────┘
                                        ▼
                  Dynamic Subbasin Station Selector & Spatial Router
                                        │
                  Panchganga 18 Rain Gauge Network (S1 to S9)
                                        │
                                        ▼
                    HEC-HMS Conservative Hyetograph Generation
```

---

## 1. Overview & Architectural Motivation

The HydroCast system requires forward-looking meteorological forcing data to drive hydrological flood predictions with a minimum lead time of **48 to 72 hours**. 

### Why Open-Meteo over Direct ECMWF MARS Subscriptions?
1. **Zero License Friction:** Open-Meteo aggregates the open-data releases from ECMWF (European Centre for Medium-Range Weather Forecasts) IFS HRES 9km (Integrated Forecasting System), DWD ICON, and NOAA GFS.
2. **Sub-second Response Times:** High-performance Rust-based servers deliver point forecasts in $< 150\text{ ms}$ per coordinate.
3. **No Local GRIB2 Storage Overhead:** Directly extracts 1D precipitation arrays without downloading multi-gigabyte GRIB2 grid files across India.
4. **Deterministic Run Schedules:** Aligned to the 00z, 06z, 12z, and 18z ECMWF operational forecast cycles.

---

## 2. Geographical Catchment Envelope

The Panchganga river basin originates along the high-rainfall crest of the Western Ghats (Sahyadri ridge, receiving $3,000 - 6,000\text{ mm}$ annually) and drains eastward toward Kolhapur city.

```
 Catchment Bounding Box:
 17.20° N  +-----------------------------------------------------------+ (North: Kasaba Walawe)
           |   Gaganbawda (680m)                                       |
           |   ~5,500 mm/yr                                            |
           |                  Karanjphen (640m)                        |
           |                                       Karvir (550m)       |
           |       Radhanagari (615m)              Kolhapur City       |
 16.20° N  +-----------------------------------------------------------+ (South: Radhanagari)
           73.70° W (Ghats Crest)                              74.50° E (Outlet Confluence)
```

### Catchment Bounding Coordinates:
- **North ($BBOX\_N$):** $17.20^\circ\text{ N}$
- **South ($BBOX\_S$):** $16.20^\circ\text{ N}$
- **East ($BBOX\_E$):** $74.50^\circ\text{ E}$
- **West ($BBOX\_W$):** $73.70^\circ\text{ E}$

---

## 3. The 18-Station Meteorological Grid

The system tracks 18 distinct meteorological nodes across the 9 hydrologic subbasins ($S_1$ to $S_9$):

```
+----+-------------------+----------+-----------+------------+------------+--------------------+
| ID | Station Name      | Subbasin | Elevation | Longitude  | Latitude   | Hierarchy Role     |
+----+-------------------+----------+-----------+------------+------------+--------------------+
| 01 | KARVIR            | S1       | 550 m     | 74.248177° | 16.706369° | Primary Governing  |
| 02 | SANGARUL          | S2       | 572 m     | 74.093163° | 16.684196° | Primary Governing  |
| 03 | BALINGA           | S2       | 560 m     | 74.170310° | 16.687844° | Alternate Backup   |
| 04 | KALE              | S2       | 580 m     | 74.056450° | 16.722809° | Alternate Backup   |
| 05 | KOTOLI            | S3       | 585 m     | 74.051871° | 16.782017° | Primary Governing  |
| 06 | BAJAR_BHOGAON     | S3       | 590 m     | 74.110782° | 16.808677° | Alternate Backup   |
| 07 | PADAL             | S3       | 575 m     | 74.115187° | 16.744601° | Alternate Backup   |
| 08 | BEED              | S4       | 565 m     | 74.128896° | 16.647984° | Primary Governing  |
| 09 | SALWAN            | S5       | 595 m     | 73.973500° | 16.671200° | Primary Governing  |
| 10 | KARANJPHEN        | S6       | 640 m     | 73.903649° | 16.785097° | Primary Governing  |
| 11 | GAGANBAWDA        | S6       | 680 m     | 73.834674° | 16.546993° | Alternate Backup   |
| 12 | RADHANAGARI       | S7       | 615 m     | 73.997182° | 16.410210° | Primary Governing  |
| 13 | SHIROLI_DHUMALA   | S8       | 560 m     | 74.106283° | 16.616677° | Alternate Backup   |
| 14 | HALADI            | S8       | 565 m     | 74.148293° | 16.583344° | Alternate Backup   |
| 15 | RASHIWADE_BK      | S8       | 570 m     | 74.058300° | 16.541700° | Alternate Backup   |
| 16 | AAVALI_BK         | S8       | 575 m     | 74.016700° | 16.500000° | Alternate Backup   |
| 17 | KASABA_TARALE     | S8       | 580 m     | 73.966700° | 16.466700° | Primary Governing  |
| 18 | KASABA_WALAWE     | S9       | 560 m     | 74.195610° | 16.824510° | Primary Governing  |
+----+-------------------+----------+-----------+------------+------------+--------------------+
```

---

## 4. API Request Construction & Parameter Specification

The forecast fetcher in [`open_meteo.py`](file:///e:/hydrocast_complete/src/ecmwf/open_meteo.py) queries the Open-Meteo v1 forecast endpoint:

### 4.1 Endpoint URL
`GET https://api.open-meteo.com/v1/forecast`

### 4.2 Query Parameters
```python
params = {
    "latitude":          round(lat, 4),
    "longitude":         round(lon, 4),
    "hourly":            "precipitation",
    "forecast_days":     4,                # 96 hours, aligned to 90
    "timezone":          "UTC",
    "cell_selection":    "land",
}
```

### 4.3 Hourly Precipitation Response Parsing
```python
# Open-Meteo JSON Structure:
{
  "latitude": 16.71,
  "longitude": 74.25,
  "elevation": 552.0,
  "hourly": {
    "time": ["2026-09-03T06:00", "2026-09-03T07:00", ...],
    "precipitation": [1.2, 3.4, 0.8, 0.0, 5.6, ...]  # mm/hr
  }
}
```

---

## 5. Enterprise Retry Engine, Fault Tolerance & Error Handling

To guarantee 100% pipeline reliability without triggering IP-level rate-limiting (`HTTP 429 Too Many Requests`) or crashing on upstream cloud hiccups, HydroCast employs a dedicated retry engine ([`src/ecmwf/retry_utils.py`](file:///e:/hydrocast_complete/src/ecmwf/retry_utils.py)):

### 5.1 Architecture of `retry_with_backoff`
The utility wraps both requests and callable workflows:
```python
def retry_with_backoff(
    fn=None,
    max_retries: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions=(requests.RequestException, Exception),
    retryable_status_codes=(429, 500, 502, 503, 504),
):
    ...
```

### 5.2 Key Resilience Mechanisms
1. **Exponential Backoff with Full Random Jitter:**
   $$\Delta t_{\text{wait}} = \min\left(t_{\text{max}}, t_{\text{base}} \cdot \text{factor}^{\text{attempt}} + \text{uniform}(0, t_{\text{jitter}})\right)$$
   This prevents synchronized retry storms across concurrent workers.
2. **Polite Inter-Station Delays:**
   A 250ms spacing between sequential station requests ensures compliance with Open-Meteo non-commercial fair-use burst limits.
3. **HTTP Status Code Discrimination:**
   Transient errors (`429 Too Many Requests`, `500 Internal Server Error`, `502 Bad Gateway`, `503 Service Unavailable`, `504 Gateway Timeout`) trigger automatic backoff, while permanent errors (`400 Bad Request`, `404 Not Found`) fail fast without wasting quota.
4. **Spatial Fallback (Nearest Neighbor):**
   If a station API fails after 4 exponential backoff attempts, the dynamic station selector automatically routes to the closest spatial alternate station in the same or adjacent subbasin using Euclidean geographic distance:
   $$d = \sqrt{(\Delta\text{lon} \cdot \cos\bar{\phi})^2 + \Delta\phi^2}$$

---


## 6. Antecedent Soil Moisture Condition (AMC) Analysis

To configure the hydrological runoff Curve Number ($CN$) accurately, the automation path classifies antecedent moisture directly from the forward 90-hour forecast signal (`classify_amc` in `src/hms/runner.py`) — no 90-day gauge archive is required on the CI runner:

$$\bar{P}_{90} = \frac{1}{N}\sum_{\text{subbasins}_{i}} \sum_{h=0}^{89} P_i(h) \quad (\text{mean cumulative 90h forecast rainfall in mm})$$

```
+-------------------+------------------------------+
| Moisture Category | Mean 90h Forecast Rain (mm) |
+-------------------+------------------------------+
| AMC-I   (Dry)     | < 25.0 mm                    |
| AMC-II  (Average) | 25.0 to 65.0 mm              |
| AMC-III (Wet)     | >= 65.0 mm                   |
+-------------------+------------------------------+
```

The class drives both the Curve Numbers (TR-55 transforms) and the initial abstraction ratio:

$$CN_{I} = \frac{4.2 \cdot CN_{II}}{10 - 0.058 \cdot CN_{II}}, \qquad CN_{III} = \frac{23 \cdot CN_{II}}{10 + 0.13 \cdot CN_{II}}, \qquad I_a = \{0.20,\; 0.15,\; 0.08\} \cdot S$$

This ensures runoff calculations reflect saturated soil conditions where nearly 100% of excess rainfall converts directly into flood discharge.

---

## 7. Soil-Moisture Capture (Fetch-and-Log Only, Future AMC Refinement)

Every forecast cycle additionally captures soil moisture per subbasin via the governing gage coordinate. This data is **observability-only**: it is recorded with each run so future work can refine AMC from the *physical* antecedent-wetness signal. It is **never** used to modify Curve Numbers, the initial-abstraction ratio, K, x, or routing in today's calculations.

Two best-effort fetches are issued per subbasin (both wrapped so any failure only logs and returns `None` — the forecast pipeline is never blocked):

| Source | Endpoint | Data | Storage key |
|---|---|---|---|
| ECMWF IFS forecast | `https://api.open-meteo.com/v1/forecast` + `models=ecmwf_ifs` | Hourly volumetric soil-moisture (m³/m³) for T+0…T+89, 4 depth layers | `forecast_90h_vwc` |
| ERA5-Land reanalysis | `https://archive-api.open-meteo.com/v1/era5` | Daily soil-moisture for the 5 days before the forecast window | `antecedent_5d_vwc` |

### 7.1 Soil-Moisture Depth Layers (m³/m³ volumetric water content)

```
+--------------------------+-------------------------------+
| API Field                | Physical Depth Stored         |
+--------------------------+-------------------------------+
| soil_moisture_0_to_7cm   | 0–7 cm    (surface)          |
| soil_moisture_7_to_28cm  | 7–28 cm                       |
| soil_moisture_28_to_100cm| 28–100 cm                     |
| soil_moisture_100_to_255cm | 100–255 cm                 |
+--------------------------+-------------------------------+
```

Values are clipped to the physical bound $[0.0,\; 0.60]\ \text{m}^3/\text{m}^3$ (`SOIL_MOISTURE_SANE_RANGE`), NaN/Inf are zeroed, and results are rounded to 4 decimals for JSON-safe archiving.

### 7.2 Where It Lives In The Run Artifacts

- `pipeline_state["soil_moisture"] = {"unit": "m3/m3", "per_subbasin": {S1…S9}}` — full per-subbasin snapshot + antecedent.
- `status.last_cycle["surface_soil_moisture_0_7cm"]` — catchment-mean surface (0–7 cm) VWC at forecast start, exposed for dashboard observability.

Implements: [`fetch_soil_moisture_snapshot`](file:///e:/hydrocast_complete/src/ecmwf/open_meteo.py) and [`fetch_antecedent_soil_moisture`](file:///e:/hydrocast_complete/src/ecmwf/open_meteo.py), both in `src/ecmwf/open_meteo.py`. Tests: `tests/test_soil_moisture.py`.
