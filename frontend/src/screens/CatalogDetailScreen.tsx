import { useParams } from "react-router-dom";
import { BackButton } from "../components/BackButton";
import { CenterMessage } from "../components/CenterMessage";
import { useCatalogDetail } from "../data/useCatalogDetail";
import { fmtTime } from "../data/trails";
import { shortSky } from "../data/useTrailWeather";
import common from "../styles/common.module.css";
import s from "./CatalogDetailScreen.module.css";

const W = 300;
const H = 130;
const PAD = 12;

/** Build the polyline + filled-area paths for a normalized 0..1 elevation profile. */
function elevationPaths(elev: number[]) {
  const step = 300 / Math.max(elev.length - 1, 1);
  const pts = elev.map((n, i) => `${(i * step).toFixed(1)},${(60 - n * 46).toFixed(1)}`);
  return { polyline: pts.join(" "), area: `M${pts.join(" L")} L300,70 L0,70 Z` };
}

const ELEV_SOURCE_LABEL: Record<string, string> = {
  usgs: "USGS 3DEP",
  "open-meteo": "Open-Meteo",
};

/** Project [lon, lat] points into an SVG polyline, uniform scale, lat pointing up. */
function linePolyline(points: [number, number][]): string {
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const rangeX = maxX - minX || 1e-6;
  const rangeY = maxY - minY || 1e-6;
  const scale = Math.min((W - 2 * PAD) / rangeX, (H - 2 * PAD) / rangeY);
  const offX = (W - rangeX * scale) / 2;
  const offY = (H - rangeY * scale) / 2;
  return points
    .map(([lon, lat]) => {
      const x = offX + (lon - minX) * scale;
      const y = H - (offY + (lat - minY) * scale);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function CatalogDetailScreen() {
  const { id = "" } = useParams();
  const { trail, linePoints, error, loading, species, areaRadiusKm, weather } =
    useCatalogDetail(id);

  if (loading || error || !trail) {
    return (
      <div className={common.screen}>
        <div className={s.backRow}>
          <BackButton bg="rgba(45,59,45,0.1)" stroke="var(--forest)" blur={false} />
        </div>
        {loading ? (
          <CenterMessage title="Loading trail…" />
        ) : (
          <CenterMessage title="Couldn't load trail" detail={error ?? undefined} />
        )}
      </div>
    );
  }

  const meta = [trail.difficulty, trail.lengthMi != null ? `${trail.lengthMi} mi` : null, trail.city]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className={common.screen}>
      <div className={common.scrollArea}>
        <div className={s.backRow}>
          <BackButton bg="rgba(45,59,45,0.1)" stroke="var(--forest)" blur={false} />
        </div>
        <div className={common.eyebrow}>
          {trail.region ?? "TrailAPI catalog"}
          {weather ? ` · ${weather.temperature}°${weather.temperatureUnit} · ${shortSky(weather.shortForecast)}` : ""}
        </div>
        <div className={common.title}>{trail.name}</div>
        {meta && <div className={s.meta}>{meta}</div>}

        {linePoints && linePoints.length > 1 ? (
          <div className={s.mapCard}>
            <div className={s.mapHead}>TRAIL LINE · OSM</div>
            <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="120" preserveAspectRatio="xMidYMid meet">
              <polyline
                points={linePolyline(linePoints)}
                style={{
                  fill: "none",
                  stroke: "var(--terracotta)",
                  strokeWidth: 3,
                  strokeLinejoin: "round",
                  strokeLinecap: "round",
                }}
              />
            </svg>
          </div>
        ) : (
          <div className={s.note}>No OSM line matched near this trailhead.</div>
        )}

        {trail.elevationProfile && trail.elevationProfile.length > 1 && (
          <>
            <div className={s.statGrid}>
              <div className={s.statTile}>
                <div className={s.statNum}>{trail.metricLengthMi ?? "–"}</div>
                <div className={s.statLabel}>MAPPED MI</div>
              </div>
              <div className={s.statTile}>
                <div className={s.statNum} style={{ color: "var(--terracotta)" }}>
                  {trail.effort ?? "–"}
                </div>
                <div className={s.statLabel}>EFFORT /10</div>
              </div>
              <div className={s.statTile}>
                <div className={s.statNum}>
                  {trail.rideTimeMin != null ? fmtTime(trail.rideTimeMin) : "–"}
                </div>
                <div className={s.statLabel}>EST TIME</div>
              </div>
            </div>

            <div className={s.elevCard}>
              <div className={s.elevHead}>
                <span className={s.elevTitle}>ELEVATION</span>
                <span className={s.elevMeta}>
                  {ELEV_SOURCE_LABEL[trail.elevSource ?? ""] ?? "DEM"}
                  {trail.metricLengthMi != null ? ` · ${trail.metricLengthMi} mi mapped` : ""}
                </span>
              </div>
              {(() => {
                const { polyline, area } = elevationPaths(trail.elevationProfile);
                return (
                  <svg viewBox="0 0 300 70" width="100%" height="58" preserveAspectRatio="none" style={{ display: "block" }}>
                    <path d={area} fill="rgba(138,154,91,0.16)" stroke="none" />
                    <polyline
                      points={polyline}
                      style={{ fill: "none", stroke: "var(--sage)", strokeWidth: 2.5, strokeLinejoin: "round", strokeLinecap: "round" }}
                    />
                  </svg>
                );
              })()}
              <div className={s.elevStats}>
                <div className={s.elevStatCell}>
                  <div className={s.elevStatNum} style={{ color: "var(--success)" }}>
                    ↑ {(trail.ascentFt ?? 0).toLocaleString()} ft
                  </div>
                  <div className={s.statLabel}>TOTAL CLIMB</div>
                </div>
                <div className={s.elevStatCell}>
                  <div className={s.elevStatNum} style={{ color: "var(--terracotta)" }}>
                    ↓ {(trail.descentFt ?? 0).toLocaleString()} ft
                  </div>
                  <div className={s.statLabel}>TOTAL DESCENT</div>
                </div>
                <div className={s.elevStatCell}>
                  <div className={s.elevStatNum} style={{ color: "var(--ink)" }}>
                    {trail.avgUpGrade ?? "–"}
                  </div>
                  <div className={s.statLabel}>AVG UP GRADE</div>
                </div>
                <div className={s.elevStatCell}>
                  <div className={s.elevStatNum} style={{ color: "var(--ink)" }}>
                    {trail.avgDownGrade ?? "–"}
                  </div>
                  <div className={s.statLabel}>AVG DOWN GRADE</div>
                </div>
              </div>
            </div>
          </>
        )}

        <div className={s.ebirdCard}>
          <div className={s.ebirdHead}>
            <span className={s.ebirdTitle}>RECENT IN THIS AREA</span>
            <span className={s.ebirdMeta}>eBird · 14d{areaRadiusKm ? ` · ${areaRadiusKm}km` : ""}</span>
          </div>
          {species === null ? (
            <div className={s.note}>Loading recent reports…</div>
          ) : species.length === 0 ? (
            <div className={s.note}>No recent eBird reports in this area.</div>
          ) : (
            <div className={s.chips}>
              {species.map((sp) => (
                <span key={sp.species_code} className={s.chip}>
                  {sp.common_name}
                  <span className={s.count}>{sp.observations}</span>
                </span>
              ))}
            </div>
          )}
        </div>

        {trail.url && (
          <a className={s.sourceLink} href={trail.url} target="_blank" rel="noreferrer">
            View on source →
          </a>
        )}
      </div>
    </div>
  );
}
