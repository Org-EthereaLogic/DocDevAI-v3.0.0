import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8002/api/:path*'
      }
    ];
  },
  // Extended timeout for AI document generation (can take 60+ seconds)
  experimental: {
    proxyTimeout: 120000, // 2 minutes
  },
  // Increase server timeout for long-running requests
  serverRuntimeConfig: {
    // Will only be available on the server-side
    timeout: 120000
  }
};

export default nextConfig;
