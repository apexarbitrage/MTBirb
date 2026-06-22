/*
 * Custom inline-SVG icons, ported 1:1 from the design handoff (1.6–1.8 stroke,
 * rounded caps/joins). No icon font/library — these are the app's icon system.
 */

interface NavIconProps {
  color: string;
  size?: number;
}

export function BinocularsIcon({ color, size = 21 }: NavIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      style={{ display: "block", fill: "none", stroke: color, strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" }}
    >
      <rect x="4" y="8.5" width="6.2" height="10.5" rx="3.1" />
      <rect x="13.8" y="8.5" width="6.2" height="10.5" rx="3.1" />
      <line x1="10.2" y1="12" x2="13.8" y2="12" />
      <line x1="5.6" y1="8.5" x2="7.1" y2="5.5" />
      <line x1="18.4" y1="8.5" x2="16.9" y2="5.5" />
    </svg>
  );
}

interface BirdGlyphProps {
  fill: string;
  eyeFill: string;
  size?: number;
}

/** The stylized bird used in the nav (Birbs) and in peak-odds / filter rows. */
export function BirdGlyph({ fill, eyeFill, size = 20 }: BirdGlyphProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={{ display: "block", flex: "none" }}>
      <circle cx="10" cy="14.5" r="6" fill={fill} />
      <path d="M4.4 13.4 L1 12.7 L4.4 15.7 Z" fill={fill} />
      <path d="M12.4 12.6 L20.5 6 L18.7 12.8 Z" fill={fill} />
      <circle cx="8.3" cy="13" r="1.05" fill={eyeFill} />
    </svg>
  );
}

export function BikeIcon({ color, size = 22 }: NavIconProps) {
  return (
    <svg
      width={size}
      height={(size * 20) / 22}
      viewBox="0 0 24 24"
      style={{ display: "block", fill: "none", stroke: color, strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round" }}
    >
      <circle cx="6" cy="16" r="4" />
      <circle cx="18" cy="16" r="4" />
      <line x1="6" y1="16" x2="11" y2="16" />
      <line x1="11" y1="16" x2="12" y2="9" />
      <line x1="12" y1="9" x2="16" y2="9.2" />
      <line x1="16" y1="9.2" x2="18" y2="16" />
      <line x1="11" y1="16" x2="16" y2="9.2" />
      <line x1="10.8" y1="8.4" x2="12.6" y2="9" />
      <line x1="15.4" y1="9.2" x2="17.4" y2="8.3" />
    </svg>
  );
}

export function CompassIcon({ color, size = 21 }: NavIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      style={{ display: "block", fill: "none", stroke: color, strokeWidth: 1.7, strokeLinecap: "round", strokeLinejoin: "round" }}
    >
      <circle cx="12" cy="12" r="8.3" />
      <polygon points="15.6,8.4 12.8,12.8 8.4,15.6 11.2,11.2" fill={color} stroke="none" />
    </svg>
  );
}

export function FaceIcon({ color, size = 21 }: NavIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      style={{ display: "block", fill: "none", stroke: color, strokeWidth: 1.7, strokeLinecap: "round", strokeLinejoin: "round" }}
    >
      <circle cx="12" cy="12" r="9" />
      <rect x="5.6" y="9.4" width="5.2" height="3.6" rx="1.8" fill={color} stroke="none" />
      <rect x="13.2" y="9.4" width="5.2" height="3.6" rx="1.8" fill={color} stroke="none" />
      <line x1="10.8" y1="10.3" x2="13.2" y2="10.3" />
      <path d="M8.8 14.8 Q12 17.4 15.2 14.8" />
    </svg>
  );
}

/** Magnifier used in the species search field. innerFill = field background. */
export function SearchIcon({ innerFill = "#fff", size = 18 }: { innerFill?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={{ display: "block", flex: "none" }}>
      <circle cx="10.5" cy="10.5" r="6.5" fill="var(--terracotta)" />
      <circle cx="10.5" cy="10.5" r="3.6" fill={innerFill} />
      <rect x="15" y="15.5" width="7" height="2.6" rx="1.3" transform="rotate(45 15 15.5)" fill="var(--terracotta)" />
    </svg>
  );
}

/** Green circular checkmark used in Connections tiles. */
export function CheckBadge({ size = 18 }: { size?: number }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: "var(--success)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flex: "none",
      }}
    >
      <div
        style={{
          width: 6,
          height: 10,
          borderRight: "2.5px solid #fff",
          borderBottom: "2.5px solid #fff",
          transform: "rotate(45deg)",
          marginTop: -2,
        }}
      />
    </div>
  );
}
