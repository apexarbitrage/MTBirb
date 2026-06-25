/*
 * Plots geotagged trip photos onto the trail's OSM line - a simple equirectangular projection
 * with a shared bounding box, the same approach the trail-line preview uses. Photos without GPS
 * are filtered out by the caller.
 */

interface GeoPoint {
  lat: number;
  lon: number;
}

const W = 300;
const H = 150;
const PAD = 16;

export function TrailPhotoMap({ line, photos }: { line: [number, number][]; photos: GeoPoint[] }) {
  const xs = [...line.map((p) => p[0]), ...photos.map((p) => p.lon)];
  const ys = [...line.map((p) => p[1]), ...photos.map((p) => p.lat)];
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const rangeX = maxX - minX || 1e-6;
  const rangeY = maxY - minY || 1e-6;
  const scale = Math.min((W - 2 * PAD) / rangeX, (H - 2 * PAD) / rangeY);
  const offX = (W - rangeX * scale) / 2;
  const offY = (H - rangeY * scale) / 2;
  const project = (lon: number, lat: number): [number, number] => [
    offX + (lon - minX) * scale,
    H - (offY + (lat - minY) * scale),
  ];

  const polyline = line
    .map(([lon, lat]) => project(lon, lat).map((n) => n.toFixed(1)).join(","))
    .join(" ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="140" preserveAspectRatio="xMidYMid meet">
      <polyline
        points={polyline}
        style={{ fill: "none", stroke: "var(--sage)", strokeWidth: 2.5, strokeLinejoin: "round", strokeLinecap: "round" }}
      />
      {photos.map((p, i) => {
        const [x, y] = project(p.lon, p.lat);
        return (
          <circle key={i} cx={x} cy={y} r={5.5} fill="var(--terracotta)" stroke="#fff" strokeWidth={2} />
        );
      })}
    </svg>
  );
}
