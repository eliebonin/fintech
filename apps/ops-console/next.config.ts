import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["api-contracts"],
  // The local browser is normally opened on 127.0.0.1 while Next advertises
  // localhost. Allow both loopback origins so dev client hydration/HMR can
  // load the same catalogue-fetching bundle on either URL.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
};

export default nextConfig;
