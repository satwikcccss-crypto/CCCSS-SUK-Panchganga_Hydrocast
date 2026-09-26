# Panchganga Basin Hydrology & Watershed Delineation

```
====================================================================================================
                        PANCHGANGA RIVER BASIN PHYSIOGRAPHIC DELINEATION
====================================================================================================

      Western Ghats Crestline (Elevation: 900m - 1100m MSL)
     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      [S6: Gaganbawda]       [S7: Garivade]       [S5: Padasali]       [S9: Radhanagari]
      (227.72 km2)           (195.39 km2)         (106.39 km2)         (366.97 km2)
           |                      |                    |                    |
       Kumbhi River          Dhamani River        Tulashi River       Bhogavati River
           \                      /                    |                    |
            \                    /                     v                    |
             v                  v                 [S8: Beed]                 |
           Confluence @ Bahireshwar              (177.44 km2)               |
                      |                                |                    |
                      v                                v                    v
               Kumbhi-Dhamani                   Tulashi-Bhogavati Confluence @ Bid
                      \                                /
                       \                              /
                        v                            v
                      Prayag Chikhali Confluence (Sacred Sangam)
                      Elevation: ~536.0m MSL | Kasari River meets Bhogavati
                                       |
                                       v
                             [PANCHGANGA TRUNK RIVER]
                                       |
                       +---------------+---------------+
                       |                               |
                       v                               v
             [S3: Kotoli Subbasin]           [S2: Sangarul Subbasin]
                 (261.32 km2)                    (153.77 km2)
                       \                               /
                        \                             /
                         v                           v
                      [S1: Karveer Local Watershed (86.21 km2)]
                                       |
                   ==========================================
                   [ CHHATRAPATI SHIVAJI MAHARAJ BRIDGE ]
                   Chainage: 6+257 | IoT Ultrasonic Sensor
                   ==========================================
                                       |
                               3,858 m River Reach
                               Bed Slope: 1:4641
                                       v
                   ==========================================
                   [ RAJARAM K.T. WEIR (KASBA BAWADA) ]
                   Chainage: 10+115 | Basin Model Sink Node
                   ==========================================
```

---

## 1. Geographic & Physiographic Setting

The **Panchganga River** is a major tributary of the Krishna River system in Maharashtra, India. It drains a total basin area of **1,837.213 km²** upstream of the Rajaram K.T. Weir at Kolhapur.

### 1.1 Origin & Tributary Network
The Panchganga is formed by the confluence of five sacred rivers:
1. **Bhogavati River:** Originates near Asane (Dajipur) in the Western Ghats. Impounded by the Radhanagari Dam (Crest elevation: 553.90 m MSL). Flows ~40 km northwards to confluence with the Tulashi at Bid.
2. **Tulashi River:** Originates in the southwestern ranges, draining Subbasin S8 (Beed).
3. **Kumbhi River:** Originates in the heavy-rainfall Gaganbawda ridge (Subbasin S6).
4. **Dhamani River:** Originates near Garivade (Subbasin S7), joining the Kumbhi at Bahireshwar.
5. **Kasari River:** Originates in the northwestern ghats near Karanjphen (Subbasin S4) and Padasali (Subbasin S5). Meets the combined Bhogavati-Tulashi-Kumbhi-Dhamani system at **Prayag Chikhali (Sacred Sangam)**.

From Prayag Chikhali onward, the unified trunk channel flows eastwards as the **Panchganga River**, through Kolhapur City, across Shivaji Bridge and Rajaram KT Weir, ultimately discharging into the Krishna River at Narsobawadi (Shirol).

---

## 2. Catchment Morphometry & Subbasin Delineation

HydroCast partitions the watershed into **9 Hydrologic Response Units (HRUs)** corresponding to USACE HEC-HMS delineated subbasins (`Basin_1.basin`):

```
+----+-------------+----------------+-----------+-----------+------------+------------+
| ID | Subbasin    | Principal      | Area      | Area      | Mean Basin | Base Lag   |
|    | Identifier  | Watercourse    | (km²)     | Ratio (%) | Slope (m/m)| Time (min) |
+----+-------------+----------------+-----------+-----------+------------+------------+
| S1 | Karveer     | Panchganga Trk |   86.213  |   4.69%   |  0.0085    |   2,152.0  |
| S2 | Sangarul    | Lower Bhogavati|  153.770  |   8.37%   |  0.0120    |   3,154.3  |
| S3 | Kotoli      | Lower Kasari   |  261.320  |  14.22%   |  0.0145    |   3,997.7  |
| S4 | Karanjphen  | Upper Kasari   |  262.000  |  14.26%   |  0.0210    |   3,115.5  |
| S5 | Padasali    | Kasari Trib    |  106.390  |   5.79%   |  0.0195    |   2,117.1  |
| S6 | Gaganbawda  | Kumbhi River   |  227.720  |  12.39%   |  0.0280    |   3,318.1  |
| S7 | Garivade    | Dhamani River  |  195.390  |  10.64%   |  0.0225    |   3,362.3  |
| S8 | Beed        | Tulashi River  |  177.440  |   9.66%   |  0.0185    |   3,387.1  |
| S9 | Radhanagari | Bhogavati Head |  366.970  |  19.97%   |  0.0310    |   5,199.0  |
+----+-------------+----------------+-----------+-----------+------------+------------+
| TOTAL            | Entire Basin   | 1,837.213 |  100.0%   |  0.0195    |      —     |
+----+-------------+----------------+-----------+-----------+------------+------------+
```

