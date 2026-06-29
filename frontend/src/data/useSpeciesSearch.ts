/*
 * Full eBird taxonomy search (GET /api/catalog/species-search) - finds a species by name even
 * with zero current nearby sightings, unlike useNearbySpecies (which only lists species someone
 * has actually reported). Debounced so typing doesn't fire a request per keystroke.
 */

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";

export interface TaxonomySpeciesItem {
  species_code: string;
  common_name: string;
  scientific_name: string;
}

interface SearchResponse {
  query: string;
  species: TaxonomySpeciesItem[];
}

const DEBOUNCE_MS = 300;
const MIN_QUERY_LEN = 2;

export function useSpeciesSearch(query: string) {
  const q = query.trim();
  const [loaded, setLoaded] = useState<{ q: string; results: TaxonomySpeciesItem[] } | null>(null);

  useEffect(() => {
    if (q.length < MIN_QUERY_LEN) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      apiGet<SearchResponse>(`/catalog/species-search?q=${encodeURIComponent(q)}&limit=20`, controller.signal)
        .then((d) => {
          if (!controller.signal.aborted) setLoaded({ q, results: d.species });
        })
        .catch(() => {
          if (!controller.signal.aborted) setLoaded({ q, results: [] });
        });
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [q]);

  const current = loaded && loaded.q === q ? loaded.results : [];
  return { results: q.length < MIN_QUERY_LEN ? [] : current };
}
