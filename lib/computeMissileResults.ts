interface Results {
  totalLength: number;
  finArea: number;
  ldRatio: number;
  cd: number;
}

export function computeMissileResults(params: any): Results {
  const { noseLength, bodyDiameter, finSpan, mach, altitude } = params;

  const totalLength = noseLength + bodyDiameter * 3;
  const finArea = (finSpan * bodyDiameter) / 10;
  let ldRatio = (mach * 1.2) / (0.02 * altitude + 0.5);
  ldRatio = Math.min(ldRatio, 12);
  const cd = 0.15 + (mach - 1) * 0.05;

  return { totalLength, finArea, ldRatio, cd };
}
