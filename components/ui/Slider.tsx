interface SliderProps {
  value: number;
  onValueChange: (value: number) => void;
  min: number;
  max: number;
  step: number;
  className?: string;
}

export function Slider({ value, onValueChange, min, max, step, className }: SliderProps) {
  const percentage = ((value - min) / (max - min)) * 100;

  return (
    <div className={`relative ${className}`}>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onValueChange(parseFloat(e.target.value))}
        className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer"
        style={{
          background: `linear-gradient(to right, #00ffff 0%, #00ffff ${percentage}%, #2a2f3f ${percentage}%, #2a2f3f 100%)`,
        }}
      />
      <style jsx>{`
        input[type='range']::-webkit-slider-thumb {
          appearance: none;
          width: 16px;
          height: 16px;
          background: #00ffff;
          border-radius: 50%;
          cursor: pointer;
          box-shadow: 0 0 8px #00ffff;
          transition: transform 0.1s;
        }
        input[type='range']::-webkit-slider-thumb:hover {
          transform: scale(1.25);
        }
      `}</style>
    </div>
  );
}
