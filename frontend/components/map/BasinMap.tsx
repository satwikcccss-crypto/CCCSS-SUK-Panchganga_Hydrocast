"use client";
// frontend/components/map/BasinMap.tsx
import { useState, useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  CircleMarker,
  Popup,
  Tooltip,
  LayersControl,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Calibrated HEC-HMS Precipitation Stations
export const GAUGE_STATIONS = [
  { id: "KARANJPHEN", name: "Karanjphen", lat: 16.7850973, lon: 73.9036487, subbasin: "S6", elevation: "640m", fc90: 55.4 },
  { id: "RADHANAGARI", name: "Radhanagari", lat: 16.41021, lon: 73.9971822, subbasin: "S7", elevation: "615m", fc90: 38.1 },
  { id: "SALWAN", name: "Salwan", lat: 16.6712, lon: 73.9735, subbasin: "S5", elevation: "595m", fc90: 25.5 },
  { id: "KOTOLI", name: "Kotoli", lat: 16.7820174, lon: 74.0518705, subbasin: "S3", elevation: "585m", fc90: 11.5 },
  { id: "BEED", name: "Beed", lat: 16.647984, lon: 74.1288964, subbasin: "S4", elevation: "565m", fc90: 9.9 },
  { id: "SANGARUL", name: "Sangarul", lat: 16.6841962, lon: 74.0931627, subbasin: "S2", elevation: "572m", fc90: 9.7 },
  { id: "KARVIR", name: "Karvir", lat: 16.706369, lon: 74.2481772, subbasin: "S1", elevation: "550m", fc90: 6.2 },
];

const BRIDGES = [
  {
    id: "SHIVAJI_BRIDGE",
    name: "Shivaji Bridge (Panchganga Ghat)",
    lat: 16.708917,
    lon: 74.219278,
    dms: "16°42'32.1\" N, 74°13'09.4\" E",
    warning: "537.50m MSL (5.5m Stage)",
    danger: "538.50m MSL (6.8m Stage)",
    desc: "Kolhapur-Ratnagiri route stone masonry bridge near Brahmapuri site",
  },
  {
    id: "RAJARAM_BRIDGE",
    name: "Rajaram K.T. Weir (Kasba Bawada)",
    lat: 16.736167,
    lon: 74.235889,
    dms: "16°44'10.2\" N, 74°14'09.2\" E",
    warning: "537.00m MSL (5.2m Stage)",
    danger: "538.30m MSL (6.5m Stage)",
    desc: "Primary Panchganga flood & water-level monitoring barrage (Gage 1)",
  },
];

function getIntensityColor(mm: number): { fill: string; stroke: string } {
  if (mm >= 40) return { fill: "#EF4444", stroke: "#B91C1C" };
  if (mm >= 20) return { fill: "#F59E0B", stroke: "#D97706" };
  if (mm >= 10) return { fill: "#FBBF24", stroke: "#B45309" };
  if (mm >= 5)  return { fill: "#38BDF8", stroke: "#0284C7" };
  return { fill: "#BAE6FD", stroke: "#0284C7" };
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
  const [subbasinGeo, setSubbasinGeo] = useState<any>(null);
  const [riverGeo, setRiverGeo] = useState<any>(null);

  const CENTER: [number, number] = [16.65, 74.12];

  useEffect(() => {
    fetch("/data/panchganga_subbasins.geojson")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setSubbasinGeo(data);
      })
      .catch(() => {});

    fetch("/data/panchganga_rivers.geojson")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setRiverGeo(data);
      })
      .catch(() => {});
  }, []);

  function getSubRainfall(subId: string) {
    const matchedStation = GAUGE_STATIONS.find((g) => g.subbasin === subId || g.id === subId);
    return matchedStation?.fc90 ?? 25.0;
  }

  return (
    <div className="relative w-full h-[520px] rounded-xl overflow-hidden border border-slate-200 shadow-xs bg-slate-900 z-0">
      {/* Header Overlay */}
      <div className="absolute top-3 left-14 z-[1000] bg-white/95 backdrop-blur-md px-3.5 py-2 rounded-lg border border-slate-200 shadow-xs text-xs pointer-events-auto">
        <div className="font-bold text-slate-900 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-sky-500 animate-ping" />
          Panchganga Basin Shapefile &amp; River Network Model
        </div>
        <div className="text-[11px] text-slate-500 font-medium mt-0.5">
          Exact HEC-HMS Subbasins (S1–S8) &amp; Hydrodynamic Stream Flowpaths
        </div>
      </div>

      {/* Floating Legend */}
      <div className="absolute bottom-3 right-3 z-[1000] bg-white/95 backdrop-blur-md px-3 py-2 rounded-lg border border-slate-200 shadow-xs text-[10px] pointer-events-auto">
        <div className="font-bold text-slate-700 uppercase tracking-wider mb-1.5">Map Layers</div>
        <div className="flex flex-col gap-1 text-slate-600 font-medium">
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-1 bg-sky-500 rounded-full" />
            <span>Panchganga River Network</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2.5 rounded-xs bg-sky-200 border border-sky-600" />
            <span>Calibrated Subbasins (S1–S8)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 border border-emerald-700" />
            <span>HEC-HMS Rain Gages (7)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 border border-rose-700" />
            <span>CWC Bridge Gauges (2)</span>
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
          <LayersControl.BaseLayer name="Esri Topographic">
            <TileLayer
              attribution='Tiles &copy; Esri'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Esri Satellite">
            <TileLayer
              attribution='Tiles &copy; Esri'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="CartoDB Dark">
            <TileLayer
              attribution='&copy; CARTO'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
          </LayersControl.BaseLayer>
        </LayersControl>

        {/* Watershed Subbasin Polygons from GeoJSON */}
        {subbasinGeo && (
          <GeoJSON
            key={`subbasins-${selectedSub}`}
            data={subbasinGeo}
            style={(feature) => {
              const name = feature?.properties?.name || "Subbasin";
              const cumVal = getSubRainfall(name);
              const { fill, stroke } = getIntensityColor(cumVal);
              const isSelected = selectedSub === name;
              return {
                fillColor: fill,
                fillOpacity: isSelected ? 0.60 : 0.30,
                color: isSelected ? "#0369A1" : stroke,
                weight: isSelected ? 3 : 1.5,
              };
            }}
            onEachFeature={(feature, layer) => {
              const props = feature.properties || {};
              const name = props.name || "Subbasin";
              const cumVal = getSubRainfall(name);

              layer.on({
                click: () => setSelectedSub(name),
              });

              layer.bindTooltip(
                `<div style="font-family: Inter, sans-serif; padding: 2px;">
                  <div style="font-weight: 700; color: #0369A1;">Subbasin ${name}</div>
                  <div style="font-size: 11px; color: #475569;">Basin Slope: <b>${(props.basin_slo || 0).toFixed(3)}</b> · Relief: <b>${props.basin_rel || 0}m</b></div>
                  <div style="font-size: 11px; color: #0F172A; margin-top: 2px;">90-hr Forecast: <b style="color: #0284C7;">${cumVal.toFixed(1)} mm</b></div>
                </div>`,
                { direction: "top", sticky: true, opacity: 0.95 }
              );
            }}
          />
        )}

        {/* Panchganga River Flowpaths from GeoJSON */}
        {riverGeo && (
          <GeoJSON
            key="rivers-geojson"
            data={riverGeo}
            style={() => ({
              color: "#0284C7",
              weight: 3,
              opacity: 0.9,
            })}
            onEachFeature={(feature, layer) => {
              const props = feature.properties || {};
              layer.bindTooltip(
                `<div style="font-family: Inter, sans-serif; padding: 2px;">
                  <div style="font-weight: 700; color: #0284C7;">Panchganga Reach (${props.subbasin || "Main Channel"})</div>
                  <div style="font-size: 10px; color: #475569;">Flowpath Stream Segment</div>
                </div>`,
                { direction: "top", sticky: true, opacity: 0.95 }
              );
            }}
          />
        )}

        {/* Calibrated HEC-HMS Rain Gauge Stations */}
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
                      HMS GAGE
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-600 mt-2 space-y-1">
                    <div>Subbasin: <b className="text-sky-700">{g.subbasin}</b></div>
                    <div>Coordinates: <span className="font-mono text-slate-700">{g.lat.toFixed(4)}°N, {g.lon.toFixed(4)}°E</span></div>
                    <div>Elevation: <b>{g.elevation}</b></div>
                    <div className="pt-1 border-t border-slate-100 text-slate-800 font-semibold">
                      90hr Forecast: <span className="text-sky-600 font-mono font-bold">{g.fc90.toFixed(1)} mm</span>
                    </div>
                  </div>
                </div>
              </Popup>
              <Tooltip direction="top" offset={[0, -8]} opacity={0.95}>
                <span className="font-mono text-[11px] font-bold">
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
                {b.name.replace(" (Panchganga Ghat)", "").replace(" (Kasba Bawada)", "")}
              </span>
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
