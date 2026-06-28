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

export async function apiPost<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    throw new Error(`POST ${path} failed (${res.status})`);
  }
  return (await res.json()) as T;
}

/** POST raw binary (e.g. a WAV clip or an image) and parse a JSON response. */
export async function apiPostBlob<T>(path: string, blob: Blob, contentType: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": contentType },
    body: blob,
  });
  if (!res.ok) {
    throw new Error(`POST ${path} failed (${res.status})`);
  }
  return (await res.json()) as T;
}

/** DELETE a resource; resolves on any 2xx (including 204 No Content). */
export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(`DELETE ${path} failed (${res.status})`);
  }
}
