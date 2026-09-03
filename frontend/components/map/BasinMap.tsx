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
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import {
  Search,
  Layers,
  Waves,
  CloudRain,
  ChevronRight,
  Filter,
} from "lucide-react";

// Complete Registry of 20 Primary & Alternate Rainfall Stations (S1–S9)
export const ALL_GAUGE_STATIONS = [
  // S1 (Area: 86.213 km²)
  { id: "KARVEER", name: "Karveer", subbasin: "S1", lon: 74.2481772, lat: 16.706369, isPrimary: true, elevation: "550m", taluka: "Karvir" },
  { id: "KARVIR", name: "Karveer", subbasin: "S1", lon: 74.2481772, lat: 16.706369, isPrimary: true, elevation: "550m", taluka: "Karvir" },

  // S2 (Area: 153.77 km²)
  { id: "SANGARUL", name: "Sangarul", subbasin: "S2", lon: 74.0931627, lat: 16.6841962, isPrimary: true, elevation: "572m", taluka: "Karvir" },
  { id: "BALINGA", name: "Balinga", subbasin: "S2", lon: 74.17031, lat: 16.6878443, isPrimary: false, elevation: "560m", taluka: "Karvir" },
  { id: "KALE", name: "Kale", subbasin: "S2", lon: 74.0564499, lat: 16.7228087, isPrimary: false, elevation: "580m", taluka: "Panhala" },

  // S3 (Area: 261.32 km²)
  { id: "KOTOLI", name: "Kotoli", subbasin: "S3", lon: 74.0518705, lat: 16.7820174, isPrimary: true, elevation: "585m", taluka: "Panhala" },
  { id: "BAJAR_BHOGAON", name: "Bajar Bhogaon", subbasin: "S3", lon: 74.1107824, lat: 16.8086769, isPrimary: false, elevation: "590m", taluka: "Panhala" },
  { id: "PADAL", name: "Padal", subbasin: "S3", lon: 74.115187, lat: 16.7446006, isPrimary: false, elevation: "575m", taluka: "Panhala" },

  // S4 (Area: 262.00 km²)
  { id: "KARANJPHEN", name: "Karanjphen", subbasin: "S4", lon: 73.9036487, lat: 16.7850973, isPrimary: true, elevation: "640m", taluka: "Panhala" },

  // S5 (Area: 106.39 km²)
  { id: "PADASALI", name: "Padasali", subbasin: "S5", lon: 73.843584, lat: 16.701934, isPrimary: true, elevation: "620m", taluka: "Gaganbawda" },
  { id: "SALWAN", name: "Salwan", subbasin: "S5", lon: 73.9735, lat: 16.6712, isPrimary: false, elevation: "595m", taluka: "Gaganbawda" },

  // S6 (Area: 227.72 km²)
  { id: "GAGANBAWDA", name: "Gaganbawda", subbasin: "S6", lon: 73.8346738, lat: 16.5469926, isPrimary: true, elevation: "680m", taluka: "Gaganbawda" },

  // S7 (Area: 195.39 km²)
  { id: "GARIVADE", name: "Garivade", subbasin: "S7", lon: 73.918419, lat: 16.520366, isPrimary: true, elevation: "610m", taluka: "Radhanagari" },

  // S8 (Area: 177.44 km²)
  { id: "BEED", name: "Beed", subbasin: "S8", lon: 74.1288964, lat: 16.647984, isPrimary: true, elevation: "565m", taluka: "Karvir" },
  { id: "SHIROLI_DHUMALA", name: "Shiroli-Dhumala", subbasin: "S8", lon: 74.1062828, lat: 16.6166768, isPrimary: false, elevation: "560m", taluka: "Karvir" },

  // S9 (Area: 366.97 km²)
  { id: "RADHANAGARI", name: "Radhanagari", subbasin: "S9", lon: 73.9971822, lat: 16.41021, isPrimary: true, elevation: "615m", taluka: "Radhanagari" },
  { id: "HALADI", name: "Haladi", subbasin: "S9", lon: 74.156292, lat: 16.5932632, isPrimary: false, elevation: "555m", taluka: "Kagal" },
  { id: "RASHIWADE_BK", name: "Rashiwade Bk.", subbasin: "S9", lon: 74.1019728, lat: 16.5475641, isPrimary: false, elevation: "570m", taluka: "Radhanagari" },
  { id: "AAVALI_BK", name: "Aavali Bk.", subbasin: "S9", lon: 74.0549812, lat: 16.481009, isPrimary: false, elevation: "585m", taluka: "Radhanagari" },
  { id: "KASABA_TARALE", name: "Kasaba Tarale", subbasin: "S9", lon: 74.021589, lat: 16.4478876, isPrimary: false, elevation: "595m", taluka: "Radhanagari" },
  { id: "KASABA_WALAWE", name: "Kasaba Walawe", subbasin: "S9", lon: 73.9971822, lat: 16.41021, isPrimary: false, elevation: "615m", taluka: "Radhanagari" },
];

