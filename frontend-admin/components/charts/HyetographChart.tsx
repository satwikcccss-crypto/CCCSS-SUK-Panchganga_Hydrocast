// frontend/components/charts/HyetographChart.tsx
"use client";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  BarController,
  LineController,
} from "chart.js";
import { Chart } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  BarController,
  LineController
);

interface Dataset {
  label: string;
  data: { x: number; y: number }[];
  color: string;
  type?: "bar" | "line";
  yAxisID?: string;
  fill?: boolean;
}

export default function HyetographChart({
  datasets,
  height = 180,
  minimal = false,
  showCumulative = false,
}: {
  datasets: Dataset[];
  height?: number;
  minimal?: boolean;
  showCumulative?: boolean;
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

  // Build chart datasets, adding cumulative line if requested
  const chartDatasets: any[] = [];
  datasets.forEach((ds) => {
    chartDatasets.push({
      type: ds.type || "bar",
      label: ds.label,
      data: ds.data.map((d) => d.y),
      backgroundColor: ds.color,
      borderColor: ds.color,
      borderWidth: ds.type === "line" ? 2 : 0.5,
      borderRadius: ds.type === "line" ? 0 : 2,
      pointRadius: ds.type === "line" ? 0 : undefined,
      yAxisID: ds.yAxisID || "y",
      fill: ds.fill ?? false,
    });

    if (showCumulative && (!ds.type || ds.type === "bar")) {
      let cum = 0;
      const cumData = ds.data.map((d) => {
        cum += Number(d.y || 0);
        return parseFloat(cum.toFixed(2));
      });
      chartDatasets.push({
        type: "line",
        label: `${ds.label} (Cum)`,
        data: cumData,
        borderColor: ds.color,
        backgroundColor: "transparent",
        borderWidth: 1.5,
        borderDash: [4, 4],
        pointRadius: 0,
        yAxisID: "y2",
      });
    }
  });

  const hasDualAxis = chartDatasets.some((d) => d.yAxisID === "y2");

  const options: any = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: !minimal && chartDatasets.length > 1,
        position: "top" as const,
        align: "end" as const,
        labels: {
          color: "#475569",
          boxWidth: 10,
          font: { size: 10, weight: "600", family: "Inter, sans-serif" },
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
          label: (c: any) => {
            const isCum = c.dataset.yAxisID === "y2";
            return ` ${c.dataset.label}: ${Number(c.parsed.y || 0).toFixed(1)} ${isCum ? "mm cum" : "mm/hr"}`;
          },
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: "#64748B",
          font: { size: minimal ? 0 : 8.5, family: "JetBrains Mono, monospace" },
          maxTicksLimit: 12,
        },
        grid: { display: false },
      },
      y: {
        position: "left" as const,
        ticks: { color: "#64748B", font: { size: minimal ? 8 : 9, family: "JetBrains Mono, monospace" } },
        grid: { color: "#F1F5F9" },
        beginAtZero: true,
        title: minimal
          ? undefined
          : { display: true, text: "Intensity (mm/hr)", color: "#64748B", font: { size: 9, weight: "600" } },
      },
      ...(hasDualAxis
        ? {
            y2: {
              position: "right" as const,
              ticks: { color: "#10B981", font: { size: 8.5, family: "JetBrains Mono, monospace" } },
              grid: { drawOnChartArea: false },
              beginAtZero: true,
              title: { display: true, text: "Cumulative (mm)", color: "#10B981", font: { size: 9, weight: "600" } },
            },
          }
        : {}),
    },
  };

  return (
    <div style={{ height }} className="w-full">
      <Chart type="bar" data={{ labels, datasets: chartDatasets }} options={options} />
    </div>
  );
}
