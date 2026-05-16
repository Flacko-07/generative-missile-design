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
};

type ParamMeta = {
  label: string;
  unit: string;
  min: number;
  max: number;
  description: string;
};

type DesignResult = {
  inputs: Record<InputKey, number>;
  design: Record<ParamKey, number>;
};

type Metric = {
  label: string;
  value: string;
  detail: string;
};

const FIELD_CONFIGS: FieldConfig[] = [
  { key: "cd", label: "Drag coefficient", symbol: "Cd", step: "0.0001", min: "-1", max: "2" },
  { key: "cl", label: "Lift coefficient", symbol: "Cl", step: "0.0001", min: "-2", max: "2" },
  { key: "cm", label: "Pitching moment", symbol: "Cm", step: "0.0001", min: "-2", max: "2" },
  { key: "mach", label: "Mach number", symbol: "Ma", step: "0.01", min: "0.05", max: "8" },
  { key: "aoa", label: "Angle of attack", symbol: "AoA", step: "0.1", min: "-20", max: "30" },
];

const DESIGN_KEYS: ParamKey[] = [
  "nose_length",
  "body_diameter",
  "body_length",
  "fin_span",
  "fin_chord",
  "fin_thickness",
  "fin_sweep_deg",
  "fin_offset",
  "flare_angle_deg",
  "flare_length",
];

const PARAM_META: Record<ParamKey, ParamMeta> = {
  nose_length: {
    label: "Nose length",
    unit: "m",
    min: 0.2,
    max: 2.5,
    description: "Forward cone section",
  },
  body_diameter: {
    label: "Body diameter",
    unit: "m",
    min: 0.15,
    max: 0.6,
    description: "Outer cylindrical diameter",
  },
  body_length: {
    label: "Body length",
    unit: "m",
    min: 0.8,
    max: 7.0,
    description: "Primary fuselage length",
  },
  fin_span: {
    label: "Fin span",
    unit: "m",
    min: 0,
    max: 1.2,
    description: "Full stabilizer span",
  },
  fin_chord: {
    label: "Fin chord",
    unit: "m",
    min: 0,
    max: 0.8,
    description: "Root chord length",
  },
  fin_thickness: {
    label: "Fin thickness",
    unit: "m",
    min: 0,
    max: 0.08,
    description: "Stabilizer section thickness",
  },
  fin_sweep_deg: {
    label: "Fin sweep",
    unit: "deg",
    min: -45,
    max: 45,
    description: "Leading edge sweep angle",
  },
  fin_offset: {
    label: "Fin offset",
    unit: "m",
    min: -0.2,
    max: 0.5,
    description: "Axial fin station adjustment",
  },
  flare_angle_deg: {
    label: "Flare angle",
    unit: "deg",
    min: 0,
    max: 15,
    description: "Aft flare or boattail angle",
  },
  flare_length: {
    label: "Flare length",
    unit: "m",
    min: 0,
    max: 0.5,
    description: "Aft transition section",
  },
};

const DEFAULT_FIELDS: Record<FieldKey, string> = {
  cd: "0.10",
  cl: "0.00",
  cm: "0.00",
  mach: "0.80",
  aoa: "5.0",
};

const PREVIEW_DESIGN: Record<ParamKey, number> = {
  nose_length: 0.56,
  body_diameter: 0.32,
  body_length: 2.98,
  fin_span: 0.12,
  fin_chord: 0.12,
  fin_thickness: 0.015,
  fin_sweep_deg: 11.5,
  fin_offset: 0.025,
  flare_angle_deg: 6.2,
  flare_length: 0.13,
};

