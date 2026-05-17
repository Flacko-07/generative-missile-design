import { useState } from 'react';
import { motion } from 'framer-motion';
import { TypeAnimation } from 'react-type-animation';
import InputPanel from '@/components/InputPanel';
import MissileViewer from '@/components/MissileViewer';
import MetricsCard from '@/components/MetricsCard';
import ResultsCard from '@/components/ResultsCard';
import GenerateButton from '@/components/GenerateButton';
import {
  computeMissileResults,
  callDesignApi,
  DesignApiGeometry,
} from '@/lib/computeMissileResults';

interface ResultsType {
  ldRatio: number;
  totalLength: number;
  finArea: number;
  cd: number;
}

interface UiParams {
  noseLength: number;
  bodyDiameter: number;
  finSpan: number;
  mach: number;
  altitude: number;
}

export default function Home() {
  const [params, setParams] = useState<UiParams>({
    noseLength: 450,
    bodyDiameter: 120,
    finSpan: 280,
    mach: 2.5,
    altitude: 8,
  });
  const [results, setResults] = useState<ResultsType | null>(null);
  const [design, setDesign] = useState<DesignApiGeometry | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setError(null);
    setIsLoading(true);

    try {
      // Map UI controls → aerodynamic targets.
      // For now we keep a simple mapping: use the heuristic cd from
      // computeMissileResults, assume Cl~0 and Cm~0, and derive AoA
      // from Mach + altitude for a reasonable default.
      const derived = computeMissileResults(params);
      const aoa = 5; // degrees – could be another control later

      const apiRes = await callDesignApi({
        cd: derived.cd,
        cl: 0,
        cm: 0,
        mach: params.mach,
        aoa,
      });

      setDesign(apiRes.design);
      setResults(derived);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to generate design');
    } finally {
      setIsLoading(false);
    }
  };

  const viewerParams = design
    ? {
        noseLength: design.nose_length * 1000, // convert m → mm for viewer scale
        bodyDiameter: design.body_diameter * 1000,
        finSpan: design.fin_span * 1000,
      }
    : params;

  return (
    <main className="max-w-7xl mx-auto px-4 md:px-8 py-12 md:py-20 space-y-20">
      {/* Hero section */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
        className="text-center space-y-4"
      >
        <h1 className="font-display font-extrabold text-5xl md:text-7xl lg:text-8xl tracking-tighter">
          <span className="gradient-text">Missile Geometry</span>
          <br />
          <span className="text-white">Console</span>
        </h1>
        <div className="h-12">
          <TypeAnimation
            sequence={[
              'Optimize aerodynamics',
              1500,
              'Generate CAD parameters',
              1500,
              'Export instantly',
              1500,
            ]}
            wrapper="p"
            speed={40}
            repeat={Infinity}
            className="text-accent font-mono text-lg md:text-xl"
          />
        </div>
      </motion.div>

      {/* Two-column dashboard */}
      <div className="grid lg:grid-cols-2 gap-8 lg:gap-12">
        {/* Left: Controls */}
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="glass-card p-6 md:p-8 space-y-8"
        >
          <InputPanel params={params} setParams={setParams} />
          {error && (
            <p className="text-sm text-red-400 font-mono">{error}</p>
          )}
          <GenerateButton onClick={handleGenerate} isLoading={isLoading} />
        </motion.div>

        {/* Right: 3D + Metrics + Output */}
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="space-y-6"
        >
          <div className="glass-card p-4 h-[320px] md:h-[400px] overflow-hidden">
            <MissileViewer params={viewerParams} />
          </div>
          {results && design && (
            <>
              <MetricsCard
                ldRatio={results.ldRatio}
                totalLength={results.totalLength}
                finArea={results.finArea}
              />
              <ResultsCard
                results={{ ldRatio: results.ldRatio, cd: results.cd }}
                params={{
                  ...params,
                  apiDesign: design,
                }}
              />
            </>
          )}
        </motion.div>
      </div>
    </main>
  );
}
