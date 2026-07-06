/*
 * The trail's OSM line drawn over real TomTom terrain (satellite + hybrid road/label overlay),
 * tiles proxied through the backend so the key stays server-side (routers/map.py `?layer=`).
 * Leaflet owns the Web-Mercator projection; the line + optional geotagged photo pins are native
 * layers fit to the line's bounds. Rendered non-interactive (a static preview) so it never traps
 * the page scroll inside the Trail-detail card - the Navigate screen is the interactive map.
 */

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const TERRACOTTA = "#c2703d";

interface GeoPoint {
  lat: number;
  lon: number;
}

interface Props {
  /** The trail line as [lon, lat] pairs (the LinePoint shape from the catalog detail). */
  line: [number, number][];
  /** Optional geotagged photo positions to pin on the line. */
  photos?: GeoPoint[];
  height?: number;
}

export function TrailMap({ line, photos = [], height = 200 }: Props) {
  const mapEl = useRef<HTMLDivElement>(null);
  const mapObj = useRef<L.Map | null>(null);
  const overlay = useRef<L.LayerGroup | null>(null);

  // Create the map once, stacking satellite imagery + the hybrid road/label overlay.
  useEffect(() => {
    if (!mapEl.current || mapObj.current) return;
    const map = L.map(mapEl.current, {
      zoomControl: false,
      // Keep attribution on (the trail line is OSM-derived; tiles are TomTom) - it's a license
      // obligation. `prefix: false` drops the "Leaflet" flag to keep the small preview uncluttered.
      attributionControl: true,
      dragging: false,
      scrollWheelZoom: false,
      doubleClickZoom: false,
      touchZoom: false,
      boxZoom: false,
      keyboard: false,
    });
    map.attributionControl.setPrefix(false);
    const credit =
      '© TomTom · Trail data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors';
    L.tileLayer("/api/map/tile/{z}/{x}/{y}?layer=sat", { minZoom: 3, maxZoom: 18, attribution: credit }).addTo(map);
    L.tileLayer("/api/map/tile/{z}/{x}/{y}?layer=hybrid", { minZoom: 3, maxZoom: 18 }).addTo(map);
    mapObj.current = map;
    requestAnimationFrame(() => map.invalidateSize());
    return () => {
      map.remove();
      mapObj.current = null;
    };
  }, []);

  // (Re)draw the line + photo pins and refit whenever they change.
  useEffect(() => {
    const map = mapObj.current;
    if (!map) return;
    overlay.current?.remove();
    const latlngs = line.map(([lon, lat]) => [lat, lon] as [number, number]);
    const group = L.layerGroup();
    if (latlngs.length > 1) {
      L.polyline(latlngs, { color: "#10160d", weight: 7, opacity: 0.4 }).addTo(group);
      L.polyline(latlngs, { color: TERRACOTTA, weight: 4 }).addTo(group);
    }
    for (const p of photos) {
      L.circleMarker([p.lat, p.lon], {
        radius: 5, color: "#fff", weight: 2, fillColor: TERRACOTTA, fillOpacity: 1,
      }).addTo(group);
    }
    group.addTo(map);
    overlay.current = group;
    if (latlngs.length > 1) {
      map.fitBounds(L.latLngBounds(latlngs), { padding: [22, 22] });
      requestAnimationFrame(() => map.invalidateSize());
    }
  }, [line, photos]);

  return (
    <div
      ref={mapEl}
      style={{ height, width: "100%", borderRadius: 12, overflow: "hidden", background: "var(--sage-tint)" }}
    />
  );
}
