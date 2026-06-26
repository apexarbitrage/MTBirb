import { BackButton } from "../components/BackButton";
import { CenterMessage } from "../components/CenterMessage";
import { useTrails } from "../data/TrailsProvider";
import { useOptimalTime, type OptimalTime } from "../data/useOptimalTime";
import { scoreColor } from "../data/trails";
import { useAppState } from "../state/AppState";
import common from "../styles/common.module.css";
import s from "./OptimalTimeScreen.module.css";

/*
 * Best time-of-day to ride a given trail. When the live model is available (US trails with an NWS
 * forecast), the dual curve, best window, and hourly strip are all real - the riding-conditions
 * axis from the hourly forecast and the wildlife axis from a dawn/dusk prior scaled by the trail's
 * eBird score. Outside the US (or on a forecast hiccup) it falls back to the illustrative sample
 * below so the screen still reads.
 */

// Illustrative fallback when no live forecast is available: [wildlife %, conditions %] per slot.
const SAMPLE_BARS: [number, number][] = [
  [30, 42], [78, 62], [96, 80], [70, 88], [44, 92], [30, 74], [38, 58], [62, 48],
];
const SAMPLE_LABELS = ["6a", "8a", "10a", "12p", "2p", "4p", "6p", "8p"];
const SAMPLE_TILES = [
  { time: "6 AM", dot: "#c2703d", temp: "48°", wind: "5mph", active: true },
  { time: "8 AM", dot: "#e3b48f", temp: "54°", wind: "6mph", active: false },
  { time: "10 AM", dot: "#e8c98a", temp: "61°", wind: "9mph", active: false },
  { time: "12 PM", dot: "#e8c98a", temp: "66°", wind: "11mph", active: false },
  { time: "2 PM", dot: "#bcd0d8", temp: "68°", wind: "13mph", active: false },
];

function wildlifeColor(pct: number): string {
  return pct >= 50 ? "var(--terracotta)" : "var(--terracotta-pale)";
}
function conditionsColor(pct: number): string {
  return pct >= 70 ? "var(--sage)" : "var(--sage-pale)";
}

interface CurveBar {
  wildlife: number;
  conditions: number;
}
interface HourTile {
  time: string;
  dot: string;
  temp: string;
  wind: string;
  active: boolean;
}
interface Curve {
  bars: CurveBar[];
  labels: string[];
  tiles: HourTile[];
  bestStart: number; // bar index where the BEST band starts
  bestCount: number; // number of bars the band spans (0 = no band)
}

/** "7 AM" -> "7a", "12 PM" -> "12p". */
function shortHour(time: string): string {
  const [h, ap] = time.split(" ");
  return `${h}${ap === "AM" ? "a" : "p"}`;
}

/** Build the unified curve from the live model, or the illustrative sample when it's absent. */
function buildCurve(live: OptimalTime | null): Curve {
  if (live && live.hours.length > 0) {
    const bestIdx = live.hours.map((h, i) => (h.isBest ? i : -1)).filter((i) => i >= 0);
    // Thin axis labels to ~6 so a full day's worth of hours doesn't crowd.
    const step = Math.max(1, Math.ceil(live.hours.length / 6));
    return {
      bars: live.hours.map((h) => ({ wildlife: h.wildlife, conditions: h.conditions })),
      labels: live.hours.filter((_, i) => i % step === 0).map((h) => shortHour(h.time)),
      tiles: live.hours.map((h) => ({
        time: h.time,
        dot: scoreColor(h.combined),
        temp: h.tempF != null ? `${h.tempF}°` : "—",
        wind: h.windMph != null ? `${h.windMph}mph` : "—",
        active: h.isBest,
      })),
      bestStart: bestIdx.length ? bestIdx[0] : 0,
      bestCount: bestIdx.length,
    };
  }
  return {
    bars: SAMPLE_BARS.map(([wildlife, conditions]) => ({ wildlife, conditions })),
    labels: SAMPLE_LABELS,
    tiles: SAMPLE_TILES.map((t) => ({ ...t })),
    bestStart: 1,
    bestCount: 2,
  };
}

function dayLabel(isoDate: string | null): string {
  if (!isoDate) return "today";
  const today = new Date();
  const d = new Date(`${isoDate}T00:00:00`);
  const diffDays = Math.round(
    (d.setHours(0, 0, 0, 0) - today.setHours(0, 0, 0, 0)) / 86_400_000,
  );
  if (diffDays <= 0) return "today";
  if (diffDays === 1) return "tomorrow";
  return d.toLocaleDateString(undefined, { weekday: "long" });
}

export function OptimalTimeScreen() {
  const { byId, loading, error, reload } = useTrails();
  const { detailTrailId } = useAppState();
  const t = byId(detailTrailId);
  const { data: opt, loading: optLoading } = useOptimalTime(t ? detailTrailId : undefined);

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

  const live = opt && opt.available && opt.hours.length > 0 ? opt : null;
  const curve = buildCurve(live);
  const total = curve.bars.length;
  const bandLeft = (curve.bestStart / total) * 100;
  const bandWidth = (curve.bestCount / total) * 100;

  const recWindow = live?.bestWindow ?? t.bestWindow ?? "Dawn & dusk";
  const recWhy =
    live?.bestWindowWhy ??
    (optLoading
      ? "Reading the hourly forecast…"
      : (t.bestWindowWhy ??
        "A live hourly-weather forecast isn't available here, so the curve below is illustrative."));

  return (
    <div className={common.screen}>
      <div className={s.scroll}>
        <div className={s.backRow}>
          <BackButton bg="rgba(45,59,45,0.1)" stroke="var(--forest)" blur={false} />
        </div>
        <div className={common.eyebrow}>
          {t.name} · {dayLabel(live?.date ?? null)}
        </div>
        <div className={common.title}>Best time to ride</div>

        <div className={s.recCard}>
          <div className={s.recLabel}>RECOMMENDED WINDOW</div>
          <div className={s.recWindow}>{recWindow}</div>
          <div className={s.recWhy}>{recWhy}</div>
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
            {curve.bestCount > 0 && (
              <>
                <div className={s.bestBand} style={{ left: `${bandLeft}%`, width: `${bandWidth}%` }} />
                <div className={s.bestLabel} style={{ left: `${bandLeft}%` }}>
                  BEST
                </div>
              </>
            )}
            <div className={s.bars}>
              {curve.bars.map((b, i) => (
                <div key={i} className={s.barGroup}>
                  <div className={s.bar} style={{ height: `${b.wildlife}%`, background: wildlifeColor(b.wildlife) }} />
                  <div className={s.bar} style={{ height: `${b.conditions}%`, background: conditionsColor(b.conditions) }} />
                </div>
              ))}
            </div>
            <div className={s.hourLabels}>
              {curve.labels.map((h, i) => (
                <span key={`${h}-${i}`}>{h}</span>
              ))}
            </div>
          </div>
        </div>

        <div className={s.hourStrip}>
          {curve.tiles.map((h, i) => (
            <div key={`${h.time}-${i}`} className={`${s.hourTile} ${h.active ? s.hourTileActive : s.hourTileIdle}`}>
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
