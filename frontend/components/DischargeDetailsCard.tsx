"use client";
import { useState, useMemo } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS, CategoryScale, LinearScale,
  BarElement, PointElement, LineElement, Title, Tooltip, Legend, Filler,
} from "chart.js";
import useSWR from "swr";
import { api } from "@/lib/api";

ChartJS.register(
  CategoryScale, LinearScale, BarElement, PointElement,
  LineElement, Title, Tooltip, Legend, Filler
);

export default function DischargeDetailsCard({ siteId = "RAJARAM_BRIDGE" }: { siteId?: string }) {
  const [activeTab, setActiveTab] = useState<"forecast" | "logs">("forecast");
  const { data: bData } = useSWR(`bridge-${siteId}`, () => api.bridgeStage(siteId), { refreshInterval: 60000 });

  const site = bData?.site;
  const forecast = bData?.forecast ?? [];

  const noData = !site || forecast.length === 0;

  const forecastChart = useMemo(() => ({
    labels: forecast.map((p: any, i: number) => `+${p.lead_hours ?? i}h`),
    datasets: [
      {
        type: "line" as const,
        label: "Forecast Stage (m MSL)",
        data: forecast.map((p: any) => p.stage_m),
        borderColor: "#333",
        backgroundColor: "rgba(0,0,0,0)",
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.1,
      },
    ],
  }), [forecast]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
    },
    scales: {
      x: { grid: { display: false }, ticks: { font: { size: 10 } } },
      y: { grid: { color: "#f0f0f0" }, ticks: { font: { size: 10 } } },
    },
  };

  // Real alert log from forecast data
  const alertEvents = useMemo(() => {
    if (forecast.length === 0 || !site) return [];
    const events: { time: string; event: string; value: string }[] = [];

    const currentStage = forecast[0]?.stage_m ?? 0;
    events.push({
      time: "Now (T+0h)",
      event: `Current water level`,
      value: `${currentStage.toFixed(2)}m MSL`,
    });

    const peakEntry = forecast.reduce((best: any, f: any) =>
      (f.stage_m > (best?.stage_m ?? 0)) ? f : best, forecast[0]);
    if (peakEntry) {
      events.push({
        time: `T+${peakEntry.lead_hours}h`,
        event: `Peak forecast stage`,
        value: `${peakEntry.stage_m.toFixed(2)}m MSL`,
      });
    }

    // Check threshold crossings
    const warnThreshold = site.warning_stage_m;
    const dangerThreshold = site.danger_stage_m;
    if (warnThreshold) {
      const firstWarn = forecast.find((f: any) => f.stage_m >= warnThreshold);
      if (firstWarn) {
        events.push({
          time: `T+${firstWarn.lead_hours}h`,
          event: `Warning threshold crossed (${warnThreshold}m)`,
          value: `${firstWarn.stage_m.toFixed(2)}m MSL`,
        });
      }
    }
    if (dangerThreshold) {
      const firstDanger = forecast.find((f: any) => f.stage_m >= dangerThreshold);
      if (firstDanger) {
        events.push({
          time: `T+${firstDanger.lead_hours}h`,
          event: `Danger threshold crossed (${dangerThreshold}m)`,
          value: `${firstDanger.stage_m.toFixed(2)}m MSL`,
        });
      }
    }

    return events;
  }, [forecast, site]);

  if (noData) {
    return (
      <div className="bg-white border border-gray-200 rounded p-5 text-center text-gray-400 text-sm py-10">
        Awaiting discharge forecast data for {siteId.replace(/_/g, " ")}...
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded p-5">
      <div className="mb-4 border-b border-gray-100 pb-2">
        <h2 className="text-base font-semibold text-gray-900">{site.site_name} - Discharge Station</h2>
        <p className="text-xs text-gray-500">Panchganga Basin Sink</p>
      </div>

      <div className="flex gap-4 mb-4 border-b border-gray-100 pb-2">
        <button
          onClick={() => setActiveTab("forecast")}
          className={`text-sm ${activeTab === "forecast" ? "text-black font-medium border-b-2 border-black" : "text-gray-500"}`}
        >
          Forecast (90h)
        </button>
        <button
          onClick={() => setActiveTab("logs")}
          className={`text-sm ${activeTab === "logs" ? "text-black font-medium border-b-2 border-black" : "text-gray-500"}`}
        >
          Alert Log
        </button>
      </div>

      <div style={{ height: 200 }} className="w-full">
        {activeTab === "forecast" && <Line data={forecastChart} options={chartOptions as any} />}
        {activeTab === "logs" && (
          <div className="overflow-y-auto h-full text-sm text-gray-700">
            {alertEvents.length === 0 ? (
              <div className="text-center text-gray-400 py-8">No alert events in current forecast</div>
            ) : (
              alertEvents.map((log, i) => (
                <div key={i} className="flex justify-between py-2 border-b border-gray-50 last:border-0">
                  <span><span className="text-gray-400 w-24 inline-block">{log.time}</span> {log.event}</span>
                  <span className="font-mono">{log.value}</span>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
