import { useState, type CSSProperties } from "react";

/*
 * Real-image replacement for the prototype's <image-slot>. Renders an <img> at
 * the given handoff asset path with object-fit cover. Until a licensed photo is
 * dropped in at that path (and if it 404s), a tasteful palette placeholder in
 * the forest/sage range shows instead — so empty slots look intentional.
 */

type Shape = "rect" | "circle" | "rounded";

function radiusFor(shape: Shape, radius: number): string | number {
  if (shape === "circle") return "50%";
  if (shape === "rounded") return radius;
  return 0;
}

// Deterministic placeholder tint so different slots don't all look identical.
function placeholderBg(seed: string): string {
  const hues = [
    "linear-gradient(135deg, #3a4a36, #6f7d4a)",
    "linear-gradient(135deg, #2d3b2d, #8a9a5b)",
    "linear-gradient(135deg, #4a3a2c, #c2703d)",
    "linear-gradient(135deg, #35433a, #5f6b3f)",
  ];
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return hues[h % hues.length];
}

export function Photo({
  src,
  alt,
  shape = "rect",
  radius = 12,
  fit = "cover",
  style,
  label,
}: {
  src: string;
  alt: string;
  shape?: Shape;
  radius?: number;
  fit?: CSSProperties["objectFit"];
  style?: CSSProperties;
  label?: string;
}) {
  const [errored, setErrored] = useState(false);
  const br = radiusFor(shape, radius);

  return (
    <div
      style={{
        position: "relative",
        overflow: "hidden",
        borderRadius: br,
        background: placeholderBg(src),
        ...style,
      }}
      aria-label={errored ? alt : undefined}
      role={errored ? "img" : undefined}
    >
      {!errored && (
        <img
          src={src}
          alt={alt}
          onError={() => setErrored(true)}
          style={{ width: "100%", height: "100%", objectFit: fit, display: "block" }}
        />
      )}
      {errored && label && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 6,
            textAlign: "center",
            fontFamily: "var(--font-mono)",
            fontSize: 9,
            letterSpacing: 0.5,
            color: "rgba(255,255,255,0.7)",
          }}
        >
          {label}
        </div>
      )}
    </div>
  );
}
