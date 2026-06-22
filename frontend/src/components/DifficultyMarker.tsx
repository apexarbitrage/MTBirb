import type { CSSProperties } from "react";
import type { Difficulty } from "../data/trails";

/*
 * Difficulty marker, ported from `diffMarker(diff, size, onDark)`:
 *   Easy → green circle, Intermediate → blue rounded square,
 *   Advanced → dark diamond (rotated square, optional white border on dark).
 */
export function DifficultyMarker({
  diff,
  size = 10,
  onDark = false,
}: {
  diff: Difficulty;
  size?: number;
  onDark?: boolean;
}) {
  const base: CSSProperties = { width: size, height: size, flex: "none" };
  let style: CSSProperties;
  if (diff === "Advanced") {
    style = {
      ...base,
      background: "var(--diff-advanced)",
      transform: "rotate(45deg)",
      border: onDark ? "1.5px solid var(--sand)" : "none",
    };
  } else if (diff === "Intermediate") {
    style = { ...base, background: "var(--diff-intermediate)", borderRadius: 3 };
  } else {
    style = { ...base, background: "var(--diff-easy)", borderRadius: "50%" };
  }
  return <div style={style} />;
}
