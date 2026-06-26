import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { BackButton } from "../components/BackButton";
import { useTrails } from "../data/TrailsProvider";
import { useDriveRoute } from "../data/useDriveRoute";
import { useAppState } from "../state/AppState";
import s from "./FunDriveNavScreen.module.css";

/*
 * Fun-drive navigation to the trailhead, on a real TomTom map (tiles proxied through the backend so
 * the key stays server-side). The route, twistiness, and ETA come from the live routing endpoint
 * (thrilling vs fastest); "Start drive" hands off to Google Maps seeded with waypoints sampled from
 * the thrilling route so the maps app follows the same scenic path. Leaflet owns the projection -
 * the route + markers are native layers fit to the map's bounds.
 */

const TERRACOTTA = "#c2703d";
const FOREST = "#2f5d3a";
const SAGE = "#8a9a5b";

type LngLat = [number, number];

function fmtDur(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? `${h} hr ${String(m).padStart(2, "0")} min` : `${m} min`;
}

function googleMapsUrl(
  origin: { lat: number; lon: number },
  destination: { lat: number; lon: number },
  waypoints?: LngLat[],
): string {
  const params = new URLSearchParams({
    api: "1",
    origin: `${origin.lat},${origin.lon}`,
    destination: `${destination.lat},${destination.lon}`,
    travelmode: "driving",
  });
  if (waypoints && waypoints.length) {
    params.set("waypoints", waypoints.map(([lon, lat]) => `${lat},${lon}`).join("|"));
  }
  return `https://www.google.com/maps/dir/?${params.toString()}`;
}

