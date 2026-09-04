# Open-Meteo & ECMWF Meteorological Data Pipeline

```
========================================================================================
             HYDROCAST METEOROLOGICAL INGESTION & FORECAST ENGINE
========================================================================================

           ECMWF Integrated Forecasting System (IFS 0.25° / ~9 km Grid)
                                       │
                                       ▼
                       Open-Meteo High-Performance REST API
                                       │
     ┌─────────────────────────────────┴─────────────────────────────────┐
     ▼                                                                   ▼
[ 90-Hour Forward Hyetograph ]                          [ 90-Day Antecedent Re-Analysis ]
Hourly precipitation (mm/hr)                             Historical daily accumulation (mm)
Horizon: T+0 to T+89h                                    Evaluates Soil Moisture:
Resolution: 1 hour                                       AMC-I (Dry) / AMC-II / AMC-III (Wet)
     │                                                                   │
     └─────────────────────────────────┬─────────────────────────────────┘
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
1. **Zero License Friction:** Open-Meteo aggregates the open-data releases from ECMWF (European Centre for Medium-Range Weather Forecasts) IFS 0.25° (Integrated Forecasting System), DWD ICON, and NOAA GFS.
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

## 5. Rate-Limiting, Fault Tolerance & Error Handling

To guarantee 100% pipeline reliability without triggering IP-level rate-limiting (`HTTP 429 Too Many Requests`), the engine implements:

1. **Polite Inter-Station Delays:**
   ```python
   time.sleep(0.25)  # 250ms spacing between sequential station requests
   ```
2. **Exponential Backoff with Jitter:**
   ```python
   for attempt in range(max_retries):
       try:
           res = requests.get(OM_URL, params=params, timeout=12.0)
           if res.status_code == 200:
               return parse_precipitation_array(res.json())
           elif res.status_code == 429:
               wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
               time.sleep(wait_time)
       except requests.exceptions.RequestException:
           time.sleep(2.0)
   ```
3. **Spatial Fallback (Nearest Neighbor):**
   If a station API times out after 3 retries, the dynamic station selector automatically routes to the closest spatial alternate station in the same or adjacent subbasin using Euclidean geographic distance:
   $$d = \sqrt{(\Delta\text{lon} \cdot \cos\bar{\phi})^2 + \Delta\phi^2}$$

---

## 6. Antecedent Soil Moisture Condition (AMC) Analysis

To configure the hydrological runoff Curve Number ($CN$) accurately in HEC-HMS, the system queries the 90-day historical precipitation:

$$P_{5} = \sum_{d=t-5}^{t} \text{Rainfall}_d \quad (\text{5-day antecedent rainfall in mm})$$

```
+-------------------+--------------------------------+--------------------------------+
| Moisture Category | 5-Day Dormant Season Rain (mm) | 5-Day Growing Season Rain (mm) |
+-------------------+--------------------------------+--------------------------------+
| AMC-I  (Dry)      | < 12.5 mm                      | < 35.0 mm                      |
| AMC-II (Average)  | 12.5 to 28.0 mm                | 35.0 to 53.0 mm                |
| AMC-III (Wet)     | > 28.0 mm                      | > 53.0 mm                      |
+-------------------+--------------------------------+--------------------------------+
```

When heavy monsoon spells occur in Kolhapur ($P_5 > 53\text{ mm}$), the engine automatically converts Curve Numbers to $CN_{III}$ using the standard hydrologic conversion:

$$CN_{III} = \frac{CN_{II} \cdot e^{0.00673 \cdot (100 - CN_{II})}}{1 + CN_{II} \cdot (e^{0.00673 \cdot (100 - CN_{II})} - 1)}$$

This ensures runoff calculations reflect saturated soil conditions where nearly 100% of excess rainfall converts directly into flood discharge.
