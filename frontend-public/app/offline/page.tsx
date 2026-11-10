"use client";

import React from "react";

export default function OfflinePage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-800 p-6">
      <div className="text-center max-w-sm bg-white border border-slate-200 rounded-xl p-8 shadow-sm">
        <div className="text-5xl mb-4">📡</div>
        <h1 className="text-xl font-bold mb-2 text-slate-900">You are offline</h1>
        <p className="text-slate-600 text-sm">
          HydroCast needs an internet connection to show live flood forecasts and telemetry.
          Please check your network connection and try again.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="mt-6 px-4 py-2 bg-sky-600 text-white rounded-lg text-sm font-medium hover:bg-sky-700 transition-colors shadow-sm"
        >
          Retry Connection
        </button>
      </div>
    </div>
  );
}
