"use client";

import { useEffect, useState } from "react";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function DigitRoll({ digit }: { digit: string }) {
  // Use translateY to simulate the mechanical roll of an odometer
  return (
    <div className="relative w-4 h-[22px] overflow-hidden text-center bg-white border-y border-gray-300 font-mono text-sm font-bold text-gray-800 shadow-inner mx-[0.5px]">
      <div
        className="absolute top-0 left-0 w-full flex flex-col transition-transform duration-[1200ms] ease-out"
        style={{ transform: `translateY(-${parseInt(digit) * 22}px)` }}
      >
        {Array.from({ length: 10 }).map((_, i) => (
          <span key={i} className="flex items-center justify-center h-[22px] w-full bg-gradient-to-b from-gray-100 via-white to-gray-100">
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
    // Delay animation slightly to allow initial render at 0
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

export default function VisitorCounterWidget() {
  const [daily, setDaily] = useState(0);
  const [total, setTotal] = useState(0);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    fetch(`${BASE_URL}/api/v1/visits/record`, { method: "POST" })
      .then((res) => {
        if (!res.ok) throw new Error("Network response was not ok");
        return res.json();
      })
      .then((data) => {
        setDaily(data.daily || 0);
        setTotal(data.total || 0);
      })
      .catch((err) => console.error("Error fetching visitor stats:", err));
  }, []);

  if (!mounted) return null;

  return (
    <div className="bg-white border border-gray-200 shadow-sm rounded-md p-3 flex flex-col items-center gap-3 animate-in fade-in duration-700">
      <div className="flex w-full justify-around items-center">
        <div className="flex flex-col items-center gap-1.5">
          <p className="text-[9px] tracking-wider uppercase font-semibold text-gray-400 mb-0.5">Today</p>
          <Odometer value={daily} padLength={4} />
        </div>
        
        <div className="w-px h-8 bg-gray-100"></div>

        <div className="flex flex-col items-center gap-1.5">
          <p className="text-[9px] tracking-wider uppercase font-semibold text-gray-400 mb-0.5">Total Visits</p>
          <Odometer value={total} padLength={6} />
        </div>
      </div>
    </div>
  );
}
