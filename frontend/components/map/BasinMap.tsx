"use client";
// frontend/components/map/BasinMap.tsx
import { useState, useMemo } from "react";
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Polyline, Popup, Tooltip, LayersControl } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// ─── Panchganga / Kolhapur Catchment Watershed Polygons ───────────────────────
const SUBBASIN_GEOJSON: GeoJSON.FeatureCollection = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: {
        id: "SUB_GHATS_UPPER",
        name: "Upper Ghats & Kasari Watershed",
        area_km2: 385.2,
        mean_cn: 72,
        key_stations: "Karanjphen, Kotoli",
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [73.84, 16.74],
            [73.88, 16.84],
            [74.02, 16.86],
            [74.14, 16.82],
            [74.10, 16.72],
            [73.98, 16.70],
            [73.84, 16.74],
          ],
        ],
      },
    },
    {
      type: "Feature",
      properties: {
        id: "SUB_BHOGAWATI_MID",
        name: "Mid Bhogawati & Kumbhi Valley",
        area_km2: 442.8,
        mean_cn: 78,
        key_stations: "Salwan, Sangarul, Beed",
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [73.92, 16.58],
            [73.95, 16.70],
            [74.10, 16.72],
            [74.20, 16.70],
            [74.18, 16.58],
            [74.06, 16.54],
            [73.92, 16.58],
          ],
        ],
      },
    },
    {
      type: "Feature",
      properties: {
        id: "SUB_RADHANAGARI_DAM",
        name: "Radhanagari Dam Upper Basin",
        area_km2: 320.5,
        mean_cn: 69,
        key_stations: "Radhanagari",
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [73.90, 16.35],
            [73.92, 16.58],
            [74.06, 16.54],
            [74.12, 16.42],
            [74.05, 16.32],
            [73.90, 16.35],
          ],
        ],
      },
    },
    {
      type: "Feature",
      properties: {
        id: "SUB_PANCHGANGA_LOWER",
        name: "Lower Panchganga Estuary & Karveer Plain",
        area_km2: 295.0,
        mean_cn: 84,
        key_stations: "Karveer",
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [74.18, 16.58],
            [74.20, 16.70],
            [74.14, 16.82],
            [74.32, 16.80],
            [74.35, 16.66],
            [74.26, 16.56],
            [74.18, 16.58],
          ],
        ],
      },
    },
  ],
};



// User's Exact Precipitation Stations
export const GAUGE_STATIONS = [
  { id: "KARANJPHEN", name: "Karanjphen", lat: 16.7850973, lon: 73.9036487, subbasin: "SUB_GHATS_UPPER", elevation: "640m", fc90: 55.4 },
  { id: "RADHANAGARI", name: "Radhanagari", lat: 16.41021, lon: 73.9971822, subbasin: "SUB_RADHANAGARI_DAM", elevation: "615m", fc90: 38.1 },
  { id: "SALWAN", name: "Salwan", lat: 16.671222, lon: 73.973457, subbasin: "SUB_BHOGAWATI_MID", elevation: "595m", fc90: 25.5 },
  { id: "KOTOLI", name: "Kotoli", lat: 16.7820174, lon: 74.0518705, subbasin: "SUB_KASARI_UPPER", elevation: "585m", fc90: 11.5 },
  { id: "BEED", name: "Beed", lat: 16.647984, lon: 74.1288964, subbasin: "SUB_TULSHI_CONFLUENCE", elevation: "565m", fc90: 9.9 },
  { id: "SANGARUL", name: "Sangarul", lat: 16.6841962, lon: 74.0931627, subbasin: "SUB_KUMBHI_MID", elevation: "572m", fc90: 9.7 },
  { id: "KARVEER", name: "Karveer", lat: 16.706369, lon: 74.2481772, subbasin: "SUB_PANCHGANGA_LOWER", elevation: "550m", fc90: 6.2 },
];

