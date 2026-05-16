import { useState } from 'react';

export default function GenerateButton({ onClick }) {
  const [isPressing, setIsPressing] = useState(false);

  return (
    <button
      onMouseDown={() => setIsPressing(true)}
      onMouseUp={() => setIsPressing(false)}
      onMouseLeave={() => setIsPressing(false)}
      onClick={onClick}
      className={`w-full py-4 bg-gradient-to-r from-accent to-cyan-600 text-black font-bold rounded-xl text-lg transition-all duration-75 flex items-center justify-center gap-2 ${
        isPressing ? 'scale-95' : 'scale-100'
      } hover:shadow-[0_0_24px_#00ffff] hover:from-cyan-400 hover:to-cyan-600`}
    >
      <span className="text-xl">⚡</span> Generate design
    </button>
  );
}
