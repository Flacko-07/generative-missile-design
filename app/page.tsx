"use client";

import { useState } from "react";

const PARAM_META: Record<string, { unit: string; min: number; max: number; description: string }> = {
  nose_length:     { unit: "m",  min: 0.2,   max: 2.5,  description: "Length of nose cone" },
  body_diameter:   { unit: "m",  min: 0.15,  max: 0.6,  description: "Body outer diameter" },
  body_length:     { unit: "m",  min: 0.8,   max: 7.0,  description: "Total body length" },
  fin_span:        { unit: "m",  min: 0.0,   max: 1.2,  description: "Fin full span" },
  fin_chord:       { unit: "m",  min: 0.0,   max: 0.8,  description: "Fin root chord" },
  fin_thickness:   { unit: "m",  min: 0.0,   max: 0.08, description: "Fin thickness" },
  fin_sweep_deg:   { unit: "°",  min: -45,   max: 45,   description: "Fin sweep angle" },
  fin_offset:      { unit: "m",  min: -0.2,  max: 0.5,  description: "Fin axial offset" },
  flare_angle_deg: { unit: "°",  min: 0.0,   max: 15,   description: "Boattail/flare angle" },
  flare_length:    { unit: "m",  min: 0.0,   max: 0.5,  description: "Flare section length" },
};

type DesignResult = {
  inputs: { Cd: number; Cl: number; Cm: number; Mach: number; AoA: number };
  design: Record<string, number>;
};

export default function Home() {
  const [fields, setFields] = useState({
    cd:   "0.10",
    cl:   "0.00",
    cm:   "0.00",
    mach: "0.80",
    aoa:  "5.0",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);
  const [result, setResult]   = useState<DesignResult | null>(null);

  function setField(key: keyof typeof fields, value: string) {
    setFields((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const params = new URLSearchParams({
        cd:   fields.cd,
        cl:   fields.cl,
        cm:   fields.cm,
        mach: fields.mach,
        aoa:  fields.aoa,
      });
      const res  = await fetch(`/api/design?${params}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
      setResult(data as DesignResult);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setResult(null);
    setError(null);
    setFields({ cd: "0.10", cl: "0.00", cm: "0.00", mach: "0.80", aoa: "5.0" });
  }

  return (
    <>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');`}</style>
      <main className="page">
        <div className="container">
          {/* Header */}
          <header className="header">
            <h1>
              <span className="header-icon" aria-hidden="true">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                  <path d="M2 17l10 5 10-5"/>
                  <path d="M2 12l10 5 10-5"/>
                </svg>
              </span>
              Generative Missile Inverse Design
            </h1>
            <p>
              Specify target aerodynamic coefficients and flight condition. The conditional GAN
              generator returns a physically feasible 10-parameter missile geometry.
            </p>
          </header>

          {/* Form */}
          <form onSubmit={handleSubmit}>
            <div className="card">
              <div className="card-title">Target Aerodynamic Condition</div>
              <div className="form-grid">
                <FormField id="cd"   label="Drag Coefficient" hint="Cd" step="0.0001" value={fields.cd}   onChange={(v) => setField("cd", v)} />
                <FormField id="cl"   label="Lift Coefficient" hint="Cl" step="0.0001" value={fields.cl}   onChange={(v) => setField("cl", v)} />
                <FormField id="cm"   label="Pitching Moment"  hint="Cm" step="0.0001" value={fields.cm}   onChange={(v) => setField("cm", v)} />
                <FormField id="mach" label="Mach Number"      hint="Ma" step="0.01"   value={fields.mach} onChange={(v) => setField("mach", v)} />
                <FormField id="aoa"  label="Angle of Attack"  hint="°"  step="0.1"    value={fields.aoa}  onChange={(v) => setField("aoa", v)} />
              </div>
              <div className="form-footer">
                {result && (
                  <button type="button" className="btn-ghost" onClick={handleReset}>
                    Reset
                  </button>
                )}
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? <span className="spinner" role="status" aria-label="Generating" /> : null}
                  {loading ? "Generating…" : "Generate Design"}
                </button>
              </div>
            </div>
          </form>

          {/* Error */}
          {error && (
            <div className="alert alert-error" role="alert">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, marginTop: "2px" }}>
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
              {error}
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="card">
              <div className="results-header">
                <h2>Generated Geometry</h2>
                <span className="badge">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                    <circle cx="12" cy="12" r="10"/>
                  </svg>
                  Feasible
                </span>
              </div>

              {/* Input echo */}
              <div className="inputs-row" aria-label="Input conditions">
                {Object.entries(result.inputs).map(([k, v], i, arr) => (
                  <>
                    <span key={k} className="input-chip">
                      <span className="input-chip-label">{k}</span>
                      <span className="input-chip-value">{(v as number).toFixed(4)}</span>
                    </span>
                    {i < arr.length - 1 && <span key={k+"-div"} className="divider" aria-hidden="true" />}
                  </>
                ))}
              </div>

              {/* Design table */}
              <table className="design-table" aria-label="Missile geometry parameters">
                <thead>
                  <tr>
                    <th>Parameter</th>
                    <th>Description</th>
                    <th>Value</th>
                    <th style={{ width: "100px" }}>Range</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.design).map(([key, value]) => {
                    const meta = PARAM_META[key];
                    const pct  = meta ? Math.max(0, Math.min(100, ((value - meta.min) / (meta.max - meta.min)) * 100)) : 50;
                    return (
                      <tr key={key}>
                        <td><span className="param-name">{key}</span></td>
                        <td style={{ color: "var(--color-text-muted)", fontSize: "var(--text-xs)" }}>
                          {meta?.description ?? "—"}
                        </td>
                        <td>
                          <span className="param-value">{value.toFixed(4)}</span>
                          {meta && <span className="param-unit">{meta.unit}</span>}
                        </td>
                        <td>
                          <div className="param-bar-wrap" aria-label={`${Math.round(pct)}% of range`}>
                            <div className="param-bar-fill" style={{ width: `${pct}%` }} />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <footer className="footer">
            <a href="https://github.com/Flacko-07/generative-missile-design" target="_blank" rel="noopener noreferrer">
              generative-missile-design
            </a>
            {" — Conditional GAN Inverse Design"}
          </footer>
        </div>
      </main>
    </>
  );
}

function FormField({
  id, label, hint, step, value, onChange,
}: {
  id: string;
  label: string;
  hint: string;
  step: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        inputMode="decimal"
      />
      <span className="hint">{hint}</span>
    </div>
  );
}
