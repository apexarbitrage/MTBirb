/*
 * The logged-ride history (GET /api/trips) plus a helper to log a new ride (POST /api/trips).
 * Single global history for now (no accounts). Lifers and stats are computed by the backend.
 */

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "../api/client";

export interface TripBird {
  speciesCode: string | null;
  commonName: string;
}

export interface Trip {
  id: number;
  trailExternalId: string | null;
  trailName: string;
  difficulty: string | null;
  miles: number | null;
  riddenOn: string;
  birds: TripBird[];
  lifers: number;
  createdAt: string;
}

export interface TripStats {
  rides: number;
  birds: number;
  lifeList: number;
}

export interface LogRidePayload {
  trailExternalId?: string | null;
  trailName: string;
  difficulty?: string | null;
  miles?: number | null;
  riddenOn?: string;
  birds: TripBird[];
}

interface TripsResponse {
  trips: Trip[];
  stats: TripStats;
}

export async function logRide(payload: LogRidePayload): Promise<Trip> {
  return apiPost<Trip>("/trips", payload);
}

export function useTrips() {
  const [data, setData] = useState<TripsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    apiGet<TripsResponse>("/trips", controller.signal)
      .then((d) => {
        if (!controller.signal.aborted) {
          setData(d);
          setError(null);
        }
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "Failed to load trips");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [reloadKey]);

  return {
    trips: data?.trips ?? [],
    stats: data?.stats ?? { rides: 0, birds: 0, lifeList: 0 },
    loading,
    error,
    reload,
  };
}