export const GAUGE_STATIONS = ALL_GAUGE_STATIONS;

export const BRIDGES = [
  {
    id: "SHIVAJI_BRIDGE",
    name: "Shivaji Bridge (Panchganga Ghat)",
    district: "Kolhapur",
    lat: 16.708917,
    lon: 74.219278,
    warning: "542.70m MSL",
    danger: "543.30m MSL",
    extreme: "544.00m MSL",
    hfl: "545.33m MSL",
    desc: "Primary urban river crossing in Kolhapur City. Ultrasonic radar level sensor mounted on bridge deck.",
    markerColor: "#0f4c81",
  },
  {
    id: "RAJARAM_BRIDGE",
    name: "Rajaram K.T. Weir (Kasba Bawada)",
    district: "Kolhapur",
    lat: 16.736167,
    lon: 74.235889,
    warning: "542.07m MSL",
    danger: "543.30m MSL",
    extreme: "544.00m MSL",
    hfl: "545.33m MSL",
    desc: "Primary Panchganga barrage & hydraulic rating station for urban flood risk assessment.",
    markerColor: "#0284c7",
  },
];

function getIntensityColor(mm: number): { fill: string; stroke: string } {
  if (mm >= 50) return { fill: "#EF4444", stroke: "#B91C1C" };
  if (mm >= 30) return { fill: "#F59E0B", stroke: "#D97706" };
  if (mm >= 15) return { fill: "#FBBF24", stroke: "#B45309" };
  if (mm >= 5)  return { fill: "#38BDF8", stroke: "#0284C7" };
  return { fill: "#BAE6FD", stroke: "#0284C7" };
}

// Map Controller for Smooth Fly-To & Pane Initialization
function MapController({ targetLocation }: { targetLocation: { lat: number; lon: number; id: string } | null }) {
  const map = useMap();

  useEffect(() => {
    if (!map.getPane("stationsPane")) {
      const sp = map.createPane("stationsPane");
      sp.style.zIndex = "650";
      sp.style.pointerEvents = "auto";
    }
    if (!map.getPane("bridgesPane")) {
      const bp = map.createPane("bridgesPane");
      bp.style.zIndex = "660";
      bp.style.pointerEvents = "auto";
    }
  }, [map]);

  useEffect(() => {
    if (targetLocation) {
      map.flyTo([targetLocation.lat, targetLocation.lon], 12, { duration: 1.2 });
    }
  }, [targetLocation, map]);

  return null;
}

