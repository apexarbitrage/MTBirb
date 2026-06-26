import { useState } from "react";
import { BackButton } from "../components/BackButton";
import { useTrails } from "../data/TrailsProvider";
import { useDriveRoute } from "../data/useDriveRoute";
import { useAppState } from "../state/AppState";
import s from "./FunDriveNavScreen.module.css";

/*
 * Fun-drive navigation to the trailhead. The route, twistiness, and ETA come from the live TomTom
 * routing endpoint (thrilling vs fastest); "Start drive" hands off to Google Maps seeded with
 * waypoints sampled from the thrilling route, so the maps app follows the same scenic path.
 */

const VB_W = 320;
const VB_H = 420;
// Project the route into this padded band (kept in the upper-middle, clear of the bottom card).
const BX0 = 22;
const BX1 = 298;
const BY0 = 30;
const BY1 = 300;

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

function NavShell({ title, detail }: { title: string; detail?: string | null }) {
  return (
    <div className={s.screen}>
      <div className={s.map} />
      <div style={{ position: "absolute", top: 54, left: 16, zIndex: 2 }}>
        <BackButton bg="rgba(45,59,45,0.92)" stroke="#fff" />
      </div>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: "0 36px",
          color: "#fff",
        }}
      >
        <div style={{ fontSize: 18, fontWeight: 800 }}>{title}</div>
        {detail && <div style={{ fontSize: 13, marginTop: 6, color: "var(--sage-on-dark)" }}>{detail}</div>}
      </div>
    </div>
  );
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

  if (!trail) return <NavShell title="Pick a trail first" detail="Open a trail, then tap Navigate to the trailhead." />;
  if (loading) return <NavShell title="Plotting the fun drive…" />;
  if (unconfigured)
    return <NavShell title="Routing isn't set up" detail="Set TOMTOM_API_KEY in backend/.env, then restart the API." />;
  if (error || !data) return <NavShell title="Couldn't plot a drive" detail="No driving route to this trailhead." />;

  const leg = style === "fun" ? data.fun : data.fastest;
  const cur = data.fun.curviness;

  // Equirectangular projection over both legs + endpoints, uniform scale (markers stay round).
  const all: LngLat[] = [
    ...data.fun.points,
    ...data.fastest.points,
    [data.origin.lon, data.origin.lat],
    [data.destination.lon, data.destination.lat],
  ];
  const minLon = Math.min(...all.map((p) => p[0]));
  const maxLon = Math.max(...all.map((p) => p[0]));
  const minLat = Math.min(...all.map((p) => p[1]));
  const maxLat = Math.max(...all.map((p) => p[1]));
  const cosLat = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);
  const rangeX = (maxLon - minLon) * cosLat || 1e-6;
  const rangeY = maxLat - minLat || 1e-6;
  const scale = Math.min((BX1 - BX0) / rangeX, (BY1 - BY0) / rangeY);
  const offX = BX0 + ((BX1 - BX0) - rangeX * scale) / 2;
  const offY = BY0 + ((BY1 - BY0) - rangeY * scale) / 2;
  const project = (lon: number, lat: number): [number, number] => [
    offX + (lon - minLon) * cosLat * scale,
    offY + (maxLat - lat) * scale,
  ];

  const polyline = leg.points.map(([lon, lat]) => project(lon, lat).map((n) => n.toFixed(1)).join(",")).join(" ");
  const [ox, oy] = project(data.origin.lon, data.origin.lat);
  const [dx, dy] = project(data.destination.lon, data.destination.lat);
  const url = googleMapsUrl(data.origin, data.destination, style === "fun" ? data.fun.waypoints : undefined);
  const filled = cur ? Math.round(cur.score / 20) : 0;

  return (
    <div className={s.screen}>
      <div className={s.map} />

      <svg viewBox={`0 0 ${VB_W} ${VB_H}`} width="100%" height="100%" preserveAspectRatio="xMidYMid meet" className={s.routeSvg}>
        <polyline points={polyline} style={{ fill: "none", stroke: "rgba(8,12,7,0.5)", strokeWidth: 7, strokeLinecap: "round", strokeLinejoin: "round" }} />
        <polyline points={polyline} style={{ fill: "none", stroke: style === "fun" ? "var(--terracotta)" : "var(--sage)", strokeWidth: 3.5, strokeLinecap: "round", strokeLinejoin: "round" }} />
        <polyline points={polyline} style={{ fill: "none", stroke: "rgba(255,255,255,0.7)", strokeWidth: 1, strokeLinecap: "round", strokeDasharray: "1 9" }} />
        <circle cx={ox} cy={oy} r={5.5} fill="#fff" stroke="var(--terracotta)" strokeWidth={3.5} />
        <circle cx={dx} cy={dy} r={6.5} fill="var(--forest)" stroke="#fff" strokeWidth={2.5} />
      </svg>

      <div className={s.topRow}>
        <BackButton bg="rgba(45,59,45,0.92)" stroke="#fff" />
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
      </div>

      <div className={s.bottomCard}>
        <div className={s.etaRow}>
          <div>
            <div className={s.eta}>{fmtDur(leg.durationMin)}</div>
            <div className={s.etaSub}>{leg.distanceMi} mi · to {trail.name}</div>
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
    </div>
  );
}
