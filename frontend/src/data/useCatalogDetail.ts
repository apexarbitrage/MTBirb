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
  // The backend warms the OSM line + USGS terrain in the background; true until they've landed.
  enriching?: boolean;
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
    enriching: boolean;
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
    let attempts = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;

    // The detail returns fast with whatever's cached; if the backend is still warming the line +
    // terrain, poll a few times so the map and elevation fill in without blocking the screen.
    const loadDetail = () => {
      apiGet<DetailResponse>(`/catalog/trails/${id}`, c.signal)
        .then((d) => {
          if (c.signal.aborted) return;
          // Keep polling only while there's budget left; once it's spent, drop `enriching` so a
          // trail that can't be lined stops showing a "loading" placeholder forever.
          const stillTrying = !!d.enriching && attempts < 6;
          setDetail({ key: id, trail: d.trail, linePoints: d.linePoints, enriching: stillTrying, error: null });
          if (stillTrying) {
            attempts += 1;
            timer = setTimeout(loadDetail, 2500);
          }
        })
        .catch((e) => {
          if (!c.signal.aborted)
            setDetail({
              key: id,
              trail: null,
              linePoints: null,
              enriching: false,
              error: e instanceof Error ? e.message : "Failed to load trail",
            });
        });
    };
    loadDetail();

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
    return () => {
      c.abort();
      if (timer) clearTimeout(timer);
    };
  }, [id]);

  const d = detail && detail.key === id ? detail : null;
  const w = wildlife && wildlife.key === id ? wildlife : null;
  const wx = weather && weather.key === id ? weather : null;

  return {
    trail: d?.trail ?? null,
    linePoints: d?.linePoints ?? null,
    error: d?.error ?? null,
    loading: d === null,
    enriching: d?.enriching ?? false,
    species: w?.species ?? null,
    areaRadiusKm: w?.areaRadiusKm ?? null,
    weather: wx?.current ?? null,
  };
}
