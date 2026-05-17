import { useState, MouseEventHandler } from 'react';

interface GenerateButtonProps {
  onClick: MouseEventHandler<HTMLButtonElement>;
  isLoading?: boolean;
}

export default function GenerateButton({ onClick, isLoading }: GenerateButtonProps) {
  const [isPressing, setIsPressing] = useState(false);

  return (
    <button
      type="button"
      disabled={isLoading}
      onMouseDown={() => setIsPressing(true)}
      onMouseUp={() => setIsPressing(false)}
      onMouseLeave={() => setIsPressing(false)}
      onClick={onClick}
      className={`w-full py-4 bg-gradient-to-r from-accent to-cyan-600 text-black font-bold rounded-xl text-lg transition-all duration-75 flex items-center justify-center gap-2 ${
        isPressing && !isLoading ? 'scale-95' : 'scale-100'
      } ${isLoading ? 'opacity-60 cursor-not-allowed' : ''} hover:shadow-[0_0_24px_#00ffff] hover:from-cyan-400 hover:to-cyan-600`}
    >
      <span className="text-xl">⚡</span>
      {isLoading ? 'Generating…' : 'Generate design'}
    </button>
  );
}
