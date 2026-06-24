/*
 * Fetches the real recent eBird species reported near a trail
 * (GET /api/trails/{slug}/wildlife). Fails soft: on error it resolves to an empty list so
 * the calling screen shows its empty state rather than breaking.
 *
 * `species` is null while the request for the current slug is in flight (including right
 * after switching trails), so callers can treat null as "loading".
 */

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";

export interface NearbySpecies {
  species_code: string;
  common_name: string;
  observations: number;
  last_observed: string | null;
}

interface WildlifeResponse {
  trail: string;
  lookbackDays: number;
  species: NearbySpecies[];
}

export function useTrailWildlife(slug: string | undefined) {
  // Store the slug the data belongs to so a stale response (or the previous trail's data)
  // is never shown for the current slug - and so state is only set in async callbacks.
  const [loaded, setLoaded] = useState<{ slug: string; species: NearbySpecies[] } | null>(null);

  useEffect(() => {
    if (!slug) return;
    const controller = new AbortController();
    apiGet<WildlifeResponse>(`/trails/${slug}/wildlife`, controller.signal)
      .then((d) => {
        if (!controller.signal.aborted) setLoaded({ slug, species: d.species });
      })
      .catch(() => {
        if (!controller.signal.aborted) setLoaded({ slug, species: [] });
      });
    return () => controller.abort();
  }, [slug]);

  const species = loaded && loaded.slug === slug ? loaded.species : null;
  return { species };
}
