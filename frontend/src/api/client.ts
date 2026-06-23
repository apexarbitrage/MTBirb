/*
 * Thin fetch wrapper for the MTBirb backend. In dev, Vite proxies `/api/*` to the FastAPI
 * server on :8000 (see vite.config.ts); in production the PWA is served behind the same
 * origin, so the `/api` prefix is the one stable contract.
 */

const API_BASE = "/api";

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!res.ok) {
    throw new Error(`GET ${path} failed (${res.status})`);
  }
  return (await res.json()) as T;
}
