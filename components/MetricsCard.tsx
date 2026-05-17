interface MetricsCardProps {
  ldRatio: number;
  totalLength: number;
  finArea: number;
}

export default function MetricsCard({ ldRatio, totalLength, finArea }: MetricsCardProps) {
  return (
    <div className="glass-card p-5 grid grid-cols-3 divide-x divide-white/10">
      <div className="text-center">
        <div className="text-3xl font-bold text-accent">{ldRatio.toFixed(2)}</div>
        <div className="text-[11px] font-mono text-gray-400 uppercase mt-1">L/D ratio</div>
      </div>
      <div className="text-center">
        <div className="text-3xl font-bold text-accent-amber">{totalLength.toFixed(0)}</div>
        <div className="text-[11px] font-mono text-gray-400 uppercase mt-1">Length (mm)</div>
      </div>
      <div className="text-center">
        <div className="text-3xl font-bold text-white">{finArea.toFixed(0)}</div>
        <div className="text-[11px] font-mono text-gray-400 uppercase mt-1">Fin area (cm²)</div>
      </div>
    </div>
  );
}
