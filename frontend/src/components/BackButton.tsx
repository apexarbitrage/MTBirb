import { useNavigate } from "react-router-dom";
import type { CSSProperties } from "react";

/*
 * Circular back button with the handoff's rotated-border chevron. Defaults to
 * router back; `bg`/`stroke` adapt it to photo/map overlays vs. light surfaces.
 */
export function BackButton({
  onClick,
  bg = "rgba(45,59,45,0.55)",
  stroke = "#fff",
  blur = true,
  style,
}: {
  onClick?: () => void;
  bg?: string;
  stroke?: string;
  blur?: boolean;
  style?: CSSProperties;
}) {
  const navigate = useNavigate();
  return (
    <button
      aria-label="Back"
      onClick={onClick ?? (() => navigate(-1))}
      style={{
        width: 40,
        height: 40,
        borderRadius: "50%",
        background: bg,
        backdropFilter: blur ? "blur(6px)" : undefined,
        WebkitBackdropFilter: blur ? "blur(6px)" : undefined,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        ...style,
      }}
    >
      <span
        style={{
          width: 9,
          height: 9,
          borderLeft: `2.5px solid ${stroke}`,
          borderBottom: `2.5px solid ${stroke}`,
          transform: "rotate(45deg)",
          marginLeft: 3,
        }}
      />
    </button>
  );
}
