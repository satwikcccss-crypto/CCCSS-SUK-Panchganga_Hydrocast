"use client";
// frontend/components/StageGauge.tsx

interface Props {
  stage: number;           // current water level (m)
  forecastStage?: number;  // predicted peak (m)
  forecastTime?: string;   // timing of peak
  minH?: number;           // gauge range min (m) MSL
  maxH?: number;           // gauge range max (m) MSL
  alert?: number;          // alert stage (m)
  warning?: number;        // warning stage (m)
  danger?: number;         // danger stage (m)
  hfl?: number;            // highest flood level (m)
}

const getAlertConfig = (h: number, danger: number, warning: number, alert: number) => {
  if (h >= danger) return { color: "bg-red-500", grad: "from-red-600 to-red-400", textCol: "text-red-700", label: "DANGER" };
  if (h >= warning) return { color: "bg-orange-500", grad: "from-orange-600 to-orange-400", textCol: "text-orange-700", label: "WARNING" };
  if (h >= alert) return { color: "bg-yellow-500", grad: "from-yellow-500 to-yellow-300", textCol: "text-yellow-700", label: "ALERT" };
  return { color: "bg-sky-500", grad: "from-sky-600 to-sky-400", textCol: "text-sky-700", label: "NORMAL" };
};

export default function StageGauge({
  stage,
  forecastStage,
  forecastTime,
  minH = 528,
  maxH = 545,
  alert = 533.5,
  warning = 535.5,
  danger = 536.8,
  hfl = 538.5,
}: Props) {
  const config = getAlertConfig(stage, danger, warning, alert);
  const range = maxH - minH;
  const pct = (val: number) => Math.min(100, Math.max(0, ((val - minH) / range) * 100));

  // Ticks every 1m
  const ticks = Array.from({ length: Math.ceil(range) + 1 }, (_, i) => Math.floor(minH) + i).filter(t => t >= minH && t <= maxH);

  const thresholds = [
    { val: alert, col: 'border-yellow-500', bg: 'bg-yellow-500', label: 'ALERT' },
    { val: warning, col: 'border-orange-500', bg: 'bg-orange-500', label: 'WARNING' },
    { val: danger, col: 'border-red-600', bg: 'bg-red-600', label: 'DANGER' },
    { val: hfl, col: 'border-purple-600', bg: 'bg-purple-600', label: 'HFL' },
  ];

  return (
    <div className="w-full flex flex-col items-center font-sans">
      {forecastTime && (
        <div className="mb-4 text-center">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest block mb-1">Forecast Peak</span>
          <span className="text-sm font-bold text-cyan-800 bg-cyan-50 border border-cyan-200 px-3 py-1 rounded-md shadow-sm">
            {forecastTime}
          </span>
        </div>
      )}

      <div className="flex w-full justify-center">
        {/* Left: Forecast & Current Badges */}
        <div className="w-24 relative pr-3">
          {forecastStage !== undefined && (
            <div 
              className="absolute right-0 flex flex-col items-end z-30 transition-all duration-500"
              style={{ bottom: `${pct(forecastStage)}%`, transform: 'translateY(50%)' }}
            >
              <div className="text-[11px] font-bold text-cyan-600 mb-1 tracking-wider uppercase animate-pulse">Forecast</div>
              <div className="flex items-center gap-1.5 bg-white border border-cyan-300 rounded-md shadow-md px-2 py-1">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
                <span className="text-sm font-mono font-bold text-cyan-800">{forecastStage.toFixed(2)}m</span>
              </div>
            </div>
          )}
          <div 
            className="absolute right-0 flex flex-col items-end z-20 transition-all duration-500"
            style={{ bottom: `${pct(stage)}%`, transform: 'translateY(50%)' }}
          >
            <div className={`text-[11px] font-bold ${config.textCol} mb-1 tracking-wider uppercase`}>Current</div>
            <div className={`flex items-center gap-1.5 bg-white border rounded-md shadow-md px-2 py-1 ${config.color.replace('bg-', 'border-')}`}>
              <span className={`w-2 h-2 rounded-full ${config.color}`}></span>
              <span className={`text-sm font-mono font-bold ${config.textCol}`}>{stage.toFixed(2)}m</span>
            </div>
          </div>
        </div>

        {/* Middle: Enterprise Level Staff (Realistic look) */}
        <div className="relative h-80 w-20 bg-white border-2 border-slate-800 rounded shadow-[inset_0_2px_10px_rgba(0,0,0,0.1)] flex overflow-hidden">
          {/* Staff markings (Left half of staff) */}
          <div className="w-1/2 h-full border-r-2 border-slate-800 bg-white relative z-10">
            {ticks.map(t => (
              <div key={`tick-${t}`}>
                {/* Major tick line */}
                <div 
                  className="absolute right-0 w-full border-t-[4px] border-black"
                  style={{ bottom: `${pct(t)}%`, transform: 'translateY(50%)' }}
                />
                {/* Large Red Number for Whole Meter */}
                <div 
                  className="absolute left-0 w-full text-center text-red-600 font-bold font-mono leading-none tracking-tighter text-[16px] z-20 bg-white/80"
                  style={{ bottom: `${pct(t)}%`, transform: 'translateY(50%)' }}
                >
                  {t}
                </div>
              </div>
            ))}
            
            {/* Sub-ticks for every 0.1m */}
            {Array.from({ length: Math.ceil(range * 10) }, (_, i) => minH + (i / 10)).map(t => {
              if (Math.abs(t % 1) < 0.01) return null; // Skip whole numbers
              const isHalf = Math.abs((t * 10) % 5) < 0.01;
              return (
                <div 
                  key={`sub-${t.toFixed(1)}`} 
                  className={`absolute right-0 border-t-[3px] border-black ${isHalf ? 'w-full' : 'w-1/2'}`}
                  style={{ bottom: `${pct(t)}%`, transform: 'translateY(50%)' }}
                >
                  {/* Small number for tenths on the half mark */}
                  {isHalf && (
                    <span className="absolute left-1 -top-1.5 text-[8px] font-bold text-black font-mono leading-none">
                      {(t % 1).toFixed(1).replace('0.', '')}
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Water and Thresholds (Right half of staff) */}
          <div className="w-1/2 h-full relative bg-slate-100 z-0">
            {/* Current Water Level Fill */}
            <div 
              className={`absolute bottom-0 w-full bg-gradient-to-t ${config.grad} opacity-95 transition-all duration-1000 ease-out border-t-[3px] border-white/60 shadow-[0_-4px_12px_rgba(0,0,0,0.15)]`}
              style={{ height: `${pct(stage)}%` }}
            >
              {/* Premium ripples */}
              <div className="absolute top-0 w-full h-1 bg-white/50" />
              <div className="absolute top-1.5 w-full h-0.5 bg-white/30" />
              <div className="absolute top-3 w-full h-0.5 bg-white/20" />
            </div>

            {/* Threshold Lines */}
            {thresholds.map(t => (
              <div 
                key={t.label}
                className={`absolute w-full border-t-[3px] ${t.col} z-20`}
                style={{ bottom: `${pct(t.val)}%`, transform: 'translateY(50%)' }}
              />
            ))}

            {/* Forecast Glowing Line */}
            {forecastStage !== undefined && (
              <div 
                className="absolute w-[250%] -ml-[150%] h-[3px] bg-cyan-400 z-30 shadow-[0_0_15px_6px_rgba(34,211,238,0.8)] animate-pulse"
                style={{ bottom: `${pct(forecastStage)}%`, transform: 'translateY(50%)' }}
              />
            )}
          </div>
        </div>

        {/* Right: Threshold Labels */}
        <div className="w-24 relative pl-3">
          {thresholds.map(t => (
            <div 
              key={t.label}
              className="absolute left-0 flex flex-col items-start"
              style={{ bottom: `${pct(t.val)}%`, transform: 'translateY(50%)' }}
            >
              <div className={`text-[10px] font-bold text-white ${t.bg} px-1.5 py-0.5 rounded shadow-sm tracking-wide uppercase`}>
                {t.label}
              </div>
              <div className="text-xs font-mono text-slate-600 font-semibold mt-0.5 ml-0.5">
                {t.val.toFixed(1)}m
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-6 text-center">
        <div className={`text-sm font-bold ${config.textCol} px-4 py-1.5 bg-white rounded-md border shadow-sm flex items-center justify-center gap-2`}>
          <span className={`w-2.5 h-2.5 rounded-full ${config.color} animate-pulse`}></span>
          STATUS: {config.label}
        </div>
      </div>
    </div>
  );
}
