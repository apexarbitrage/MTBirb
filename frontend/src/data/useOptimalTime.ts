/*
 * Fetches the optimal-time-to-ride curve for a catalog trail
 * (GET /api/catalog/trails/{id}/optimal-time): a per-hour blend of live NWS conditions and a
 * dawn/dusk wildlife prior, plus the picked best window. Fails soft like useTrailWeather - on error
 * (or outside the US, where NWS has no data) it resolves to null and the screen shows its
 * illustrative fallback. `data` is null while the request for the current slug is in flight.
 */

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";

export interface OptimalHour {
  time: string; // "7 AM"
  iso: string;
  conditions: number;
  wildlife: number;
  combined: number;
  tempF: number | null;
  windMph: number | null;
  popPct: number;
  isBest: boolean;
}

export interface TrailConditions {
  score: number;
  label: string; // Dry | Firm | Tacky | Wet | Muddy
}

export interface OptimalTime {
  available: boolean;
  date: string | null; // YYYY-MM-DD
  hours: OptimalHour[];
  bestWindow: string | null;
  bestWindowWhy: string | null;
  window: string | null;
  trailConditions: TrailConditions | null;
}

interface OptimalTimeResponse extends OptimalTime {
  trail?: string;
  route?: number;
}

/** `source: "route"` points the same curve at a saved multi-trail route
 * (GET /api/trail-routes/{id}/optimal-time - identical response shape). */
export function useOptimalTime(slug: string | undefined, source: "trail" | "route" = "trail") {
  const [loaded, setLoaded] = useState<{ slug: string; data: OptimalTime | null } | null>(null);

  useEffect(() => {
    if (!slug) return;
    const controller = new AbortController();
    const path =
      source === "route" ? `/trail-routes/${slug}/optimal-time` : `/catalog/trails/${slug}/optimal-time`;
    apiGet<OptimalTimeResponse>(path, controller.signal)
      .then((d) => {
        if (!controller.signal.aborted) setLoaded({ slug, data: d });
      })
      .catch(() => {
        if (!controller.signal.aborted) setLoaded({ slug, data: null });
      });
    return () => controller.abort();
  }, [slug, source]);

  const data = loaded && loaded.slug === slug ? loaded.data : null;
  return { data, loading: !loaded || loaded.slug !== slug };
}
