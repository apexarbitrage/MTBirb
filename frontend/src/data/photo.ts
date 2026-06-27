/*
 * Reads a chosen photo into a small geotagged record: its EXIF GPS (so it can be mapped onto a
 * trail) and a downscaled JPEG thumbnail data-URL. We never upload the full image - only the
 * thumbnail and coordinates are kept. Coordinates are null when the photo has no EXIF GPS.
 */

import exifr from "exifr";

export interface GeoPhoto {
  lat: number | null;
  lon: number | null;
  takenAt: string | null;
  thumb: string;
}

const MAX_DIM = 320;

export async function makeThumb(file: File): Promise<string> {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = reject;
      el.src = url;
    });
    const scale = Math.min(1, MAX_DIM / Math.max(img.width, img.height));
    const w = Math.max(1, Math.round(img.width * scale));
    const h = Math.max(1, Math.round(img.height * scale));
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return "";
    ctx.drawImage(img, 0, 0, w, h);
    return canvas.toDataURL("image/jpeg", 0.6);
  } finally {
    URL.revokeObjectURL(url);
  }
}

export async function readGeoPhoto(file: File): Promise<GeoPhoto> {
  let lat: number | null = null;
  let lon: number | null = null;
  let takenAt: string | null = null;
  try {
    const gps = await exifr.gps(file);
    if (gps) {
      lat = gps.latitude ?? null;
      lon = gps.longitude ?? null;
    }
    const exif = await exifr.parse(file, ["DateTimeOriginal"]).catch(() => null);
    if (exif?.DateTimeOriginal instanceof Date) takenAt = exif.DateTimeOriginal.toISOString();
  } catch {
    // No/unsupported EXIF - keep the thumbnail without coordinates.
  }
  return { lat, lon, takenAt, thumb: await makeThumb(file) };
}
