/*
 * Saved multi-trail routes (GET/POST/DELETE /api/trail-routes) - the chains of adjacent trails
 * built in the route builder. Like trips, one global set for now (no accounts). Stats come
 * recomputed from the member trails by the backend, so they improve as members get mapped.
 */

import { useCallback, useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost } from "../api/client";

export interface RouteTrailLite {
  id: string; // catalog external_id
  name: string;
  difficulty: string | null;
  lengthMi: number | null;
  metricLengthMi: number | null;
  ascentFt: number | null;
  rideTimeMin: number | null;
  lat: number;
  lon: number;
  linePoints: [number, number][] | null; // [lon, lat]
}

export interface TrailRouteSummary {
  id: number;
  name: string;
  trailCount: number;
  mappedCount: number;
  miles: number | null;
  ascentFt: number | null;
  wildlifeScore: number | null;
  createdAt: string;
}

export async function createTrailRoute(name: string, trailIds: string[]): Promise<TrailRouteSummary> {
  return apiPost<TrailRouteSummary>("/trail-routes", { name, trailIds });
}

export async function deleteTrailRoute(id: number): Promise<void> {
  return apiDelete(`/trail-routes/${id}`);
}

export function useTrailRoutes() {
  const [data, setData] = useState<{ routes: TrailRouteSummary[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    apiGet<{ routes: TrailRouteSummary[] }>("/trail-routes", controller.signal)
      .then((d) => {
        if (!controller.signal.aborted) {
          setData(d);
          setError(null);
        }
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "Failed to load routes");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [reloadKey]);

  return { routes: data?.routes ?? [], loading, error, reload };
}
