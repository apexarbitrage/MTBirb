import { BackButton } from "../components/BackButton";
import { CenterMessage } from "../components/CenterMessage";
import { useTrails } from "../data/TrailsProvider";
import { useAppState } from "../state/AppState";
import common from "../styles/common.module.css";
import s from "./OptimalTimeScreen.module.css";

/*
 * Best time-of-day to ride a given trail. The recommended window/headline are
 * driven by the subject trail; the dual-curve and hourly strip are an
 * illustrative sample forecast (in production: hourly weather + activity model).
 */

// [wildlife %, conditions %] per 2-hour slot, 6a → 8p.
const BARS: [number, number][] = [
  [30, 42],
  [78, 62],
  [96, 80],
  [70, 88],
  [44, 92],
  [30, 74],
  [38, 58],
  [62, 48],
];

const HOURS = [
  { time: "6 AM", dot: "#c2703d", temp: "48°", wind: "5mph", active: true },
  { time: "8 AM", dot: "#e3b48f", temp: "54°", wind: "6mph", active: false },
  { time: "10 AM", dot: "#e8c98a", temp: "61°", wind: "9mph", active: false },
  { time: "12 PM", dot: "#e8c98a", temp: "66°", wind: "11mph", active: false },
  { time: "2 PM", dot: "#bcd0d8", temp: "68°", wind: "13mph", active: false },
];

const HOUR_LABELS = ["6a", "8a", "10a", "12p", "2p", "4p", "6p", "8p"];

function wildlifeColor(pct: number): string {
  return pct >= 50 ? "var(--terracotta)" : "var(--terracotta-pale)";
}
function conditionsColor(pct: number): string {
  return pct >= 70 ? "var(--sage)" : "var(--sage-pale)";
}

export function OptimalTimeScreen() {
  const { byId, loading, error, reload } = useTrails();
  const { detailTrailId } = useAppState();
  const t = byId(detailTrailId);

  if (loading || error || !t) {
    return (
      <div className={common.screen}>
        <div style={{ position: "absolute", top: 16, left: 16, zIndex: 2 }}>
          <BackButton bg="rgba(45,59,45,0.1)" stroke="var(--forest)" blur={false} />
        </div>
        {loading ? (
          <CenterMessage title="Loading…" />
        ) : error ? (
          <CenterMessage title="Couldn't load trail" detail={error} onRetry={reload} />
        ) : (
          <CenterMessage title="Trail not found" detail="This trail isn't available." />
        )}
      </div>
    );
  }

  return (
    <div className={common.screen}>
      <div className={s.scroll}>
        <div className={s.backRow}>
          <BackButton bg="rgba(45,59,45,0.1)" stroke="var(--forest)" blur={false} />
        </div>
        <div className={common.eyebrow}>{t.name} · today</div>
        <div className={common.title}>Best time to ride</div>

        <div className={s.recCard}>
          <div className={s.recLabel}>RECOMMENDED WINDOW</div>
          <div className={s.recWindow}>{t.bestWindow ?? "Dawn & dusk"}</div>
          <div className={s.recWhy}>
            {t.bestWindowWhy ??
              "A calibrated best-time model (hourly weather + activity) is on the way; the curve below is illustrative."}
          </div>
        </div>

        <div className={s.curveCard}>
          <div className={s.legend}>
            <div className={s.legendItem}>
              <div className={s.legendSwatch} style={{ background: "var(--terracotta)" }} />
              <span className={s.legendText}>Wildlife activity</span>
            </div>
            <div className={s.legendItem}>
              <div className={s.legendSwatch} style={{ background: "var(--sage)" }} />
              <span className={s.legendText}>Riding conditions</span>
            </div>
          </div>

          <div className={s.chart}>
            <div className={s.bestBand} />
            <div className={s.bestLabel}>BEST</div>
            <div className={s.bars}>
              {BARS.map(([w, c], i) => (
                <div key={i} className={s.barGroup}>
                  <div className={s.bar} style={{ height: `${w}%`, background: wildlifeColor(w) }} />
                  <div className={s.bar} style={{ height: `${c}%`, background: conditionsColor(c) }} />
                </div>
              ))}
            </div>
            <div className={s.hourLabels}>
              {HOUR_LABELS.map((h) => (
                <span key={h}>{h}</span>
              ))}
            </div>
          </div>
        </div>

        <div className={s.hourStrip}>
          {HOURS.map((h) => (
            <div key={h.time} className={`${s.hourTile} ${h.active ? s.hourTileActive : s.hourTileIdle}`}>
              <div
                className={s.hourTime}
                style={{ color: h.active ? "var(--sage-on-dark)" : "var(--text-placeholder)" }}
              >
                {h.time}
              </div>
              <div className={s.hourDot} style={{ background: h.dot }} />
              <div className={s.hourTemp}>{h.temp}</div>
              <div className={s.hourWind} style={{ color: h.active ? "var(--sage-on-dark)" : "var(--text-placeholder)" }}>
                {h.wind}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
