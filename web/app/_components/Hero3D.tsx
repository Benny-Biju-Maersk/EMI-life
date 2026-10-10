"use client";

import { Float, MeshDistortMaterial } from "@react-three/drei";
import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { Suspense, useRef, useState } from "react";
import type { Group, Mesh } from "three";

// The interactive piece: drag to spin it yourself, let go and it drifts back
// into a slow idle auto-rotate. No OrbitControls — that also gives zoom/pan,
// which fights a hero object rather than inviting a quick fiddle. Rotation
// is applied directly to the mesh group from pointer deltas, the simplest
// "this is an object, not a video" interaction that still works on touch.
function Gem() {
  const group = useRef<Group>(null);
  const meshRef = useRef<Mesh>(null);
  const dragging = useRef(false);
  const last = useRef({ x: 0, y: 0 });
  const velocity = useRef({ x: 0, y: 0 });
  const [hovered, setHovered] = useState(false);

  useFrame((_, delta) => {
    if (!group.current) return;
    if (!dragging.current) {
      // Idle: gentle constant spin plus whatever drag momentum is left,
      // decaying back to the constant drift rather than stopping dead.
      velocity.current.x += (0 - velocity.current.x) * Math.min(delta * 2, 1);
      velocity.current.y += (0.15 - velocity.current.y) * Math.min(delta * 1.5, 1);
    }
    group.current.rotation.x += velocity.current.x * delta;
    group.current.rotation.y += velocity.current.y * delta;
  });

  function onPointerDown(e: ThreeEvent<PointerEvent>) {
    e.stopPropagation();
    (e.target as Element).setPointerCapture?.(e.pointerId);
    dragging.current = true;
    last.current = { x: e.clientX, y: e.clientY };
  }
  function onPointerMove(e: ThreeEvent<PointerEvent>) {
    if (!dragging.current) return;
    const dx = e.clientX - last.current.x;
    const dy = e.clientY - last.current.y;
    last.current = { x: e.clientX, y: e.clientY };
    velocity.current = { x: dy * 0.08, y: dx * 0.08 };
    if (group.current) {
      group.current.rotation.x += dy * 0.01;
      group.current.rotation.y += dx * 0.01;
    }
  }
  function onPointerUp(e: ThreeEvent<PointerEvent>) {
    e.stopPropagation();
    dragging.current = false;
  }

  return (
    <Float speed={1.5} rotationIntensity={0.15} floatIntensity={0.6}>
      <group
        ref={group}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <mesh ref={meshRef} scale={hovered ? 1.06 : 1}>
          <icosahedronGeometry args={[1.4, 8]} />
          <MeshDistortMaterial
            color="#3b5bfd"
            distort={0.35}
            speed={2}
            roughness={0.1}
            metalness={0.6}
          />
        </mesh>
      </group>
    </Float>
  );
}

// Manual lighting rather than drei's <Environment> — that preset fetches
// an HDRI from an external CDN at runtime, an odd thing for an otherwise
// self-contained component to depend on. A key + fill + rim light gives
// MeshDistortMaterial's metalness/roughness enough to react to without it.
function Scene() {
  return (
    <>
      <ambientLight intensity={0.4} />
      <directionalLight position={[4, 3, 5]} intensity={1.4} />
      <pointLight position={[-4, -2, -3]} intensity={0.8} color="#8ea2ff" />
      <pointLight position={[3, -3, 2]} intensity={0.4} color="#ffffff" />
      <Suspense fallback={null}>
        <Gem />
      </Suspense>
    </>
  );
}

export function Hero3D() {
  return (
    <div className="h-[340px] w-full cursor-grab touch-none active:cursor-grabbing sm:h-[420px]">
      <Canvas camera={{ position: [0, 0, 5], fov: 40 }} dpr={[1, 1.5]}>
        <Scene />
      </Canvas>
    </div>
  );
}
