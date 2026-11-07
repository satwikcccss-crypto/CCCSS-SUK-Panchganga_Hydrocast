"use client";

import { useEffect, useRef, useState } from "react";

// Use the relative same-origin route in the browser; this keeps the widget
// working on Vercel without mixed-content or localhost fallbacks.
function getVisitsUrl() {
  if (typeof window !== "undefined") {
    return "/api/v1/visits/record";
  }
  const api = process.env.NEXT_PUBLIC_API_URL;
  return api && api.startsWith("https://")
    ? `${api}/api/v1/visits/record`
    : "/api/v1/visits/record";
}

type VisitCounts = {
  daily: number;
  total: number;
  persisted?: boolean;
};

function DigitRoll({ digit }: { digit: string }) {
  // Use translateY to simulate the mechanical roll of an odometer
  return (
    <div className="relative w-4 h-[22px] overflow-hidden text-center bg-white border-y border-gray-300 font-mono text-sm font-bold text-gray-800 shadow-inner mx-[0.5px]">
      <div
        className="absolute top-0 left-0 w-full flex flex-col transition-transform duration-[1200ms] ease-out"
        style={{ transform: `translateY(-${parseInt(digit) * 22}px)` }}
      >
        {Array.from({ length: 10 }).map((_, i) => (
          <span
            key={i}
            className="flex items-center justify-center h-[22px] w-full bg-gradient-to-b from-gray-100 via-white to-gray-100"
          >
            {i}
          </span>
        ))}
      </div>
    </div>
  );
}

function Odometer({ value, padLength = 5 }: { value: number; padLength?: number }) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    // Delay animation slightly to allow initial render
    const t = setTimeout(() => setDisplayValue(value), 300);
    return () => clearTimeout(t);
  }, [value]);

  const digits = displayValue.toString().padStart(padLength, "0").split("");

  return (
    <div className="flex border-x border-gray-300 rounded-[3px] overflow-hidden shadow-sm">
      {digits.map((d, i) => (
        <DigitRoll key={`${i}-${digits.length}`} digit={d} />
      ))}
    </div>
  );
}

export default function VisitorCounterWidget({ compact = false }: { compact?: boolean }) {
  const [daily, setDaily] = useState(0);
  const [total, setTotal] = useState(0);
  const [mounted, setMounted] = useState(false);

  // Tracks whether we have ever received a value from a persistent ledger.
  // A process-memory fallback must not overwrite a real count with 0/stale data.
  const hasPersistedValue = useRef(false);

  useEffect(() => {
    setMounted(true);

    const controller = new AbortController();
    let cancelled = false;

    const today = new Date().toISOString().slice(0, 10);
    const recordedKey = `hydrocast_visit_recorded_${today}`;

    // Record at most one visit per browser session per UTC day. Subsequent
    // reads use GET so the widget can refresh without inflating the counter.
    let needRecord = true;
    try {
      needRecord = sessionStorage.getItem(recordedKey) !== "1";
    } catch {
      // sessionStorage can be unavailable in strict privacy modes.
    }

    const applyCounts = (data: VisitCounts) => {
      if (cancelled) return;
      if (typeof data?.daily !== "number" || typeof data?.total !== "number") return;

      // Ignore a degraded in-memory response once we have a real ledger value.
      if (data.persisted === false && hasPersistedValue.current) return;

      setDaily(data.daily);
      setTotal(data.total);
      if (data.persisted !== false) hasPersistedValue.current = true;
    };

    const refresh = async () => {
      const record = needRecord;
      try {
        const res = await fetch(getVisitsUrl(), {
          method: record ? "POST" : "GET",
          cache: "no-store",
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data: VisitCounts = await res.json();
        applyCounts(data);

        if (record && data.persisted !== false) {
          needRecord = false;
          try {
            sessionStorage.setItem(recordedKey, "1");
          } catch {
            // Ignore storage failures.
          }
        }
      } catch (err) {
        if (!cancelled && (err as Error)?.name !== "AbortError") {
          console.warn("Could not refresh visitor counter:", err);
        }
      }
    };

    void refresh();

    // Poll the read-only endpoint so all open dashboards converge on the same
    // persisted value without creating extra visits.
    const interval = setInterval(() => void refresh(), 60_000);

    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      cancelled = true;
      controller.abort();
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, []);

  if (!mounted) return null;

  if (compact) {
    return (
      <div
        className="flex items-center gap-2 bg-slate-50 border border-slate-200/80 rounded-md px-2.5 py-1 text-xs shadow-xs"
        title={`Total visits: ${total.toLocaleString("en-IN")}`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
        <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Visits</span>
        <Odometer value={total} padLength={6} />
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 shadow-sm rounded-md p-3 flex flex-col items-center gap-3 animate-in fade-in duration-700">
      <div className="flex w-full justify-around items-center">
        <div className="flex flex-col items-center gap-1.5">
          <p className="text-[9px] tracking-wider uppercase font-semibold text-gray-400 mb-0.5">Today</p>
          <Odometer value={daily} padLength={4} />
        </div>

        <div className="w-px h-8 bg-gray-100"></div>

        <div className="flex flex-col items-center gap-1.5">
          <div className="flex items-center gap-1 mb-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <p className="text-[9px] tracking-wider uppercase font-semibold text-gray-400">Total Visits</p>
          </div>
          <Odometer value={total} padLength={6} />
        </div>
      </div>
    </div>
  );
}
