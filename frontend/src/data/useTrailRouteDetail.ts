/*
 * Loads a saved route's detail (GET /api/trail-routes/{id}): the ordered members, the combined
 * oriented line, summed stats, a live wildlife score, and the species reported near any part of
 * the route (they ride along in the same response - no separate wildlife call). Keyed by route id
 * so switching routes never shows stale data.
 */

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";
import type { NearbySpecies } from "./useTrailWildlife";
import type { RouteTrailLite, TrailRouteSummary } from "./useTrailRoutes";

export interface TrailRouteDetail extends TrailRouteSummary {
  descentFt: number | null;
  rideTimeMin: number | null;
  highPointFt: number | null;
  lowPointFt: number | null;
  members: RouteTrailLite[];
  missingTrailIds: string[];
  linePoints: [number, number][]; // [] when no member has a line yet
  startLat: number | null;
  startLon: number | null;
}

interface DetailResponse {
  route: TrailRouteDetail;
  species: NearbySpecies[];
  areaRadiusKm: number;
}

export function useTrailRouteDetail(id: number | null) {
  const [state, setState] = useState<{
    id: number;
    route: TrailRouteDetail | null;
    species: NearbySpecies[];
    areaRadiusKm: number | null;
    error: string | null;
  } | null>(null);

  useEffect(() => {
    if (id == null) return;
    const c = new AbortController();
    apiGet<DetailResponse>(`/trail-routes/${id}`, c.signal)
      .then((d) => {
        if (!c.signal.aborted)
          setState({ id, route: d.route, species: d.species, areaRadiusKm: d.areaRadiusKm, error: null });
      })
      .catch((e) => {
        if (!c.signal.aborted)
          setState({
            id,
            route: null,
            species: [],
            areaRadiusKm: null,
            error: e instanceof Error ? e.message : "Failed to load route",
          });
      });
    return () => c.abort();
  }, [id]);

  const s = state && state.id === id ? state : null;
  return {
    route: s?.route ?? null,
    species: s?.species ?? null,
    areaRadiusKm: s?.areaRadiusKm ?? null,
    error: s?.error ?? null,
    loading: s === null,
  };
}
