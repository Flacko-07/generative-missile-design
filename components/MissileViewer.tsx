import { Canvas } from '@react-three/fiber';
import { OrbitControls, Cylinder, Cone } from '@react-three/drei';

interface MissileViewerProps {
  params: {
    noseLength: number;
    bodyDiameter: number;
    finSpan: number;
  };
}

export default function MissileViewer({ params }: MissileViewerProps) {
  const { noseLength, bodyDiameter, finSpan } = params;

  const bodyRadius = bodyDiameter / 200;   // scale for preview (120mm → 0.6)
  const bodyHeight = 2.0;
  const noseHeight = noseLength / 200;     // 450mm → 2.25
  const finWidth = finSpan / 200;          // 280mm → 1.4

  return (
    <Canvas camera={{ position: [4, 3, 6], fov: 45 }} className="rounded-xl">
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <directionalLight position={[2, 5, 3]} intensity={0.8} />
      <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={1.2} />

      {/* Missile body */}
      <Cylinder
        args={[bodyRadius, bodyRadius, bodyHeight, 64]}
        position={[0, 0, 0]}
      >
        <meshStandardMaterial color="#8aabff" metalness={0.85} roughness={0.2} />
      </Cylinder>

      {/* Nose cone */}
      <Cone
        args={[bodyRadius, noseHeight, 64]}
        position={[0, bodyHeight / 2 + noseHeight / 2, 0]}
      >
        <meshStandardMaterial color="#ffaa66" metalness={0.9} roughness={0.1} />
      </Cone>

      {/* Fins (4 x rotated) */}
      {[0, Math.PI / 2, Math.PI, 3 * Math.PI / 2].map((angle, i) => (
        <group key={i} rotation={[0, angle, 0]}>
          <Cylinder
            args={[finWidth * 0.1, finWidth * 0.2, finWidth, 8]}
            position={[bodyRadius + finWidth * 0.3, -bodyHeight / 2 + 0.3, 0]}
            rotation={[0, 0, Math.PI / 6]}
          >
            <meshStandardMaterial color="#c0cfe0" metalness={0.7} />
          </Cylinder>
        </group>
      ))}

      {/* Grid floor */}
      <gridHelper args={[10, 20, '#00ffff', '#333']} position={[0, -1.5, 0]} />
    </Canvas>
  );
}
