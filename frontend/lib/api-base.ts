const configuredApiBase = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").trim();

function trimTrailingSlash(url: string): string {
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

/**
 * Resolve API base URL for browser/mobile use.
 * - Explicit env var wins (works for production/reverse-proxy setups)
 * - Otherwise derive from current host and assume API is on :8000
 */
export function getApiBaseUrl(): string {
  if (configuredApiBase) {
    return trimTrailingSlash(configuredApiBase);
  }
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}
