import type { CSSProperties } from "react";

/*
 * Match-score ring: a conic-gradient terracotta arc (= score%) over a track,
 * with a centered disc showing the number. Used small on the Discover hero and
 * large (with a MATCH label) on Trail Detail.
 */
export function ScoreRing({
  score,
  size,
  centerSize,
  centerBg,
  track = "rgba(255,255,255,0.2)",
  numberStyle,
  label,
}: {
  score: number;
  size: number;
  centerSize: number;
  centerBg: string;
  track?: string;
  numberStyle?: CSSProperties;
  label?: string;
}) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        flex: "none",
        background: `conic-gradient(var(--terracotta) 0% ${score}%, ${track} ${score}% 100%)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          width: centerSize,
          height: centerSize,
          borderRadius: "50%",
          background: centerBg,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span style={{ fontWeight: 800, lineHeight: 1, ...numberStyle }}>{score}</span>
        {label && (
          <span
            style={{
              fontSize: 8,
              color: "var(--terracotta)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {label}
          </span>
        )}
      </div>
    </div>
  );
}
