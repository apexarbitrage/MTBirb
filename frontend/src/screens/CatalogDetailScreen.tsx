import { useParams } from "react-router-dom";
import { BackButton } from "../components/BackButton";
import { CenterMessage } from "../components/CenterMessage";
import { useCatalogDetail } from "../data/useCatalogDetail";
import { shortSky } from "../data/useTrailWeather";
import common from "../styles/common.module.css";
import s from "./CatalogDetailScreen.module.css";

const W = 300;
const H = 130;
const PAD = 12;

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
