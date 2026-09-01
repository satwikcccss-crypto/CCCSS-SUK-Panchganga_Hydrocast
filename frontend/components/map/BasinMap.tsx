"use client";
// frontend/components/map/BasinMap.tsx
import { useState, useEffect, useMemo } from "react";
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

// Full List of Primary and Alternate Stations across S1–S9
export const ALL_GAUGE_STATIONS = [
  // S1
  { id: "KARVIR", name: "Karvir", subbasin: "S1", lon: 74.2481772, lat: 16.706369, isPrimary: true, elevation: "550m", fc90: 6.2 },

  // S2
  { id: "SANGARUL", name: "Sangarul", subbasin: "S2", lon: 74.0931627, lat: 16.6841962, isPrimary: true, elevation: "572m", fc90: 9.7 },
  { id: "BALINGA", name: "Balinga (Alt)", subbasin: "S2", lon: 74.17031, lat: 16.6878443, isPrimary: false, elevation: "560m", fc90: 8.4 },
  { id: "KALE", name: "Kale (Alt)", subbasin: "S2", lon: 74.0564499, lat: 16.7228087, isPrimary: false, elevation: "580m", fc90: 12.1 },

  // S3
  { id: "KOTOLI", name: "Kotoli", subbasin: "S3", lon: 74.0518705, lat: 16.7820174, isPrimary: true, elevation: "585m", fc90: 11.5 },
  { id: "BAJAR_BHOGAON", name: "Bajar Bhogaon (Alt)", subbasin: "S3", lon: 74.1107824, lat: 16.8086769, isPrimary: false, elevation: "590m", fc90: 14.8 },
  { id: "PADAL", name: "Padal (Alt)", subbasin: "S3", lon: 74.115187, lat: 16.7446006, isPrimary: false, elevation: "575m", fc90: 10.2 },

  // S4
  { id: "BEED", name: "Beed", subbasin: "S4", lon: 74.1288964, lat: 16.647984, isPrimary: true, elevation: "565m", fc90: 9.9 },

  // S5
  { id: "SALWAN", name: "Salwan", subbasin: "S5", lon: 73.9735, lat: 16.6712, isPrimary: true, elevation: "595m", fc90: 25.5 },

  // S6
  { id: "KARANJPHEN", name: "Karanjphen", subbasin: "S6", lon: 73.9036487, lat: 16.7850973, isPrimary: true, elevation: "640m", fc90: 55.4 },
  { id: "GAGANBAWDA", name: "Gaganbawda (Alt)", subbasin: "S6", lon: 73.8346738, lat: 16.5469926, isPrimary: false, elevation: "680m", fc90: 68.2 },

  // S7
  { id: "RADHANAGARI", name: "Radhanagari", subbasin: "S7", lon: 73.9971822, lat: 16.41021, isPrimary: true, elevation: "615m", fc90: 38.1 },

  // S8
  { id: "SHIROLI_DHUMALA", name: "Shiroli-Dhumala", subbasin: "S8", lon: 74.1062828, lat: 16.6166768, isPrimary: false, elevation: "560m", fc90: 15.6 },

  // S9
  { id: "HALADI", name: "Haladi", subbasin: "S9", lon: 74.156292, lat: 16.5932632, isPrimary: false, elevation: "555m", fc90: 18.3 },
  { id: "RASHIWADE_BK", name: "Rashiwade Bk.", subbasin: "S9", lon: 74.1019728, lat: 16.5475641, isPrimary: false, elevation: "570m", fc90: 22.4 },
  { id: "AAVALI_BK", name: "Aavali Bk.", subbasin: "S9", lon: 74.0549812, lat: 16.481009, isPrimary: false, elevation: "585m", fc90: 29.8 },
  { id: "KASABA_TARALE", name: "Kasaba Tarale", subbasin: "S9", lon: 74.021589, lat: 16.4478876, isPrimary: false, elevation: "595m", fc90: 34.0 },
  { id: "KASABA_WALAWE", name: "Kasaba Walawe", subbasin: "S9", lon: 73.9971822, lat: 16.41021, isPrimary: false, elevation: "615m", fc90: 37.8 },
];

