/*
 * Fetches the "fun drive" + fastest route to a trailhead (GET /api/catalog/trails/{id}/drive),
 * computed server-side via TomTom. Fails soft like the other hooks; surfaces `unconfigured` (the
 * 503 the backend returns when TOMTOM_API_KEY isn't set) so the screen can prompt for the key.
 */

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";

export interface DriveCurviness {
  score: number;
  label: string;
  curve_count: number;
}

export interface DriveLeg {
  distanceMi: number;
  durationMin: number;
  points: [number, number][]; // [lon, lat]
  curviness?: DriveCurviness;
  waypoints?: [number, number][]; // [lon, lat]
}

export interface DriveRoute {
  trail: string;
  origin: { lat: number; lon: number };
  destination: { lat: number; lon: number };
  fun: DriveLeg;
  fastest: DriveLeg;
  extraMin: number;
}

export function useDriveRoute(trailId: string | undefined, lat: number, lon: number) {
  const key = `${trailId}|${lat},${lon}`;
  const [loaded, setLoaded] = useState<{
    key: string;
    data: DriveRoute | null;
    unconfigured: boolean;
    error: string | null;
  } | null>(null);

  useEffect(() => {
    if (!trailId) return;
    const controller = new AbortController();
    apiGet<DriveRoute>(
      `/catalog/trails/${trailId}/drive?from_lat=${lat}&from_lon=${lon}`,
      controller.signal,
    )
      .then((d) => {
        if (!controller.signal.aborted) setLoaded({ key, data: d, unconfigured: false, error: null });
      })
      .catch((e) => {
        if (controller.signal.aborted) return;
        const msg = e instanceof Error ? e.message : "Couldn't load the drive";
        setLoaded({ key, data: null, unconfigured: msg.includes("(503)"), error: msg });
      });
    return () => controller.abort();
  }, [trailId, lat, lon, key]);

  const cur = loaded && loaded.key === key ? loaded : null;
  return {
    data: cur?.data ?? null,
    loading: cur === null,
    unconfigured: cur?.unconfigured ?? false,
    error: cur?.error ?? null,
  };
}
