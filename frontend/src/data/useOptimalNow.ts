/*
 * Fetches the "optimal now" ranking for nearby trails (GET /api/catalog/optimal-now): how well the
 * current time overlaps each trail's optimal window (live conditions + recent-rain surface +
 * dawn/dusk wildlife). Only runs when `enabled` (the optimal sort is active on Discover or Trails),
 * so the default catalog list stays fast. Returns a {externalId -> score} map; fails soft to {}.
 */

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";

interface OptimalNowResponse {
  trails: { id: string; optimalNow: number }[];
  conditionsNow: number | null;
  trailConditions: { score: number; label: string } | null;
}

export function useOptimalNow(lat: number, lon: number, enabled: boolean) {
  const key = `${lat},${lon}`;
  const [loaded, setLoaded] = useState<{ key: string; scores: Record<string, number> } | null>(null);

  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    apiGet<OptimalNowResponse>(
      `/catalog/optimal-now?lat=${lat}&lon=${lon}&radius_km=60&limit=60`,
      controller.signal,
    )
      .then((d) => {
        if (controller.signal.aborted) return;
        const scores: Record<string, number> = {};
        for (const t of d.trails) scores[t.id] = t.optimalNow;
        setLoaded({ key, scores });
      })
      .catch(() => {
        if (!controller.signal.aborted) setLoaded({ key, scores: {} });
      });
    return () => controller.abort();
  }, [lat, lon, key, enabled]);

  const scores = enabled && loaded && loaded.key === key ? loaded.scores : {};
  return { scores };
}
