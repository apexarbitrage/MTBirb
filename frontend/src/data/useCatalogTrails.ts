/*
 * Fetches catalog trails near a location (GET /api/catalog/trails). The backend serves cached
 * TrailAPI trails and fills new areas in on demand. `loading` is true until the response for
 * the current location arrives; switching locations re-loads cleanly (data is keyed by
 * location, so a stale response is never shown).
 */

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";

export interface CatalogTrail {
  id: string;
  name: string;
  difficulty: string | null;
  lengthMi: number | null;
  city: string | null;
  region: string | null;
  lat: number;
  lon: number;
  url: string | null;
  // DEM-derived terrain metrics (null until computed by the backend; see trail_metrics.py).
  metricLengthMi: number | null;
  ascentFt: number | null;
  descentFt: number | null;
  avgUpGrade: string | null;
  avgDownGrade: string | null;
  elevationProfile: number[] | null;
  rideTimeMin: number | null;
  effort: number | null;
  elevSource: string | null;
}

interface CatalogResponse {
  count: number;
  fetchedNow: number;
  trails: CatalogTrail[];
}

export function useCatalogTrails(lat: number, lon: number) {
  const key = `${lat},${lon}`;
  const [loaded, setLoaded] = useState<{
    key: string;
    trails: CatalogTrail[];
    error: string | null;
    fetchedNow: number;
  } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    apiGet<CatalogResponse>(
      `/catalog/trails?lat=${lat}&lon=${lon}&radius_km=60&limit=60`,
      controller.signal,
    )
      .then((d) => {
        if (!controller.signal.aborted)
          setLoaded({ key, trails: d.trails, error: null, fetchedNow: d.fetchedNow });
      })
      .catch((e) => {
        if (!controller.signal.aborted)
          setLoaded({
            key,
            trails: [],
            error: e instanceof Error ? e.message : "Failed to load trails",
            fetchedNow: 0,
          });
      });
    return () => controller.abort();
  }, [lat, lon, key]);

  const current = loaded && loaded.key === key ? loaded : null;
  return {
    trails: current?.trails ?? [],
    error: current?.error ?? null,
    fetchedNow: current?.fetchedNow ?? 0,
    loading: current === null,
  };
}
