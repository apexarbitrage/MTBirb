import { useState } from "react";
import { BackButton } from "../components/BackButton";
import s from "./FunDriveNavScreen.module.css";

const ROUTE = "M205,520 C258,496 250,452 193,439 C143,427 132,392 196,376 C252,361 257,325 197,310 C146,297 150,266 201,253 C247,241 236,220 191,213";

const OPTIONS = [
  { name: "Fun drive", sub: "MAX TWISTIES" },
  { name: "Fastest", sub: "52 MIN" },
  { name: "Quiet roads", sub: "LOW TRAFFIC" },
  { name: "Efficient", sub: "BEST MPG" },
];

export function FunDriveNavScreen() {
  const [active, setActive] = useState(0);

  return (
    <div className={s.screen}>
      <div className={s.map} />

      <svg viewBox="0 0 402 874" width="100%" height="100%" preserveAspectRatio="none" className={s.routeSvg}>
        {/* faint background road network */}
        <path d="M40,610 C120,580 150,540 250,548 C330,554 360,500 402,470" style={{ fill: "none", stroke: "rgba(255,255,255,0.07)", strokeWidth: 6, strokeLinecap: "round" }} />
        <path d="M0,300 C70,320 120,300 150,250 C175,210 250,205 300,170" style={{ fill: "none", stroke: "rgba(255,255,255,0.06)", strokeWidth: 5, strokeLinecap: "round" }} />
        {/* route casing → surface → centerline */}
        <path d={ROUTE} style={{ fill: "none", stroke: "rgba(8,12,7,0.5)", strokeWidth: 11, strokeLinecap: "round", strokeLinejoin: "round" }} />
        <path d={ROUTE} style={{ fill: "none", stroke: "var(--terracotta)", strokeWidth: 5, strokeLinecap: "round", strokeLinejoin: "round" }} />
        <path d={ROUTE} style={{ fill: "none", stroke: "rgba(255,255,255,0.7)", strokeWidth: 1.4, strokeLinecap: "round", strokeDasharray: "1 12" }} />
      </svg>

      {/* destination pin + current location */}
      <div className={s.pin} style={{ top: 190, left: 181 }}>
        <div className={s.pinDot} />
        <div className={s.pinTail} />
      </div>
      <div className={s.youDot} style={{ top: 511, left: 196 }} />

      {/* top: back + route prefs */}
      <div className={s.topRow}>
        <BackButton bg="rgba(45,59,45,0.92)" stroke="#fff" />
        <div className={s.routePanel}>
          <div className={s.routeLabel}>ROUTE STYLE</div>
          <div className={s.routeOptions}>
            {OPTIONS.map((o, i) => {
              const on = i === active;
              return (
                <button
                  key={o.name}
                  className={`${s.routeOpt} ${on ? s.routeOptActive : s.routeOptIdle}`}
                  onClick={() => setActive(i)}
                >
                  <div className={`${s.routeOptName} ${on ? s.routeOptNameActive : ""}`}>{o.name}</div>
                  <div className={s.routeOptSub}>{o.sub}</div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* bottom card */}
      <div className={s.bottomCard}>
        <div className={s.etaRow}>
          <div>
            <div className={s.eta}>1 hr 08 min</div>
            <div className={s.etaSub}>47 mi · arrive 6:02 AM</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div className={s.extraNum}>+16</div>
            <div className={s.extraLabel}>MORE MIN, WORTH IT</div>
          </div>
        </div>

        <div className={s.twistCard}>
          <div className={s.twistTop}>
            <span style={{ color: "var(--text-muted-2)", fontWeight: 600 }}>Twistiness</span>
            <span style={{ fontWeight: 800, color: "var(--terracotta)" }}>Very high · 312 curves</span>
          </div>
          <div className={s.twistBars}>
            {[0, 1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className={s.twistSeg}
                style={{ background: i < 4 ? "var(--terracotta)" : "#e3d2c3" }}
              />
            ))}
          </div>
          <div className={s.twistNote}>Chuckanut Dr · 2 overlooks · low traffic</div>
        </div>

        <button className={s.startBtn}>Start drive</button>
      </div>
    </div>
  );
}
