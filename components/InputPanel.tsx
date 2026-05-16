import { Slider } from './ui/Slider';

export default function InputPanel({ params, setParams }) {
  const updateParam = (key, value) => setParams({ ...params, [key]: value });

  return (
    <div className="space-y-6">
      {/* Aerodynamics group */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-mono uppercase tracking-wider text-accent">Aerodynamics</h3>
          <span className="text-[10px] text-gray-500">drag optimization</span>
        </div>
        <div className="space-y-4">
          <ParamField
            label="Nose length"
            unit="mm"
            value={params.noseLength}
            onChange={(v) => updateParam('noseLength', v)}
            min={200}
            max={800}
          />
          <ParamField
            label="Body diameter"
            unit="mm"
            value={params.bodyDiameter}
            onChange={(v) => updateParam('bodyDiameter', v)}
            min={60}
            max={200}
          />
          <ParamField
            label="Fin span"
            unit="mm"
            value={params.finSpan}
            onChange={(v) => updateParam('finSpan', v)}
            min={150}
            max={400}
          />
        </div>
      </div>

      {/* Conditions group */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-mono uppercase tracking-wider text-accent-amber">Flight conditions</h3>
          <span className="text-[10px] text-gray-500">Mach & altitude</span>
        </div>
        <div className="space-y-4">
          <ParamField
            label="Mach number"
            unit="Ma"
            value={params.mach}
            onChange={(v) => updateParam('mach', v)}
            min={0.5}
            max={5.0}
            step={0.1}
          />
          <ParamField
            label="Altitude"
            unit="km"
            value={params.altitude}
            onChange={(v) => updateParam('altitude', v)}
            min={0}
            max={20}
          />
        </div>
      </div>
    </div>
  );
}

// Reusable parameter field with slider + number input
function ParamField({ label, unit, value, onChange, min, max, step = 1 }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <label className="font-mono text-gray-300">{label}</label>
        <span className="font-mono text-accent">
          {value} {unit}
        </span>
      </div>
      <Slider
        value={value}
        onValueChange={onChange}
        min={min}
        max={max}
        step={step}
        className="mb-2"
      />
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full bg-black/40 border border-gray-700 rounded-lg px-3 py-1.5 text-sm font-mono focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition"
        step={step}
      />
    </div>
  );
}
