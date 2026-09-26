# Panchganga Rain Gauge Network & Subbasin Station Routing Topology

```
========================================================================================================================
                 PANCHGANGA BASIN RAIN GAUGE NETWORK & SUBBASIN ROUTING TOPOLOGY
========================================================================================================================

  Elevation & Orographic Rainfall Gradient (West to East):
  Altitude (m MSL)
   700 +   [ GAGANBAWDA (680m) ]  <-- Crest of Western Ghats (Highest Rainfall Zone ~5,000 mm/year)
       |   [ KARANJPHEN (640m) ]  [ PADASALI (620m) ]
   600 +   [ RADHANAGARI (615m) ] [ GARIVADE (610m) ] [ KOTOLI (585m) ]
       |   [ SANGARUL (572m) ]    [ BEED (565m) ]     [ KASABA TARALE (595m) ]
   550 +---------------------------------------------- [ KARVEER (550m) ] <-- Valley Floor / Outlet
       +----------------------------------------------------------------------------------------->
       West (Sahyadri Escarpment)                                          East (Kolhapur Plains)

  Subbasin Spatial Hierarchy & Delineated Drainage Areas (Total Gauged Catchment: 1,837.21 km²):

  ┌───────────────┬──────────────┬────────────────────────────────┬──────────────────────────────────────────┐
  │ Subbasin ID   │ Area (km²)   │ Primary Raingauge Station      │ Alternate Station(s)                     │
  ├───────────────┼──────────────┼────────────────────────────────┼──────────────────────────────────────────┤
  │ S1            │ 86.213 km²   │ Karveer                        │ — (Centroid fallback to Karveer)         │
  │ S2            │ 153.770 km²  │ Sangarul                       │ Balinga, Kale                            │
  │ S3            │ 261.320 km²  │ Kotoli                         │ Bajar Bhogaon, Padal                     │
  │ S4            │ 262.000 km²  │ Karanjphen                     │ — (High-altitude headwater gauge)        │
  │ S5            │ 106.390 km²  │ Padasali                       │ Salwan                                   │
  │ S6            │ 227.720 km²  │ Gaganbawda                     │ Gaganbawda (Crest Gauge)                 │
  │ S7            │ 195.390 km²  │ Garivade                       │ — (Dudhganga-Panchganga ridge)           │
  │ S8            │ 177.440 km²  │ Beed                           │ Shiroli-Dhumala                          │
  │ S9            │ 366.970 km²  │ Radhanagari                    │ Haladi, Rashiwade Bk, Aavali Bk,         │
  │               │              │                                │ Kasaba Tarale, Kasaba Walawe             │
  └───────────────┴──────────────┴────────────────────────────────┴──────────────────────────────────────────┘
```

---

## 1. Official Subbasin Delineation & Station Registry

The rainfall network is configured to capture the steep spatial precipitation gradients across the Sahyadri range. The primary stations serve as the default input for each subbasin, with alternate stations evaluated dynamically:

```
+----+-------------------+----------+-------------+-----------+------------+------------+--------------------+
| No | Station Name      | Subbasin | Subbasin km²| Elevation | Longitude  | Latitude   | Hierarchy Role     |
+----+-------------------+----------+-------------+-----------+------------+------------+--------------------+
| 01 | KARVEER           | S1       | 86.213 km²  | 550 m     | 74.248177° | 16.706369° | PRIMARY GOVERNING  |
| 02 | SANGARUL          | S2       | 153.770 km² | 572 m     | 74.093163° | 16.684196° | PRIMARY GOVERNING  |
| 03 | BALINGA           | S2       | —           | 560 m     | 74.170310° | 16.687844° | Alternate Backup   |
| 04 | KALE              | S2       | —           | 580 m     | 74.056450° | 16.722809° | Alternate Backup   |
| 05 | KOTOLI            | S3       | 261.320 km² | 585 m     | 74.051871° | 16.782017° | PRIMARY GOVERNING  |
| 06 | BAJAR_BHOGAON     | S3       | —           | 590 m     | 74.110782° | 16.808677° | Alternate Backup   |
| 07 | PADAL             | S3       | —           | 575 m     | 74.115187° | 16.744601° | Alternate Backup   |
| 08 | KARANJPHEN        | S4       | 262.000 km² | 640 m     | 73.903649° | 16.785097° | PRIMARY GOVERNING  |
| 09 | PADASALI          | S5       | 106.390 km² | 620 m     | 73.843584° | 16.701934° | PRIMARY GOVERNING  |
| 10 | SALWAN            | S5       | —           | 595 m     | 73.973500° | 16.671200° | Alternate Backup   |
| 11 | GAGANBAWDA        | S6       | 227.720 km² | 680 m     | 73.834674° | 16.546993° | PRIMARY GOVERNING  |
| 12 | GARIVADE          | S7       | 195.390 km² | 610 m     | 73.918419° | 16.520366° | PRIMARY GOVERNING  |
| 13 | BEED              | S8       | 177.440 km² | 565 m     | 74.128896° | 16.647984° | PRIMARY GOVERNING  |
| 14 | SHIROLI_DHUMALA   | S8       | —           | 560 m     | 74.106283° | 16.616677° | Alternate Backup   |
| 15 | RADHANAGARI       | S9       | 366.970 km² | 615 m     | 73.997182° | 16.410210° | PRIMARY GOVERNING  |
| 16 | HALADI            | S9       | —           | 555 m     | 74.156292° | 16.593263° | Alternate Backup   |
| 17 | RASHIWADE_BK      | S9       | —           | 570 m     | 74.101973° | 16.547564° | Alternate Backup   |
| 18 | AAVALI_BK         | S9       | —           | 585 m     | 74.054981° | 16.481009° | Alternate Backup   |
| 19 | KASABA_TARALE     | S9       | —           | 595 m     | 74.021589° | 16.447888° | Alternate Backup   |
| 20 | KASABA_WALAWE     | S9       | —           | 615 m     | 73.997182° | 16.410210° | Alternate Backup   |
+----+-------------------+----------+-------------+-----------+------------+------------+--------------------+
|    | TOTAL GAUGED AREA | 9 SUBS   | 1,837.21 km²| —         | —          | —          | 20 STATIONS ACTIVE |
+----+-------------------+----------+-------------+-----------+------------+------------+--------------------+
```

---

## 2. Dynamic Conservative Station Selection Algorithm

In open-channel flood safety, under-predicting rainfall can lead to catastrophic late evacuations. For subbasins with multiple rain gauges ($S_2, S_3, S_5, S_8, S_9$), HydroCast implements **Dynamic Maximum Rainfall Selection**:

```python
def select_active_subbasin_gages(
    station_rainfall_90hr: Dict[str, float]
) -> Dict[str, dict]:
    """
    Evaluates 90-hour rainfall across all primary and alternate stations in each subbasin.
    Selects the maximum-precipitation station as the governing gauge.
    """
    by_subbasin = group_by_subbasin(STATION_REGISTRY)
    selection_results = {}

    for sub_id in ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"]:
        candidates = by_subbasin.get(sub_id, [])
        scored = [(station_rainfall_90hr.get(c.station_id, 0.0), c) for c in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        best_rf, best_st = scored[0]

        selection_results[sub_id] = {
            "subbasin_id": sub_id,
            "selected_station_id": best_st.station_id,
            "station_name": best_st.name,
            "lat": best_st.lat,
            "lon": best_st.lon,
            "cumulative_mm": round(best_rf, 2),
            "method": "MAX_RAIN_VOLUME",
            "candidates_count": len(candidates),
        }
    return selection_results
```

---

## 3. Hydrologic Impact of the Station Update

1. **Orographic Catchment Alignment:** In Subbasin $S_5$ (Kumbhi Basin), switching to `Padasali` ($73.843584^\circ\text{ E}, 16.701934^\circ\text{ N}$, elevation $620\text{ m}$) captures the high-intensity storm front along the western ghats crest ($48.7\text{ mm}$ vs $16.5\text{ mm}$ at valley station Salwan).
2. **Headwater Precision in $S_4$ & $S_7$:** Subbasin $S_4$ now directly links to `Karanjphen` ($262.00\text{ km}^2$), and $S_7$ links to `Garivade` ($195.39\text{ km}^2$), ensuring runoff generation from all 5 headwater tributaries (Kumbhi, Dhamani, Kasari, Bhogawati, and Tulsi) is faithfully integrated.
3. **Conservative Subbasin $S_9$ Buffering:** Subbasin $S_9$ ($366.97\text{ km}^2$) contains the Radhanagari reservoir drainage zone with 6 active telemetry candidates (`Radhanagari`, `Haladi`, `Rashiwade Bk.`, `Aavali Bk.`, `Kasaba Tarale`, and `Kasaba Walawe`). The max-volume router automatically tracks the localized convective cloudburst clusters across the reservoir catchment.