const BRIDGES = [
  {
    id: "SHIVAJI_BRIDGE",
    name: "Shivaji Bridge (Panchganga Ghat)",
    lat: 16.708917,
    lon: 74.219278,
    dms: "16°42'32.1\" N, 74°13'09.4\" E",
    warning: "5.50m",
    danger: "6.80m",
    desc: "Kolhapur-Ratnagiri route stone masonry bridge near Brahmapuri site",
  },
  {
    id: "RAJARAM_BRIDGE",
    name: "Rajaram K.T. Weir (Kasba Bawada)",
    lat: 16.736167,
    lon: 74.235889,
    dms: "16°44'10.2\" N, 74°14'09.2\" E",
    warning: "5.20m",
    danger: "6.50m",
    desc: "Primary Panchganga flood & water-level monitoring barrage",
  },
];

function getIntensityColor(mm: number): { fill: string; stroke: string } {
  if (mm >= 40) return { fill: "#EF4444", stroke: "#B91C1C" };
  if (mm >= 20) return { fill: "#F59E0B", stroke: "#D97706" };
  if (mm >= 10) return { fill: "#FBBF24", stroke: "#B45309" };
  if (mm >= 5)  return { fill: "#38BDF8", stroke: "#0284C7" };
  return { fill: "#E2E8F0", stroke: "#94A3B8" };
}

