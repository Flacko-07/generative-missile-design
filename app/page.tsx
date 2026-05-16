"use client";

import { FormEvent, useMemo, useState } from "react";

type FieldKey = "cd" | "cl" | "cm" | "mach" | "aoa";
type InputKey = "Cd" | "Cl" | "Cm" | "Mach" | "AoA";
type ParamKey =
  | "nose_length"
  | "body_diameter"
  | "body_length"
  | "fin_span"
  | "fin_chord"
  | "fin_thickness"
  | "fin_sweep_deg"
  | "fin_offset"
  | "flare_angle_deg"
  | "flare_length";

type FieldConfig = {
  key: FieldKey;
  label: string;
  symbol: string;
  step: string;
  min: string;
  max: string;
  hint: string;
};

type ParamMeta = {
  label: string;
  unit: string;
  min: number;
  max: number;
  description: string;
  group: "nose" | "body" | "fin" | "flare";
};

type DesignResult = {
  inputs: Record<InputKey, number>;
  design: Record<ParamKey, number>;
};

type Metric = {
  label: string;
  value: string;
  detail: string;
  icon: string;
};

const FIELD_CONFIGS: FieldConfig[] = [
  { key: "cd", label: "Drag coefficient", symbol: "Cd", step: "0.001", min: "-1", max: "2", hint: "0.05 – 0.30 typical" },
  { key: "cl", label: "Lift coefficient", symbol: "Cl", step: "0.001", min: "-2", max: "2", hint: "-0.5 – 0.5 typical" },
  { key: "cm", label: "Pitching moment", symbol: "Cm", step: "0.001", min: "-2", max: "2", hint: "Near 0 for stability" },
  { key: "mach", label: "Mach number", symbol: "Ma", step: "0.05", min: "0.05", max: "8", hint: "0.8 subsonic · 2.5 supersonic" },
  { key: "aoa", label: "Angle of attack", symbol: "α", step: "0.5", min: "-20", max: "30", hint: "Degrees" },
];

const DESIGN_KEYS: ParamKey[] = [
  "nose_length", "body_diameter", "body_length",
  "fin_span", "fin_chord", "fin_thickness", "fin_sweep_deg", "fin_offset",
  "flare_angle_deg", "flare_length",
];

const PARAM_META: Record<ParamKey, ParamMeta> = {
  nose_length:     { label: "Nose length",     unit: "m",   min: 0.2,  max: 2.5,  description: "Forward ogive/cone section",        group: "nose"  },
  body_diameter:   { label: "Body diameter",   unit: "m",   min: 0.15, max: 0.6,  description: "Outer cylindrical diameter",         group: "body"  },
  body_length:     { label: "Body length",     unit: "m",   min: 0.8,  max: 7.0,  description: "Primary fuselage length",           group: "body"  },
  fin_span:        { label: "Fin span",         unit: "m",   min: 0,    max: 1.2,  description: "Full stabilizer span",             group: "fin"   },
  fin_chord:       { label: "Fin chord",        unit: "m",   min: 0,    max: 0.8,  description: "Root chord length",                group: "fin"   },
  fin_thickness:   { label: "Fin thickness",    unit: "m",   min: 0,    max: 0.08, description: "Stabilizer section thickness",     group: "fin"   },
  fin_sweep_deg:   { label: "Fin sweep",        unit: "°",   min: -45,  max: 45,   description: "Leading edge sweep angle",         group: "fin"   },
  fin_offset:      { label: "Fin offset",       unit: "m",   min: -0.2, max: 0.5,  description: "Axial fin station adjustment",     group: "fin"   },
  flare_angle_deg: { label: "Flare angle",      unit: "°",   min: 0,    max: 15,   description: "Aft flare or boattail angle",     group: "flare" },
  flare_length:    { label: "Flare length",     unit: "m",   min: 0,    max: 0.5,  description: "Aft transition section length",   group: "flare" },
};

