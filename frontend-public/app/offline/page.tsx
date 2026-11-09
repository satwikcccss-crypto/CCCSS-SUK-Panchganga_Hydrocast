export default function OfflinePage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white p-6">
      <div className="text-center max-w-sm">
        <div className="text-5xl mb-4">📡</div>
        <h1 className="text-xl font-bold mb-2">You are offline</h1>
        <p className="text-slate-400 text-sm">
          HydroCast needs an internet connection to show live flood forecasts.
          Please check your connection and try again.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="mt-6 px-4 py-2 bg-sky-600 rounded text-sm font-medium hover:bg-sky-500"
        >
          Retry
        </button>
      </div>
    </div>
  );
}
