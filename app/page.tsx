"use client";

import { useState } from "react";

const PARAM_META: Record<string, { unit: string; min: number; max: number; description: string }> = {
  nose_length:     { unit: "m",  min: 0.2,   max: 2.5,  description: "Nose cone length" },
  body_diameter:   { unit: "m",  min: 0.15,  max: 0.6,  description: "Body outer diameter" },
  body_length:     { unit: "m",  min: 0.8,   max: 7.0,  description: "Total body length" },
  fin_span:        { unit: "m",  min: 0.0,   max: 1.2,  description: "Fin full span" },
  fin_chord:       { unit: "m",  min: 0.0,   max: 0.8,  description: "Fin root chord" },
  fin_thickness:   { unit: "m",  min: 0.0,   max: 0.08, description: "Fin thickness" },
  fin_sweep_deg:   { unit: "°",  min: -45,   max: 45,   description: "Fin sweep angle" },
  fin_offset:      { unit: "m",  min: -0.2,  max: 0.5,  description: "Fin axial offset" },
  flare_angle_deg: { unit: "°",  min: 0.0,   max: 15,   description: "Boattail / flare angle" },
  flare_length:    { unit: "m",  min: 0.0,   max: 0.5,  description: "Flare section length" },
};

function getMachRegime(mach: number) {
  if (mach < 0.8)  return { label: "Subsonic",    cls: "regime-sub" };
  if (mach < 1.2)  return { label: "Transonic",   cls: "regime-trans" };
  if (mach < 5.0)  return { label: "Supersonic",  cls: "regime-super" };
  return             { label: "Hypersonic",  cls: "regime-hyper" };
}

type DesignResult = {
  inputs: { Cd: number; Cl: number; Cm: number; Mach: number; AoA: number };
  design: Record<string, number>;
};

