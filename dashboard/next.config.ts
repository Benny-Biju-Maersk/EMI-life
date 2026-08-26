import type { NextConfig } from "next";

import path from "node:path";

const nextConfig: NextConfig = {
  // better-sqlite3 (src/lib/db.ts) has a native binding — keep it external
  // to the bundler rather than letting Turbopack try to process it.
  serverExternalPackages: ["better-sqlite3"],
  // The repo root has its own package-lock.json (from `shadcn mcp init`,
  // unrelated to this app) — pin the workspace root explicitly so
  // Turbopack doesn't guess wrong about where this project's boundary is.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
