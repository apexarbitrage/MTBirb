import { useNavigate } from "react-router-dom";
import { BackButton } from "../components/BackButton";
import { BirdIdFab } from "../components/BirdIdFab";
import { ScoreRing } from "../components/ScoreRing";
import { Photo } from "../components/Photo";
import { CenterMessage } from "../components/CenterMessage";
import { useCatalogDetail } from "../data/useCatalogDetail";
import { shortSky } from "../data/useTrailWeather";
import { TRAIL_HERO_IMG, fmtTime, normalizeDifficulty } from "../data/trails";
import { useAppState } from "../state/AppState";
import s from "./TrailDetailScreen.module.css";

function elevationPaths(elev: number[]) {
  const W = 300;
  const step = W / Math.max(elev.length - 1, 1);
  const pts = elev.map((n, i) => `${(i * step).toFixed(1)},${(60 - n * 46).toFixed(1)}`);
  return { polyline: pts.join(" "), area: `M${pts.join(" L")} L${W},70 L0,70 Z` };
}

const ELEV_SOURCE_LABEL: Record<string, string> = { usgs: "USGS 3DEP", "open-meteo": "Open-Meteo" };

export function TrailDetailScreen() {
  const navigate = useNavigate();
  const { detailTrailId, setDetailTrailId } = useAppState();
  const { trail, error, loading, species, areaRadiusKm, weather } = useCatalogDetail(detailTrailId);

  if (loading || error || !trail) {
    return (
      <div className={s.screen}>
        <div style={{ position: "absolute", top: 16, left: 16, zIndex: 2 }}>
          <BackButton bg="rgba(45,59,45,0.1)" stroke="var(--forest)" blur={false} />
        </div>
        {loading ? (
          <CenterMessage title="Loading trail…" />
        ) : error ? (
          <CenterMessage title="Couldn't load trail" detail={error} />
        ) : (
          <CenterMessage title="Trail not found" detail="This trail isn't available." />
        )}
      </div>
    );
  }

  const diff = normalizeDifficulty(trail.difficulty);
  const miles = trail.metricLengthMi ?? trail.lengthMi;
  const profile = trail.elevationProfile ?? [];
  const hasElevation = profile.length > 1;
  const { polyline, area } = elevationPaths(profile);

  return (
    <div className={s.screen}>
      <div className={s.scroll}>
        {/* Hero */}
        <div className={s.hero}>
          <Photo
            src={TRAIL_HERO_IMG}
            alt={trail.name}
            fit="cover"
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
            label="Trail hero photo"
          />
          <div className={s.heroBtnTop} style={{ left: 16 }}>
            <BackButton />
          </div>
          {diff && (
            <div className={s.diffPill}>
              <div style={{ width: 10, height: 10, background: "var(--forest-1a)", transform: "rotate(45deg)", border: "1px solid #fff" }} />
              <span className={s.diffPillText}>{diff}</span>
            </div>
          )}
        </div>

        <div className={s.body}>
          <div className={s.titleRow}>
            <div style={{ flex: 1 }}>
              <div className={s.trailTitle}>{trail.name}</div>
              <div className={s.location}>
                {[trail.city, trail.region].filter(Boolean).join(", ") || "TrailAPI catalog"}
                {weather ? ` · ${weather.temperature}°${weather.temperatureUnit} · ${shortSky(weather.shortForecast)}` : ""}
              </div>
            </div>
            <ScoreRing
              score={trail.score ?? 0}
              size={64}
              centerSize={51}
              centerBg="var(--sand)"
              track="rgba(194,112,61,0.16)"
              numberStyle={{ fontSize: 21 }}
              label="MATCH"
            />
          </div>

          {/* Stat grid */}
          <div className={s.statGrid}>
            <button className={s.statTile} onClick={() => { setDetailTrailId(trail.id); navigate("/optimal-time"); }}>
              <div className={s.statNum}>{miles ?? "–"}</div>
              <div className={s.statLabel}>MILES</div>
            </button>
            <div className={s.statTile}>
              <div className={s.statNum} style={{ color: "var(--terracotta)" }}>{trail.effort ?? "–"}</div>
              <div className={s.statLabel}>EFFORT /10</div>
            </div>
            <button className={s.statTile} onClick={() => { setDetailTrailId(trail.id); navigate("/optimal-time"); }}>
              <div className={s.statNum}>{trail.rideTimeMin != null ? fmtTime(trail.rideTimeMin) : "–"}</div>
              <div className={s.statLabel}>EST TIME</div>
            </button>
          </div>

          {/* Elevation (only when a mapped line produced a profile) */}
          {hasElevation && (
            <div className={s.elevCard}>
              <div className={s.elevHead}>
                <span style={{ color: "var(--sage)" }}>ELEVATION</span>
                <span style={{ color: "var(--text-placeholder)" }}>
                  {ELEV_SOURCE_LABEL[trail.elevSource ?? ""] ?? "DEM"}
                  {miles != null ? ` · ${miles} mi mapped` : ""}
                </span>
              </div>
              <svg viewBox="0 0 300 70" width="100%" height="58" preserveAspectRatio="none" style={{ display: "block" }}>
                <path d={area} fill="rgba(138,154,91,0.16)" stroke="none" />
                <polyline points={polyline} style={{ fill: "none", stroke: "var(--sage)", strokeWidth: 2.5, strokeLinejoin: "round", strokeLinecap: "round" }} />
              </svg>
              <div className={s.elevStats}>
                <div className={s.elevStatCell}>
                  <div className={s.elevStatNum} style={{ color: "var(--success)" }}>↑ {(trail.ascentFt ?? 0).toLocaleString()} ft</div>
                  <div className={s.statLabel}>TOTAL CLIMB</div>
                </div>
                <div className={s.elevStatCell}>
                  <div className={s.elevStatNum} style={{ color: "var(--terracotta)" }}>↓ {(trail.descentFt ?? 0).toLocaleString()} ft</div>
                  <div className={s.statLabel}>TOTAL DESCENT</div>
                </div>
                <div className={s.elevStatCell}>
                  <div className={s.elevStatNum} style={{ color: "var(--ink)" }}>{trail.avgUpGrade ?? "–"}</div>
                  <div className={s.statLabel}>AVG UP GRADE</div>
                </div>
                <div className={s.elevStatCell}>
                  <div className={s.elevStatNum} style={{ color: "var(--ink)" }}>{trail.avgDownGrade ?? "–"}</div>
                  <div className={s.statLabel}>AVG DOWN GRADE</div>
                </div>
              </div>
            </div>
          )}

          {/* Sighting probability (recency + seasonality + notable; first-pass preview) */}
          <div className={s.probCard}>
            <div className={s.probHead}>
              <div className={s.probTitle}>Sighting probability</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--terracotta)" }}>
                Preview · eBird
              </div>
            </div>
            {trail.sightingHeadline && <div className={s.probHeadline}>{trail.sightingHeadline}</div>}
            <div className={s.factors}>
              {trail.factors.map((f) => (
                <div key={f.label}>
                  <div className={s.factorTop}>
                    <span style={{ color: "var(--text-on-forest-soft)" }}>{f.label}</span>
                    <span style={{ fontWeight: 700 }}>{f.value}</span>
                  </div>
                  <div className={s.factorTrack}>
                    <div className={s.factorFill} style={{ width: `${f.pct}%`, background: f.tone === "terracotta" ? "var(--terracotta)" : "var(--sage)" }} />
                  </div>
                </div>
              ))}
            </div>
            {trail.notableBirds.length > 0 && (
              <div style={{ marginTop: 14 }}>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--sand)", opacity: 0.7, marginBottom: 8 }}>
                  NOTABLE NEARBY
                </div>
                <div className={s.ebirdChips}>
                  {trail.notableBirds.map((b) => (
                    <span key={b} className={s.ebirdChip}>{b}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Recent eBird species in the area (real cached observations) */}
          <div className={s.ebirdCard}>
            <div className={s.ebirdHead}>
              <span className={s.ebirdHeadTitle}>RECENT IN THIS AREA</span>
              <span className={s.ebirdHeadMeta}>eBird{areaRadiusKm ? ` · ${areaRadiusKm}km` : ""}</span>
            </div>
            {species === null ? (
              <div className={s.ebirdEmpty}>Loading recent reports…</div>
            ) : species.length === 0 ? (
              <div className={s.ebirdEmpty}>No recent eBird reports in this area.</div>
            ) : (
              <div className={s.ebirdChips}>
                {species.map((sp) => (
                  <span key={sp.species_code} className={s.ebirdChip}>
                    {sp.common_name}
                    <span className={s.ebirdCount}>{sp.observations}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <BirdIdFab bottom={92} />

      {/* Action bar */}
      <div className={s.actionBar}>
        <button className={s.garminBtn} aria-label="Export to Garmin">
          <div style={{ width: 18, height: 13, border: "2px solid var(--forest)", borderRadius: 3 }} />
          <span className={s.garminLabel}>GARMIN</span>
        </button>
        <button className={s.navBtn} onClick={() => navigate("/navigate")}>
          Navigate to trailhead →
        </button>
      </div>
    </div>
  );
}
