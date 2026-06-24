import { BottomNav } from "../components/BottomNav";
import { CenterMessage } from "../components/CenterMessage";
import { DifficultyMarker } from "../components/DifficultyMarker";
import { normalizeDifficulty } from "../data/trails";
import { useTrips } from "../data/useTrips";
import common from "../styles/common.module.css";
import s from "./TripsScreen.module.css";

function fmtDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function TripsScreen() {
  const { trips, stats, loading, error, reload } = useTrips();

  return (
    <div className={common.screen}>
      <div className={s.header}>
        <div className={common.eyebrow}>Your history</div>
        <div className={common.title}>Trips</div>
        <div className={s.statRow}>
          <div className={s.statTile}>
            <div className={s.statNum}>{stats.rides}</div>
            <div className={s.statLabel}>RIDES LOGGED</div>
          </div>
          <div className={s.statTile}>
            <div className={s.statNum} style={{ color: "var(--terracotta)" }}>
              {stats.lifeList}
            </div>
            <div className={s.statLabel}>LIFE LIST</div>
          </div>
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
                      +{tr.lifers} lifer{tr.lifers > 1 ? "s" : ""}
                    </div>
                  )}
                </div>
                <div className={s.tripMain}>
                  {diff && <DifficultyMarker diff={diff} size={10} />}
                  <div className={s.tripTrail}>{tr.trailName}</div>
                  <div className={common.monoMeta}>
                    {[tr.miles != null ? `${tr.miles} mi` : null, diff].filter(Boolean).join(" · ")}
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
              </div>
            );
          })}
        </div>
      )}

      <BottomNav active="trips" />
    </div>
  );
}
