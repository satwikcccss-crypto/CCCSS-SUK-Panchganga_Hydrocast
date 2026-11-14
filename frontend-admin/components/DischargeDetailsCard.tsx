"use client";
import { useState, useMemo } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS, CategoryScale, LinearScale,
  BarElement, PointElement, LineElement, Title, Tooltip, Legend, Filler,
  LineController, BarController,
} from "chart.js";
import useSWR from "swr";
import { api } from "@/lib/api";

ChartJS.register(
  CategoryScale, LinearScale, BarElement, PointElement,
  LineElement, Title, Tooltip, Legend, Filler,
  LineController, BarController
);

export default function DischargeDetailsCard({ siteId = "RAJARAM_BRIDGE" }: { siteId?: string }) {
  const [activeTab, setActiveTab] = useState<"stage" | "discharge" | "logs">("stage");
  const { data: bData } = useSWR(`bridge-${siteId}`, () => api.bridgeStage(siteId), { refreshInterval: 60000 });

  const site = bData?.site;
  const forecast = bData?.forecast ?? [];

  const noData = !site || forecast.length === 0;

  const currentStage = forecast[0]?.stage_m ?? site?.current_stage_m ?? 533.10;
  const currentDischarge = forecast[0]?.discharge_m3s ?? 12.0;

  const chartData = useMemo(() => {
    const isStage = activeTab === "stage";
    return {
      labels: forecast.map((p: any, i: number) => `+${p.lead_hours ?? i}h`),
      datasets: [
        {
          type: "line" as const,
          label: isStage ? "Forecast Stage (m MSL)" : "Forecast Discharge (m³/s)",
          data: forecast.map((p: any) => isStage ? p.stage_m : p.discharge_m3s),
          borderColor: isStage ? "#0284c7" : "#4f46e5",
          backgroundColor: isStage ? "rgba(2, 132, 199, 0.08)" : "rgba(79, 70, 229, 0.08)",
          fill: true,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.2,
        },
      ],
    };
  }, [forecast, activeTab]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx: any) => `${ctx.parsed.y.toFixed(2)} ${activeTab === "stage" ? "m MSL" : "m³/s"}`,
        },
      },
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
      const peakArr = bData?.peak_arrival;
      const ciStr = peakArr?.confidence_interval
        ? `[T+${peakArr.confidence_interval.earliest_lead_hours}h to T+${peakArr.confidence_interval.latest_lead_hours}h] (±2.0h)`
        : `(±2.0h window)`;
      events.push({
        time: `T+${peakEntry.lead_hours}h`,
        event: `Peak flood strike ${ciStr}`,
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
  }, [forecast, site, bData]);

  if (noData) {
    return (
      <div className="bg-white border border-gray-200 rounded p-5 text-center text-gray-400 text-sm py-10">
        Awaiting discharge forecast data for {siteId.replace(/_/g, " ")}...
      </div>
    );
  }

  const peakLead = bData?.peak_arrival?.peak_lead_hours ?? (forecast.length > 0 ? forecast.reduce((best: any, f: any) => (f.stage_m > (best?.stage_m ?? 0)) ? f : best, forecast[0])?.lead_hours : 0);

  return (
    <div className="bg-white border border-gray-200 rounded p-5">
      <div className="mb-4 border-b border-gray-100 pb-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-gray-900">{site.site_name} - Discharge Station</h2>
          <p className="text-xs text-gray-500">Panchganga Basin Sink & Dynamic Rating Station</p>
        </div>
        <div className="flex items-center gap-2">
          {bData?.peak_arrival?.is_receding ? (
            <span className="inline-flex items-center px-2.5 py-1 rounded bg-slate-50 border border-slate-200 text-xs font-medium text-slate-600">
              Flow Receding
            </span>
          ) : (
            <span className="inline-flex items-center px-2.5 py-1 rounded bg-indigo-50 border border-indigo-200 text-xs font-medium text-indigo-800">
              Peak Arrival: T+{peakLead}h (±2.0h window)
            </span>
          )}
        </div>
      </div>

      {/* Live Reading Badges */}
      <div className="flex items-center gap-3 mb-3 text-xs">
        <div className="px-2.5 py-1 bg-sky-50 border border-sky-200 rounded text-sky-800 font-mono">
          <span className="text-gray-500 font-sans mr-1">Current WSE:</span>
          <strong>{currentStage.toFixed(2)} m MSL</strong>
        </div>
        <div className="px-2.5 py-1 bg-indigo-50 border border-indigo-200 rounded text-indigo-800 font-mono">
          <span className="text-gray-500 font-sans mr-1">Current Q:</span>
          <strong>{currentDischarge.toFixed(1)} m³/s</strong>
        </div>
      </div>

      <div className="flex gap-4 mb-4 border-b border-gray-100 pb-2">
        <button
          onClick={() => setActiveTab("stage")}
          className={`text-sm ${activeTab === "stage" ? "text-sky-700 font-semibold border-b-2 border-sky-600 pb-1" : "text-gray-500"}`}
        >
          Water Stage (90h)
        </button>
        <button
          onClick={() => setActiveTab("discharge")}
          className={`text-sm ${activeTab === "discharge" ? "text-indigo-700 font-semibold border-b-2 border-indigo-600 pb-1" : "text-gray-500"}`}
        >
          Discharge Flow (90h)
        </button>
        <button
          onClick={() => setActiveTab("logs")}
          className={`text-sm ${activeTab === "logs" ? "text-black font-semibold border-b-2 border-black pb-1" : "text-gray-500"}`}
        >
          Alert Log
        </button>
      </div>

      <div style={{ height: 200 }} className="w-full">
        {(activeTab === "stage" || activeTab === "discharge") && <Line data={chartData} options={chartOptions as any} />}
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
