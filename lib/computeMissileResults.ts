interface Results {
  totalLength: number;
  finArea: number;
  ldRatio: number;
  cd: number;
}

// Simple derived metrics from geometry + flight conditions
// Note: this is now only used as a fallback / secondary view; primary
// geometry comes from the GAN-backed /api/design endpoint.
export function computeMissileResults(params: any): Results {
  const { noseLength, bodyDiameter, finSpan, mach, altitude } = params;

  const totalLength = noseLength + bodyDiameter * 3;
  const finArea = (finSpan * bodyDiameter) / 10;
  let ldRatio = (mach * 1.2) / (0.02 * altitude + 0.5);
  ldRatio = Math.min(ldRatio, 12);
  const cd = 0.15 + (mach - 1) * 0.05;

  return { totalLength, finArea, ldRatio, cd };
}

export interface DesignApiInputs {
  cd: number;
  cl: number;
  cm: number;
  mach: number;
  aoa: number;
}

export interface DesignApiGeometry {
  nose_length: number;
  body_diameter: number;
  body_length: number;
  fin_span: number;
  fin_chord: number;
  fin_thickness: number;
  fin_sweep_deg: number;
  fin_offset: number;
  flare_angle_deg: number;
  flare_length: number;
}

export interface DesignApiResponse {
  inputs: {
    Cd: number;
    Cl: number;
    Cm: number;
    Mach: number;
    AoA: number;
  };
  design: DesignApiGeometry;
}

export async function callDesignApi(inputs: DesignApiInputs): Promise<DesignApiResponse> {
  const params = new URLSearchParams({
    cd: String(inputs.cd),
    cl: String(inputs.cl),
    cm: String(inputs.cm),
    mach: String(inputs.mach),
    aoa: String(inputs.aoa),
  });

  const res = await fetch(`/api/design?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Design API error: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as DesignApiResponse;
}
