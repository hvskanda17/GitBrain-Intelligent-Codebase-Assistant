import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Server Actions and Server Components call the FastAPI backend directly (see
  // src/lib/api.ts) using API_BASE_URL read at request time -- no rewrites needed.
};

export default nextConfig;
