import type { NextConfig } from "next";
import path from "path";

// Railway/Docker: uvicorn listens on 8180 (see start.sh).
// Local: set INTERNAL_API_URL=http://127.0.0.1:8290 when using an alternate PORT.
const internalApi =
  process.env.INTERNAL_API_URL || "http://127.0.0.1:8180";

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.join(__dirname),
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${internalApi}/api/:path*` },
      { source: "/health", destination: `${internalApi}/health` },
      { source: "/docs", destination: `${internalApi}/docs` },
      { source: "/openapi.json", destination: `${internalApi}/openapi.json` },
    ];
  },
};

export default nextConfig;