const GROUP_LABELS: Record<string, string> = {
  nose: "Nose", body: "Body", fin: "Fins", flare: "Flare / Aft",
};
const GROUP_ORDER = ["nose", "body", "fin", "flare"];

const DEFAULT_FIELDS: Record<FieldKey, string> = {
  cd: "0.100", cl: "0.000", cm: "0.000", mach: "0.80", aoa: "5.0",
};

const PREVIEW_DESIGN: Record<ParamKey, number> = {
  nose_length: 0.56, body_diameter: 0.32, body_length: 2.98,
  fin_span: 0.12,    fin_chord: 0.12,     fin_thickness: 0.015,
  fin_sweep_deg: 11.5, fin_offset: 0.025, flare_angle_deg: 6.2, flare_length: 0.13,
};

const PRESETS = [
  { label: "Subsonic cruise",  values: { cd: "0.08",  cl: "0.12",  cm: "0.01",  mach: "0.70", aoa: "3.0"  } },
  { label: "Transonic",        values: { cd: "0.18",  cl: "0.00",  cm: "0.00",  mach: "1.10", aoa: "0.0"  } },
  { label: "Supersonic dash",  values: { cd: "0.22",  cl: "-0.05", cm: "-0.02", mach: "2.50", aoa: "5.0"  } },
  { label: "Hypersonic",       values: { cd: "0.35",  cl: "0.08",  cm: "-0.10", mach: "6.00", aoa: "8.0"  } },
];

async function fetchWithRetry(url: string, maxAttempts = 3): Promise<Response> {
  let lastErr: unknown;
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      return res;
    } catch (err) {
      lastErr = err;
      if (i < maxAttempts - 1) await new Promise(r => setTimeout(r, 600 * (i + 1)));
    }
  }
  throw lastErr;
}

