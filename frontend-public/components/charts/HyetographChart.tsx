// frontend/components/charts/HyetographChart.tsx
"use client";
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement,
  PointElement, LineElement, Title, Tooltip, Legend, Filler,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(
  CategoryScale, LinearScale, BarElement, PointElement,
  LineElement, Title, Tooltip, Legend, Filler
);

interface Dataset {
  label: string;
  data: { x: number; y: number }[];
  color: string;
}

export default function HyetographChart({
  datasets,
  height = 180,
  minimal = false,
}: {
  datasets: Dataset[];
  height?: number;
  minimal?: boolean;
}) {
  if (!datasets?.length || !datasets[0]?.data?.length) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center text-slate-400 text-xs font-mono-code bg-slate-50 rounded-lg border border-dashed border-slate-200"
      >
        Waiting for hyetograph data...
      </div>
    );
  }

  const labels = datasets[0].data.map((d) => (minimal ? "" : `+${d.x}h`));
  const chartData = {
    labels,
    datasets: datasets.map((ds) => ({
      label: ds.label,
      data: ds.data.map((d) => d.y),
      backgroundColor: ds.color,
      borderColor: ds.color,
      borderWidth: 0.5,
      borderRadius: 2,
    })),
  };

  const options: any = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: !minimal && datasets.length > 1,
        position: "top" as const,
        align: "end" as const,
        labels: {
          color: "#475569",
          boxWidth: 10,
          font: { size: 11, weight: "600", family: "Inter, sans-serif" },
        },
      },
      tooltip: {
        backgroundColor: "#FFFFFF",
        borderColor: "#E2E8F0",
        borderWidth: 1,
        titleColor: "#0F172A",
        bodyColor: "#334155",
        titleFont: { weight: "700", size: 12, family: "Inter, sans-serif" },
        bodyFont: { size: 11, family: "JetBrains Mono, monospace" },
        padding: 8,
        callbacks: {
          label: (c: any) => ` ${c.dataset.label}: ${c.parsed.y.toFixed(1)} mm/hr`,
        },
      },
    },
    scales: {
      x: {
        ticks: { color: "#64748B", font: { size: minimal ? 0 : 9, family: "JetBrains Mono, monospace" }, maxTicksLimit: 12 },
        grid: { display: false },
      },
      y: {
        ticks: { color: "#64748B", font: { size: minimal ? 8 : 9, family: "JetBrains Mono, monospace" } },
        grid: { color: "#F1F5F9" },
        beginAtZero: true,
        title: minimal
          ? undefined
          : { display: true, text: "Intensity (mm/hr)", color: "#64748B", font: { size: 9, weight: "600" } },
      },
    },
  };

  return (
    <div style={{ height }} className="w-full">
      <Bar data={chartData} options={options} />
    </div>
  );
}
