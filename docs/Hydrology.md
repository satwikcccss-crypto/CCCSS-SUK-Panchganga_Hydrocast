# Panchganga Catchment Hydrology & Watershed Delineation

```
========================================================================================
             PANCHGANGA BASIN HYDROLOGICAL SYSTEM (2,140 KM² CATCHMENT)
========================================================================================

                 Western Ghats Sahyadri Ridge (High Elevation 600 - 1,000m)
               [ Kasari ]    [ Kumbhi ]    [ Tulsi ]    [ Bhogawati ]    [ Saraswati ]
                  (S6)          (S5)          (S4)          (S7)              (S2)
                    │             │             │             │                 │
                    ▼             ▼             ▼             ▼                 ▼
             ┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
             │ Subbasin S6 │ Subbasin S5 │ Subbasin S4 │ Subbasin S7 │ Subbasin S2 │
             │ Karanjphen  │   Salwan    │    Beed     │ Radhanagari │  Sangarul   │
             │ Area: 412km²│ Area: 285km²│ Area: 198km²│ Area: 510km²│ Area: 224km²│
             └──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┘
                    │             │             │             │             │
                    └─────────────┴─────────────┼─────────────┴─────────────┘
                                                ▼
                                    Prayag Chikhali Confluence
                                 (Official Formation of Panchganga)
                                                │
                                                ▼
                                        Subbasin S1 (Karvir)
                                     Kolhapur Urban Floodplain
                                                │
                                ┌───────────────┴───────────────┐
                                ▼                               ▼
                    [ Shivaji Maharaj Bridge ]         [ Rajaram K.T. Weir ]
                     (Historical Ghat Gauge)            (Hydraulic Control)
                                                │
                                                ▼
                                          Subbasin S9
                                  Confluence with Krishna River
                                          (Shirol / Narsobawadi)
```

<p align="center">
  <img src="./assets/panchganga_catchment_topology.svg" alt="Panchganga River Basin Topographical Hydrometric Network" width="100%" />
</p>

---

## 1. Physical Physiography of the Panchganga Basin

The Panchganga river is a major tributary of the Krishna river basin, draining an area of approximately **$2,140\text{ km}^2$** across Kolhapur district, Maharashtra.

### 1.1 The Five Sacred Tributaries
The river is formed at Prayag Chikhali by the confluence of five streams:
1. **Kasari River:** Originates near Dajipur / Gaganbawda ($S_6$), drains through rocky forested gorges.
2. **Kumbhi River:** Originates near Shengaon ($S_5$), fast-draining basaltic steep terrain.
3. **Tulsi River:** Originates near Dhamod ($S_4$), moderate agricultural valley.
4. **Bhogawati River:** The largest tributary, controlled upstream by Radhanagari Dam ($S_7$).
5. **Saraswati Stream:** Minor subterranean channel joining near Prayag ($S_2$).

---

## 2. Subbasin Delineation Parameters ($S_1$ to $S_9$)

The catchment is divided into nine hydrologically distinct subbasins based on 30-meter SRTM Digital Elevation Models (DEM):

```
+----+-------------------+------------+-----------+-----------+------------+------------+
| ID | Subbasin Name     | Area (km²) | CN (AMC-II| CN (AMC-III| Tc (Hours) | R (Hours)  |
+----+-------------------+------------+-----------+-----------+------------+------------+
| S1 | Karvir (Outlet)   | 145.2      | 78.0      | 89.2      | 6.5        | 8.2        |
| S2 | Sangarul (Tulsi)  | 224.8      | 74.5      | 87.1      | 7.2        | 9.4        |
| S3 | Kotoli (Kasari L.)| 168.4      | 76.0      | 88.0      | 8.0        | 10.5       |
| S4 | Beed (Tulsi Lower)| 198.6      | 75.0      | 87.4      | 9.1        | 11.8       |
| S5 | Salwan (Kumbhi)   | 285.4      | 72.0      | 85.3      | 11.4       | 14.2       |
| S6 | Karanjphen(Kasari)| 412.0      | 70.5      | 84.1      | 14.2       | 18.5       |
| S7 | Radhanagari(Bhog.)| 510.5      | 68.0      | 82.2      | 16.5       | 21.0       |
| S8 | Shiroli/K. Tarale | 115.0      | 77.0      | 88.6      | 5.8        | 7.1        |
| S9 | Kasaba Walawe     | 80.1       | 79.0      | 90.0      | 4.2        | 5.6        |
+----+-------------------+------------+-----------+-----------+------------+------------+
|    | TOTAL PANCHGANGA  | 2,140.0 km²|           |           |            |            |
+----+-------------------+------------+-----------+-----------+------------+------------+
```

