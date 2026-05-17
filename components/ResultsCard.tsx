import { useState } from 'react';

interface ResultsCardProps {
  results: {
    ldRatio: number;
    cd: number;
  };
  params: any;
}

export default function ResultsCard({ results, params }: ResultsCardProps) {
  const [copied, setCopied] = useState(false);

  const exportData = {
    geometry: params.apiDesign ?? params,
    aerodynamics: {
      ldRatio: results.ldRatio,
      dragCoefficient: results.cd,
    },
    timestamp: new Date().toISOString(),
  };

  const copyJSON = () => {
    navigator.clipboard.writeText(JSON.stringify(exportData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="glass-card p-6 space-y-4">
      <h3 className="text-sm font-mono uppercase tracking-wider text-accent">Design Output</h3>
      <pre className="bg-black/50 p-4 rounded-lg text-xs font-mono overflow-x-auto">
        {JSON.stringify(exportData.geometry, null, 2)}
      </pre>
      <button
        onClick={copyJSON}
        className="w-full flex items-center justify-center gap-2 bg-gray-800 hover:bg-gray-700 text-white text-sm py-2 rounded-lg transition"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M8 4v12h12V4H8zM4 8v12h12" strokeWidth="2" />
        </svg>
        {copied ? 'Copied!' : 'Copy as JSON'}
      </button>
    </div>
  );
}
