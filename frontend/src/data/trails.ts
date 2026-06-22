/*
 * Static sample data for the MTBirb prototype.
 *
 * Mirrors the data in the design handoff's `renderVals()` (4 trails, 4 species,
 * 4 trips), extended with per-trail detail fields (elevation, climb/descent,
 * sighting factors) so every trail has a coherent Trail Detail screen rather
 * than reusing Raptor Ridge's numbers everywhere.
 *
 * In production this is replaced by: trails from a trails source (e.g.
 * Trailforks), wildlife probability from eBird calibrated by search effort /
 * seasonality / time of day / weather, weather from a forecast API.
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

export const TRAILS: Trail[] = [
  {
    id: "raptor",
    name: "Raptor Ridge",
    score: 94,
    diff: "Advanced",
    miles: 8.4,
    effort: 8.7,
    window: "6:10–8:30 AM · best light & activity",
    realfeel: "54°",
    sky: "Clear",
    condition: "Tacky",
    peak: "Northern Goshawk, Pileated Woodpecker",
    metaTime: "AM",
    metaBird: "Goshawk",
    features: ["Rock garden", "Drops", "Tech climb"],
    rideTime: 65,
    likelyBirds: ["Northern Goshawk", "Pileated Woodpecker", "Sooty Grouse"],
    location: "Galbraith Mtn · Bellingham, WA",
    gainFt: 2050,
    dirt: "Tacky",
    climbFt: 2050,
    descentFt: 2180,
    avgUpGrade: "9.2%",
    avgDownGrade: "7.8%",
    elevation: [0.1, 0.22, 0.38, 0.48, 0.66, 0.8, 0.58, 0.44, 0.3, 0.2, 0.13],
    sightingHeadline: "94% chance of a notable encounter this morning",
    factors: [
      { label: "Seasonality", value: "Peak", pct: 90, tone: "terracotta" },
      { label: "Time of day", value: "Dawn — ideal", pct: 96, tone: "terracotta" },
      { label: "Weather match", value: "Calm, clear", pct: 84, tone: "sage" },
      { label: "Recent reports (14d)", value: "23 checklists", pct: 72, tone: "sage" },
    ],
    bestWindow: "6:10 – 8:30 AM",
    bestWindowWhy: "Dry dirt, calm wind, and peak wildlife activity overlap.",
  },
  {
    id: "owl",
    name: "Owl Hollow",
    score: 91,
    diff: "Intermediate",
    miles: 5.5,
    effort: 6.1,
    window: "Dusk · 7:40–8:50 PM · peak owl calls",
    realfeel: "58°",
    sky: "Clear",
    condition: "Tacky",
    peak: "Northern Pygmy-Owl",
    metaTime: "dusk",
    metaBird: "Pygmy-Owl",
    features: ["Jumps", "Berms", "Flow"],
    rideTime: 48,
    likelyBirds: ["Northern Pygmy-Owl", "Varied Thrush", "Pacific Wren"],
    location: "Lake Padden · Bellingham, WA",
    gainFt: 1180,
    dirt: "Tacky",
    climbFt: 1180,
    descentFt: 1210,
    avgUpGrade: "6.4%",
    avgDownGrade: "6.0%",
    elevation: [0.15, 0.28, 0.4, 0.52, 0.46, 0.6, 0.7, 0.55, 0.4, 0.28, 0.18],
    sightingHeadline: "91% chance of a notable encounter at dusk",
    factors: [
      { label: "Seasonality", value: "Peak", pct: 88, tone: "terracotta" },
      { label: "Time of day", value: "Dusk — ideal", pct: 92, tone: "terracotta" },
      { label: "Weather match", value: "Calm, clear", pct: 80, tone: "sage" },
      { label: "Recent reports (14d)", value: "18 checklists", pct: 64, tone: "sage" },
    ],
    bestWindow: "7:40 – 8:50 PM",
    bestWindowWhy: "Cooling air and peak owl calls overlap at dusk.",
  },
  {
    id: "cedar",
    name: "Cedar Dust",
    score: 88,
    diff: "Intermediate",
    miles: 6.2,
    effort: 6.8,
    window: "Morning · 6:30–9:00 AM · cool & calm",
    realfeel: "52°",
    sky: "Part cloud",
    condition: "Tacky",
    peak: "Pileated Woodpecker",
    metaTime: "AM",
    metaBird: "Pileated Woodpecker",
    features: ["Flow", "Roots"],
    rideTime: 52,
    likelyBirds: ["Pileated Woodpecker", "Red Crossbill", "Gray Jay"],
    location: "Stewart Mtn · Bellingham, WA",
    gainFt: 1420,
    dirt: "Tacky",
    climbFt: 1420,
    descentFt: 1450,
    avgUpGrade: "7.1%",
    avgDownGrade: "6.6%",
    elevation: [0.12, 0.3, 0.42, 0.5, 0.62, 0.72, 0.6, 0.48, 0.36, 0.24, 0.16],
    sightingHeadline: "88% chance of a notable encounter this morning",
    factors: [
      { label: "Seasonality", value: "High", pct: 82, tone: "terracotta" },
      { label: "Time of day", value: "Morning — good", pct: 86, tone: "terracotta" },
      { label: "Weather match", value: "Cool, calm", pct: 78, tone: "sage" },
      { label: "Recent reports (14d)", value: "15 checklists", pct: 58, tone: "sage" },
    ],
    bestWindow: "6:30 – 9:00 AM",
    bestWindowWhy: "Cool, calm morning with low traffic and good light.",
  },
  {
    id: "marsh",
    name: "Marsh Loop",
    score: 76,
    diff: "Easy",
    miles: 3.1,
    effort: 3.4,
    window: "Midday · 11 AM–1 PM · wetland activity",
    realfeel: "63°",
    sky: "Clear",
    condition: "Dry",
    peak: "Great Blue Heron",
    metaTime: "midday",
    metaBird: "Heron",
    features: ["Boardwalk", "Flowy"],
    rideTime: 26,
    likelyBirds: ["Great Blue Heron", "Green Heron", "Belted Kingfisher"],
    location: "Tennant Lake · Ferndale, WA",
    gainFt: 240,
    dirt: "Dry",
    climbFt: 240,
    descentFt: 240,
    avgUpGrade: "2.1%",
    avgDownGrade: "2.0%",
    elevation: [0.4, 0.46, 0.42, 0.5, 0.45, 0.52, 0.48, 0.54, 0.46, 0.5, 0.44],
    sightingHeadline: "76% chance of a wildlife encounter midday",
    factors: [
      { label: "Seasonality", value: "Moderate", pct: 70, tone: "terracotta" },
      { label: "Time of day", value: "Midday — fair", pct: 64, tone: "sage" },
      { label: "Weather match", value: "Warm, clear", pct: 72, tone: "sage" },
      { label: "Recent reports (14d)", value: "31 checklists", pct: 80, tone: "terracotta" },
    ],
    bestWindow: "11:00 AM – 1:00 PM",
    bestWindowWhy: "Midday wetland activity with warm, clear skies.",
  },
];

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

export function trailById(id: string): Trail {
  return TRAILS.find((t) => t.id === id) ?? TRAILS[0];
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
