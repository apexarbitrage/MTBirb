/*
 * Trails near a location ranked by one species' odds (GET /api/catalog/trails?species=code).
 * Used by the Trails screen when a targeting species filter is active. Keyed by species+location
 * so a stale ranking is never shown; fails soft.
 */

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";
import type { CatalogTrail } from "./useCatalogTrails";

interface SpeciesTrailsResponse {
  count: number;
  species: string | null;
  trails: CatalogTrail[];
}

export function useSpeciesTrails(code: string | null, lat: number, lon: number) {
  const key = code ? `${code},${lat},${lon}` : null;
  const [loaded, setLoaded] = useState<{
    key: string;
    trails: CatalogTrail[];
    error: string | null;
  } | null>(null);

  useEffect(() => {
    if (!code || !key) return;
    const controller = new AbortController();
    apiGet<SpeciesTrailsResponse>(
      `/catalog/trails?lat=${lat}&lon=${lon}&radius_km=60&limit=60&species=${code}`,
      controller.signal,
    )
      .then((d) => {
        if (!controller.signal.aborted) setLoaded({ key, trails: d.trails, error: null });
      })
      .catch((e) => {
        if (!controller.signal.aborted)
          setLoaded({ key, trails: [], error: e instanceof Error ? e.message : "Failed" });
      });
    return () => controller.abort();
  }, [code, lat, lon, key]);

  const current = key && loaded && loaded.key === key ? loaded : null;
  return {
    trails: current?.trails ?? [],
    error: current?.error ?? null,
    loading: code != null && current === null,
  };
}
