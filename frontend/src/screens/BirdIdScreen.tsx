import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { BackButton } from "../components/BackButton";
import { Photo } from "../components/Photo";
import { apiPostBlob } from "../api/client";
import { recordWavClip } from "../data/audio";
import { useGeolocation } from "../data/useGeolocation";
import { VIEWFINDER_IMG } from "../data/trails";
import s from "./BirdIdScreen.module.css";

// Heights/tones for the listening waveform, ported from the design.
const WAVE = [
  [40, "sage"], [70, "sage"], [95, "terracotta"], [60, "sage"], [85, "terracotta"],
  [45, "sage"], [75, "sage"], [100, "terracotta"], [55, "sage"], [80, "sage"], [38, "sage"],
] as const;

const RECORD_SECONDS = 5;

interface Detection {
  commonName: string;
  scientificName: string;
  confidence: number;
}

type Status = "idle" | "listening" | "analyzing" | "done" | "error";

export function BirdIdScreen() {
  const navigate = useNavigate();
  const { lat, lon } = useGeolocation();
  const [status, setStatus] = useState<Status>("idle");
  const [results, setResults] = useState<Detection[]>([]);
  const [error, setError] = useState<string | null>(null);

  const listen = async () => {
    setError(null);
    setResults([]);
    setStatus("listening");
    try {
      const wav = await recordWavClip(RECORD_SECONDS);
      setStatus("analyzing");
      const { detections } = await apiPostBlob<{ detections: Detection[] }>(
        `/birdnet/identify?lat=${lat}&lon=${lon}`,
        wav,
        "audio/wav",
      );
      setResults(detections);
      setStatus("done");
    } catch (e) {
      setError(
        e instanceof Error && e.name === "NotAllowedError"
          ? "Microphone access denied."
          : e instanceof Error
            ? e.message
            : "Couldn't identify.",
      );
      setStatus("error");
    }
  };

  const top = results[0];
  const busy = status === "listening" || status === "analyzing";

  return (
    <div className={s.screen}>
      <Photo
        src={VIEWFINDER_IMG}
        alt="Camera viewfinder"
        fit="cover"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
        label="Viewfinder"
      />

      <div className={s.reticle}>
        <div className={`${s.corner} ${s.cTL}`} />
        <div className={`${s.corner} ${s.cTR}`} />
        <div className={`${s.corner} ${s.cBL}`} />
        <div className={`${s.corner} ${s.cBR}`} />
      </div>

      <div className={s.topRow}>
        <BackButton bg="rgba(0,0,0,0.45)" stroke="#fff" />
        <div className={s.modeToggle}>
          <button className={`${s.modeOpt} ${s.modeActive}`}>Sound</button>
          <button className={s.modeOpt} title="Photo ID isn't wired yet">
            Photo
          </button>
        </div>
        <div className={s.settings}>
          <div className={s.settingsDot} />
        </div>
      </div>

      {/* Listening waveform - animated only while capturing */}
      <div className={s.waveform} style={{ opacity: status === "listening" ? 1 : 0.25 }}>
        {WAVE.map(([h, tone], i) => (
          <div
            key={i}
            className={s.wave}
            style={{
              height: `${h}%`,
              background: tone === "terracotta" ? "var(--terracotta)" : "var(--sage)",
              animationPlayState: status === "listening" ? "running" : "paused",
              animationDelay: `${(i % 5) * 0.12}s`,
            }}
          />
        ))}
      </div>

      {/* Result sheet */}
      <div className={s.sheet}>
        <div className={s.handle} />

        {status === "idle" && (
          <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: 14, padding: "8px 0 4px" }}>
            Point toward the bird and listen — BirdNET will identify the song.
          </div>
        )}
        {status === "error" && (
          <div style={{ textAlign: "center", color: "var(--terracotta)", fontSize: 14, padding: "8px 0" }}>
            {error}
          </div>
        )}
        {status === "done" && !top && (
          <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: 14, padding: "8px 0" }}>
            No birds detected — move closer and try again.
          </div>
        )}

        {top && (
          <>
            <div className={s.resultRow}>
              <div
                style={{
                  width: 60,
                  height: 60,
                  flex: "none",
                  borderRadius: 14,
                  background: "var(--sage-tint-strong)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 26,
                }}
              >
                🐦
              </div>
              <div style={{ flex: 1 }}>
                <div className={s.spName}>{top.commonName}</div>
                <div className={s.spSci}>{top.scientificName}</div>
                <div className={s.matchRow}>
                  <div className={s.matchBadge}>{Math.round(top.confidence * 100)}% match</div>
                  <span className={s.heardNote}>BirdNET · sound</span>
                </div>
              </div>
            </div>
            {results.length > 1 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 7, marginBottom: 12 }}>
                {results.slice(1).map((d) => (
                  <span
                    key={d.scientificName}
                    style={{
                      fontSize: 12,
                      fontWeight: 600,
                      color: "var(--tan-accent)",
                      background: "var(--sand-bird-chip)",
                      padding: "5px 10px",
                      borderRadius: 8,
                    }}
                  >
                    {d.commonName} {Math.round(d.confidence * 100)}%
                  </span>
                ))}
              </div>
            )}
          </>
        )}

        <div className={s.actions}>
          <button className={s.addBtn} onClick={listen} disabled={busy}>
            {status === "listening"
              ? `Listening… ${RECORD_SECONDS}s`
              : status === "analyzing"
                ? "Identifying…"
                : top
                  ? "Listen again"
                  : "Tap to listen"}
          </button>
          {top && (
            <button className={s.bookmarkBtn} aria-label="Add to trips" onClick={() => navigate("/trips")}>
              <div style={{ width: 14, height: 14, border: "2px solid var(--forest)", borderRadius: "0 3px 3px 3px" }} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
