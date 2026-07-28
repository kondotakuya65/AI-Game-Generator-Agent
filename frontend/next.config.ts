import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Keep /play/{id}/ trailing slash so relative game.js / style.css resolve correctly.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const target = process.env.API_PROXY_TARGET || "http://localhost:8200";
    return [
      {
        source: "/api/:path*",
        destination: `${target}/api/:path*`,
      },
      {
        source: "/play/:path*",
        destination: `${target}/play/:path*`,
      },
    ];
  },
};

export default nextConfig;
