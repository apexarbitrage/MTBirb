/*
 * Loads a catalog trail's detail: the trail + its OSM line, the area's recent eBird species,
 * and the live forecast - three parallel calls. Each is keyed by trail id so switching trails
 * never shows stale data, and state is only set in async callbacks. Wildlife/weather fail soft.
 */

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";
import type { CatalogTrail } from "./useCatalogTrails";
import type { NearbySpecies } from "./useTrailWildlife";
import type { WeatherPeriod } from "./useTrailWeather";

type LinePoint = [number, number];

interface DetailResponse {
  trail: CatalogTrail;
  linePoints: LinePoint[] | null;
}
interface WildlifeResponse {
  syncedNow: number;
  areaRadiusKm: number;
  species: NearbySpecies[];
}
interface WeatherResponse {
  periods: WeatherPeriod[];
}

export function useCatalogDetail(id: string) {
  const [detail, setDetail] = useState<{
    key: string;
    trail: CatalogTrail | null;
    linePoints: LinePoint[] | null;
    error: string | null;
  } | null>(null);
  const [wildlife, setWildlife] = useState<{
    key: string;
    species: NearbySpecies[];
    areaRadiusKm: number | null;
  } | null>(null);
  const [weather, setWeather] = useState<{ key: string; current: WeatherPeriod | null } | null>(null);

  useEffect(() => {
    const c = new AbortController();
    apiGet<DetailResponse>(`/catalog/trails/${id}`, c.signal)
      .then((d) => {
        if (!c.signal.aborted)
          setDetail({ key: id, trail: d.trail, linePoints: d.linePoints, error: null });
      })
      .catch((e) => {
        if (!c.signal.aborted)
          setDetail({
            key: id,
            trail: null,
            linePoints: null,
            error: e instanceof Error ? e.message : "Failed to load trail",
          });
      });
    apiGet<WildlifeResponse>(`/catalog/trails/${id}/wildlife`, c.signal)
      .then((d) => {
        if (!c.signal.aborted)
          setWildlife({ key: id, species: d.species, areaRadiusKm: d.areaRadiusKm });
      })
      .catch(() => {
        if (!c.signal.aborted) setWildlife({ key: id, species: [], areaRadiusKm: null });
      });
    apiGet<WeatherResponse>(`/catalog/trails/${id}/weather`, c.signal)
      .then((d) => {
        if (!c.signal.aborted) setWeather({ key: id, current: d.periods[0] ?? null });
      })
      .catch(() => {
        if (!c.signal.aborted) setWeather({ key: id, current: null });
      });
    return () => c.abort();
  }, [id]);

  const d = detail && detail.key === id ? detail : null;
  const w = wildlife && wildlife.key === id ? wildlife : null;
  const wx = weather && weather.key === id ? weather : null;

  return {
    trail: d?.trail ?? null,
    linePoints: d?.linePoints ?? null,
    error: d?.error ?? null,
    loading: d === null,
    species: w?.species ?? null,
    areaRadiusKm: w?.areaRadiusKm ?? null,
    weather: wx?.current ?? null,
  };
}
