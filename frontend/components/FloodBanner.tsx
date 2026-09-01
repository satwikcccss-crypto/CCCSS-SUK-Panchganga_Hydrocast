// frontend/components/FloodBanner.tsx
"use client";
import { useState } from "react";

export default function FloodBanner({ alerts }: { alerts: any[] }) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed || !alerts.length) return null;

  const worst =
    alerts.find((a) => ["emergency", "danger"].includes(a.alert_type?.toLowerCase())) ??
    alerts.find((a) => a.alert_type?.toLowerCase() === "warning") ??
    alerts[0];

  const alertType = worst?.alert_type?.toUpperCase() || "ALERT";
  const isDanger = ["EMERGENCY", "DANGER"].includes(alertType);

  return (
    <div
      className={`flex items-center justify-between px-6 py-2.5 text-sm font-medium border-b transition-all ${
        isDanger
          ? "bg-rose-50 border-rose-200 text-rose-800 shadow-sm"
          : "bg-amber-50 border-amber-200 text-amber-900 shadow-sm"
      }`}
    >
      <div className="flex items-center gap-3.5">
        <span
          className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold text-white shadow-sm ${
            isDanger ? "bg-rose-600 animate-bounce" : "bg-amber-500 animate-pulse"
          }`}
        >
          !
        </span>
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-bold tracking-wide uppercase px-2 py-0.5 rounded text-xs bg-white/80 border border-current">
            FLOOD {alertType}
          </span>
          <span className="font-semibold">{worst?.alert_message}</span>
          {worst?.arrival_time && (
            <span className="text-xs opacity-75 font-mono-code bg-white/60 px-2 py-0.5 rounded">
              Est. Arrival: {new Date(worst.arrival_time).toUTCString().replace(" GMT", " UTC")}
            </span>
          )}
        </div>
      </div>
      <button
        onClick={() => setDismissed(true)}
        className="text-xs font-semibold uppercase tracking-wider px-3 py-1 bg-white border border-current rounded-md hover:bg-slate-50 transition-colors shadow-xs"
      >
        Dismiss
      </button>
    </div>
  );
}
