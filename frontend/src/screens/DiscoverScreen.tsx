import { useNavigate } from "react-router-dom";
import { BottomNav } from "../components/BottomNav";
import { BirdIdFab } from "../components/BirdIdFab";
import { DifficultyMarker } from "../components/DifficultyMarker";
import { ScoreRing } from "../components/ScoreRing";
import { Photo } from "../components/Photo";
import { BirdGlyph } from "../components/icons";
import {
  TRAILS,
  TRAIL_HERO_IMG,
  scoreColor,
  scoreChipBg,
  trailById,
} from "../data/trails";
import { useAppState } from "../state/AppState";
import common from "../styles/common.module.css";
import s from "./DiscoverScreen.module.css";

const SORT_LABELS: Record<string, string> = {
  wildlife: "WILDLIFE",
  distance: "DISTANCE",
  effort: "EFFORT",
};

export function DiscoverScreen() {
  const navigate = useNavigate();
  const {
    discoverSelectedId,
    setDiscoverSelectedId,
    discoverSort,
    cycleDiscoverSort,
    setDetailTrailId,
  } = useAppState();

  const sel = trailById(discoverSelectedId);

  const rest = TRAILS.filter((t) => t.id !== sel.id).sort((a, b) =>
    discoverSort === "distance"
      ? a.miles - b.miles
      : discoverSort === "effort"
        ? a.effort - b.effort
        : b.score - a.score,
  );

  const openDetail = (id: string) => {
    setDetailTrailId(id);
    navigate("/trail");
  };

  return (
    <div className={common.screen}>
      <div className={common.scrollArea}>
        <div className={common.eyebrow} style={{ letterSpacing: 1.5 }}>
          Sat · Jun 20 · 5:42 AM
        </div>
        <div className={common.title}>Good morning, Max</div>

        {/* Hero optimal card */}
        <div className={s.heroCard}>
          <div className={s.heroTop}>
            <Photo
              src={TRAIL_HERO_IMG}
              alt={sel.name}
              fit="cover"
              style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
              label="Trail photo"
            />
            <div className={s.heroOverlay} />
            <div style={{ position: "relative" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    letterSpacing: 1,
                    color: "var(--terracotta-light)",
                  }}
                >
                  OPTIMAL WINDOW TODAY
                </div>
                <ScoreRing
                  score={sel.score}
                  size={34}
                  centerSize={25}
                  centerBg="var(--forest)"
                  numberStyle={{ fontSize: 12, color: "#fff" }}
                />
              </div>
              <div className={s.heroName}>{sel.name}</div>
              <button
                className={s.heroWindow}
                onClick={() => {
                  setDetailTrailId(sel.id);
                  navigate("/optimal-time");
                }}
              >
                {sel.window}
              </button>
            </div>
          </div>

          {/* Weather strip */}
          <div className={s.weatherStrip}>
            <div className={s.weatherCell}>
              <div style={{ height: 19, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <DifficultyMarker diff={sel.diff} size={13} onDark />
              </div>
              <div className={s.weatherLabel} style={{ marginTop: 2 }}>
                {sel.diff.toUpperCase()}
              </div>
            </div>
            <div className={s.weatherCell}>
              <div className={s.weatherValue}>{sel.realfeel}</div>
              <div className={s.weatherLabel}>REALFEEL</div>
            </div>
            <div className={s.weatherCell}>
              <div className={s.weatherValue}>{sel.sky}</div>
              <div className={s.weatherLabel}>SKY</div>
            </div>
            <div className={s.weatherCell}>
              <div className={s.weatherValue} style={{ color: "var(--terracotta)" }}>
                {sel.condition}
              </div>
              <div className={s.weatherLabel}>CONDITION</div>
            </div>
          </div>

          {/* Peak odds */}
          <div className={s.peakRow}>
            <BirdGlyph fill="var(--terracotta)" eyeFill="var(--forest)" size={24} />
            <div className={s.peakText}>
              <span style={{ fontWeight: 700 }}>Peak odds:</span> {sel.peak}
            </div>
          </div>

          {/* Actions */}
          <div className={s.actionRow}>
            <button className={`${s.actionBtn} ${s.actionPrimary}`} onClick={() => openDetail(sel.id)}>
              View trail
            </button>
            <button className={`${s.actionBtn} ${s.actionSecondary}`} onClick={() => navigate("/navigate")}>
              Navigate →
            </button>
          </div>
        </div>

        {/* Ranked list */}
        <div className={s.rankedHeader}>
          <div className={s.rankedTitle}>Ranked for you</div>
          <button className={s.sortToggle} onClick={cycleDiscoverSort}>
            SORT: {SORT_LABELS[discoverSort]} ↕
          </button>
        </div>

        <div className={s.rankedList}>
          {rest.map((t, i) => (
            <button key={t.id} className={s.rankedRow} onClick={() => setDiscoverSelectedId(t.id)}>
              <div className={s.rankBox} style={{ color: scoreColor(t.score) }}>
                {i + 2}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                  <DifficultyMarker diff={t.diff} size={10} />
                  <div className={s.rowName}>{t.name}</div>
                </div>
                <div className={common.monoMeta}>
                  {t.miles} mi · {t.metaTime} · {t.metaBird}
                </div>
              </div>
              <div
                className={t.score >= 85 ? common.scoreChipHi : common.scoreChipMed}
                style={{ background: scoreChipBg(t.score), color: scoreColor(t.score) }}
              >
                {t.score}
              </div>
            </button>
          ))}
        </div>
      </div>

      <BirdIdFab />
      <BottomNav active="discover" />
    </div>
  );
}
