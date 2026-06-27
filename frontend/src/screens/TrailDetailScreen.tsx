import { useState, type CSSProperties } from "react";
import { useNavigate } from "react-router-dom";
import { BackButton } from "../components/BackButton";
import { BirdIdFab } from "../components/BirdIdFab";
import { ScoreRing } from "../components/ScoreRing";
import { Photo } from "../components/Photo";
import { CenterMessage } from "../components/CenterMessage";
import { LogRideSheet } from "../components/LogRideSheet";
import { TrailPhotoMap } from "../components/TrailPhotoMap";
import { useCatalogDetail } from "../data/useCatalogDetail";
import { useTrips } from "../data/useTrips";
import { shortSky } from "../data/useTrailWeather";
import { useOptimalTime } from "../data/useOptimalTime";
import { TRAIL_HERO_IMG, fmtTime, normalizeDifficulty } from "../data/trails";
import { HeartIcon } from "../components/icons";
import { useAppState } from "../state/AppState";
import { useProfile } from "../state/ProfileContext";
import s from "./TrailDetailScreen.module.css";

function elevationPaths(elev: number[]) {
  const W = 300;
  const step = W / Math.max(elev.length - 1, 1);
  const pts = elev.map((n, i) => `${(i * step).toFixed(1)},${(60 - n * 46).toFixed(1)}`);
  return { polyline: pts.join(" "), area: `M${pts.join(" L")} L${W},70 L0,70 Z` };
}

const ELEV_SOURCE_LABEL: Record<string, string> = { usgs: "USGS 3DEP", "open-meteo": "Open-Meteo" };

/** A plain-language read on a trail's sun exposure (0..1, 1 = fully equator-facing). */
function sunWord(exposure: number | null): string {
  if (exposure == null) return "varied sun";
  return exposure >= 0.66 ? "mostly sunny" : exposure <= 0.34 ? "mostly shaded" : "mixed sun";
}

const surfaceChip: CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  color: "var(--sage-text)",
  background: "var(--sage-tint)",
  border: "1px solid var(--sage-pale)",
  padding: "5px 10px",
  borderRadius: 8,
};

