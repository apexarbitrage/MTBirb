import { BottomNav } from "../components/BottomNav";
import { DifficultyMarker } from "../components/DifficultyMarker";
import { TRIPS } from "../data/trails";
import common from "../styles/common.module.css";
import s from "./TripsScreen.module.css";

export function TripsScreen() {
  const totalBirds = TRIPS.reduce((n, t) => n + t.birds.length, 0);

  return (
    <div className={common.screen}>
      <div className={s.header}>
        <div className={common.eyebrow}>Your history</div>
        <div className={common.title}>Trips</div>
        <div className={s.statRow}>
          <div className={s.statTile}>
            <div className={s.statNum}>{TRIPS.length}</div>
            <div className={s.statLabel}>RIDES LOGGED</div>
          </div>
          <div className={s.statTile}>
            <div className={s.statNum} style={{ color: "var(--terracotta)" }}>
              {totalBirds}
            </div>
            <div className={s.statLabel}>BIRDS SEEN</div>
          </div>
        </div>
      </div>

      <div className={s.list}>
        {TRIPS.map((tr) => (
          <div key={`${tr.date}-${tr.trail}`} className={s.tripCard}>
            <div className={s.tripTop}>
              <div className={common.monoMeta}>{tr.date}</div>
              {tr.lifers > 0 && (
                <div className={s.liferBadge}>
                  +{tr.lifers} lifer{tr.lifers > 1 ? "s" : ""}
                </div>
              )}
            </div>
            <div className={s.tripMain}>
              <DifficultyMarker diff={tr.diff} size={10} />
              <div className={s.tripTrail}>{tr.trail}</div>
              <div className={common.monoMeta}>
                {tr.miles} mi · {tr.diff}
              </div>
            </div>
            <div className={s.birdChips}>
              {tr.birds.map((b) => (
                <span key={b} className={s.birdChip}>
                  {b}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      <BottomNav active="trips" />
    </div>
  );
}
