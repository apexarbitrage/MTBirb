import { useNavigate } from "react-router-dom";
import { BackButton } from "../components/BackButton";
import { Photo } from "../components/Photo";
import { VIEWFINDER_IMG } from "../data/trails";
import s from "./BirdIdScreen.module.css";

// Heights (%) and tones for the listening waveform, ported from the design.
const WAVE = [
  [40, "sage"],
  [70, "sage"],
  [95, "terracotta"],
  [60, "sage"],
  [85, "terracotta"],
  [45, "sage"],
  [75, "sage"],
  [100, "terracotta"],
  [55, "sage"],
  [80, "sage"],
  [38, "sage"],
] as const;

export function BirdIdScreen() {
  const navigate = useNavigate();

  return (
    <div className={s.screen}>
      <Photo
        src={VIEWFINDER_IMG}
        alt="Camera viewfinder"
        fit="cover"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
        label="Viewfinder"
      />

      {/* focus reticle */}
      <div className={s.reticle}>
        <div className={`${s.corner} ${s.cTL}`} />
        <div className={`${s.corner} ${s.cTR}`} />
        <div className={`${s.corner} ${s.cBL}`} />
        <div className={`${s.corner} ${s.cBR}`} />
      </div>

      {/* top: back + mode + settings */}
      <div className={s.topRow}>
        <BackButton bg="rgba(0,0,0,0.45)" stroke="#fff" />
        <div className={s.modeToggle}>
          <button className={`${s.modeOpt} ${s.modeActive}`}>Sound</button>
          <button className={s.modeOpt}>Photo</button>
        </div>
        <div className={s.settings}>
          <div className={s.settingsDot} />
        </div>
      </div>

      {/* listening waveform */}
      <div className={s.waveform}>
        {WAVE.map(([h, tone], i) => (
          <div
            key={i}
            className={s.wave}
            style={{
              height: `${h}%`,
              background: tone === "terracotta" ? "var(--terracotta)" : "var(--sage)",
              animationDelay: `${(i % 5) * 0.12}s`,
            }}
          />
        ))}
      </div>

      {/* result sheet */}
      <div className={s.sheet}>
        <div className={s.handle} />
        <div className={s.resultRow}>
          <Photo
            src="/assets/pileated-woodpecker.jpg"
            alt="Pileated Woodpecker"
            shape="rounded"
            radius={14}
            style={{ width: 60, height: 60, flex: "none" }}
            label="Photo"
          />
          <div style={{ flex: 1 }}>
            <div className={s.spName}>Pileated Woodpecker</div>
            <div className={s.spSci}>Dryocopus pileatus</div>
            <div className={s.matchRow}>
              <div className={s.matchBadge}>97% match</div>
              <span className={s.heardNote}>Heard 2× nearby</span>
            </div>
          </div>
        </div>
        <div className={s.actions}>
          <button className={s.addBtn} onClick={() => navigate("/trips")}>
            Add to trip list
          </button>
          <button className={s.bookmarkBtn} aria-label="Bookmark">
            <div style={{ width: 14, height: 14, border: "2px solid var(--forest)", borderRadius: "0 3px 3px 3px" }} />
          </button>
        </div>
      </div>
    </div>
  );
}
