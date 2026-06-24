import { useNavigate } from "react-router-dom";
import { BottomNav } from "../components/BottomNav";
import { CenterMessage } from "../components/CenterMessage";
import { DifficultyMarker } from "../components/DifficultyMarker";
import { BirdGlyph } from "../components/icons";
import { useTrails } from "../data/TrailsProvider";
import {
  TRAIL_SORT_CHIPS,
  TRAIL_SORT_LABELS,
  TOTAL_TRAILS_NEARBY,
  compareTrails,
  fmtTime,
  scoreChipBg,
  scoreColor,
  speciesByName,
} from "../data/trails";
import { useAppState } from "../state/AppState";
import common from "../styles/common.module.css";
import s from "./TrailsScreen.module.css";

export function TrailsScreen() {
  const navigate = useNavigate();
  const { trails, loading, error, reload } = useTrails();
  const { trailSort, trailDir, pickTrailSort, trailFilter, setTrailFilter, setDetailTrailId } =
    useAppState();

  const filterEntry = speciesByName(trailFilter);

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

  const sorted = [...trails].sort((a, b) => {
    const c = compareTrails(a, b, trailSort);
    return trailDir === "asc" ? c : -c;
  });
  const display = filterEntry ? sorted.filter((t) => filterEntry.trails.includes(t.id)) : sorted;

  const arrow = trailDir === "asc" ? "↑" : "↓";
  const countLabel = filterEntry
    ? `${display.length} trail${display.length === 1 ? "" : "s"}`
    : `${TOTAL_TRAILS_NEARBY} trails`;

  const open = (id: string) => {
    setDetailTrailId(id);
    navigate("/trail");
  };

  return (
    <div className={common.screen}>
      <div className={s.header}>
        <div className={common.eyebrow}>Bellingham, WA · {countLabel}</div>
        <div className={s.titleRow}>
          <div className={common.title}>All trails</div>
          <button className={s.browseLink} onClick={() => navigate("/catalog")}>
            Browse catalog →
          </button>
        </div>

        {filterEntry && (
          <div className={s.filterBanner}>
            <BirdGlyph fill="var(--terracotta)" eyeFill="var(--forest)" size={16} />
            <div className={s.filterText}>
              <span style={{ color: "var(--sage-on-dark)" }}>Filtered for</span>{" "}
              <span style={{ fontWeight: 700 }}>{filterEntry.name}</span>
            </div>
            <button className={s.clearBtn} onClick={() => setTrailFilter(null)}>
              Clear ✕
            </button>
          </div>
        )}

        <div className={s.sortedBy}>
          Sorted by{" "}
          <span style={{ fontWeight: 700, color: "var(--terracotta)" }}>
            {TRAIL_SORT_LABELS[trailSort]} {arrow}
          </span>
        </div>

        <div className={s.chipRow}>
          {TRAIL_SORT_CHIPS.map(({ key, label }) => {
            const active = trailSort === key;
            return (
              <button
                key={key}
                className={`${s.chip} ${active ? s.chipActive : s.chipIdle}`}
                onClick={() => pickTrailSort(key)}
              >
                {active ? `${label}  ${arrow}` : label}
              </button>
            );
          })}
        </div>
      </div>

      <div className={s.list}>
        {display.map((t) => (
          <button key={t.id} className={s.trailCard} onClick={() => open(t.id)}>
            <div className={s.cardTop}>
              <DifficultyMarker diff={t.diff} size={11} />
              <div className={s.trailName}>{t.name}</div>
              <div
                className={t.score >= 85 ? common.scoreChipHi : common.scoreChipMed}
                style={{ background: scoreChipBg(t.score), color: scoreColor(t.score) }}
              >
                {t.score}
              </div>
            </div>
            <div className={s.cardMeta}>
              {t.miles} mi · {fmtTime(t.rideTime)} · E{t.effort} · {t.diff}
            </div>
            <div className={s.cardFeatures}>{t.features.join("  ·  ")}</div>
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
