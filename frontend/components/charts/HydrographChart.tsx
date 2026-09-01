"use client";
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Filler, Title, Tooltip, Legend,
} from "chart.js";
import annotationPlugin from "chartjs-plugin-annotation";
import { Line } from "react-chartjs-2";

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  Filler, Title, Tooltip, Legend, annotationPlugin,
);

interface HydrographProps {
  data: { hour: number; q: number; stage?: number }[];
  thresholds?: { watch?: number; warning?: number; emergency?: number };
  showStage?: boolean;
  highlightPeak?: boolean;
  height?: number;
}

export default function HydrographChart({
  data,
  thresholds = { watch: 500, warning: 750, emergency: 1000 },
  showStage = false,
  height = 240,
}: HydrographProps) {
  if (!data?.length) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center text-gray-400 text-xs font-mono bg-gray-50 rounded border border-dashed border-gray-200"
      >
        Waiting for hydrograph data...
      </div>
    );
  }

  const labels = data.map((d) => `+${d.hour}h`);
  const qValues = data.map((d) => d.q ?? 0);
  const stgValues = data.map((d) => d.stage ?? null);

  const datasets: any[] = [
    {
      label: "Discharge (m³/s)",
      data: qValues,
      borderColor: "#2563EB", // Tailwind blue-600
      backgroundColor: "rgba(37, 99, 235, 0.05)",
      borderWidth: 2,
      fill: true,
      tension: 0.2,
      pointRadius: 0,
      pointHoverRadius: 4,
      yAxisID: "y",
    },
  ];

  if (showStage) {
    datasets.push({
      label: "Stage (m)",
      data: stgValues,
      borderColor: "#7C3AED", // Tailwind violet-600
      backgroundColor: "transparent",
      borderWidth: 1.5,
      borderDash: [4, 4],
      fill: false,
      tension: 0.2,
      pointRadius: 0,
      pointHoverRadius: 4,
      yAxisID: "y2",
    });
  }

  const annotations: any = {};
  if (thresholds.watch) annotations.watch = hline(thresholds.watch, "#EAB308", "Watch");
  if (thresholds.warning) annotations.warning = hline(thresholds.warning, "#F97316", "Warning");
  if (thresholds.emergency) annotations.emergency = hline(thresholds.emergency, "#EF4444", "Danger");

  const options: any = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        display: showStage,
        position: "top" as const,
        align: "end" as const,
        labels: {
          color: "#4B5563",
          boxWidth: 10,
          font: { size: 11, family: "sans-serif" },
        },
      },
      tooltip: {
        backgroundColor: "rgba(255, 255, 255, 0.95)",
        borderColor: "#E5E7EB",
        borderWidth: 1,
        titleColor: "#111827",
        bodyColor: "#374151",
        titleFont: { size: 12, family: "sans-serif" },
        bodyFont: { size: 11, family: "monospace" },
        padding: 8,
        usePointStyle: true,
      },
      annotation: { annotations },
    },
    scales: {
      x: {
        ticks: { color: "#6B7280", font: { size: 10, family: "monospace" }, maxTicksLimit: 12 },
        grid: { display: false },
      },
      y: {
        position: "left",
        ticks: { color: "#4B5563", font: { size: 10, family: "monospace" } },
        grid: { color: "#F3F4F6" },
      },
      ...(showStage
        ? {
            y2: {
              position: "right",
              ticks: { color: "#4B5563", font: { size: 10, family: "monospace" } },
              grid: { drawOnChartArea: false },
            },
          }
        : {}),
    },
  };

  return (
    <div style={{ height }} className="w-full">
      <Line data={{ labels, datasets }} options={options} />
    </div>
  );
}

function hline(y: number, color: string, label: string) {
  return {
    type: "line" as const,
    yMin: y,
    yMax: y,
    borderColor: color,
    borderWidth: 1,
    borderDash: [4, 4],
    label: {
      display: true,
      content: `${label} (${y})`,
      backgroundColor: "transparent",
      color: color,
      font: { size: 10, family: "monospace" },
      position: "end" as const,
      padding: 2,
    },
  };
}