export function FunDriveNavScreen() {
  const { location, byId } = useTrails();
  const { detailTrailId } = useAppState();
  const trail = byId(detailTrailId);
  const { data, loading, unconfigured, error } = useDriveRoute(
    trail ? detailTrailId : undefined,
    location.lat,
    location.lon,
  );
  const [style, setStyle] = useState<"fun" | "fastest">("fun");

  const mapEl = useRef<HTMLDivElement>(null);
  const mapObj = useRef<L.Map | null>(null);
  const routeLayer = useRef<L.LayerGroup | null>(null);
  const fittedTrail = useRef<string | null>(null);

  // Create the Leaflet map once, pointed at the backend tile proxy.
  useEffect(() => {
    if (!mapEl.current || mapObj.current) return;
    const map = L.map(mapEl.current, { zoomControl: false, attributionControl: false }).setView(
      [location.lat, location.lon],
      11,
    );
    L.tileLayer("/api/map/tile/{z}/{x}/{y}", { minZoom: 3, maxZoom: 20 }).addTo(map);
    mapObj.current = map;
    return () => {
      map.remove();
      mapObj.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // (Re)draw the active route + markers whenever the data or style changes.
  useEffect(() => {
    const map = mapObj.current;
    if (!map || !data) return;
    routeLayer.current?.remove();
    const leg = style === "fun" ? data.fun : data.fastest;
    const latlngs = leg.points.map(([lon, lat]) => [lat, lon] as [number, number]);
    const group = L.layerGroup();
    if (latlngs.length > 1) {
      L.polyline(latlngs, { color: "#10160d", weight: 8, opacity: 0.45 }).addTo(group);
      L.polyline(latlngs, { color: style === "fun" ? TERRACOTTA : SAGE, weight: 4.5 }).addTo(group);
    }
    L.circleMarker([data.origin.lat, data.origin.lon], {
      radius: 6, color: TERRACOTTA, weight: 4, fillColor: "#fff", fillOpacity: 1,
    }).addTo(group);
    L.circleMarker([data.destination.lat, data.destination.lon], {
      radius: 7, color: "#fff", weight: 2.5, fillColor: FOREST, fillOpacity: 1,
    }).addTo(group);
    group.addTo(map);
    routeLayer.current = group;

    // Fit once per trail (not on every Fun/Fastest toggle), leaving room for the overlays.
    if (latlngs.length > 1 && fittedTrail.current !== data.trail) {
      map.fitBounds(L.latLngBounds(latlngs), { paddingTopLeft: [30, 170], paddingBottomRight: [30, 300] });
      fittedTrail.current = data.trail;
    }
  }, [data, style]);

  const cur = data?.fun.curviness;
  const leg = data ? (style === "fun" ? data.fun : data.fastest) : null;
  const filled = cur ? Math.round(cur.score / 20) : 0;
  const url = data
    ? googleMapsUrl(data.origin, data.destination, style === "fun" ? data.fun.waypoints : undefined)
    : "#";

  const overlay = !trail
    ? { title: "Pick a trail first", detail: "Open a trail, then tap Navigate to the trailhead." }
    : loading
      ? { title: "Plotting the fun drive…", detail: null as string | null }
      : unconfigured
        ? { title: "Routing isn't set up", detail: "Set TOMTOM_API_KEY in backend/.env, then restart the API." }
        : error || !data
          ? { title: "Couldn't plot a drive", detail: "No driving route to this trailhead." }
          : null;

  return (
    <div className={s.screen}>
      <div ref={mapEl} className={s.map} />
      <div
        style={{
          position: "absolute", top: 108, left: 16, zIndex: 500,
          fontFamily: "var(--font-mono)", fontSize: 9, color: "#fff",
          background: "rgba(0,0,0,0.35)", padding: "2px 6px", borderRadius: 5,
        }}
      >
        © TomTom
      </div>

      <div className={s.topRow} style={{ zIndex: 1000 }}>
        <BackButton bg="rgba(45,59,45,0.92)" stroke="#fff" />
        {data && (
          <div className={s.routePanel}>
            <div className={s.routeLabel}>ROUTE STYLE</div>
            <div className={s.routeOptions}>
              {(
                [
                  ["fun", "Fun drive", cur ? cur.label.toUpperCase() : "TWISTY"],
                  ["fastest", "Fastest", `${data.fastest.durationMin} MIN`],
                ] as const
              ).map(([key, name, sub]) => {
                const on = style === key;
                return (
                  <button
                    key={key}
                    className={`${s.routeOpt} ${on ? s.routeOptActive : s.routeOptIdle}`}
                    onClick={() => setStyle(key)}
                  >
                    <div className={`${s.routeOptName} ${on ? s.routeOptNameActive : ""}`}>{name}</div>
                    <div className={s.routeOptSub}>{sub}</div>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {overlay && (
        <div
          style={{
            position: "absolute", inset: 0, display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", textAlign: "center",
            padding: "0 36px", color: "var(--ink)", pointerEvents: "none", zIndex: 600,
          }}
        >
          <div style={{ background: "rgba(255,255,255,0.92)", borderRadius: 16, padding: "16px 20px", boxShadow: "0 8px 24px rgba(0,0,0,0.25)" }}>
            <div style={{ fontSize: 17, fontWeight: 800 }}>{overlay.title}</div>
            {overlay.detail && <div style={{ fontSize: 13, marginTop: 6, color: "var(--text-muted)" }}>{overlay.detail}</div>}
          </div>
        </div>
      )}

      {data && leg && (
        <div className={s.bottomCard} style={{ zIndex: 1000 }}>
          <div className={s.etaRow}>
            <div>
              <div className={s.eta}>{fmtDur(leg.durationMin)}</div>
              <div className={s.etaSub}>{leg.distanceMi} mi · to {trail?.name}</div>
            </div>
            {style === "fun" && data.extraMin > 0 && (
              <div style={{ textAlign: "right" }}>
                <div className={s.extraNum}>+{data.extraMin}</div>
                <div className={s.extraLabel}>MORE MIN, WORTH IT</div>
              </div>
            )}
          </div>

          {style === "fun" && cur && (
            <div className={s.twistCard}>
              <div className={s.twistTop}>
                <span style={{ color: "var(--text-muted-2)", fontWeight: 600 }}>Twistiness</span>
                <span style={{ fontWeight: 800, color: "var(--terracotta)" }}>
                  {cur.label} · {cur.curve_count} curves
                </span>
              </div>
              <div className={s.twistBars}>
                {[0, 1, 2, 3, 4].map((i) => (
                  <div key={i} className={s.twistSeg} style={{ background: i < filled ? "var(--terracotta)" : "#e3d2c3" }} />
                ))}
              </div>
              <div className={s.twistNote}>via TomTom thrilling route</div>
            </div>
          )}

          <a className={s.startBtn} href={url} target="_blank" rel="noopener noreferrer">
            Start drive
          </a>
        </div>
      )}
    </div>
  );
}
