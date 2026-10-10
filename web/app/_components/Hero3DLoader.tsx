"use client";

import dynamic from "next/dynamic";

// WebGL needs a real browser — rendering Hero3D on the server would just
// error out during the build, and there's nothing meaningful to
// server-render for a canvas anyway. ssr: false + this loading placeholder
// (same footprint as the real canvas, so nothing jumps when it swaps in)
// is the standard Next.js answer for a client-only visual like this.
const Hero3D = dynamic(() => import("./Hero3D").then((m) => m.Hero3D), {
  ssr: false,
  loading: () => (
    <div className="flex h-[340px] w-full items-center justify-center sm:h-[420px]">
      <div className="h-40 w-40 animate-pulse rounded-full bg-gradient-to-br from-primary/30 to-primary/10" />
    </div>
  ),
});

export function Hero3DLoader() {
  return <Hero3D />;
}
