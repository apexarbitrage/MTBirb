/*
 * Loads trails from the live catalog near the user's location and shares them across screens.
 * Discover, Trails, and Optimal time read from here. Each catalog trail is adapted to the shared
 * `Trail` shape (catalogToTrail), carrying the recency/season/notable wildlife score; the rich
 * Trail-detail screen fetches its own enriched detail separately (useCatalogDetail).
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { apiGet } from "../api/client";
import { catalogToTrail, type CatalogTrail } from "./useCatalogTrails";
import { useGeolocation, type AppLocation } from "./useGeolocation";
import type { Trail } from "./trails";

interface CatalogResponse {
  count: number;
  trails: CatalogTrail[];
}

interface TrailsState {
  trails: Trail[];
  byId: (id: string) => Trail | undefined;
  location: AppLocation;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

const TrailsContext = createContext<TrailsState | null>(null);

export function TrailsProvider({ children }: { children: ReactNode }) {
  const location = useGeolocation();
  const [trails, setTrails] = useState<Trail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    setReloadKey((k) => k + 1);
  }, []);

  const { lat, lon } = location;
  useEffect(() => {
    const controller = new AbortController();
    apiGet<CatalogResponse>(
      `/catalog/trails?lat=${lat}&lon=${lon}&radius_km=60&limit=60`,
      controller.signal,
    )
      .then((data) => {
        setTrails(data.trails.map(catalogToTrail));
        setError(null);
      })
      .catch((e) => {
        if (controller.signal.aborted) return;
        setError(e instanceof Error ? e.message : "Failed to load trails");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [lat, lon, reloadKey]);

  const value = useMemo<TrailsState>(
    () => ({
      trails,
      byId: (id) => trails.find((t) => t.id === id),
      location,
      loading,
      error,
      reload,
    }),
    [trails, location, loading, error, reload],
  );

  return <TrailsContext.Provider value={value}>{children}</TrailsContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTrails(): TrailsState {
  const ctx = useContext(TrailsContext);
  if (!ctx) throw new Error("useTrails must be used within a TrailsProvider");
  return ctx;
}