export default function BasinMap({
  subbasins,
  ecmwf = {},
  stations = [],
  selectedStationId = "KARVIR",
  showSidebar = false,
  onSelectStation,
}: {
  subbasins?: string[];
  ecmwf?: Record<string, any[]>;
  stations?: any[];
  selectedStationId?: string;
  showSidebar?: boolean;
  onSelectStation?: (stationId: string) => void;
}) {
  const [selectedSub, setSelectedSub] = useState<string | null>(null);
  const [subbasinGeo, setSubbasinGeo] = useState<any>(null);
  const [riverGeo, setRiverGeo] = useState<any>(null);
  const [filterMode, setFilterMode] = useState<"governing" | "all" | "river">("governing");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [flyTarget, setFlyTarget] = useState<{ lat: number; lon: number; id: string } | null>(null);

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
    if (ecmwf && ecmwf[subId] && ecmwf[subId].length > 0) {
      const sum = ecmwf[subId].reduce((acc: number, p: any) => acc + (p.mm_hr ?? 0), 0);
      return parseFloat(sum.toFixed(1));
    }
    const stMatch = stations?.find((s: any) => s.subbasin_id === subId);
    if (stMatch && stMatch.cumulative_90h_mm !== undefined) {
      return stMatch.cumulative_90h_mm;
    }
    return 0.0;
  }

  // Unified stations list with real live precipitation data
  const enrichedStations = useMemo(() => {
    return ALL_GAUGE_STATIONS.map((g) => {
      const stMatch = stations?.find(
        (s: any) =>
          s.station_id === g.id ||
          s.station_name?.toLowerCase().includes(g.name.split(" ")[0].toLowerCase())
      );

      let rainVal = stMatch?.cumulative_90h_mm;
      if (rainVal === undefined) {
        rainVal = getSubRainfall(g.subbasin);
      }

      // Check if this station is active governing selection in HEC-HMS (subbasins S1-S9)
      const isGoverning = stMatch?.is_governing ?? (
        g.id === "KARVEER" || g.id === "KARVIR" || // S1
        g.id === "SANGARUL" ||                     // S2
        g.id === "KOTOLI" ||                       // S3
        g.id === "KARANJPHEN" ||                   // S4
        g.id === "PADASALI" ||                     // S5
        g.id === "GAGANBAWDA" ||                   // S6
        g.id === "GARIVADE" ||                     // S7
        g.id === "BEED" ||                         // S8
        g.id === "RADHANAGARI"                     // S9
      );
      const peakRate = stMatch?.peak_rate_mmh ?? (rainVal > 0 ? (rainVal / 18).toFixed(1) : "0.0");

      return {
        ...g,
        fc90: rainVal ?? 0.0,
        isGoverning,
        peakRate,
      };
    });
  }, [stations, ecmwf]);

  // Filtered stations for side navigator and map
  const displayedMapStations = useMemo(() => {
    if (filterMode === "governing") {
      return enrichedStations.filter((s) => s.isGoverning);
    }
    return enrichedStations;
  }, [enrichedStations, filterMode]);

  const filteredList = useMemo(() => {
    let list = enrichedStations;
    if (filterMode === "governing") {
      list = list.filter((s) => s.isGoverning);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.subbasin.toLowerCase().includes(q) ||
          s.taluka?.toLowerCase().includes(q)
      );
    }
    return list;
  }, [enrichedStations, filterMode, searchQuery]);

  const handleLocationClick = (loc: { lat: number; lon: number; id: string }) => {
    setFlyTarget({ lat: loc.lat, lon: loc.lon, id: loc.id });
    if (onSelectStation) {
      onSelectStation(loc.id);
    }
  };

  return (
    <div className="flex flex-col lg:flex-row gap-0 w-full bg-white rounded-xl overflow-hidden border border-gray-200 shadow-xs">
      {/* ── LEFT: OPTIONAL SIDEBAR (Only if showSidebar=true) ──────────────── */}
      {showSidebar && (
        <div className="w-full lg:w-80 bg-gray-50 border-r border-gray-200 flex flex-col h-[520px] flex-shrink-0 z-10">
          <div className="p-3 border-b border-gray-200 bg-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <h3 className="text-xs font-bold text-gray-800 uppercase tracking-wider">
                  HEC-HMS Stations ({filterMode === "governing" ? "9 Active" : `${enrichedStations.length} Total`})
                </h3>
              </div>
              <span className="text-[10px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded font-mono font-bold border border-emerald-200">
                DSS Linked
              </span>
            </div>

            <div className="relative mt-2">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-gray-400" />
              <input
                type="text"
                placeholder="Search station, subbasin S1–S9..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-white border border-gray-200 rounded-md pl-8 pr-3 py-1.5 text-xs text-gray-800 placeholder-gray-400 focus:outline-none focus:border-blue-500 transition-all font-sans"
              />
            </div>

            <div className="flex items-center gap-1 mt-2">
              <button
                onClick={() => setFilterMode("governing")}
                className={`px-2.5 py-1 rounded text-[10px] font-bold transition-all ${
                  filterMode === "governing"
                    ? "bg-emerald-600 text-white shadow-xs"
                    : "bg-white text-gray-700 hover:bg-gray-100 border border-gray-200"
                }`}
              >
                ★ HEC-DSS Active (9)
              </button>
              <button
                onClick={() => setFilterMode("all")}
                className={`px-2.5 py-1 rounded text-[10px] font-bold transition-all ${
                  filterMode === "all"
                    ? "bg-blue-600 text-white shadow-xs"
                    : "bg-white text-gray-700 hover:bg-gray-100 border border-gray-200"
                }`}
              >
                All (18)
              </button>
            </div>
          </div>

          <div className="flex-grow overflow-y-auto p-2 space-y-1">
            {filteredList.map((st) => {
              const isSelected = selectedStationId === st.id;
              return (
                <button
                  key={st.id}
                  onClick={() => handleLocationClick({ lat: st.lat, lon: st.lon, id: st.id })}
                  className={`w-full text-left p-2 rounded-lg border transition-all flex items-center justify-between group ${
                    isSelected
                      ? "bg-sky-50 border-sky-300 shadow-xs"
                      : "bg-white hover:bg-gray-50 border-gray-200"
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${st.isGoverning ? "bg-emerald-500" : "bg-purple-500"}`} />
                      <span className="text-xs font-bold text-gray-900 truncate">{st.name}</span>
                      <span className="text-[9px] font-bold px-1 rounded bg-gray-100 text-gray-700 border border-gray-200">
                        {st.subbasin}
                      </span>
                    </div>
                    <div className="text-[10px] text-gray-500 mt-0.5">
                      {st.taluka} · {st.elevation}
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0 ml-2">
                    <div className="text-xs font-mono font-bold text-blue-600">{st.fc90.toFixed(1)} mm</div>
                    <div className={`text-[8px] font-bold uppercase px-1 rounded ${st.isGoverning ? "text-emerald-700 bg-emerald-50" : "text-purple-700 bg-purple-50"}`}>
                      {st.isGoverning ? "DSS GOVERNING" : "BACKUP"}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* ── MAP CONTAINER (Light, Clean Styling) ─────────────────────────── */}
      <div className="relative flex-1 h-[520px] bg-slate-50">
        {/* Top Controls Overlay */}
        <div className="absolute top-3 left-14 z-[1000] bg-white/95 backdrop-blur-md px-3.5 py-1.5 rounded-lg border border-gray-200 shadow-xs text-xs pointer-events-auto flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-gray-800">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="font-bold text-[11px]">
              {filterMode === "governing" ? "HEC-DSS Active Simulation Stations (S1–S9)" : "All Panchganga Stations"}
            </span>
          </div>
          <div className="flex items-center gap-1 border-l border-gray-200 pl-2">
            <button
              onClick={() => setFilterMode(filterMode === "governing" ? "all" : "governing")}
              className="text-[10px] font-bold text-blue-600 hover:text-blue-700 px-1.5 py-0.5 rounded hover:bg-blue-50 transition-colors"
            >
              {filterMode === "governing" ? "Show All 18 Gages" : "Show 9 DSS Gages"}
            </button>
          </div>
        </div>

        {/* Floating Legend */}
        <div className="absolute bottom-3 right-3 z-[1000] bg-white/95 backdrop-blur-md px-3 py-2 rounded-lg border border-gray-200 shadow-xs text-[10px] pointer-events-auto">
          <div className="font-bold text-gray-700 uppercase tracking-wider mb-1 flex items-center gap-1">
            <Layers className="w-3 h-3 text-blue-600" /> Legend
          </div>
          <div className="flex flex-col gap-1 text-gray-600 font-medium">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-1 bg-sky-500 rounded-full" />
              <span>Panchganga Stream Network</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 border border-emerald-700" />
              <span>HEC-DSS Active Station (Governing)</span>
            </div>
            {filterMode === "all" && (
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-500 border border-purple-700" />
                <span>Alternate / Backup Gage</span>
              </div>
            )}
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 border border-rose-700" />
              <span>River Bridge Flood Gauge</span>
            </div>
          </div>
        </div>

        <MapContainer
          center={CENTER}
          zoom={10}
          scrollWheelZoom={true}
          className="w-full h-full z-0"
          zoomControl={true}
          attributionControl={true}
        >
          <MapController targetLocation={flyTarget} />

          <LayersControl position="topright">
            <LayersControl.BaseLayer checked name="OpenStreetMap Standard">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
            </LayersControl.BaseLayer>
            <LayersControl.BaseLayer name="Esri Topographic Relief">
              <TileLayer
                attribution='Tiles &copy; Esri'
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
              />
            </LayersControl.BaseLayer>
            <LayersControl.BaseLayer name="Esri World Satellite">
              <TileLayer
                attribution='Tiles &copy; Esri'
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              />
            </LayersControl.BaseLayer>
          </LayersControl>

          {/* Subbasin Shapefile / GeoJSON Polygons (Light background fill) */}
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
                  fillOpacity: isSelected ? 0.35 : 0.15,
                  color: isSelected ? "#0284C7" : stroke,
                  weight: isSelected ? 2.5 : 1.2,
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
                    <div style="font-weight: 700; color: #0284C7;">Subbasin ${name}</div>
                    <div style="font-size: 10px; color: #475569;">Slope: <b>${(props.basin_slo || 0).toFixed(3)}</b> · Relief: <b>${props.basin_rel || 0}m</b></div>
                    <div style="font-size: 11px; color: #0F172A; font-weight: 600; margin-top: 2px;">90-hr Forecast: <span style="color: #0284C7;">${cumVal.toFixed(1)} mm</span></div>
                  </div>`,
                  { direction: "top", sticky: true, opacity: 0.95 }
                );
              }}
            />
          )}

          {/* Panchganga River Flowpaths */}
          {riverGeo && (
            <GeoJSON
              key="rivers-geojson"
              data={riverGeo}
              style={() => ({
                color: "#0284C7",
                weight: 3,
                opacity: 0.85,
              })}
              onEachFeature={(feature, layer) => {
                layer.bindTooltip(
                  `<div style="font-family: Inter, sans-serif; padding: 2px;">
                    <div style="font-weight: 700; color: #0284C7;">Panchganga River Reach</div>
                  </div>`,
                  { direction: "top", sticky: true, opacity: 0.95 }
                );
              }}
            />
          )}

          {/* Rainfall Station Markers (Pane: markerPane, zIndex: 650) */}
          {displayedMapStations.map((g) => {
            const isSelected = selectedStationId === g.id;
            const isGov = g.isGoverning;
            const markerColor = isGov ? "#059669" : "#7C3AED";
            const markerFill = isGov ? "#10B981" : "#A78BFA";

            return (
              <CircleMarker
                key={`st_${g.id}`}
                center={[g.lat, g.lon]}
                radius={isSelected ? 10 : isGov ? 7.5 : 5.5}
                pane="markerPane"
                pathOptions={{
                  color: isSelected ? "#0284C7" : markerColor,
                  fillColor: isSelected ? "#38BDF8" : markerFill,
                  fillOpacity: 0.95,
                  weight: isSelected ? 3.5 : isGov ? 2 : 1.5,
                }}
                eventHandlers={{
                  click: () => handleLocationClick({ lat: g.lat, lon: g.lon, id: g.id }),
                }}
              >
                <Popup>
                  <div style={{ fontFamily: "Inter, sans-serif", minWidth: 210, padding: 2 }}>
                    <div className="flex items-center justify-between border-b border-gray-200 pb-1">
                      <div>
                        <div className="font-bold text-sm text-gray-900">{g.name}</div>
                        <div className="text-[10px] text-gray-500 font-mono">{g.taluka}</div>
                      </div>
                      <span
                        className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${
                          isGov ? "bg-emerald-100 text-emerald-800" : "bg-purple-100 text-purple-800"
                        }`}
                      >
                        {isGov ? "DSS ACTIVE" : "BACKUP"}
                      </span>
                    </div>

                    <div className="text-[11px] text-gray-600 mt-2 space-y-1">
                      <div className="flex justify-between">
                        <span>Assigned Subbasin:</span>
                        <b className="text-blue-700 font-mono">{g.subbasin}</b>
                      </div>
                      <div className="flex justify-between">
                        <span>GPS Coordinates:</span>
                        <span className="font-mono text-gray-800 font-medium">
                          {g.lat.toFixed(3)}°N, {g.lon.toFixed(3)}°E
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Elevation:</span>
                        <b>{g.elevation}</b>
                      </div>
                      <div className="flex justify-between pt-1 border-t border-gray-100">
                        <span className="font-semibold text-gray-800">90-hr Forecast Total:</span>
                        <span className="text-blue-600 font-mono font-bold text-xs">{g.fc90.toFixed(1)} mm</span>
                      </div>
                    </div>

                    <div className="mt-2.5 pt-2 border-t border-gray-200 flex justify-end">
                      <button
                        onClick={() => {
                          if (onSelectStation) onSelectStation(g.id);
                        }}
                        className="text-[10px] font-bold text-white bg-blue-600 hover:bg-blue-700 px-2.5 py-1 rounded transition-colors"
                      >
                        View Station Hyetograph →
                      </button>
                    </div>
                  </div>
                </Popup>

                <Tooltip direction="top" offset={[0, -8]} opacity={0.95}>
                  <div className="font-mono text-[10px] font-bold text-gray-900">
                    {g.name} ({g.fc90.toFixed(1)}mm) {isGov ? "★" : "○"}
                  </div>
                </Tooltip>
              </CircleMarker>
            );
          })}

          {/* River Bridge Flood Monitoring Gauge Markers */}
          {BRIDGES.map((b) => (
            <CircleMarker
              key={`br_${b.id}`}
              center={[b.lat, b.lon]}
              radius={9}
              pane="markerPane"
              pathOptions={{
                color: "#B91C1C",
                fillColor: "#EF4444",
                fillOpacity: 0.95,
                weight: 2.5,
              }}
              eventHandlers={{
                click: () => handleLocationClick({ lat: b.lat, lon: b.lon, id: b.id }),
              }}
            >
              <Popup>
                <div style={{ fontFamily: "Inter, sans-serif", minWidth: 220, padding: 2 }}>
                  <div className="font-bold text-sm text-rose-900 border-b border-rose-200 pb-1">
                    {b.name}
                  </div>
                  <div className="text-[10px] text-gray-500 mt-1">{b.desc}</div>
                  <div className="text-[11px] text-gray-700 mt-2 space-y-1">
                    <div className="flex justify-between">
                      <span className="text-amber-700 font-medium">Alert Level:</span>
                      <b className="font-mono">542.10 m MSL</b>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-orange-700 font-medium">Warning Level:</span>
                      <b className="font-mono">{b.warning}</b>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-red-700 font-medium">Danger Level:</span>
                      <b className="font-mono">{b.danger}</b>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-purple-700 font-medium">High Flood Level (HFL):</span>
                      <b className="font-mono">{b.hfl}</b>
                    </div>
                  </div>
                </div>
              </Popup>

              <Tooltip permanent direction="bottom" offset={[0, 8]} opacity={0.95}>
                <span className="text-[10px] font-bold text-rose-700 bg-white px-1.5 py-0.5 rounded shadow-xs border border-rose-200">
                  {b.name.replace(" (Panchganga Ghat)", "").replace(" (Kasba Bawada)", "")}
                </span>
              </Tooltip>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
