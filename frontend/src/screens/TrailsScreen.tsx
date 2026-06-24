import { useNavigate } from "react-router-dom";
import { BottomNav } from "../components/BottomNav";
import { CenterMessage } from "../components/CenterMessage";
import { DifficultyMarker } from "../components/DifficultyMarker";
import { BirdGlyph } from "../components/icons";
import { useTrails } from "../data/TrailsProvider";
import { useSpeciesTrails } from "../data/useSpeciesTrails";
import {
  TRAIL_SORT_CHIPS,
  TRAIL_SORT_LABELS,
  compareTrails,
  fmtTime,
  normalizeDifficulty,
  scoreChipBg,
  scoreColor,
} from "../data/trails";
import { useAppState } from "../state/AppState";
import common from "../styles/common.module.css";
import s from "./TrailsScreen.module.css";

export function TrailsScreen() {
  const navigate = useNavigate();
  const { trails, location, loading, error, reload } = useTrails();
  const { trailSort, trailDir, pickTrailSort, speciesFilter, setSpeciesFilter, setDetailTrailId } =
    useAppState();
  const speciesView = useSpeciesTrails(speciesFilter?.code ?? null, location.lat, location.lon);

  const open = (id: string) => {
    setDetailTrailId(id);
    navigate("/trail");
  };

  if (loading || error) {
    return (
      <div className={common.screen}>
        {loading ? (
          <CenterMessage title="Loading trails…" />
        ) : (
          <CenterMessage title="Couldn't load trails" detail={error ?? undefined} onRetry={reload} />
        )}
        <BottomNav active="trails" />
      </div>
    );
  }

  // --- Targeted view: trails ranked by one species' live odds ---
  if (speciesFilter) {
    const ranked = speciesView.trails;
    return (
      <div className={common.screen}>
        <div className={s.header}>
          <div className={common.eyebrow}>
            {location.label} · best trails for this species
          </div>
          <div className={s.titleRow}>
            <div className={common.title}>{speciesFilter.name}</div>
          </div>
          <div className={s.filterBanner}>
            <BirdGlyph fill="var(--terracotta)" eyeFill="var(--forest)" size={16} />
            <div className={s.filterText}>
              <span style={{ color: "var(--sage-on-dark)" }}>Ranked by</span>{" "}
              <span style={{ fontWeight: 700 }}>recent reports + season</span>
            </div>
            <button className={s.clearBtn} onClick={() => setSpeciesFilter(null)}>
              Clear ✕
            </button>
          </div>
        </div>

        <div className={s.list}>
          {speciesView.loading ? (
            <CenterMessage title="Ranking trails…" />
          ) : ranked.length === 0 ? (
            <CenterMessage title="No nearby reports" detail="No recent reports of this species near you." />
          ) : (
            ranked.map((t) => {
              const diff = normalizeDifficulty(t.difficulty);
              const miles = t.metricLengthMi ?? t.lengthMi;
              const odds = t.speciesLikelihood ?? 0;
              return (
                <button key={t.id} className={s.trailCard} onClick={() => open(t.id)}>
                  <div className={s.cardTop}>
                    {diff && <DifficultyMarker diff={diff} size={11} />}
                    <div className={s.trailName}>{t.name}</div>
                    <div
                      className={odds >= 60 ? common.scoreChipHi : common.scoreChipMed}
                      style={{ background: scoreChipBg(odds), color: scoreColor(odds) }}
                    >
                      {odds}%
                    </div>
                  </div>
                  <div className={s.cardMeta}>
                    {[miles != null ? `${miles} mi` : null, diff, `${odds}% odds nearby`]
                      .filter(Boolean)
                      .join(" · ")}
                  </div>
                  <div className={s.birdRow}>
                    <BirdGlyph fill="var(--terracotta)" eyeFill="#fff" size={16} />
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {t.likelyBirds.slice(0, 4).map((b) => (
                        <span key={b} className={s.birdChip}>
                          {b}
                        </span>
                      ))}
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </div>

        <BottomNav active="trails" />
      </div>
    );
  }

  // --- Default view: all trails, sortable ---
  const sorted = [...trails].sort((a, b) => {
    const c = compareTrails(a, b, trailSort);
    return trailDir === "asc" ? c : -c;
  });
  const arrow = trailDir === "asc" ? "↑" : "↓";

  return (
    <div className={common.screen}>
      <div className={s.header}>
        <div className={common.eyebrow}>
          {location.label} · {sorted.length} trail{sorted.length === 1 ? "" : "s"}
        </div>
        <div className={s.titleRow}>
          <div className={common.title}>All trails</div>
        </div>

        <div className={s.sortedBy}>
          Sorted by{" "}
          <span style={{ fontWeight: 700, color: "var(--terracotta)" }}>
            {TRAIL_SORT_LABELS[trailSort]} {arrow}
          </span>
        </div>

        <div className={s.chipRow}>
          {TRAIL_SORT_CHIPS.map(({ key, label }) => {
            const isActive = trailSort === key;
            return (
              <button
                key={key}
                className={`${s.chip} ${isActive ? s.chipActive : s.chipIdle}`}
                onClick={() => pickTrailSort(key)}
              >
                {isActive ? `${label}  ${arrow}` : label}
              </button>
            );
          })}
        </div>
      </div>

      <div className={s.list}>
        {sorted.map((t) => (
          <button key={t.id} className={s.trailCard} onClick={() => open(t.id)}>
            <div className={s.cardTop}>
              {t.diff && <DifficultyMarker diff={t.diff} size={11} />}
              <div className={s.trailName}>{t.name}</div>
              <div
                className={t.score >= 85 ? common.scoreChipHi : common.scoreChipMed}
                style={{ background: scoreChipBg(t.score), color: scoreColor(t.score) }}
              >
                {t.score}
              </div>
            </div>
            <div className={s.cardMeta}>
              {[
                t.miles != null ? `${t.miles} mi` : null,
                t.rideTime != null ? fmtTime(t.rideTime) : null,
                t.effort != null ? `E${t.effort}` : null,
                t.diff,
              ]
                .filter(Boolean)
                .join(" · ")}
            </div>
            <div className={s.birdRow}>
              <BirdGlyph fill="var(--terracotta)" eyeFill="#fff" size={16} />
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {t.likelyBirds.map((b) => (
                  <span key={b} className={s.birdChip}>
                    {b}
                  </span>
                ))}
              </div>
            </div>
          </button>
        ))}
      </div>

      <BottomNav active="trails" />
    </div>
  );
}
