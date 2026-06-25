import { useNavigate } from "react-router-dom";
import { BottomNav } from "../components/BottomNav";
import { BirdIdFab } from "../components/BirdIdFab";
import { DifficultyMarker } from "../components/DifficultyMarker";
import { ScoreRing } from "../components/ScoreRing";
import { Photo } from "../components/Photo";
import { BirdGlyph } from "../components/icons";
import { CenterMessage } from "../components/CenterMessage";
import { useTrails } from "../data/TrailsProvider";
import { useTrailWeather, shortSky } from "../data/useTrailWeather";
import { TRAIL_HERO_IMG, scoreColor, scoreChipBg } from "../data/trails";
import { PROFILE } from "../data/profile";
import { buildGreeting, formatEyebrowDate } from "../data/greeting";
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
  const { trails, byId, loading, error, reload } = useTrails();
  const {
    discoverSelectedId,
    setDiscoverSelectedId,
    discoverSort,
    cycleDiscoverSort,
    setDetailTrailId,
  } = useAppState();

  // Live forecast for the currently-selected hero trail.
  const selSlug = byId(discoverSelectedId)?.id ?? trails[0]?.id;
  const { current: wx } = useTrailWeather(selSlug);
  const now = new Date();

  if (loading || error || trails.length === 0) {
    return (
      <div className={common.screen}>
        {loading ? (
          <CenterMessage title="Loading trails…" />
        ) : error ? (
          <CenterMessage title="Couldn't load trails" detail={error} onRetry={reload} />
        ) : (
          <CenterMessage title="No trails nearby yet" />
        )}
        <BottomNav active="discover" />
      </div>
    );
  }

  const sel = byId(discoverSelectedId) ?? trails[0];

  const rest = trails.filter((t) => t.id !== sel.id).sort((a, b) =>
    discoverSort === "distance"
      ? (a.miles ?? 0) - (b.miles ?? 0)
      : discoverSort === "effort"
        ? (a.effort ?? 0) - (b.effort ?? 0)
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
          {formatEyebrowDate(now)}
        </div>
        <div className={common.title}>
          {buildGreeting({
            firstName: PROFILE.firstName,
            date: now,
            sky: wx ? shortSky(wx.shortForecast) : null,
            condition: sel.condition,
            trailName: sel.name,
            rareSpecies: sel.notableBirds[0] ?? null,
          })}
        </div>

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
                {sel.window ?? sel.sightingHeadline ?? "Find the best time to ride →"}
              </button>
            </div>
          </div>

          {/* Weather strip */}
          <div className={s.weatherStrip}>
            <div className={s.weatherCell}>
              <div style={{ height: 19, display: "flex", alignItems: "center", justifyContent: "center" }}>
                {sel.diff && <DifficultyMarker diff={sel.diff} size={13} onDark />}
              </div>
              <div className={s.weatherLabel} style={{ marginTop: 2 }}>
                {(sel.diff ?? "Unrated").toUpperCase()}
              </div>
            </div>
            <div className={s.weatherCell}>
              <div className={s.weatherValue}>{wx ? `${wx.temperature}°` : sel.realfeel}</div>
              <div className={s.weatherLabel}>{wx ? "TEMP" : "REALFEEL"}</div>
            </div>
            <div className={s.weatherCell}>
              <div className={s.weatherValue}>{wx ? shortSky(wx.shortForecast) : sel.sky}</div>
              <div className={s.weatherLabel}>SKY</div>
            </div>
            <div className={s.weatherCell}>
              <div className={s.weatherValue} style={{ color: "var(--terracotta)" }}>
                {sel.condition ?? (wx ? wx.windSpeed : "—")}
              </div>
              <div className={s.weatherLabel}>{sel.condition ? "CONDITION" : "WIND"}</div>
            </div>
          </div>

          {/* Peak odds */}
          <div className={s.peakRow}>
            <BirdGlyph fill="var(--terracotta)" eyeFill="var(--forest)" size={24} />
            <div className={s.peakText}>
              <span style={{ fontWeight: 700 }}>Notable nearby:</span>{" "}
              {sel.peak ?? "No notable reports recently"}
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
                  {t.diff && <DifficultyMarker diff={t.diff} size={10} />}
                  <div className={s.rowName}>{t.name}</div>
                </div>
                <div className={common.monoMeta}>
                  {[t.miles != null ? `${t.miles} mi` : null, t.metaBird]
                    .filter(Boolean)
                    .join(" · ")}
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
