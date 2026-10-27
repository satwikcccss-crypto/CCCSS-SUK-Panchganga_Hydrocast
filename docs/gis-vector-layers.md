# GIS Geospatial Data, Shapefiles & Subbasin Vector Layers


---

## Interactive diagram consoles

The console below is the rendered reference for this page: it carries the same structure, tier boundaries and failure branches that the prose describes.

<div class="hydrocast-diagram-card">
  <div class="hydrocast-diagram-header">
    <div class="hydrocast-diagram-title">
      <span class="hydrocast-diagram-badge">Interactive Console · Diagram 16</span>
      <strong>Repository Tree</strong>
    </div>
    <div class="hydrocast-diagram-actions">
      <a class="hydrocast-diagram-btn" href="../diagrams/16-repository-tree.html" target="_blank">Open Fullscreen ↗</a>
    </div>
  </div>
  <iframe class="hydrocast-diagram-frame" src="../diagrams/16-repository-tree.html?embed=1" title="Repository Tree Console"></iframe>
</div>

---

## 1. Directory Structure & File Manifest

The geospatial repository contains both raw QGIS spatial layers and web-optimized GeoJSON files:


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

Each layer carries only the properties the pipeline reads. Subbasin polygons carry
`subbasin_id` (S1–S9), `area_km2`, `curve_number`, `lag_hours` and the Thiessen
gauge list; reach centrelines carry `reach_id` (R1–R5), `length_km`, `slope`,
`muskingum_k_hours` and `muskingum_x`. Anything else — labels, styling, survey
notes — lives in the QGIS project and is not shipped to the runtime.

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
