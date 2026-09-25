import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produces a minimal .next/standalone server (see Dockerfile).
  output: "standalone",
};

export default nextConfig;
