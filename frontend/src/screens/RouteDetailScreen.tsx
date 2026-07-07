import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { BackButton } from "../components/BackButton";
import { CenterMessage } from "../components/CenterMessage";
import { DifficultyMarker } from "../components/DifficultyMarker";
import { LogRideSheet } from "../components/LogRideSheet";
import { ScoreRing } from "../components/ScoreRing";
import { TrailMap } from "../components/TrailMap";
import { fmtTime, normalizeDifficulty } from "../data/trails";
import { useOptimalTime } from "../data/useOptimalTime";
import { useTrailRouteDetail } from "../data/useTrailRouteDetail";
import { useAppState } from "../state/AppState";
import s from "./TrailDetailScreen.module.css";

/*
 * A saved route's detail: a simplified trail detail over the combined chain - map of the whole
 * line, summed stats, species near any part of the route, the best-time window, GPX export, and
 * navigation to the starting trailhead. Reuses TrailDetailScreen's styles so a route reads as
 * "a big trail", which is exactly what it is to the rider.
 */

export function RouteDetailScreen() {
  const navigate = useNavigate();
  const { detailRouteId, setDetailTrailId, setSpeciesFilter } = useAppState();
  const { route, species, areaRadiusKm, error, loading } = useTrailRouteDetail(detailRouteId);
  const { data: optimal } = useOptimalTime(
    detailRouteId != null ? String(detailRouteId) : undefined,
    "route",
  );
  const [showLog, setShowLog] = useState(false);

  if (loading || error || !route) {
    return (
      <div className={s.screen}>
        <div style={{ position: "absolute", top: 16, left: 16, zIndex: 2 }}>
          <BackButton bg="rgba(45,59,45,0.1)" stroke="var(--forest)" blur={false} />
        </div>
        {loading && detailRouteId != null ? (
          <CenterMessage title="Loading route…" />
        ) : error ? (
          <CenterMessage title="Couldn't load route" detail={error} />
        ) : (
          <CenterMessage title="Route not found" detail="Pick a route from the Trips tab." />
        )}
      </div>
    );
  }

  const hasLine = route.linePoints.length > 1;

  return (
    <div className={s.screen}>
      <div className={s.scroll}>
        <div className={s.body} style={{ paddingTop: "var(--screen-pad-top)" }}>
          <div style={{ marginBottom: 12 }}>
            <BackButton bg="rgba(45,59,45,0.1)" stroke="var(--forest)" blur={false} />
          </div>

          <div className={s.titleRow}>
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--terracotta)" }}>
                SAVED ROUTE
              </div>
              <div className={s.trailTitle}>{route.name}</div>
              <div className={s.location}>
                {route.trailCount} trails
                {route.mappedCount < route.trailCount ? ` · ${route.mappedCount}/${route.trailCount} mapped` : ""}
                {route.missingTrailIds.length > 0 ? ` · ${route.missingTrailIds.length} no longer in catalog` : ""}
              </div>
            </div>
            <ScoreRing
              score={route.wildlifeScore ?? 0}
              size={64}
              centerSize={51}
              centerBg="var(--sand)"
              track="rgba(194,112,61,0.16)"
              numberStyle={{ fontSize: 21 }}
              label="MATCH"
            />
          </div>

          {/* Combined stat grid */}
          <div className={s.statGrid}>
            <div className={s.statTile}>
              <div className={s.statNum}>{route.miles ?? "–"}</div>
              <div className={s.statLabel}>MILES</div>
            </div>
            <div className={s.statTile}>
              <div className={s.statNum} style={{ color: "var(--success)" }}>
                {route.ascentFt != null ? `↑ ${route.ascentFt.toLocaleString()}` : "–"}
              </div>
              <div className={s.statLabel}>CLIMB FT</div>
            </div>
            <div className={s.statTile}>
              <div className={s.statNum}>{route.rideTimeMin != null ? fmtTime(route.rideTimeMin) : "–"}</div>
              <div className={s.statLabel}>EST TIME</div>
            </div>
          </div>

          {/* Best-time window over the whole route */}
          {optimal?.available && optimal.bestWindow && (
            <button
              onClick={() =>
                navigate("/optimal-time", { state: { route: { id: route.id, name: route.name } } })
              }
              style={{
                width: "100%",
                marginTop: 10,
                padding: "11px 14px",
                borderRadius: 12,
                border: "1px solid var(--sage-pale)",
                background: "var(--sage-tint)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 10,
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              <div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--sage)" }}>
                  BEST TIME TO RIDE
                </div>
                <div style={{ fontWeight: 800, fontSize: 16, color: "var(--ink)" }}>{optimal.bestWindow}</div>
                {optimal.bestWindowWhy && (
                  <div style={{ fontSize: 12, color: "var(--text-muted-2)" }}>{optimal.bestWindowWhy}</div>
                )}
              </div>
              <span style={{ color: "var(--sage)", fontSize: 18 }}>→</span>
            </button>
          )}

          <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
            <button
              onClick={() => setShowLog(true)}
              style={{
                flex: 1,
                padding: "13px",
                borderRadius: 12,
                border: "1.5px solid var(--terracotta)",
                background: "var(--terracotta-tint)",
                color: "var(--terracotta)",
                fontWeight: 800,
                fontSize: 15,
                cursor: "pointer",
              }}
            >
              ＋ Log this ride
            </button>
          </div>

          {/* The whole chain over TomTom terrain */}
          {hasLine && (
            <div className={s.elevCard}>
              <div className={s.elevHead}>
                <span style={{ color: "var(--sage)" }}>ROUTE MAP</span>
                <span style={{ color: "var(--text-placeholder)" }}>
                  {route.miles != null ? `${route.miles} mi` : "TomTom"}
                </span>
              </div>
              <TrailMap line={route.linePoints} height={220} />
            </div>
          )}

          {/* The chain, in ride order - tap through to each trail's own detail */}
          <div className={s.elevCard}>
            <div className={s.elevHead}>
              <span style={{ color: "var(--sage)" }}>TRAILS ON THIS ROUTE</span>
              <span style={{ color: "var(--text-placeholder)" }}>in order</span>
            </div>
            {route.members.map((m, i) => {
              const diff = normalizeDifficulty(m.difficulty);
              const mi = m.metricLengthMi ?? m.lengthMi;
              return (
                <button
                  key={m.id}
                  onClick={() => {
                    setDetailTrailId(m.id);
                    navigate("/trail");
                  }}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    width: "100%",
                    padding: "10px 2px",
                    background: "none",
                    border: "none",
                    borderBottom: i < route.members.length - 1 ? "1px solid var(--card-tile-divider)" : "none",
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                >
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)", width: 16 }}>
                    {i + 1}
                  </span>
                  {diff && <DifficultyMarker diff={diff} size={10} />}
                  <span style={{ flex: 1, fontWeight: 700, fontSize: 14, color: "var(--ink)" }}>{m.name}</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)" }}>
                    {mi != null ? `${mi} mi` : ""}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Species near any part of the route */}
          <div className={s.ebirdCard}>
            <div className={s.ebirdHead}>
              <span className={s.ebirdHeadTitle}>BIRDS ON THIS ROUTE</span>
              <span className={s.ebirdHeadMeta}>eBird{areaRadiusKm ? ` · ${areaRadiusKm}km` : ""}</span>
            </div>
            {species === null ? (
              <div className={s.ebirdEmpty}>Loading recent reports…</div>
            ) : species.length === 0 ? (
              <div className={s.ebirdEmpty}>No recent eBird reports along this route.</div>
            ) : (
              <div className={s.ebirdChips}>
                {species.map((sp) => (
                  <button
                    key={sp.species_code}
                    className={s.ebirdChip}
                    style={{ cursor: "pointer", border: "none" }}
                    title={`Find trails for ${sp.common_name}`}
                    onClick={() => {
                      setSpeciesFilter({ code: sp.species_code, name: sp.common_name });
                      navigate("/trails");
                    }}
                  >
                    {sp.common_name}
                    <span className={s.ebirdCount}>{sp.observations}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Action bar: GPX for the whole chain + drive to the first trailhead */}
      <div className={s.actionBar}>
        {hasLine ? (
          <a
            className={s.garminBtn}
            href={`/api/trail-routes/${route.id}/export.gpx`}
            download
            aria-label="Export GPX course for Garmin"
          >
            <div style={{ width: 18, height: 13, border: "2px solid var(--forest)", borderRadius: 3 }} />
            <span className={s.garminLabel}>GARMIN</span>
          </a>
        ) : (
          <button className={s.garminBtn} disabled aria-label="No line to export" style={{ opacity: 0.4 }}>
            <div style={{ width: 18, height: 13, border: "2px solid var(--forest)", borderRadius: 3 }} />
            <span className={s.garminLabel}>GARMIN</span>
          </button>
        )}
        <button
          className={s.navBtn}
          disabled={route.members.length === 0}
          onClick={() => {
            if (route.members.length === 0) return;
            setDetailTrailId(route.members[0].id);
            navigate("/navigate");
          }}
        >
          Navigate to start →
        </button>
      </div>

      {showLog && (
        <LogRideSheet
          trail={{ id: null, name: route.name, difficulty: null, miles: route.miles }}
          routeId={route.id}
          options={(species ?? []).map((sp) => ({ speciesCode: sp.species_code, commonName: sp.common_name }))}
          onClose={() => setShowLog(false)}
          onLogged={() => {
            setShowLog(false);
            navigate("/trips");
          }}
        />
      )}
    </div>
  );
}
