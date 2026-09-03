# GIS Geospatial Data, Shapefiles & Subbasin Vector Layers

```
========================================================================================
             PANCHGANGA BASIN GIS SHAPEFILES & VECTOR GEOJSON LAYERS
========================================================================================

                 [ 30m SRTM DEM Elevation Grid ]
                               │
               D8 Flow Direction & Flow Accumulation
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
 [ Panchganga_RJKT_RB.geojson ]        [ Panchganga_RJKT_Flowpath.geojson ]
 Basin Outer Boundary & Subbasins     Vector Stream Network & Flowpaths
 - Catchment Area: 2,140 km²           - Strahler Stream Orders (1 to 5)
 - S1 to S9 Subbasin Polygons          - Kasari, Kumbhi, Tulsi, Bhogawati,
 - Attributes: Area, Slope, CN         - Main Stem Panchganga Channel
            │                                     │
            └──────────────────┬──────────────────┘
                               ▼
               Web-Ready Projection Transform
                     (UTM 43N ──> EPSG:4326)
                               │
                               ▼
            [ Leaflet Web GIS Interactive Dashboard Map ]
```

---

## 1. Directory Structure & File Manifest

The geospatial repository contains both raw QGIS spatial layers and web-optimized GeoJSON files:

```
system/
 ├── data/
 │    └── Shapefiles_Panchganga basin/
 │         ├── Panchganga_RJKT_RB.geojson        # Watershed boundary & subbasins (1.07 MB)
 │         ├── Panchganga_RJKT_RB.qmd            # QGIS metadata descriptor
 │         ├── Panchganga_RJKT_Flowpath.geojson  # High-resolution river centerlines (749 KB)
 │         └── Panchganga_RJKT_Flowpath.qmd      # QGIS stream layer metadata
 └── frontend/
      └── public/
           └── data/
                ├── panchganga_subbasins.geojson # Leaflet-optimized polygon layer
                └── panchganga_rivers.geojson    # Leaflet-optimized stream network
```

---

## 2. Coordinate Reference Systems (CRS) Specification

Hydrologic vector processing uses dual spatial reference frames:

1. **Analytical Hydrologic Projected CRS: `EPSG:32643` (UTM Zone 43N)**
   - **Units:** Meters ($m$)
   - **Spheroid:** WGS 84
   - **Usage:** Used in GIS preprocessing for exact planimetric area calculation ($\text{Area } A = \iint dx\,dy$), channel length measurement ($L$), and reach slope determination ($\Delta z / \Delta L$).
2. **Web Map Geographic CRS: `EPSG:4326` (WGS 84 Lat/Long)**
   - **Units:** Decimal degrees ($^\circ$)
   - **Usage:** Used for client-side Leaflet rendering, Open-Meteo coordinate queries, and GeoJSON serialization.

---

## 3. GeoJSON Feature Property Schemas

### 3.1 Subbasin Boundary Polygons (`Panchganga_RJKT_RB.geojson`)

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[74.093, 16.684], [74.128, 16.647], ...]]
  },
  "properties": {
    "Subbasin": "S2",
    "Name": "Sangarul (Tulsi Upper)",
    "Area_km2": 224.8,
    "Mean_Elev_m": 572.0,
    "CN_AMC2": 74.5,
    "Tc_hours": 7.2,
    "R_hours": 9.4,
    "Primary_Gage": "SANGARUL"
  }
}
```

### 3.2 River Network Centerlines (`Panchganga_RJKT_Flowpath.geojson`)

```json
{
  "type": "Feature",
  "geometry": {
    "type": "LineString",
    "coordinates": [[[73.834, 16.546], [73.903, 16.785], ...]]
  },
  "properties": {
    "Reach_ID": "R_KASARI_01",
    "Stream_Name": "Kasari River",
    "Strahler_Order": 4,
    "Length_km": 42.6,
    "Bed_Slope_m_per_m": 0.0034,
    "Manning_n": 0.040
  }
}
```

---

## 4. Leaflet Web GIS Integration

The interactive map in `OverviewPanel.tsx` visualizes these spatial layers:
- **Subbasin Choropleth:** Color-coded by cumulative 90-hour rainfall intensity (green: $< 30\text{ mm}$, amber: $30-75\text{ mm}$, purple: $> 75\text{ mm}$).
- **River Flowpaths:** Dynamic blue vector lines with thickness proportional to Strahler stream order.
- **Sensor Pin Overlays:** Interactive markers at Shivaji Bridge and Rajaram Weir displaying live water level ($m$ MSL), alert badges, and historical flood marks.
