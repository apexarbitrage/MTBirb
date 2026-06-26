/*
 * Trail types, helpers, and the remaining static sample data for MTBirb.
 *
 * Trails are now served by the backend (`GET /api/trails`, loaded via TrailsProvider) - the
 * former static `TRAILS` array moved into the database seed (backend/app/seed.py). Species
 * and trips are still static samples here: they depend on integrations not yet wired (eBird
 * for species likelihood, a rides store for trips) and light up in a later pass.
 *
 * In production the trail wildlife/weather fields come from eBird (calibrated by search
 * effort / seasonality / time of day / weather) and a forecast API; today they are seeded
 * placeholders served under each trail's `derived` overlay.
 */

export type Difficulty = "Easy" | "Intermediate" | "Advanced";

export interface SightingFactor {
  label: string;
  value: string;
  pct: number;
  tone: "terracotta" | "sage";
}

/*
 * The shared trail shape the screens render. It now comes from the live catalog
 * (`catalogToTrail` in useCatalogTrails.ts), so fields the catalog can't supply yet are
 * nullable: weather/best-time (fetched live per-trail or deferred) and terrain metrics that
 * only exist once a trail's OSM line has been enriched. `score` is the recency+season+notable
 * wildlife activity score; `notableScore` is the "odds of something unusual" axis.
 */
export interface Trail {
  id: string;
  name: string;
  score: number;
  notableScore: number | null;
  diff: Difficulty | null;
  miles: number | null;
  effort: number | null;
  window: string | null;
  realfeel: string | null;
  sky: string | null;
  condition: string | null;
  peak: string | null;
  metaTime: string | null;
  metaBird: string | null;
  // extras (Trails list)
  features: string[];
  rideTime: number | null; // minutes
  likelyBirds: string[];
  notableBirds: string[];
  // detail screen
  location: string | null;
  gainFt: number | null;
  dirt: string | null;
  climbFt: number | null;
  descentFt: number | null;
  avgUpGrade: string | null;
  avgDownGrade: string | null;
  elevation: number[]; // normalized 0..1 sample points, left→right
  sightingHeadline: string | null;
  factors: SightingFactor[];
  // optimal-time screen
  bestWindow: string | null;
  bestWindowWhy: string | null;
}

/** Map the catalog's free-text difficulty onto the design's three buckets (null if unrated). */
export function normalizeDifficulty(d: string | null): Difficulty | null {
  switch ((d ?? "").toLowerCase()) {
    case "easiest":
    case "beginner":
    case "easy":
      return "Easy";
    case "intermediate":
      return "Intermediate";
    case "advanced":
    case "expert":
      return "Advanced";
    default:
      return null;
  }
}

export interface Trip {
  date: string;
  trail: string;
  diff: Difficulty;
  miles: number;
  birds: string[];
  lifers: number;
}

export const TRIPS: Trip[] = [
  {
    date: "Jun 14, 2026",
    trail: "Owl Hollow",
    diff: "Intermediate",
    miles: 5.5,
    birds: ["Northern Pygmy-Owl", "Varied Thrush", "Pacific Wren"],
    lifers: 1,
  },
  {
    date: "Jun 7, 2026",
    trail: "Cedar Dust",
    diff: "Intermediate",
    miles: 6.2,
    birds: ["Pileated Woodpecker", "Red Crossbill"],
    lifers: 0,
  },
  {
    date: "May 30, 2026",
    trail: "Raptor Ridge",
    diff: "Advanced",
    miles: 8.4,
    birds: ["Northern Goshawk", "Band-tailed Pigeon", "Sooty Grouse", "Hermit Warbler"],
    lifers: 2,
  },
  {
    date: "May 18, 2026",
    trail: "Marsh Loop",
    diff: "Easy",
    miles: 3.1,
    birds: ["Great Blue Heron", "Green Heron"],
    lifers: 0,
  },
];

export type Likelihood = "High" | "Med" | "Rare";

export const TRAIL_HERO_IMG = "/assets/raptor-ridge.jpg";
export const AVATAR_IMG = "/assets/avatar.jpg";
export const VIEWFINDER_IMG = "/assets/viewfinder.jpg";

/* ---------- helpers (ported from renderVals) ---------- */

export function scoreColor(score: number): string {
  return score >= 85 ? "var(--terracotta)" : "var(--sage-text)";
}

export function scoreChipBg(score: number): string {
  return score >= 85 ? "var(--terracotta-tint)" : "var(--sage-tint-strong)";
}

export function likelihoodColor(like: Likelihood): string {
  return like === "High"
    ? "var(--terracotta)"
    : like === "Med"
      ? "var(--sage)"
      : "var(--rare)";
}

export function diffRank(d: Difficulty | null): number {
  return d === "Easy" ? 1 : d === "Intermediate" ? 2 : d === "Advanced" ? 3 : 0;
}

export function fmtTime(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}` : `${m} min`;
}

export type TrailSortKey = "sighting" | "optimal" | "difficulty" | "time" | "effort" | "features";

export const TRAIL_SORT_DEFAULT_DIR: Record<TrailSortKey, "asc" | "desc"> = {
  sighting: "desc",
  optimal: "desc",
  difficulty: "asc",
  time: "asc",
  effort: "asc",
  features: "desc",
};

export const TRAIL_SORT_LABELS: Record<TrailSortKey, string> = {
  sighting: "Sighting probability",
  optimal: "Optimal now",
  difficulty: "Difficulty",
  time: "Time to ride",
  effort: "Effort",
  features: "Features",
};

export const TRAIL_SORT_CHIPS: { key: TrailSortKey; label: string }[] = [
  { key: "sighting", label: "Sighting" },
  { key: "optimal", label: "Optimal now" },
  { key: "difficulty", label: "Difficulty" },
  { key: "time", label: "Time to ride" },
  { key: "effort", label: "Effort" },
  { key: "features", label: "Features" },
];

export function compareTrails(a: Trail, b: Trail, key: TrailSortKey): number {
  switch (key) {
    case "difficulty":
      return diffRank(a.diff) - diffRank(b.diff);
    case "time":
      return (a.rideTime ?? 0) - (b.rideTime ?? 0);
    case "effort":
      return (a.effort ?? 0) - (b.effort ?? 0);
    case "features":
      return a.features.length - b.features.length;
    case "sighting":
    default:
      return a.score - b.score;
  }
}
