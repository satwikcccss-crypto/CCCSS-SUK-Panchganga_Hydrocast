# Panchganga 18 Rain Gauge Network & Station Selection Engine

```
========================================================================================
             PANCHGANGA BASIN 18 RAIN GAUGE NETWORK & ROUTING TOPOLOGY
========================================================================================

  Elevation Profile (West to East Gradient):
  Altitude (m)
  700 +   [ GAGANBAWDA (680m) ]  <-- Western Ghats Crest (Highest Orographic Rainfall)
      |   [ KARANJPHEN (640m) ]
  600 +   [ RADHANAGARI (615m) ]
      |   [ SALWAN (595m) ]   [ KOTOLI (585m) ]
      |   [ SANGARUL (572m) ] [ BEED (565m) ]   [ KASABA TARALE (580m) ]
  550 +----------------------------------------- [ KARVIR (550m) ] <-- Valley Floor
      +-------------------------------------------------------------------->
      West (Sahyadri Mountains)                                 East (Kolhapur Plains)

  Spatial Distribution Across Subbasins S1 to S9:
  
  [S6: Kasari Upper]       [S3: Kasari Lower]       [S9: Kasaba Walawe]
  - Karanjphen (Primary)   - Kotoli (Primary)       - Kasaba Walawe (Primary)
  - Gaganbawda (Alternate) - Bajar Bhogaon (Alt)
                           - Padal (Alternate)
                                                    [S1: Karvir / Outlet]
  [S5: Kumbhi Basin]       [S2: Tulsi Upper]        - Karvir (Primary)
  - Salwan (Primary)       - Sangarul (Primary)
                           - Balinga (Alternate)
                           - Kale (Alternate)       [S8: Bhogawati Lower]
                                                    - Kasaba Tarale (Primary)
  [S4: Tulsi Lower]        [S7: Bhogawati Upper]    - Shiroli-Dhumala (Alt)
  - Beed (Primary)         - Radhanagari (Primary)  - Haladi (Alternate)
                                                    - Rashiwade Bk. (Alt)
                                                    - Aavali Bk. (Alternate)
```

---

## 1. Station Registry & Spatial Coordinate Metadata

The full registry of all 18 rain gauge stations is defined in [`station_selector.py`](file:///e:/hydrocast_complete/system/src/ecmwf/station_selector.py):

```
+----+-------------------+----------+-----------+------------+------------+--------------------+
| No | Station Name      | Subbasin | Elevation | Longitude  | Latitude   | Hierarchy Role     |
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

## 2. Dynamic Conservative Station Selection Engine

In mountainous tropical catchments, spatial rainfall variability is extreme. For subbasins with multiple rain gauges ($S_2, S_3, S_6, S_8$), HydroCast implements **Dynamic Maximum Rainfall Selection**:

```python
def select_active_subbasin_gages(station_precip: Dict[str, np.ndarray]) -> Dict[str, dict]:
    """
    Evaluates cumulative 90-hour rainfall across all stations in each subbasin.
    Selects the maximum-precipitation station as the governing gauge.
    """
    subbasin_groups = group_by_subbasin(STATION_REGISTRY)
    governing_gages = {}

    for subbasin, stations in subbasin_groups.items():
        # Compute 90-hour cumulative precipitation for each candidate station
        cumulatives = {st.station_id: np.sum(station_precip[st.station_id]) for st in stations}
        
        # Select station with maximum precipitation
        governing_id = max(cumulatives, key=cumulatives.get)
        governing_gages[subbasin] = {
            "selected_station": governing_id,
            "cumulative_mm": cumulatives[governing_id],
            "hyetograph": station_precip[governing_id]
        }
    return governing_gages
```

### Why Conservative Selection?
If station A in subbasin $S_6$ (Karanjphen) receives $45\text{ mm}$ while station B (Gaganbawda) receives $120\text{ mm}$ due to cloud bursts over the ghats ridge, using the arithmetic mean would dilute the flood wave and under-predict peak discharge. The conservative selection guarantees that emergency authorities are never blindsided by localized severe rainfall events.

---

## 3. Spatial Nearest-Neighbor Fallback Router

For ungauged subbasins or when a primary telemetry gauge drops offline, the system calculates geographic distance to all operational stations:

$$d_i = \sqrt{ (\Delta\lambda_i \cdot \cos\bar{\phi})^2 + \Delta\phi_i^2 } \cdot R_{earth}$$

The station with minimum distance $d_i$ is dynamically assigned as the fallback input to the HEC-HMS boundary condition.