export default function Home() {
  const [fields, setFields] = useState<Record<FieldKey, string>>(DEFAULT_FIELDS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DesignResult | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<"table" | "json">("table");

  const metrics = useMemo(() => buildMetrics(result?.design ?? PREVIEW_DESIGN, Boolean(result)), [result]);
  const runState = loading ? "running" : error ? "error" : result ? "complete" : "ready";

  function setField(key: FieldKey, value: string) {
    setFields(prev => ({ ...prev, [key]: value }));
  }

  function applyPreset(preset: typeof PRESETS[0]) {
    setFields(prev => ({ ...prev, ...preset.values }));
    setResult(null);
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setCopied(false);

    const params = new URLSearchParams({
      cd: fields.cd, cl: fields.cl, cm: fields.cm, mach: fields.mach, aoa: fields.aoa,
    });

    try {
      const response = await fetchWithRetry(`/api/design?${params.toString()}`);
      let data: Record<string, unknown>;
      try {
        data = await response.json();
      } catch {
        throw new Error(`Server returned non-JSON response (status ${response.status}). The model may still be warming up — try again in a few seconds.`);
      }

      if (!response.ok || (data as { error?: string }).error) {
        throw new Error(
          (data as { error?: string }).error ||
          `Request failed with status ${response.status}`
        );
      }

      setResult(data as DesignResult);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "The design request failed.");
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setFields(DEFAULT_FIELDS);
    setResult(null);
    setError(null);
    setCopied(false);
  }

  async function handleCopy() {
    if (!result) return;
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  const groupedKeys = GROUP_ORDER.map(group => ({
    group,
    keys: DESIGN_KEYS.filter(k => PARAM_META[k].group === group),
  }));

  return (
    <main className="app-shell">
      {/* NAV */}
      <nav className="topnav">
        <div className="nav-brand">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
            <polygon points="14,2 26,8 26,20 14,26 2,20 2,8" fill="none" stroke="#4cc9f0" strokeWidth="1.5"/>
            <polygon points="14,6 22,10 22,18 14,22 6,18 6,10" fill="rgba(76,201,240,0.12)" stroke="#4cc9f0" strokeWidth="1"/>
            <circle cx="14" cy="14" r="2.5" fill="#4cc9f0"/>
            <line x1="14" y1="2" x2="14" y2="6" stroke="#4cc9f0" strokeWidth="1.5"/>
          </svg>
          <span>MissileGen <em>v2</em></span>
        </div>
        <div className="nav-center">
          <span>Generative Inverse Design</span>
        </div>
        <div className={`run-badge is-${runState}`}>
          <span className="status-dot" />
          {statusLabel(runState)}
        </div>
      </nav>

      <div className="workspace">
        {/* HERO */}
        <header className="hero-row">
          <div className="hero-text">
            <p className="eyebrow">Conditional GAN · Numpy inference</p>
            <h1>Missile Geometry Console</h1>
            <p className="hero-sub">Enter target aerodynamic coefficients to generate an optimal missile geometry using an inverse-design CGAN trained on CFD-augmented parametric sweep data.</p>
          </div>
          <div className="hero-stats">
            <div className="stat"><strong>10</strong><span>Design params</span></div>
            <div className="stat"><strong>5</strong><span>Input conditions</span></div>
            <div className="stat"><strong>GAN</strong><span>Inference engine</span></div>
          </div>
        </header>

        {/* MAIN LAYOUT */}
        <div className="main-grid">
          {/* LEFT: CONTROL PANEL */}
          <aside className="control-panel">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">Target condition</p>
                <h2>Aerodynamic Inputs</h2>
              </div>
              <button type="button" className="ghost-btn" onClick={handleReset}>Reset</button>
            </div>

            {/* PRESETS */}
            <div className="preset-row">
              <p className="preset-label">Presets</p>
              <div className="preset-chips">
                {PRESETS.map(p => (
                  <button key={p.label} type="button" className="preset-chip" onClick={() => applyPreset(p)}>
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <form id="design-form" onSubmit={handleSubmit}>
              <div className="field-grid">
                {FIELD_CONFIGS.map(config => (
                  <FormField
                    key={config.key}
                    config={config}
                    value={fields[config.key]}
                    onChange={v => setField(config.key, v)}
                  />
                ))}
              </div>

              <button className="primary-btn" type="submit" disabled={loading}>
                {loading ? (
                  <><span className="spinner" /><span>Generating&hellip;</span></>
                ) : (
                  <><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true"><polyline points="5 12 12 5 19 12" /><line x1="12" y1="5" x2="12" y2="19" /></svg><span>Generate design</span></>
                )}
              </button>
            </form>
          </aside>

          {/* RIGHT: PREVIEW */}
          <section className={`preview-panel ${result ? "preview-has-result" : ""}`}>
            <div className="panel-header">
              <div>
                <p className="panel-kicker">Geometry profile</p>
                <h2>{result ? "Generated design" : "Preview"}</h2>
              </div>
              <span className={`result-pill ${result ? "is-live" : ""}`}>
                {result ? "Model output" : "Awaiting run"}
              </span>
            </div>

            <DesignPreview design={result?.design ?? PREVIEW_DESIGN} hasResult={Boolean(result)} loading={loading} />

            <div className="metric-grid">
              {metrics.map(m => (
                <div className="metric-card" key={m.label}>
                  <span className="metric-icon">{m.icon}</span>
                  <strong className={loading ? "skeleton-text" : ""}>{m.value}</strong>
                  <p className="metric-label">{m.label}</p>
                  <small>{m.detail}</small>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* ERROR BANNER */}
        {error && (
          <div className="error-banner" role="alert">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <div>
              <strong>Design request failed</strong>
              <span>{error}</span>
              {error.includes("warm") && <span className="retry-hint">The serverless function cold-starts on first request. Click Generate again — it should work immediately.</span>}
            </div>
            <button className="ghost-btn" onClick={() => setError(null)}>Dismiss</button>
          </div>
        )}

        {/* RESULTS TABLE */}
        <section className={`results-section ${result ? "results-has-result" : ""}`}>
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Numerical output</p>
              <h2>Design Parameters</h2>
            </div>
            <div className="results-actions">
              <div className="tab-group">
                <button
                  className={`tab-btn ${activeTab === "table" ? "is-active" : ""}`}
                  onClick={() => setActiveTab("table")}
                  type="button"
                >Table</button>
                <button
                  className={`tab-btn ${activeTab === "json" ? "is-active" : ""}`}
                  onClick={() => setActiveTab("json")}
                  type="button"
                  disabled={!result}
                >JSON</button>
              </div>
              <button className="ghost-btn" disabled={!result} onClick={handleCopy}>
                {copied ? "✓ Copied" : "Copy JSON"}
              </button>
            </div>
          </div>

          {!loading && result && (
            <div className="result-summary">
              <div className="result-summary-main">
                <span className="result-pill is-live">CGAN result</span>
                <h3>Design snapshot</h3>
                <p>
                  L/D {formatNumber(
                    (result.design.nose_length +
                      result.design.body_length +
                      result.design.flare_length) /
                    Math.max(result.design.body_diameter, 0.001)
                  )},{" "}
                  total length{" "}
                  {formatNumber(
                    result.design.nose_length +
                    result.design.body_length +
                    result.design.flare_length
                  )}{" "}
                  m.
                </p>
              </div>
              <div className="result-summary-chips">
                <span className="summary-chip">
                  <small>Mach</small>
                  <strong>{formatNumber(result.inputs.Mach)}</strong>
                </span>
                <span className="summary-chip">
                  <small>AoA</small>
                  <strong>{formatNumber(result.inputs.AoA)}</strong>
                </span>
                <span className="summary-chip">
                  <small>Cd</small>
                  <strong>{formatNumber(result.inputs.Cd)}</strong>
                </span>
                <span className="summary-chip">
                  <small>Cl</small>
                  <strong>{formatNumber(result.inputs.Cl)}</strong>
                </span>
              </div>
            </div>
          )}

          {loading ? (
            <SkeletonTable />
          ) : result && activeTab === "table" ? (
            <>
              <InputSummary inputs={result.inputs} />
              <div className="table-scroll">
                <table className="design-table">
                  <thead>
                    <tr>
                      <th>Parameter</th>
                      <th>Value</th>
                      <th style={{ minWidth: 180 }}>Range position</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {groupedKeys.map(({ group, keys }) => (
                      keys.length > 0 ? (
                        <>
                          <tr className="group-row" key={group}>
                            <td colSpan={4}>{GROUP_LABELS[group]}</td>
                          </tr>
                          {keys.map(key => {
                            const value = result.design[key];
                            const meta = PARAM_META[key];
                            const pct = rangePercent(value, meta.min, meta.max);
                            const colorClass = pct < 20 ? "bar-low" : pct > 80 ? "bar-high" : "bar-mid";
                            return (
                              <tr key={key}>
                                <td>
                                  <span className="param-name">{meta.label}</span>
                                  <code>{key}</code>
                                </td>
                                <td>
                                  <span className="value-cell">
                                    {formatNumber(value)}
                                    <small>{meta.unit}</small>
                                  </span>
                                </td>
                                <td>
                                  <div className="range-cell">
                                    <div className="range-track">
                                      <div
                                        className={`range-fill ${colorClass}`}
                                        style={{ width: `${Math.max(pct, 2)}%` }}
                                      />
                                    </div>
                                    <span className="range-pct">{Math.round(pct)}%</span>
                                  </div>
                                </td>
                                <td className="desc-cell">{meta.description}</td>
                              </tr>
                            );
                          })}
                        </>
                      ) : null
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : result && activeTab === "json" ? (
            <pre className="json-view">{JSON.stringify(result, null, 2)}</pre>
          ) : (
            <EmptyState />
          )}
        </section>
      </div>

      <footer className="app-footer">
        <span>Generative Missile Design · CGAN inverse design engine</span>
        <a href="https://github.com/Flacko-07/generative-missile-design" target="_blank" rel="noopener noreferrer">GitHub ↗</a>
      </footer>
    </main>
  );
}

function FormField({ config, value, onChange }: {
  config: FieldConfig;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="field" htmlFor={config.key}>
      <span className="field-label">
        {config.label}
        <span className="field-symbol">{config.symbol}</span>
      </span>
      <input
        id={config.key}
        type="number"
        value={value}
        min={config.min}
        max={config.max}
        step={config.step}
        onChange={e => onChange(e.target.value)}
        required
        inputMode="decimal"
        autoComplete="off"
      />
      <span className="field-hint">{config.hint}</span>
    </label>
  );
}

function InputSummary({ inputs }: { inputs: Record<InputKey, number> }) {
  return (
    <div className="input-summary">
      <span className="input-summary-label">Run with:</span>
      {(Object.entries(inputs) as [InputKey, number][]).map(([key, value]) => (
        <span className="input-chip" key={key}>
          <small>{key}</small>
          <strong>{formatNumber(value)}</strong>
        </span>
      ))}
    </div>
  );
}

function DesignPreview({ design, hasResult, loading }: {
  design: Record<ParamKey, number>;
  hasResult: boolean;
  loading: boolean;
}) {
  const totalLength = design.nose_length + design.body_length + design.flare_length;
  const noseWidth  = scaled(design.nose_length,  totalLength, 500, 60);
  const bodyWidth  = scaled(design.body_length,  totalLength, 500, 160);
  const flareWidth = scaled(design.flare_length, totalLength, 500, 28);
  const bodyH   = clamp(design.body_diameter * 180, 38, 78);
  const finH    = clamp(design.fin_span * 80, 18, 68);
  const finW    = clamp(design.fin_chord * 180, 24, 88);
  const cy = 118;
  const sx = 90;
  const ne = sx + noseWidth;
  const be = ne + bodyWidth;
  const fe = be + flareWidth;
  const top = cy - bodyH / 2;
  const bot = cy + bodyH / 2;
  const finBase = Math.max(ne + bodyWidth * 0.55, be - finW - 24);
  const sweepOff = clamp(design.fin_sweep_deg / 45, -1, 1) * finW * 0.28;

  return (
    <div className={`schematic-wrap ${hasResult ? "is-live" : ""} ${loading ? "is-loading" : ""}`}>
      <svg viewBox="0 0 720 240" role="img" aria-label="Side-view schematic of generated missile geometry">
        <defs>
          <linearGradient id="bodyGrad" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%"  stopColor="#dce6ee" />
            <stop offset="55%" stopColor="#94a3b8" />
            <stop offset="100%" stopColor="#56657a" />
          </linearGradient>
          <linearGradient id="finGrad" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%"  stopColor="#f2b84b" />
            <stop offset="100%" stopColor="#b56c21" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {[cy - 60, cy - 30, cy, cy + 30, cy + 60].map(y => (
          <line key={y} x1="60" x2="660" y1={y} y2={y}
            stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
        ))}

        <line className="axis" x1="55" x2="665" y1={cy} y2={cy} />
        <polygon className="arrowhead" points={`665,${cy} 658,${cy-4} 658,${cy+4}`} fill="rgba(76,201,240,0.5)" />

        <polygon className="fin fin-shadow"
          points={`${finBase},${bot-2} ${finBase+finW+sweepOff},${bot-2} ${finBase+finW*0.42},${bot+finH}`} />
        <rect x={ne} y={top} width={bodyWidth} height={bodyH} rx="4" fill="url(#bodyGrad)"
          stroke="rgba(255,255,255,0.35)" strokeWidth="1" />
        <polygon className="nose-poly"
          points={`${sx},${cy} ${ne},${top} ${ne},${bot}`} />
        <polygon className="flare-poly"
          points={`${be},${top} ${fe},${top+bodyH*0.18} ${fe},${bot-bodyH*0.18} ${be},${bot}`} />
        <polygon className="fin fin-top"
          points={`${finBase},${top+2} ${finBase+finW+sweepOff},${top+2} ${finBase+finW*0.42},${top-finH}`} />
        <polygon className="fin fin-bot"
          points={`${finBase},${bot-2} ${finBase+finW+sweepOff},${bot-2} ${finBase+finW*0.42},${bot+finH}`} />

        <circle cx={sx} cy={cy} r="5" fill="#4cc9f0" filter="url(#glow)" />
        <circle cx={sx} cy={cy} r="3" fill="#fff" />

        <text className="svg-label" x={sx + noseWidth/2 - 14} y="208">nose</text>
        <text className="svg-label" x={ne + bodyWidth/2 - 14} y="208">body</text>
        {design.flare_length > 0.02 && (
          <text className="svg-label" x={Math.min(be + 4, 620)} y="208">flare</text>
        )}

        <line x1={sx} x2={fe} y1="226" y2="226" stroke="rgba(76,201,240,0.25)" strokeWidth="1" />
        <text className="svg-dim" x={(sx + fe) / 2 - 26} y="222">
          L = {formatNumber(totalLength)} m
        </text>
      </svg>
    </div>
  );
}

function SkeletonTable() {
  return (
    <div className="skeleton-wrap">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="skeleton-row">
          <div className="skel" style={{ width: "22%" }} />
          <div className="skel" style={{ width: "12%" }} />
          <div className="skel" style={{ width: "32%" }} />
          <div className="skel" style={{ width: "28%" }} />
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
          <path d="M12 2L2 7l10 5 10-5-10-5z"/>
          <path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
      </div>
      <h3>No design generated yet</h3>
      <p>Set your target aerodynamic coefficients and click <strong>Generate design</strong> to run the CGAN inference engine. Results will appear here with visual range indicators.</p>
    </div>
  );
}

function buildMetrics(design: Record<ParamKey, number>, isRealResult: boolean): Metric[] {
  const totalLength = design.nose_length + design.body_length + design.flare_length;
  const ld = totalLength / Math.max(design.body_diameter, 0.001);
  const finArea = design.fin_span * design.fin_chord;

  return [
    {
      label: "Total length",
      value: `${formatNumber(totalLength)} m`,
      detail: isRealResult ? "nose + body + flare" : "Static preview geometry",
      icon: "📏",
    },
    {
      label: "L/D ratio",
      value: formatNumber(ld),
      detail: isRealResult ? "slenderness ratio" : "Preview slenderness estimate",
      icon: "⚡",
    },
    {
      label: "Fin area",
      value: `${formatNumber(finArea)} m²`,
      detail: isRealResult ? "span × chord" : "Preview fin planform area",
      icon: "◈",
    },
    {
      label: "Aft flare",
      value: `${formatNumber(design.flare_angle_deg)}°`,
      detail: `${formatNumber(design.flare_length)} m section`,
      icon: "🔺",
    },
  ];
}

function statusLabel(s: string) {
  if (s === "running")  return "Generating";
  if (s === "complete") return "Result ready";
  if (s === "error")    return "Request error";
  return "Ready";
}

function formatNumber(v: number) {
  return v.toLocaleString("en-US", {
    minimumFractionDigits: Math.abs(v) >= 10 ? 2 : 4,
    maximumFractionDigits: Math.abs(v) >= 10 ? 2 : 4,
  });
}

function rangePercent(v: number, min: number, max: number) {
  return clamp(((v - min) / (max - min)) * 100, 0, 100);
}

function scaled(v: number, total: number, width: number, minimum: number) {
  return Math.max(minimum, (v / Math.max(total, 0.001)) * width);
}

function clamp(v: number, min: number, max: number) {
  return Math.min(max, Math.max(min, v));
}
