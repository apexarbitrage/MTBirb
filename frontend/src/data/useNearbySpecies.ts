/*
 * Species reported near a location, ranked by recency+seasonality odds (GET /api/catalog/species).
 * Drives the targeting picker. `notableOnly` switches to the "Rarest" feed. Keyed by query so a
 * stale response is never shown; fails soft to an empty list.
 */

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";

export interface NearbySpeciesItem {
  species_code: string;
  common_name: string;
  last_observed: string | null;
  notable: boolean;
  observations: number;
  likelihood: number;
  like: "High" | "Med" | "Rare";
}

interface SpeciesResponse {
  count: number;
  syncedNow: number;
  species: NearbySpeciesItem[];
}

export function useNearbySpecies(lat: number, lon: number, notableOnly: boolean) {
  const key = `${lat},${lon},${notableOnly}`;
  const [loaded, setLoaded] = useState<{ key: string; species: NearbySpeciesItem[] } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    apiGet<SpeciesResponse>(
      `/catalog/species?lat=${lat}&lon=${lon}&radius_km=25&limit=20&notable_only=${notableOnly}`,
      controller.signal,
    )
      .then((d) => {
        if (!controller.signal.aborted) setLoaded({ key, species: d.species });
      })
      .catch(() => {
        if (!controller.signal.aborted) setLoaded({ key, species: [] });
      });
    return () => controller.abort();
  }, [lat, lon, notableOnly, key]);

  const current = loaded && loaded.key === key ? loaded : null;
  return { species: current?.species ?? null };
}
