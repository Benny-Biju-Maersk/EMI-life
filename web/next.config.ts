import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The repo root (one level up) also has a package-lock.json (for the
  // shadcn MCP server's npx invocation — see ../.mcp.json), which makes
  // Turbopack guess the wrong workspace root without this pinned.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
