/*
 * Fetches catalog trails near a location (GET /api/catalog/trails). The backend serves cached
 * TrailAPI trails and fills new areas in on demand. `loading` is true until the response for
 * the current location arrives; switching locations re-loads cleanly (data is keyed by
 * location, so a stale response is never shown).
 */

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";
import { normalizeDifficulty, type SightingFactor, type Trail } from "./trails";

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
  // Expanded terrain + surface stats (detail screen; null until computed/enriched).
  maxGrade: string | null;
  highPointFt: number | null;
  lowPointFt: number | null;
  longestClimbMi: number | null;
  aspect: string | null;
  sunExposure: number | null;
  surface: string | null;
  mtbScale: string | null;
  // First-pass wildlife overlay (recency + seasonality + notable; see wildlife_likelihood.py).
  score: number | null;
  notableScore: number | null;
  likelyBirds: string[];
  notableBirds: string[];
  metaBird: string | null;
  peak: string | null;
  sightingHeadline: string | null;
  factors: SightingFactor[];
  // Set only when the list is fetched with a species filter: that species' odds near this trail.
  speciesLikelihood: number | null;
}

/** Adapt a live catalog trail into the shared `Trail` shape the screens render. */
export function catalogToTrail(c: CatalogTrail): Trail {
  const location = [c.city, c.region].filter(Boolean).join(", ");
  return {
    id: c.id,
    name: c.name,
    score: c.score ?? 0,
    notableScore: c.notableScore,
    diff: normalizeDifficulty(c.difficulty),
    miles: c.metricLengthMi ?? c.lengthMi,
    effort: c.effort,
    // weather / best-time aren't in the list response - fetched live per-trail or still deferred.
    window: null,
    realfeel: null,
    sky: null,
    condition: null,
    peak: c.peak,
    metaTime: null,
    metaBird: c.metaBird,
    features: [],
    rideTime: c.rideTimeMin,
    likelyBirds: c.likelyBirds ?? [],
    notableBirds: c.notableBirds ?? [],
    location: location || null,
    gainFt: c.ascentFt,
    dirt: null,
    climbFt: c.ascentFt,
    descentFt: c.descentFt,
    avgUpGrade: c.avgUpGrade,
    avgDownGrade: c.avgDownGrade,
    elevation: c.elevationProfile ?? [],
    sightingHeadline: c.sightingHeadline,
    factors: c.factors ?? [],
    bestWindow: null,
    bestWindowWhy: null,
  };
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