export default function BasinMap({
  subbasins,
  ecmwf = {},
  stations = [],
  selectedStationId = "KARANJPHEN",
  onSelectStation,
}: {
  subbasins: string[];
  ecmwf?: Record<string, any[]>;
  stations?: any[];
  selectedStationId?: string;
  onSelectStation?: (stationId: string) => void;
}) {
  const [selectedSub, setSelectedSub] = useState<string | null>(null);
  const CENTER: [number, number] = [16.65, 74.12];

  function getSubRainfall(subId: string) {
    const matchedStation = GAUGE_STATIONS.find((g) => g.subbasin === subId);
    return matchedStation?.fc90 ?? 25.0;
  }

  return (
    <div className="relative w-full h-[450px] rounded-xl overflow-hidden border border-slate-200 shadow-xs bg-white z-0">
      {/* Header Overlay */}
      <div className="absolute top-3 left-14 z-[1000] bg-white/95 backdrop-blur-md px-3.5 py-2 rounded-lg border border-slate-200 shadow-xs text-xs pointer-events-auto">
        <div className="font-bold text-slate-900 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-sky-500 animate-ping" />
          Panchganga Basin & Raingauge Stations
        </div>
        <div className="text-[11px] text-slate-500 font-medium mt-0.5">
          Click any station marker to view 90-day logged &amp; 90-hour forecast widget
        </div>
      </div>

      {/* Floating Legend */}
      <div className="absolute bottom-3 right-3 z-[1000] bg-white/95 backdrop-blur-md px-3 py-2 rounded-lg border border-slate-200 shadow-xs text-[10px] pointer-events-auto">
        <div className="font-bold text-slate-700 uppercase tracking-wider mb-1.5">90-hr Precipitation</div>
        <div className="flex flex-col gap-1 text-slate-600 font-medium">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2.5 rounded-xs bg-red-500 border border-red-700" />
            <span>&gt; 40 mm (Ghats Catchment)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2.5 rounded-xs bg-amber-500 border border-amber-600" />
            <span>20–40 mm (Mid Valley)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2.5 rounded-xs bg-sky-400 border border-sky-600" />
            <span>5–20 mm (Plains)</span>
          </div>
          <div className="flex items-center gap-1.5 mt-0.5 pt-1 border-t border-slate-100">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 border border-emerald-700" />
            <span>Open-Meteo v1 Station</span>
          </div>
        </div>
      </div>

      <MapContainer
        center={CENTER}
        zoom={10}
        scrollWheelZoom={false}
        className="w-full h-full z-0"
        zoomControl={true}
        attributionControl={true}
      >
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="OpenStreetMap">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="OpenTopoMap">
            <TileLayer
              attribution='Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
              url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Esri World Imagery">
            <TileLayer
              attribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="CartoDB Positron">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
            />
          </LayersControl.BaseLayer>
        </LayersControl>

        {/* Watershed Subbasin Polygons */}
        <GeoJSON
          key={`subbasins-${selectedSub}`}
          data={SUBBASIN_GEOJSON}
          style={(feature) => {
            const id = feature?.properties?.id;
            const cumVal = getSubRainfall(id);
            const { fill, stroke } = getIntensityColor(cumVal);
            const isSelected = selectedSub === id;
            return {
              fillColor: fill,
              fillOpacity: isSelected ? 0.65 : 0.38,
              color: isSelected ? "#0369A1" : stroke,
              weight: isSelected ? 3 : 2,
              dashArray: isSelected ? undefined : "4 4",
            };
          }}
          onEachFeature={(feature, layer) => {
            const props = feature.properties;
            const cumVal = getSubRainfall(props.id);

            layer.on({
              click: () => setSelectedSub(props.id),
            });

            layer.bindTooltip(
              `<div style="font-family: Inter, sans-serif; padding: 2px;">
                <div style="font-weight: 700; color: #0369A1;">${props.name}</div>
                <div style="font-size: 11px; color: #475569;">Area: <b>${props.area_km2} km²</b> · Mean CN: <b>${props.mean_cn}</b></div>
                <div style="font-size: 11px; color: #0F172A; margin-top: 2px;">90-hr Forecast: <b style="color: #0284C7;">${cumVal.toFixed(1)} mm</b></div>
                <div style="font-size: 11px; color: #059669;">Key Stations: <b>${props.key_stations}</b></div>
              </div>`,
              { direction: "top", sticky: true, opacity: 0.95 }
            );
          }}
        />



        {/* User's Rain Gauge Stations */}
        {GAUGE_STATIONS.map((g) => {
          const isSelected = selectedStationId === g.id;
          return (
            <CircleMarker
              key={g.id}
              center={[g.lat, g.lon]}
              radius={isSelected ? 11 : 8}
              pathOptions={{
                color: isSelected ? "#0284C7" : "#059669",
                fillColor: isSelected ? "#38BDF8" : "#10B981",
                fillOpacity: 1,
                weight: isSelected ? 4 : 2,
              }}
              eventHandlers={{
                click: () => {
                  if (onSelectStation) onSelectStation(g.id);
                },
              }}
            >
              <Popup>
                <div style={{ fontFamily: "Inter, sans-serif", minWidth: 180, padding: 4 }}>
                  <div className="flex items-center justify-between font-bold text-slate-900 border-b border-slate-100 pb-1">
                    <span>{g.name} Station</span>
                    <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded font-bold">
                      CLICKED
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-600 mt-2 space-y-1">
                    <div>Subbasin: <b className="text-sky-700">{g.subbasin}</b></div>
                    <div>Coordinates: <span className="font-mono-code text-slate-700">{g.lat.toFixed(4)}°N, {g.lon.toFixed(4)}°E</span></div>
                    <div>Elevation: <b>{g.elevation}</b></div>
                    <div className="pt-1 border-t border-slate-100 text-slate-800 font-semibold">
                      90hr Forecast: <span className="text-sky-600 font-mono-code font-bold">{g.fc90.toFixed(1)} mm</span>
                    </div>
                  </div>
                </div>
              </Popup>
              <Tooltip direction="top" offset={[0, -8]} opacity={0.95}>
                <span className="font-mono-code text-[11px] font-bold">
                  {g.name} ({g.fc90}mm) {isSelected ? "★" : ""}
                </span>
              </Tooltip>
            </CircleMarker>
          );
        })}

        {/* CWC Bridge Flood Gauges */}
        {BRIDGES.map((b) => (
          <CircleMarker
            key={b.id}
            center={[b.lat, b.lon]}
            radius={9}
            pathOptions={{
              color: "#B91C1C",
              fillColor: "#EF4444",
              fillOpacity: 0.9,
              weight: 2.5,
            }}
          >
            <Tooltip permanent direction="bottom" offset={[0, 8]} opacity={0.95}>
              <span className="text-[10px] font-bold text-rose-700 bg-white px-1.5 py-0.5 rounded shadow-xs border border-rose-200">
                {b.name.replace(" (Kolhapur)", "").replace(" (Bawda)", "")}
              </span>
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
