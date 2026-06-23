/*
 * Loads trails from the backend once and shares them across screens. This is what replaced
 * the former static `TRAILS` array: Discover, Trails, Trail detail, and Optimal time all read
 * from here, so they run on backend-served data over HTTP.
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
import type { Trail } from "./trails";

interface TrailsState {
  trails: Trail[];
  byId: (id: string) => Trail | undefined;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

const TrailsContext = createContext<TrailsState | null>(null);

export function TrailsProvider({ children }: { children: ReactNode }) {
  const [trails, setTrails] = useState<Trail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Bumped to re-run the fetch effect. State is reset here (a user/event callback), not in
  // the effect body, so we never call setState synchronously inside the effect.
  const [reloadKey, setReloadKey] = useState(0);

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    setReloadKey((k) => k + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    apiGet<Trail[]>("/trails", controller.signal)
      .then((data) => {
        setTrails(data);
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
  }, [reloadKey]);

  const value = useMemo<TrailsState>(
    () => ({
      trails,
      byId: (id) => trails.find((t) => t.id === id),
      loading,
      error,
      reload,
    }),
    [trails, loading, error, reload],
  );

  return <TrailsContext.Provider value={value}>{children}</TrailsContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTrails(): TrailsState {
  const ctx = useContext(TrailsContext);
  if (!ctx) throw new Error("useTrails must be used within a TrailsProvider");
  return ctx;
}
