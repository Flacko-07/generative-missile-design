"use client";

import { useState } from "react";

export default function Home() {
  const [cd, setCd] = useState("0.10");
  const [cl, setCl] = useState("0.00");
  const [cm, setCm] = useState("0.00");
  const [mach, setMach] = useState("0.80");
  const [aoa, setAoa] = useState("5.0");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const params = new URLSearchParams({
        cd,
        cl,
        cm,
        mach,
        aoa,
      });

      const res = await fetch(`/api/design?${params.toString()}`);
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Request failed");
      }

      setResult(data);
    } catch (err: any) {
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 flex flex-col items-center px-4 py-10">
      <div className="w-full max-w-3xl">
        <h1 className="text-2xl md:text-3xl font-semibold mb-4">
          Generative Missile Inverse Design
        </h1>
        <p className="text-sm md:text-base text-slate-300 mb-6">
          Specify target aerodynamic coefficients and flight condition.
          The backend Python generator will return a feasible missile geometry.
        </p>

        <form
          onSubmit={handleSubmit}
          className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6 bg-slate-900/60 border border-slate-800 rounded-lg p-4"
        >
          <Field label="Cd" value={cd} onChange={setCd} step="0.0001" />
          <Field label="Cl" value={cl} onChange={setCl} step="0.0001" />
          <Field label="Cm" value={cm} onChange={setCm} step="0.0001" />
          <Field label="Mach" value={mach} onChange={setMach} step="0.01" />
          <Field label="AoA (deg)" value={aoa} onChange={setAoa} step="0.1" />

          <div className="md:col-span-2 flex items-center justify-end mt-2">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center px-4 py-2 rounded-md bg-emerald-500 hover:bg-emerald-400 disabled:bg-emerald-700 text-slate-950 font-medium text-sm"
            >
              {loading ? "Generating..." : "Generate Design"}
            </button>
          </div>
        </form>

        {error && (
          <div className="mb-4 text-sm text-red-400 bg-red-950/40 border border-red-800 rounded-md px-3 py-2">
            {error}
          </div>
        )}

        {result && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 text-sm overflow-x-auto">
            <h2 className="font-semibold mb-2">Generated Design</h2>
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="py-1 pr-4">Parameter</th>
                  <th className="py-1 pr-4">Value</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(result.design || {}).map(([key, value]) => (
                  <tr key={key} className="border-b border-slate-900">
                    <td className="py-1 pr-4 font-mono text-xs md:text-sm">
                      {key}
                    </td>
                    <td className="py-1 pr-4 font-mono text-xs md:text-sm">
                      {typeof value === "number"
                        ? value.toFixed(4)
                        : String(value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}

function Field({
  label,
  value,
  onChange,
  step,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  step: string;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs md:text-sm">
      <span className="text-slate-300">{label}</span>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md bg-slate-950 border border-slate-700 px-2 py-1 text-xs md:text-sm font-mono focus:outline-none focus:ring-1 focus:ring-emerald-500"
        required
      />
    </label>
  );
}