export function TrailDetailScreen() {
  const navigate = useNavigate();
  const { detailTrailId, setDetailTrailId } = useAppState();
  const { trail, linePoints, error, loading, species, areaRadiusKm, weather } =
    useCatalogDetail(detailTrailId);
  const { trips } = useTrips();
  const { data: optimal } = useOptimalTime(detailTrailId);
  const { isFavorite, toggleFavorite } = useProfile();
  const [showLog, setShowLog] = useState(false);

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

  // Your logged photos on this trail that carry GPS, for the map overlay.
  const myPhotos = trips
    .filter((t) => t.trailExternalId === trail.id)
    .flatMap((t) => t.photos)
    .filter((p): p is typeof p & { lat: number; lon: number } => p.lat != null && p.lon != null);

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

          {/* Live best-time-to-ride window (taps through to the full curve) */}
          {optimal?.available && optimal.bestWindow && (
            <button
              onClick={() => { setDetailTrailId(trail.id); navigate("/optimal-time"); }}
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
                <div style={{ fontWeight: 800, fontSize: 16, color: "var(--ink)" }}>
                  {optimal.bestWindow}
                </div>
                {optimal.bestWindowWhy && (
                  <div style={{ fontSize: 12, color: "var(--text-muted-2)" }}>{optimal.bestWindowWhy}</div>
                )}
              </div>
              <span style={{ color: "var(--sage)", fontSize: 18 }}>→</span>
            </button>
          )}

          <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
            <button
              onClick={() => toggleFavorite({ id: trail.id, name: trail.name, difficulty: trail.difficulty, miles })}
              aria-label={isFavorite(trail.id) ? "Remove from favorites" : "Save to favorites"}
              style={{
                flex: "none",
                width: 52,
                borderRadius: 12,
                border: "1.5px solid var(--terracotta)",
                background: isFavorite(trail.id) ? "var(--terracotta)" : "var(--terracotta-tint)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
              }}
            >
              <HeartIcon color={isFavorite(trail.id) ? "#fff" : "var(--terracotta)"} filled={isFavorite(trail.id)} size={21} />
            </button>
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
                {trail.maxGrade && (
                  <div className={s.elevStatCell}>
                    <div className={s.elevStatNum} style={{ color: "var(--ink)" }}>{trail.maxGrade}</div>
                    <div className={s.statLabel}>MAX GRADE</div>
                  </div>
                )}
                {trail.longestClimbMi != null && (
                  <div className={s.elevStatCell}>
                    <div className={s.elevStatNum} style={{ color: "var(--ink)" }}>{trail.longestClimbMi} mi</div>
                    <div className={s.statLabel}>LONGEST CLIMB</div>
                  </div>
                )}
                {trail.highPointFt != null && (
                  <div className={s.elevStatCell}>
                    <div className={s.elevStatNum} style={{ color: "var(--ink)" }}>{trail.highPointFt.toLocaleString()} ft</div>
                    <div className={s.statLabel}>HIGH POINT</div>
                  </div>
                )}
                {trail.lowPointFt != null && (
                  <div className={s.elevStatCell}>
                    <div className={s.elevStatNum} style={{ color: "var(--ink)" }}>{trail.lowPointFt.toLocaleString()} ft</div>
                    <div className={s.statLabel}>LOW POINT</div>
                  </div>
                )}
              </div>

              {/* Surface descriptor from OSM tags + computed slope aspect */}
              {(trail.surface || trail.mtbScale || trail.aspect) && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 7, marginTop: 12 }}>
                  {trail.surface && (
                    <span style={surfaceChip}>{trail.surface}</span>
                  )}
                  {trail.mtbScale && (
                    <span style={surfaceChip}>Tech S{trail.mtbScale}</span>
                  )}
                  {trail.aspect && (
                    <span style={surfaceChip}>{trail.aspect}-facing · {sunWord(trail.sunExposure)}</span>
                  )}
                </div>
              )}
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

          {myPhotos.length > 0 && linePoints && linePoints.length > 1 && (
            <div className={s.elevCard}>
              <div className={s.elevHead}>
                <span style={{ color: "var(--sage)" }}>YOUR PHOTOS ON THIS TRAIL</span>
                <span style={{ color: "var(--text-placeholder)" }}>
                  {myPhotos.length} mapped by GPS
                </span>
              </div>
              <TrailPhotoMap line={linePoints} photos={myPhotos} />
            </div>
          )}
        </div>
      </div>

      <BirdIdFab bottom={92} />

      {/* Action bar */}
      <div className={s.actionBar}>
        {linePoints && linePoints.length > 1 ? (
          <a
            className={s.garminBtn}
            href={`/api/catalog/trails/${trail.id}/export.gpx`}
            download
            aria-label="Export GPX course for Garmin"
          >
            <div style={{ width: 18, height: 13, border: "2px solid var(--forest)", borderRadius: 3 }} />
            <span className={s.garminLabel}>GARMIN</span>
          </a>
        ) : (
          <button className={s.garminBtn} disabled aria-label="No route to export" style={{ opacity: 0.4 }}>
            <div style={{ width: 18, height: 13, border: "2px solid var(--forest)", borderRadius: 3 }} />
            <span className={s.garminLabel}>GARMIN</span>
          </button>
        )}
        <button className={s.navBtn} onClick={() => navigate("/navigate")}>
          Navigate to trailhead →
        </button>
      </div>

      {showLog && (
        <LogRideSheet
          trail={{ id: trail.id, name: trail.name, difficulty: trail.difficulty, miles }}
          options={[
            ...(species ?? []).map((sp) => ({ speciesCode: sp.species_code, commonName: sp.common_name })),
            ...trail.notableBirds.map((n) => ({ speciesCode: null, commonName: n })),
            ...trail.likelyBirds.map((n) => ({ speciesCode: null, commonName: n })),
          ]}
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
