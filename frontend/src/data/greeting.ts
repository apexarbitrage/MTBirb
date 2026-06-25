/*
 * Builds the Discover screen's header copy (date eyebrow + headline) from
 * the real clock plus the selected trail's existing conditions/species data,
 * instead of the two lines that used to be hardcoded.
 */

import { SPECIES } from "./trails";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

export function formatEyebrowDate(date: Date): string {
  const weekday = WEEKDAYS[date.getDay()];
  const month = MONTHS[date.getMonth()];
  const day = date.getDate();
  let hours = date.getHours();
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const ampm = hours >= 12 ? "PM" : "AM";
  hours = hours % 12 || 12;
  return `${weekday} · ${month} ${day} · ${hours}:${minutes} ${ampm}`;
}

type TimeBucketKey = "night" | "dawn" | "morning" | "midday" | "afternoon" | "goldenHour" | "dusk";

interface TimeBucket {
  key: TimeBucketKey;
  phrase: string;
  light: string;
}

export function timeOfDayBucket(date: Date): TimeBucket {
  const h = date.getHours();
  if (h < 4) return { key: "night", phrase: "night", light: "quiet" };
  if (h < 7) return { key: "dawn", phrase: "dawn", light: "crisp" };
  if (h < 11) return { key: "morning", phrase: "morning", light: "bright" };
  if (h < 14) return { key: "midday", phrase: "midday", light: "bluebird" };
  if (h < 17) return { key: "afternoon", phrase: "afternoon", light: "warm" };
  if (h < 19) return { key: "goldenHour", phrase: "golden hour", light: "golden" };
  if (h < 21) return { key: "dusk", phrase: "dusk", light: "blue" };
  return { key: "night", phrase: "night", light: "quiet" };
}

type Season = "winter" | "spring" | "summer" | "fall";

export function seasonOf(date: Date): Season {
  const m = date.getMonth();
  if (m === 11 || m <= 1) return "winter";
  if (m <= 4) return "spring";
  if (m <= 7) return "summer";
  return "fall";
}

const KNOWN_SKY_ADJ: Record<string, string> = {
  Clear: "clear",
  "Part cloud": "partly cloudy",
};

export function conditionAdj(sky: string): string {
  return KNOWN_SKY_ADJ[sky] ?? sky.toLowerCase();
}

export function rareSpeciesFor(trailId: string): string | null {
  const match = SPECIES.find((sp) => sp.like === "Rare" && sp.trails.includes(trailId));
  return match?.name ?? null;
}

export function article(word: string): string {
  return /^[aeiou]/i.test(word) ? "an" : "a";
}

interface BuildGreetingInput {
  firstName: string;
  date: Date;
  sky: string;
  condition: string;
  trailId: string;
  trailName: string;
}

export function buildGreeting({ firstName, date, sky, condition, trailId, trailName }: BuildGreetingInput): string {
  const bucket = timeOfDayBucket(date);
  const seasonAdj = seasonOf(date);
  const skyAdj = conditionAdj(sky);
  const species = rareSpeciesFor(trailId);

  if (species) {
    return `This ${skyAdj} ${seasonAdj} ${bucket.phrase} is the perfect time to find ${article(species)} ${species} at ${trailName}!`;
  }

  const conditionTail = condition ? ` with ${condition.toLowerCase()} dirt` : "";
  switch (bucket.key) {
    case "goldenHour":
      return `${firstName}, what a ${seasonAdj} golden hour on ${trailName}!`;
    case "dawn":
      return `${firstName}, ${bucket.light} ${seasonAdj} dawn on ${trailName} — ${skyAdj} skies${conditionTail}.`;
    case "morning":
      return `${firstName}, ${skyAdj} ${seasonAdj} morning on ${trailName}${conditionTail}.`;
    case "midday":
      return `${firstName}, ${bucket.light} skies over ${trailName} this ${seasonAdj} midday.`;
    case "afternoon":
      return `${firstName}, a ${skyAdj} ${seasonAdj} afternoon on ${trailName}${conditionTail}.`;
    case "dusk":
      return `${firstName}, ${bucket.light} ${seasonAdj} dusk settling over ${trailName}.`;
    case "night":
    default:
      return `${firstName}, a ${seasonAdj} night near ${trailName} — plan tomorrow's ride.`;
  }
}