export default function Home() {
  const [fields, setFields] = useState({ cd: "0.10", cl: "0.00", cm: "0.00", mach: "0.80", aoa: "5.0" });
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const [result,  setResult]  = useState<DesignResult | null>(null);

  function setField(key: keyof typeof fields, value: string) {
    setFields((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const params = new URLSearchParams(fields);
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

  const machNum = parseFloat(fields.mach);
  const regime  = getMachRegime(isNaN(machNum) ? 0 : machNum);

  return (
    <>
      {/* ── Nav ── */}
      <nav className="navbar" aria-label="Site navigation">
        <div className="navbar-inner">
          <a href="#" className="nav-logo" aria-label="Home">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
              {/* Missile silhouette mark */}
              <path d="M14 3 L17 10 L17 20 L14 25 L11 20 L11 10 Z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
              <path d="M11 18 L7 22" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              <path d="M17 18 L21 22" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              <circle cx="14" cy="9" r="1.5" fill="currentColor" />
            </svg>
            <span>MissileGAN</span>
          </a>
          <div className="nav-links">
            <span className="nav-status">
              <span className="status-dot" aria-hidden="true" />
              GAN Ready
            </span>
            <a
              href="https://github.com/Flacko-07/generative-missile-design"
              target="_blank"
              rel="noopener noreferrer"
              className="nav-link"
              aria-label="GitHub repository"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z" />
              </svg>
              GitHub
            </a>
          </div>
        </div>
      </nav>

      <main className="page">
        <div className="container">

          {/* ── Hero ── */}
          <header className="hero">
            <div className="hero-eyebrow">
              <span className={`regime-badge ${regime.cls}`}>{regime.label}</span>
              <span className="hero-eyebrow-text">Conditional GAN · Inverse Design</span>
            </div>
            <h1 className="hero-title">
              Generative <span className="accent">Missile</span> Design
            </h1>
            <p className="hero-sub">
              Specify target aerodynamic coefficients and flight condition.
              The generator returns a physically feasible 10-parameter geometry.
            </p>
          </header>

          {/* ── Form ── */}
          <form onSubmit={handleSubmit}>
            <div className="card">
              <div className="card-header">
                <span className="card-title">Target Aerodynamic Condition</span>
                <span className={`regime-badge ${regime.cls}`}>{regime.label} · Ma {fields.mach}</span>
              </div>
              <div className="form-grid">
                <FormField id="cd"   label="Drag Coeff." unit="Cd"  step="0.0001" value={fields.cd}   onChange={(v) => setField("cd", v)} />
                <FormField id="cl"   label="Lift Coeff." unit="Cl"  step="0.0001" value={fields.cl}   onChange={(v) => setField("cl", v)} />
                <FormField id="cm"   label="Pitch Moment" unit="Cm" step="0.0001" value={fields.cm}   onChange={(v) => setField("cm", v)} />
                <FormField id="mach" label="Mach Number" unit="Ma"  step="0.01"   value={fields.mach} onChange={(v) => setField("mach", v)} />
                <FormField id="aoa"  label="Angle of Attack" unit="°" step="0.1" value={fields.aoa}  onChange={(v) => setField("aoa", v)} />
              </div>
              <div className="form-footer">
                {result && (
                  <button type="button" className="btn-ghost" onClick={handleReset}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                      <path d="M3 3v5h5" />
                    </svg>
                    Reset
                  </button>
                )}
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? <span className="spinner" role="status" aria-label="Generating" /> : (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                  )}
                  {loading ? "Generating…" : "Generate Design"}
                </button>
              </div>
            </div>
          </form>

          {/* ── Error ── */}
          {error && (
            <div className="alert alert-error" role="alert">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, marginTop: "1px" }} aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
              {error}
            </div>
          )}

          {/* ── Results ── */}
          {result && (
            <div className="card result-card">
              <div className="result-card-header">
                <div className="result-title-row">
                  <h2 className="result-title">Generated Geometry</h2>
                  <span className="badge-feasible">
                    <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor" aria-hidden="true"><circle cx="4" cy="4" r="4" /></svg>
                    Feasible
                  </span>
                </div>
                {/* Input echo chips */}
                <div className="inputs-row" aria-label="Input conditions">
                  {Object.entries(result.inputs).map(([k, v], i, arr) => (
                    <span key={k} className="input-chip">
                      <span className="input-chip-label">{k}</span>
                      <span className="input-chip-value">{(v as number).toFixed(4)}</span>
                      {i < arr.length - 1 && <span className="chip-sep" aria-hidden="true" />}
                    </span>
                  ))}
                </div>
              </div>

              {/* Params table */}
              <table className="design-table" aria-label="Missile geometry parameters">
                <thead>
                  <tr>
                    <th>Parameter</th>
                    <th>Description</th>
                    <th>Value</th>
                    <th style={{ width: "110px" }}>Range</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.design).map(([key, value]) => {
                    const meta = PARAM_META[key];
                    const pct  = meta ? Math.max(0, Math.min(100, ((value - meta.min) / (meta.max - meta.min)) * 100)) : 50;
                    const barColor = pct > 80 ? "var(--color-warn)" : pct < 20 ? "var(--color-blue)" : "var(--color-primary)";
                    return (
                      <tr key={key}>
                        <td><code className="param-name">{key}</code></td>
                        <td className="param-desc">{meta?.description ?? "—"}</td>
                        <td>
                          <span className="param-value">{value.toFixed(4)}</span>
                          {meta && <span className="param-unit">{meta.unit}</span>}
                        </td>
                        <td>
                          <div className="param-bar-wrap" role="meter" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100} aria-label={`${Math.round(pct)}% of range`}>
                            <div className="param-bar-fill" style={{ width: `${pct}%`, background: barColor }} />
                            <span className="param-bar-pct">{Math.round(pct)}%</span>
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
  id, label, unit, step, value, onChange,
}: {
  id: string;
  label: string;
  unit: string;
  step: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="input-wrap">
        <input
          id={id}
          type="number"
          step={step}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required
          inputMode="decimal"
        />
        <span className="input-unit" aria-hidden="true">{unit}</span>
      </div>
    </div>
  );
}
