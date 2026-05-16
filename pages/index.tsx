import { useState } from 'react';
import { motion } from 'framer-motion';
import { TypeAnimation } from 'react-type-animation';
import InputPanel from '@/components/InputPanel';
import MissileViewer from '@/components/MissileViewer';
import MetricsCard from '@/components/MetricsCard';
import ResultsCard from '@/components/ResultsCard';
import GenerateButton from '@/components/GenerateButton';
import { computeMissileResults } from '@/lib/computeMissileResults';

export default function Home() {
  const [params, setParams] = useState({
    noseLength: 450,
    bodyDiameter: 120,
    finSpan: 280,
    mach: 2.5,
    altitude: 8,
    // Add other parameters as needed
  });
  const [results, setResults] = useState(null);

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
          <GenerateButton
            onClick={() => {
              const computed = computeMissileResults(params);
              setResults(computed);
            }}
          />
        </motion.div>

        {/* Right: 3D + Metrics + Output */}
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="space-y-6"
        >
          <div className="glass-card p-4 h-[320px] md:h-[400px] overflow-hidden">
            <MissileViewer params={params} />
          </div>
          {results && (
            <>
              <MetricsCard
                ldRatio={results.ldRatio}
                totalLength={results.totalLength}
                finArea={results.finArea}
              />
              <ResultsCard results={results} params={params} />
            </>
          )}
        </motion.div>
      </div>
    </main>
  );
}
