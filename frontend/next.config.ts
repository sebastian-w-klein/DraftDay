import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

/** Always the `frontend/` folder — never `process.cwd()` (differs if dev is started from repo root). */
const frontendDir = path.dirname(fileURLToPath(import.meta.url));

/**
 * When a parent directory has its own `package-lock.json`, Next can infer the wrong workspace root.
 * Pin tracing to this package so dev CSS routes (`/_next/static/css/app/layout.css`) resolve correctly.
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: frontendDir,
};

export default nextConfig;
