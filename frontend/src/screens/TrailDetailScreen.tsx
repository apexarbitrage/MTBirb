import { useNavigate } from "react-router-dom";
import { BackButton } from "../components/BackButton";
import { BirdIdFab } from "../components/BirdIdFab";
import { ScoreRing } from "../components/ScoreRing";
import { Photo } from "../components/Photo";
import { TRAIL_HERO_IMG, fmtTime, trailById } from "../data/trails";
import { useAppState } from "../state/AppState";
import s from "./TrailDetailScreen.module.css";

function elevationPaths(elev: number[]) {
  const W = 300;
  const step = W / (elev.length - 1);
  const pts = elev.map((n, i) => {
    const x = +(i * step).toFixed(1);
    const y = +(60 - n * 46).toFixed(1);
    return `${x},${y}`;
  });
  const polyline = pts.join(" ");
  const area = `M${pts.join(" L")} L${W},70 L0,70 Z`;
  return { polyline, area };
}

export function TrailDetailScreen() {
  const navigate = useNavigate();
  const { detailTrailId, setDetailTrailId } = useAppState();
  const t = trailById(detailTrailId);
  const { polyline, area } = elevationPaths(t.elevation);

  return (
    <div className={s.screen}>
      <div className={s.scroll}>
        {/* Hero */}
        <div className={s.hero}>
          <Photo
            src={TRAIL_HERO_IMG}
            alt={t.name}
            fit="cover"
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
            label="Trail hero photo"
          />
          <div className={s.heroBtnTop} style={{ left: 16 }}>
            <BackButton />
          </div>
          <button
            className={s.heroBtnTop}
            aria-label="Bookmark"
            style={{
              right: 16,
              width: 40,
              height: 40,
              borderRadius: "50%",
              background: "rgba(45,59,45,0.55)",
              backdropFilter: "blur(6px)",
              WebkitBackdropFilter: "blur(6px)",
            }}
          />
          <div className={s.diffPill}>
            <div
              style={{
                width: 10,
                height: 10,
                background: "var(--forest-1a)",
                transform: "rotate(45deg)",
                border: "1px solid #fff",
              }}
            />
            <span className={s.diffPillText}>{t.diff}</span>
          </div>
        </div>

        <div className={s.body}>
          <div className={s.titleRow}>
            <div style={{ flex: 1 }}>
              <div className={s.trailTitle}>{t.name}</div>
              <div className={s.location}>{t.location}</div>
            </div>
            <ScoreRing
              score={t.score}
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
            <button className={s.statTile} onClick={() => { setDetailTrailId(t.id); navigate("/optimal-time"); }}>
              <div className={s.statNum}>{t.miles}</div>
              <div className={s.statLabel}>MILES</div>
            </button>
            <div className={s.statTile}>
              <div className={s.statNum} style={{ color: "var(--terracotta)" }}>
                {t.effort}
              </div>
              <div className={s.statLabel}>EFFORT /10</div>
            </div>
            <button className={s.statTile} onClick={() => { setDetailTrailId(t.id); navigate("/optimal-time"); }}>
              <div className={s.statNum}>{fmtTime(t.rideTime)}</div>
              <div className={s.statLabel}>EST TIME</div>
            </button>
            <div className={s.statTile}>
              <div className={s.statNum} style={{ color: "var(--success)" }}>
                {t.dirt}
              </div>
              <div className={s.statLabel}>DIRT</div>
            </div>
          </div>

          {/* Elevation */}
          <div className={s.elevCard}>
            <div className={s.elevHead}>
              <span style={{ color: "var(--sage)" }}>ELEVATION</span>
              <span style={{ color: "var(--text-placeholder)" }}>{t.miles} mi</span>
            </div>
            <svg viewBox="0 0 300 70" width="100%" height="58" preserveAspectRatio="none" style={{ display: "block" }}>
              <path d={area} fill="rgba(138,154,91,0.16)" stroke="none" />
              <polyline
                points={polyline}
                style={{ fill: "none", stroke: "var(--sage)", strokeWidth: 2.5, strokeLinejoin: "round", strokeLinecap: "round" }}
              />
            </svg>
            <div className={s.elevStats}>
              <div className={s.elevStatCell}>
                <div className={s.elevStatNum} style={{ color: "var(--success)" }}>
                  ↑ {t.climbFt.toLocaleString()} ft
                </div>
                <div className={s.statLabel}>TOTAL CLIMB</div>
              </div>
              <div className={s.elevStatCell}>
                <div className={s.elevStatNum} style={{ color: "var(--terracotta)" }}>
                  ↓ {t.descentFt.toLocaleString()} ft
                </div>
                <div className={s.statLabel}>TOTAL DESCENT</div>
              </div>
              <div className={s.elevStatCell}>
                <div className={s.elevStatNum} style={{ color: "var(--ink)" }}>
                  {t.avgUpGrade}
                </div>
                <div className={s.statLabel}>AVG UP GRADE</div>
              </div>
              <div className={s.elevStatCell}>
                <div className={s.elevStatNum} style={{ color: "var(--ink)" }}>
                  {t.avgDownGrade}
                </div>
                <div className={s.statLabel}>AVG DOWN GRADE</div>
              </div>
            </div>
          </div>

          {/* Sighting probability */}
          <div className={s.probCard}>
            <div className={s.probHead}>
              <div className={s.probTitle}>Sighting probability</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--terracotta)" }}>
                eBird-calibrated
              </div>
            </div>
            <div className={s.probHeadline}>{t.sightingHeadline}</div>
            <div className={s.factors}>
              {t.factors.map((f) => (
                <div key={f.label}>
                  <div className={s.factorTop}>
                    <span style={{ color: "var(--text-on-forest-soft)" }}>{f.label}</span>
                    <span style={{ fontWeight: 700 }}>{f.value}</span>
                  </div>
                  <div className={s.factorTrack}>
                    <div
                      className={s.factorFill}
                      style={{
                        width: `${f.pct}%`,
                        background: f.tone === "terracotta" ? "var(--terracotta)" : "var(--sage)",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Features */}
          <div className={s.features}>
            {t.features.map((f) => (
              <span key={f} className={s.featureChip}>
                {f}
              </span>
            ))}
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
