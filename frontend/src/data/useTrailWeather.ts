/*
 * Fetches the live NWS forecast for a catalog trail (GET /api/catalog/trails/{id}/weather) and
 * exposes the current period. Fails soft: on error it resolves to an empty list so callers fall
 * back gracefully. `current` is null while the request for the current id is in flight.
 */

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";

export interface WeatherPeriod {
  name: string;
  startTime: string;
  isDaytime: boolean;
  temperature: number;
  temperatureUnit: string;
  shortForecast: string;
  windSpeed: string;
}

interface WeatherResponse {
  trail: string;
  periods: WeatherPeriod[];
}

export function useTrailWeather(slug: string | undefined) {
  const [loaded, setLoaded] = useState<{ slug: string; periods: WeatherPeriod[] } | null>(null);

  useEffect(() => {
    if (!slug) return;
    const controller = new AbortController();
    apiGet<WeatherResponse>(`/catalog/trails/${slug}/weather`, controller.signal)
      .then((d) => {
        if (!controller.signal.aborted) setLoaded({ slug, periods: d.periods });
      })
      .catch(() => {
        if (!controller.signal.aborted) setLoaded({ slug, periods: [] });
      });
    return () => controller.abort();
  }, [slug]);

  const periods = loaded && loaded.slug === slug ? loaded.periods : null;
  return { current: periods && periods.length > 0 ? periods[0] : null };
}

/** Condense an NWS shortForecast ("Partly Sunny then Chance Light Rain") to a compact label. */
export function shortSky(forecast: string): string {
  return forecast.split(" then ")[0];
}