---

## 3. Hydro-Meteorological Gauge Network

Precipitation is ingested every 6 hours from the **ECMWF 9km High-Resolution IFS model** across **18 geo-referenced gauge locations**, organized into a primary and fail-safe alternate network:

```
                          18-STATION GAUGING NETWORK MATRIX
+----+--------------------+---------+----------+-----------+------------+------------+
| No | Station Name       | Type    | Subbasin | Latitude  | Longitude  | Elev (m)   |
+----+--------------------+---------+----------+-----------+------------+------------+
| 01 | Karveer (Kolhapur) | Primary | S1       | 16.6946°N | 74.2235°E  | 545.0 m    |
| 02 | Sangarul           | Primary | S2       | 16.6120°N | 74.1560°E  | 552.0 m    |
| 03 | Kotoli             | Primary | S3       | 16.7820°N | 74.1030°E  | 568.0 m    |
| 04 | Karanjphen         | Primary | S4       | 16.8250°N | 73.9560°E  | 610.0 m    |
| 05 | Padasali           | Primary | S5       | 16.7450°N | 73.9120°E  | 625.0 m    |
| 06 | Gaganbawda         | Primary | S6       | 16.5420°N | 73.8290°E  | 640.0 m    |
| 07 | Radhanagari Dam    | Primary | S9       | 16.4180°N | 73.9980°E  | 562.0 m    |
| 08 | Garivade           | Altern. | S7       | 16.5120°N | 73.9450°E  | 605.0 m    |
| 09 | Beed               | Altern. | S8       | 16.6340°N | 74.0560°E  | 558.0 m    |
| 10 | Kale               | Altern. | S3       | 16.7410°N | 74.1850°E  | 550.0 m    |
| 11 | Bahireshwar        | Altern. | S6       | 16.5920°N | 73.9210°E  | 575.0 m    |
| 12 | Prayag Chikhali    | Altern. | S1       | 16.7210°N | 74.1890°E  | 542.0 m    |
| 13 | Kasba Bawada       | Altern. | S1       | 16.7360°N | 74.2350°E  | 538.0 m    |
| 14 | Shirol             | Altern. | S1       | 16.7280°N | 74.5980°E  | 528.0 m    |
| 15 | Dajipur (Bison)    | Altern. | S9       | 16.3680°N | 73.8820°E  | 710.0 m    |
| 16 | Panhala (Fort)     | Altern. | S3       | 16.8120°N | 74.1120°E  | 820.0 m    |
| 17 | Shahuwadi          | Altern. | S4       | 16.9120°N | 73.9450°E  | 630.0 m    |
| 18 | Kagal              | Altern. | S8       | 16.5780°N | 74.3120°E  | 555.0 m    |
+----+--------------------+---------+----------+-----------+------------+------------+
```

---

## 4. Soil Retention & Infiltration Characteristics

Catchment soils are derived from Cretaceous-Eocene basaltic lava flows (**Deccan Traps**). The upper ridge subbasins (S4, S5, S6, S7, S9) are characterized by shallow reddish-brown lateritic clay loams with high initial permeability but rapid saturation, whereas the lower valleys (S1, S2, S3) are deep black cotton soils (Vertisols) with high clay content and low hydraulic conductivity.

```
       SOIL HYDRAULIC RETENTION CURVE (SCS-CN)
    Retention S (mm)
     180 +
         |   * S5: Padasali (CN=60.97, S=162.7mm)
     160 |     * S7: Garivade (CN=61.28, S=160.5mm)
         |       * S6: Gaganbawda (CN=61.78, S=157.1mm)
     140 |         * S4: Karanjphen (CN=61.89, S=156.4mm)
         |             * S9: Radhanagari (CN=64.31, S=140.7mm)
     120 |               * S3: Kotoli (CN=64.82, S=137.6mm)
         |                   * S2: Sangarul (CN=65.74, S=132.3mm)
     100 |                     * S8: Beed (CN=65.76, S=132.2mm)
         |
      80 |                                * S1: Karveer (CN=74.85, S=85.3mm)
         +---+-----+-----+-----+-----+-----+-----+-----+-----+-----+
            55    60    65    70    75    80    85    90    95   100  Curve Number (CN)
```
