import type { NextConfig } from "next";

// The browser only talks to this Next server; /api/* is forwarded to the Python API (:8091).
const api = process.env.CARGO_API_URL ?? "http://127.0.0.1:8091";
const config: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
};
export default config;