export const GAUGE_STATIONS = ALL_GAUGE_STATIONS;

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
    warning: "535.20m MSL (5.2m Stage)",
    danger: "536.50m MSL (6.5m Stage)",
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
  const [showAlternates, setShowAlternates] = useState<boolean>(true);

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
    const matchedStation = ALL_GAUGE_STATIONS.find((g) => g.subbasin === subId || g.id === subId);
    return matchedStation?.fc90 ?? 25.0;
  }

  const displayedStations = useMemo(() => {
    return showAlternates
      ? ALL_GAUGE_STATIONS
      : ALL_GAUGE_STATIONS.filter((g) => g.isPrimary);
  }, [showAlternates]);

  return (
    <div className="relative w-full h-[520px] rounded-xl overflow-hidden border border-slate-200 shadow-xs bg-slate-900 z-0">
      {/* Header Overlay with Toggle */}
      <div className="absolute top-3 left-14 z-[1000] bg-white/95 backdrop-blur-md px-3.5 py-2 rounded-lg border border-slate-200 shadow-xs text-xs pointer-events-auto flex items-center gap-4">
        <div>
          <div className="font-bold text-slate-900 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-sky-500 animate-ping" />
            Panchganga Dynamic Station Selection &amp; River Model
          </div>
          <div className="text-[11px] text-slate-500 font-medium mt-0.5">
            Auto-selects max volume &amp; nearest fallback stations across S1–S9
          </div>
        </div>

        <button
          onClick={() => setShowAlternates(!showAlternates)}
          className={`px-2.5 py-1 rounded text-[10px] font-bold border transition-colors ${
            showAlternates
              ? "bg-sky-50 text-sky-700 border-sky-300 hover:bg-sky-100"
              : "bg-slate-100 text-slate-600 border-slate-300 hover:bg-slate-200"
          }`}
        >
          {showAlternates ? "Showing: All 17 Stations (Primary + Alt)" : "Showing: Primary 7 Only"}
        </button>
      </div>

      {/* Floating Legend */}
      <div className="absolute bottom-3 right-3 z-[1000] bg-white/95 backdrop-blur-md px-3 py-2 rounded-lg border border-slate-200 shadow-xs text-[10px] pointer-events-auto">
        <div className="font-bold text-slate-700 uppercase tracking-wider mb-1.5">Stations &amp; Layers</div>
        <div className="flex flex-col gap-1 text-slate-600 font-medium">
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-1 bg-sky-500 rounded-full" />
            <span>Panchganga River Network</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 border border-emerald-700" />
            <span>Primary HMS Gages (Governing)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500 border border-purple-700" />
            <span>Alternate &amp; Fallback Gages</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 border border-rose-700" />
            <span>CWC Bridge Gauges</span>
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

        {/* Render Primary & Alternate Stations */}
        {displayedStations.map((g) => {
          const isSelected = selectedStationId === g.id;
          const isPrimary = g.isPrimary;
          const markerColor = isPrimary ? "#059669" : "#7C3AED";
          const markerFill = isPrimary ? "#10B981" : "#A78BFA";

          return (
            <CircleMarker
              key={g.id}
              center={[g.lat, g.lon]}
              radius={isSelected ? 11 : isPrimary ? 8 : 6}
              pathOptions={{
                color: isSelected ? "#0284C7" : markerColor,
                fillColor: isSelected ? "#38BDF8" : markerFill,
                fillOpacity: 0.95,
                weight: isSelected ? 4 : isPrimary ? 2 : 1.5,
              }}
              eventHandlers={{
                click: () => {
                  if (onSelectStation) onSelectStation(g.id);
                },
              }}
            >
              <Popup>
                <div style={{ fontFamily: "Inter, sans-serif", minWidth: 190, padding: 4 }}>
                  <div className="flex items-center justify-between font-bold text-slate-900 border-b border-slate-100 pb-1">
                    <span>{g.name}</span>
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${
                        isPrimary
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-purple-100 text-purple-800"
                      }`}
                    >
                      {isPrimary ? "PRIMARY GAGE" : "ALTERNATE GAGE"}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-600 mt-2 space-y-1">
                    <div>Assigned Subbasin: <b className="text-sky-700">{g.subbasin}</b></div>
                    <div>Coordinates: <span className="font-mono text-slate-700">{g.lat.toFixed(4)}°N, {g.lon.toFixed(4)}°E</span></div>
                    <div>Elevation: <b>{g.elevation}</b></div>
                    <div className="pt-1 border-t border-slate-100 text-slate-800 font-semibold">
                      90hr Rain Volume: <span className="text-sky-600 font-mono font-bold">{g.fc90.toFixed(1)} mm</span>
                    </div>
                  </div>
                </div>
              </Popup>
              <Tooltip direction="top" offset={[0, -8]} opacity={0.95}>
                <span className="font-mono text-[10px] font-bold">
                  {g.name} ({g.fc90}mm) {isPrimary ? "★" : "○"}
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
