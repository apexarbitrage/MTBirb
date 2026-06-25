/*
 * The app's "near you" location. Starts on a sensible default (Bay Area, which the backend has
 * seeded and scored) so the first render has trails immediately, then upgrades to the device's
 * real position if the user allows it. On denial/unavailability we simply keep the default.
 */

import { useEffect, useState } from "react";

export interface AppLocation {
  lat: number;
  lon: number;
  label: string;
  source: "default" | "device";
}

const DEFAULT_LOCATION: AppLocation = {
  lat: 37.55,
  lon: -122.31,
  label: "Bay Area",
  source: "default",
};

export function useGeolocation(): AppLocation {
  const [location, setLocation] = useState<AppLocation>(DEFAULT_LOCATION);

  useEffect(() => {
    if (!("geolocation" in navigator)) return;
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        setLocation({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          label: "Near you",
          source: "device",
        }),
      () => {}, // denied or unavailable → keep the default
      { timeout: 8000, maximumAge: 10 * 60 * 1000 },
    );
  }, []);

  return location;
}