export default function Home() {
  const [fields, setFields] = useState<Record<FieldKey, string>>(DEFAULT_FIELDS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DesignResult | null>(null);
  const [copied, setCopied] = useState(false);

  const metrics = useMemo(() => buildMetrics(result?.design ?? null), [result]);
  const runState = loading ? "running" : error ? "error" : result ? "complete" : "ready";

  function setField(key: FieldKey, value: string) {
    setFields((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setCopied(false);

    try {
      const params = new URLSearchParams({
        cd: fields.cd,
        cl: fields.cl,
        cm: fields.cm,
        mach: fields.mach,
        aoa: fields.aoa,
      });

      const response = await fetch(`/api/design?${params.toString()}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `Request failed with HTTP ${response.status}`);
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
    window.setTimeout(() => setCopied(false), 1400);
  }

  return (
    <main className="app-shell">
      <section className="workspace" aria-label="Missile inverse design workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Generative inverse design</p>
            <h1>Missile Geometry Console</h1>
          </div>
          <div className={`run-status is-${runState}`} aria-live="polite">
            <span className="status-dot" aria-hidden="true" />
            {statusLabel(runState)}
          </div>
        </header>

        <div className="main-grid">
          <form className="control-panel" onSubmit={handleSubmit}>
            <div className="panel-heading">
              <div>
                <p className="panel-kicker">Target condition</p>
                <h2>Inputs</h2>
              </div>
              <button type="button" className="text-button" onClick={handleReset}>
                Reset
              </button>
            </div>

            <div className="field-grid">
              {FIELD_CONFIGS.map((config) => (
                <FormField
                  key={config.key}
                  config={config}
                  value={fields[config.key]}
                  onChange={(value) => setField(config.key, value)}
                />
              ))}
            </div>

            <button className="primary-button" type="submit" disabled={loading}>
              {loading && <span className="spinner" aria-hidden="true" />}
              {loading ? "Generating..." : "Generate design"}
            </button>
          </form>

          <section className="preview-panel" aria-label="Generated missile profile">
            <div className="panel-heading">
              <div>
                <p className="panel-kicker">Geometry profile</p>
                <h2>{result ? "Generated design" : "Preview state"}</h2>
              </div>
              <span className="result-pill">{result ? "Model output" : "Awaiting run"}</span>
            </div>

            <DesignPreview design={result?.design ?? PREVIEW_DESIGN} hasResult={Boolean(result)} />

            <div className="metric-grid" aria-label="Derived metrics">
              {metrics.map((metric) => (
                <div className="metric" key={metric.label}>
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                  <small>{metric.detail}</small>
                </div>
              ))}
            </div>
          </section>
        </div>

        {error && (
          <div className="alert" role="alert">
            <strong>Design request failed</strong>
            <span>{error}</span>
          </div>
        )}

        <section className="results-panel" aria-label="Generated geometry parameters">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Numerical output</p>
              <h2>Parameters</h2>
            </div>
            <button type="button" className="secondary-button" disabled={!result} onClick={handleCopy}>
              {copied ? "Copied" : "Copy JSON"}
            </button>
          </div>

          {result ? (
            <>
              <InputSummary inputs={result.inputs} />
              <div className="table-scroll">
                <table className="design-table">
                  <thead>
                    <tr>
                      <th>Parameter</th>
                      <th>Value</th>
                      <th>Range</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {DESIGN_KEYS.map((key) => {
                      const value = result.design[key];
                      const meta = PARAM_META[key];
                      const pct = rangePercent(value, meta.min, meta.max);

                      return (
                        <tr key={key}>
                          <td>
                            <span className="param-label">{meta.label}</span>
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
                              <div className="range-track" aria-hidden="true">
                                <span style={{ width: `${pct}%` }} />
                              </div>
                              <small>{Math.round(pct)}%</small>
                            </div>
                          </td>
                          <td>{meta.description}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="empty-result">
              <span>No generated result yet</span>
              <p>Run the target condition to populate geometry values, range positions, and derived dimensions.</p>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

function FormField({
  config,
  value,
  onChange,
}: {
  config: FieldConfig;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="field" htmlFor={config.key}>
      <span>
        {config.label}
        <small>{config.symbol}</small>
      </span>
      <input
        id={config.key}
        type="number"
        value={value}
        min={config.min}
        max={config.max}
        step={config.step}
        onChange={(event) => onChange(event.target.value)}
        required
        inputMode="decimal"
      />
    </label>
  );
}

function InputSummary({ inputs }: { inputs: Record<InputKey, number> }) {
  return (
    <div className="input-summary">
      {(Object.entries(inputs) as [InputKey, number][]).map(([key, value]) => (
        <span key={key}>
          <small>{key}</small>
          {formatNumber(value)}
        </span>
      ))}
    </div>
  );
}

function DesignPreview({
  design,
  hasResult,
}: {
  design: Record<ParamKey, number>;
  hasResult: boolean;
}) {
  const totalLength = design.nose_length + design.body_length + design.flare_length;
  const noseWidth = scaled(design.nose_length, totalLength, 520, 70);
  const bodyWidth = scaled(design.body_length, totalLength, 520, 180);
  const flareWidth = scaled(design.flare_length, totalLength, 520, 34);
  const bodyHeight = clamp(design.body_diameter * 180, 42, 82);
  const finHeight = clamp(design.fin_span * 80, 20, 70);
  const finWidth = clamp(design.fin_chord * 180, 28, 90);
  const centerY = 122;
  const startX = 80;
  const noseEnd = startX + noseWidth;
  const bodyEnd = noseEnd + bodyWidth;
  const flareEnd = bodyEnd + flareWidth;
  const top = centerY - bodyHeight / 2;
  const bottom = centerY + bodyHeight / 2;
  const finBase = Math.max(noseEnd + bodyWidth * 0.58, bodyEnd - finWidth - 28);

  return (
    <div className={`schematic ${hasResult ? "is-live" : ""}`}>
      <svg viewBox="0 0 720 250" role="img" aria-label="Side profile of generated missile geometry">
        <defs>
          <linearGradient id="bodyGradient" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="#dce6ee" />
            <stop offset="55%" stopColor="#94a3b8" />
            <stop offset="100%" stopColor="#56657a" />
          </linearGradient>
          <linearGradient id="finGradient" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#f2b84b" />
            <stop offset="100%" stopColor="#b56c21" />
          </linearGradient>
        </defs>

        <line className="axis-line" x1="52" x2="668" y1={centerY} y2={centerY} />
        <polygon
          className="nose"
          points={`${startX},${centerY} ${noseEnd},${top} ${noseEnd},${bottom}`}
        />
        <rect x={noseEnd} y={top} width={bodyWidth} height={bodyHeight} rx="6" />
        <polygon
          className="flare"
          points={`${bodyEnd},${top} ${flareEnd},${top + bodyHeight * 0.16} ${flareEnd},${
            bottom - bodyHeight * 0.16
          } ${bodyEnd},${bottom}`}
        />
        <polygon
          className="fin fin-top"
          points={`${finBase},${top + 3} ${finBase + finWidth},${top + 3} ${
            finBase + finWidth * 0.45
          },${top - finHeight}`}
        />
        <polygon
          className="fin fin-bottom"
          points={`${finBase},${bottom - 3} ${finBase + finWidth},${bottom - 3} ${
            finBase + finWidth * 0.45
          },${bottom + finHeight}`}
        />
        <circle className="nose-tip" cx={startX} cy={centerY} r="4" />
        <text x={startX} y="214">nose</text>
        <text x={noseEnd + bodyWidth / 2 - 18} y="214">body</text>
        <text x={Math.min(flareEnd - 42, 620)} y="214">flare</text>
      </svg>
    </div>
  );
}

function buildMetrics(design: Record<ParamKey, number> | null): Metric[] {
  if (!design) {
    return [
      { label: "Total length", value: "--", detail: "Available after generation" },
      { label: "L/D ratio", value: "--", detail: "Length over diameter" },
      { label: "Fin area", value: "--", detail: "Planform estimate" },
      { label: "Aft flare", value: "--", detail: "Angle and section length" },
    ];
  }

  const totalLength = design.nose_length + design.body_length + design.flare_length;
  const lengthDiameter = totalLength / Math.max(design.body_diameter, 0.001);
  const finArea = design.fin_span * design.fin_chord;

  return [
    { label: "Total length", value: `${formatNumber(totalLength)} m`, detail: "Nose + body + flare" },
    { label: "L/D ratio", value: formatNumber(lengthDiameter), detail: "Length over diameter" },
    { label: "Fin area", value: `${formatNumber(finArea)} m2`, detail: "Span times chord" },
    {
      label: "Aft flare",
      value: `${formatNumber(design.flare_angle_deg)} deg`,
      detail: `${formatNumber(design.flare_length)} m section`,
    },
  ];
}

function statusLabel(state: string) {
  if (state === "running") return "Generating";
  if (state === "complete") return "Result ready";
  if (state === "error") return "Request error";
  return "Ready";
}

function formatNumber(value: number) {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: Math.abs(value) >= 10 ? 2 : 4,
    maximumFractionDigits: Math.abs(value) >= 10 ? 2 : 4,
  });
}

function rangePercent(value: number, min: number, max: number) {
  return clamp(((value - min) / (max - min)) * 100, 0, 100);
}

function scaled(value: number, total: number, width: number, minimum: number) {
  return Math.max(minimum, (value / Math.max(total, 0.001)) * width);
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}