---

## 3. SCS Curve Number Runoff Depth Mechanics

The physical runoff volume generation follows the United States Natural Resources Conservation Service (NRCS / SCS-CN) standard:

### 3.1 Potential Soil Retention
Given a calibrated Curve Number $CN$:

$$S_{ret} = \frac{25,400}{CN} - 254 \quad (\text{expressed in mm})$$

### 3.2 Initial Abstraction
The initial surface wetting, depression storage, and vegetative canopy interception prior to runoff:

$$I_a = 0.2 \cdot S_{ret}$$

*(For dense basaltic soil with monsoon pre-saturation, this can be dynamically lowered to $I_a = 0.05 \cdot S_{ret}$).*

### 3.3 Cumulative Runoff Equation
For any accumulated precipitation depth $P$:

$$Q_{cum} = \begin{cases} 
0 & \text{if } P \le I_a \\ 
\frac{(P - I_a)^2}{P - I_a + S_{ret}} & \text{if } P > I_a 
\end{cases}$$

### 3.4 Incremental Runoff Hyetograph
The excess rainfall generated in time step $\Delta t$ (hour $h$) is:

$$\Delta Q_{excess}[h] = Q_{cum}[h] - Q_{cum}[h-1]$$

---

## 4. Hydrograph Transformation: Clark Unit Hydrograph

To convert the rainfall-excess hyetograph into a river discharge hydrograph at the subbasin outlet, HydroCast utilizes the **Clark Unit Hydrograph method**:

```
        Excess Rain Hyetograph                     Clark Translation & Attenuation
             [ mm/hr ]                                     [ m³/s ]
                |                                             /\  Peak Runoff
                |                                            /  \
               ---       ====== Convolution ======>         /    \
              |   |                                        /      \
            --|   |--                                    /          \
                                                        /            \_____ Baseflow
```

1. **Translation (Time-Area Routing):**
   Runoff is lagged to the outlet according to the dimensionless time-area curve:
   $$\frac{A_t}{A} = \begin{cases} 
   1.414 \cdot \left(\frac{t}{T_c}\right)^{1.5} & \text{for } 0 \le t \le 0.5 T_c \\ 
   1 - 1.414 \cdot \left(1 - \frac{t}{T_c}\right)^{1.5} & \text{for } 0.5 T_c < t \le T_c 
   \end{cases}$$
   Where $T_c$ is the Time of Concentration.

2. **Attenuation (Linear Reservoir Routing):**
   Storage effects in channels and valley wetlands are modeled through a linear reservoir with storage coefficient $R$:
   $$S = R \cdot O$$
   Using finite differences:
   $$O_2 = C_A \cdot I_2 + C_B \cdot I_1 + C_C \cdot O_1$$
   Where routing coefficients are derived from $\Delta t$ and $R$:
   $$C_A = C_B = \frac{\Delta t}{2R + \Delta t}, \quad C_C = \frac{2R - \Delta t}{2R + \Delta t}$$

---

## 5. Monsoon Baseflow Separation & Physical Groundwater Release

The Panchganga river maintains a continuous physical baseflow during the June–September Southwest Monsoon generated by unconfined groundwater aquifers in the Sahyadri lateritic formations.

In [`runner.py`](file:///e:/hydrocast_complete/src/hms/runner.py):
1. **Physical Live Baseflow:** Extracted directly from live RTDAS water level telemetry:
   $$Q_{base} = \text{convert\_stage\_to\_discharge\_manning}(h_{live}, \text{"SHIVAJI\_BRIDGE"})$$
   At current normal monsoon stages ($532.63 - 533.28\text{ m MSL}$), $Q_{base} \approx 91.1 - 109.2\text{ m}^3/s$.
2. **Total River Hydrograph:**
   $$Q_{total}(t) = Q_{base} + \sum_{i=1}^{9} Q_{surface, i}(t)$$

This ensures that even during dry weather breaks between monsoon storms, river discharge never collapses to artificial zero or non-physical single-digit values.
