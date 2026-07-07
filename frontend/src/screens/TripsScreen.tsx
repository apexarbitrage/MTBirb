import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { BottomNav } from "../components/BottomNav";
import { CenterMessage } from "../components/CenterMessage";
import { DifficultyMarker } from "../components/DifficultyMarker";
import { normalizeDifficulty, scoreChipBg, scoreColor } from "../data/trails";
import { useTrips } from "../data/useTrips";
import { deleteTrailRoute, useTrailRoutes } from "../data/useTrailRoutes";
import { useAppState } from "../state/AppState";
import common from "../styles/common.module.css";
import s from "./TripsScreen.module.css";

function fmtDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function TripsScreen() {
  const { tripsSegment, setTripsSegment } = useAppState();
  return (
    <div className={common.screen}>
      <div className={s.header}>
        <div className={common.eyebrow}>Your history</div>
        <div className={common.title}>{tripsSegment === "trips" ? "Trips" : "Routes"}</div>
        <div className={s.segRow}>
          {(
            [
              ["trips", "Trips"],
              ["routes", "Routes"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              className={`${s.segBtn} ${tripsSegment === key ? s.segBtnActive : ""}`}
              onClick={() => setTripsSegment(key)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {tripsSegment === "trips" ? <TripsSegment /> : <RoutesSegment />}
      <BottomNav active="trips" />
    </div>
  );
}

function TripsSegment() {
  const { trips, stats, loading, error, reload } = useTrips();

  return (
    <>
      <div className={s.statRowInBody}>
        <div className={s.statTile}>
          <div className={s.statNum}>{stats.rides}</div>
          <div className={s.statLabel}>RIDES LOGGED</div>
        </div>
        <div className={s.statTile}>
          <div className={s.statNum} style={{ color: "var(--terracotta)" }}>
            {stats.lifeList}
          </div>
          <div className={s.statLabel}>BIRDS SPOTTED</div>
        </div>
      </div>

      {loading ? (
        <CenterMessage title="Loading trips…" />
      ) : error ? (
        <CenterMessage title="Couldn't load trips" detail={error} onRetry={reload} />
      ) : trips.length === 0 ? (
        <CenterMessage
          title="No rides logged yet"
          detail="Open a trail and tap “Log this ride” to record it and the birds you saw."
        />
      ) : (
        <div className={s.list}>
          {trips.map((tr) => {
            const diff = normalizeDifficulty(tr.difficulty);
            return (
              <div key={tr.id} className={s.tripCard}>
                <div className={s.tripTop}>
                  <div className={common.monoMeta}>{fmtDate(tr.riddenOn)}</div>
                  {tr.lifers > 0 && (
                    <div className={s.liferBadge}>
                      +{tr.lifers} bird{tr.lifers > 1 ? "s" : ""}
                    </div>
                  )}
                </div>
                <div className={s.tripMain}>
                  {diff && <DifficultyMarker diff={diff} size={10} />}
                  <div className={s.tripTrail}>{tr.trailName}</div>
                  <div className={common.monoMeta}>
                    {[
                      tr.miles != null ? `${tr.miles} mi` : null,
                      tr.routeId != null ? "route" : diff,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </div>
                </div>
                {tr.birds.length > 0 && (
                  <div className={s.birdChips}>
                    {tr.birds.map((b) => (
                      <span key={b.commonName} className={s.birdChip}>
                        {b.commonName}
                      </span>
                    ))}
                  </div>
                )}
                {tr.photos.length > 0 && (
                  <div style={{ display: "flex", gap: 6, marginTop: 10, flexWrap: "wrap" }}>
                    {tr.photos.map((p, i) => (
                      <div key={i} style={{ position: "relative" }}>
                        <img
                          src={p.thumb}
                          alt=""
                          style={{ width: 56, height: 56, objectFit: "cover", borderRadius: 8, display: "block" }}
                        />
                        {p.lat != null && (
                          <span
                            style={{
                              position: "absolute",
                              left: 2,
                              bottom: 2,
                              fontSize: 9,
                              background: "rgba(33,48,42,0.7)",
                              borderRadius: 4,
                              padding: "0 3px",
                            }}
                          >
                            📍
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}

function RoutesSegment() {
  const navigate = useNavigate();
  const { setDetailRouteId } = useAppState();
  const { routes, loading, error, reload } = useTrailRoutes();
  // Two-tap delete: first tap arms this route's button, second confirms.
  const [armed, setArmed] = useState<number | null>(null);

  const remove = async (id: number) => {
    try {
      await deleteTrailRoute(id);
    } finally {
      setArmed(null);
      reload();
    }
  };

  if (loading) return <CenterMessage title="Loading routes…" />;
  if (error) return <CenterMessage title="Couldn't load routes" detail={error} onRetry={reload} />;
  if (routes.length === 0)
    return (
      <CenterMessage
        title="No saved routes yet"
        detail="Open a trail and tap the route button to chain it with the trails around it."
      />
    );

  return (
    <div className={s.list}>
      {routes.map((r) => (
        <div key={r.id} className={s.tripCard}>
          <button
            onClick={() => {
              setDetailRouteId(r.id);
              navigate("/route");
            }}
            style={{ display: "block", width: "100%", textAlign: "left", background: "none", border: "none", padding: 0, cursor: "pointer" }}
          >
            <div className={s.tripTop}>
              <div className={common.monoMeta}>{fmtDate(r.createdAt.slice(0, 10))}</div>
              {r.wildlifeScore != null && (
                <span
                  className={s.routeScoreChip}
                  style={{ color: scoreColor(r.wildlifeScore), background: scoreChipBg(r.wildlifeScore) }}
                >
                  {r.wildlifeScore}
                </span>
              )}
            </div>
            <div className={s.tripMain}>
              <div className={s.tripTrail}>{r.name}</div>
            </div>
            <div className={common.monoMeta} style={{ marginTop: 4 }}>
              {[
                `${r.trailCount} trails`,
                r.miles != null ? `${r.miles} mi` : null,
                r.ascentFt != null ? `↑ ${r.ascentFt.toLocaleString()} ft` : null,
                r.mappedCount < r.trailCount ? `${r.mappedCount}/${r.trailCount} mapped` : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </div>
          </button>
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
            {armed === r.id ? (
              <div style={{ display: "flex", gap: 8 }}>
                <button className={s.routeDeleteBtn} onClick={() => setArmed(null)}>
                  Keep
                </button>
                <button className={`${s.routeDeleteBtn} ${s.routeDeleteConfirm}`} onClick={() => remove(r.id)}>
                  Delete route
                </button>
              </div>
            ) : (
              <button className={s.routeDeleteBtn} onClick={() => setArmed(r.id)}>
                Delete…
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
