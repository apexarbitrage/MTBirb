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

export interface Trail {
  id: string;
  name: string;
  score: number;
  diff: Difficulty;
  miles: number;
  effort: number;
  window: string;
  realfeel: string;
  sky: string;
  condition: string;
  peak: string;
  metaTime: string;
  metaBird: string;
  // extras (Trails list)
  features: string[];
  rideTime: number; // minutes
  likelyBirds: string[];
  // detail screen
  location: string;
  gainFt: number;
  dirt: string;
  climbFt: number;
  descentFt: number;
  avgUpGrade: string;
  avgDownGrade: string;
  elevation: number[]; // normalized 0..1 sample points, left→right
  sightingHeadline: string;
  factors: SightingFactor[];
  // optimal-time screen
  bestWindow: string;
  bestWindowWhy: string;
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

export interface Species {
  name: string;
  sci: string;
  slotId: string;
  img: string;
  like: Likelihood;
  trails: string[];
}

export const SPECIES: Species[] = [
  {
    name: "Barred Owl",
    sci: "Strix varia",
    slotId: "sp-barred-owl",
    img: "/assets/barred-owl.jpg",
    like: "High",
    trails: ["owl", "cedar"],
  },
  {
    name: "Pileated Woodpecker",
    sci: "Dryocopus pileatus",
    slotId: "sp-pileated",
    img: "/assets/pileated-woodpecker.jpg",
    like: "High",
    trails: ["raptor", "cedar"],
  },
  {
    name: "Red Fox",
    sci: "Vulpes vulpes",
    slotId: "sp-redfox",
    img: "/assets/red-fox.jpg",
    like: "Med",
    trails: ["raptor", "marsh"],
  },
  {
    name: "Northern Goshawk",
    sci: "Accipiter gentilis",
    slotId: "sp-goshawk",
    img: "/assets/northern-goshawk.jpg",
    like: "Rare",
    trails: ["raptor"],
  },
];

export const TOTAL_TRAILS_NEARBY = 14;
export const SPECIES_NEARBY_COUNT = 412;
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

export function diffRank(d: Difficulty): number {
  return d === "Easy" ? 1 : d === "Intermediate" ? 2 : 3;
}

export function fmtTime(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}` : `${m} min`;
}

export function speciesByName(name: string | null): Species | null {
  if (!name) return null;
  return SPECIES.find((s) => s.name === name) ?? null;
}

export type TrailSortKey = "sighting" | "difficulty" | "time" | "effort" | "features";

export const TRAIL_SORT_DEFAULT_DIR: Record<TrailSortKey, "asc" | "desc"> = {
  sighting: "desc",
  difficulty: "asc",
  time: "asc",
  effort: "asc",
  features: "desc",
};

export const TRAIL_SORT_LABELS: Record<TrailSortKey, string> = {
  sighting: "Sighting probability",
  difficulty: "Difficulty",
  time: "Time to ride",
  effort: "Effort",
  features: "Features",
};

export const TRAIL_SORT_CHIPS: { key: TrailSortKey; label: string }[] = [
  { key: "sighting", label: "Sighting" },
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
      return a.rideTime - b.rideTime;
    case "effort":
      return a.effort - b.effort;
    case "features":
      return a.features.length - b.features.length;
    case "sighting":
    default:
      return a.score - b.score;
  }
}
