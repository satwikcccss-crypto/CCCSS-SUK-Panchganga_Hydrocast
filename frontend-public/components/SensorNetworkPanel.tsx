import useSWR from "swr";
import { api } from "@/lib/api";

const CARD = "bg-white border border-gray-200 rounded p-4";

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  ONLINE: { bg: "bg-green-100", text: "text-green-800", label: "Online" },
  STALE: { bg: "bg-orange-100", text: "text-orange-800", label: "Stale" },
  OFFLINE: { bg: "bg-red-100", text: "text-red-800", label: "Offline" },
  NO_DATA: { bg: "bg-yellow-100", text: "text-yellow-800", label: "No Data" },
  NOT_CONFIGURED: { bg: "bg-gray-100", text: "text-gray-600", label: "Not Configured" },
};

function formatTime(ts?: string | null): string {
  if (!ts) return "—";
  try {
    const d = new Date(ts);
    return d.toLocaleString("en-IN", { timeZone: "Asia/Kolkata", hour12: true, day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  } catch {
    return ts;
  }
}

export default function SensorNetworkPanel() {
  const { data: sensors, error, isLoading } = useSWR("sensors-live", api.sensorsLive, { refreshInterval: 15000 });

  const stationList: any[] = Array.isArray(sensors) ? sensors : sensors?.stations ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-800">IoT Sensor Network — Live Water Levels</h2>
        <span className="text-[10px] text-gray-500">Auto-refresh: 15s</span>
      </div>

      {isLoading && stationList.length === 0 && (
        <div className={CARD}>
          <p className="text-xs text-gray-500 text-center py-6">Loading sensor data...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3">
          <p className="text-xs text-red-700">Sensor API unavailable. Check backend connectivity.</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {stationList.map((s: any) => {
          const st = STATUS_STYLES[s.status] ?? STATUS_STYLES.OFFLINE;
          const aboveZero = s.stage_m != null && s.zero_level_m != null ? (s.stage_m - s.zero_level_m).toFixed(2) : null;

          return (
            <div key={s.station_id} className={CARD}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="text-sm font-semibold text-gray-900">{s.name}</p>
                  <p className="text-[10px] text-gray-500">{s.full_name}</p>
                </div>
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${st.bg} ${st.text}`}>{st.label}</span>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">Stage (m MSL)</span>
                  <span className="font-mono font-semibold text-gray-900">{s.stage_m != null ? s.stage_m.toFixed(2) : "—"}</span>
                </div>
                {aboveZero != null && (
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">Above Zero Gauge</span>
                    <span className="font-mono text-gray-700">{aboveZero} m</span>
                  </div>
                )}
                {s.raw_distance_ft != null && (
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">Raw Distance</span>
                    <span className="font-mono text-gray-700">{s.raw_distance_ft} ft</span>
                  </div>
                )}
                {s.voltage != null && (
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">Battery Voltage</span>
                    <span className="font-mono text-gray-700">{s.voltage} V</span>
                  </div>
                )}
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">Sensor Datum</span>
                  <span className="font-mono text-gray-500">{s.sensor_datum_m} m MSL</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">Last Update</span>
                  <span className="text-gray-500">{formatTime(s.timestamp)}</span>
                </div>
              </div>

              <div className="mt-3 pt-2 border-t border-gray-100 flex items-center gap-2 text-[10px] text-gray-400">
                <span>{s.station_id}</span>
                <span>·</span>
                <span>{s.type}</span>
                <span>·</span>
                <span>{s.latitude?.toFixed(4)}°N, {s.longitude?.toFixed(4)}°E</span>
              </div>
            </div>
          );
        })}
      </div>

      {stationList.length === 0 && !isLoading && !error && (
        <div className={CARD}>
          <p className="text-xs text-gray-500 text-center py-6">No sensor stations configured.</p>
        </div>
      )}
    </div>
  );
}
