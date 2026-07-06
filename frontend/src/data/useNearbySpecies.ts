/*
 * Species reported near a location, ranked by recency+seasonality odds (GET /api/catalog/species).
 * Drives the targeting picker. `notableOnly` switches to the "Rarest" feed. Keyed by query so a
 * stale response is never shown. Distinguishes loading / error / empty so a backend outage shows a
 * retry instead of reading as "no species nearby".
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

interface State {
  key: string;
  species: NearbySpeciesItem[] | null; // null while loading or after an error
  error: string | null;
}

export function useNearbySpecies(lat: number, lon: number, notableOnly: boolean) {
  const key = `${lat},${lon},${notableOnly}`;
  const [state, setState] = useState<State>({ key, species: null, error: null });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    apiGet<SpeciesResponse>(
      `/catalog/species?lat=${lat}&lon=${lon}&radius_km=25&limit=50&notable_only=${notableOnly}`,
      controller.signal,
    )
      .then((d) => {
        if (!controller.signal.aborted) setState({ key, species: d.species, error: null });
      })
      .catch((e) => {
        if (!controller.signal.aborted) {
          setState({ key, species: null, error: e instanceof Error ? e.message : "Failed to load species" });
        }
      });
    return () => controller.abort();
  }, [lat, lon, notableOnly, key, nonce]);

  // Until the effect resolves for the current key, state still holds the previous key -> treat as
  // loading (so a key change shows the spinner, not stale data).
  const current = state.key === key ? state : null;
  const error = current?.error ?? null;
  return {
    species: current?.species ?? null,
    loading: !current || (current.species === null && !error),
    error,
    reload: () => setNonce((n) => n + 1),
  };
}
