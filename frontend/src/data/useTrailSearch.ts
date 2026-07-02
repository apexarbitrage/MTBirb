/*
 * Full-catalog trail name search (GET /api/catalog/trails-search) - finds trails anywhere in
 * the cache by name, not just those within the current browsing radius. Debounced so typing
 * doesn't fire a request per keystroke.
 */

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";
import type { CatalogTrail } from "./useCatalogTrails";

export interface TrailSearchItem extends CatalogTrail {
  distanceMi: number;
}

interface SearchResponse {
  query: string;
  count: number;
  trails: TrailSearchItem[];
}

const DEBOUNCE_MS = 300;
const MIN_QUERY_LEN = 3;

export function useTrailSearch(query: string, lat: number, lon: number) {
  const q = query.trim();
  const [loaded, setLoaded] = useState<{ q: string; results: TrailSearchItem[] } | null>(null);

  useEffect(() => {
    if (q.length < MIN_QUERY_LEN) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      apiGet<SearchResponse>(
        `/catalog/trails-search?q=${encodeURIComponent(q)}&lat=${lat}&lon=${lon}&limit=20`,
        controller.signal,
      )
        .then((d) => {
          if (!controller.signal.aborted) setLoaded({ q, results: d.trails });
        })
        .catch(() => {
          if (!controller.signal.aborted) setLoaded({ q, results: [] });
        });
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [q, lat, lon]);

  const current = loaded && loaded.q === q ? loaded.results : [];
  return { results: q.length < MIN_QUERY_LEN ? [] : current };
}
