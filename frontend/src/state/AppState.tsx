import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import {
  TRAIL_SORT_DEFAULT_DIR,
  type TrailSortKey,
} from "../data/trails";

/*
 * Cross-screen app state, mirroring the prototype's logic-class state plus the
 * detail-trail selection that real navigation needs. Screen-local UI state
 * (presses, scroll) stays in the screens; anything that must survive a tab
 * switch lives here.
 */

type DiscoverSort = "wildlife" | "distance" | "effort";
type Dir = "asc" | "desc";

interface AppState {
  // Discover
  discoverSelectedId: string;
  setDiscoverSelectedId: (id: string) => void;
  discoverSort: DiscoverSort;
  cycleDiscoverSort: () => void;

  // Trails
  trailSort: TrailSortKey;
  trailDir: Dir;
  pickTrailSort: (key: TrailSortKey) => void;

  // Targeting → Trails filter
  trailFilter: string | null;
  setTrailFilter: (species: string | null) => void;
  targetSpecies: string;
  setTargetSpecies: (species: string) => void;

  // Trail Detail / Optimal time subject
  detailTrailId: string;
  setDetailTrailId: (id: string) => void;
}

const Ctx = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [discoverSelectedId, setDiscoverSelectedId] = useState("raptor");
  const [discoverSort, setDiscoverSort] = useState<DiscoverSort>("wildlife");
  const [trailSort, setTrailSort] = useState<TrailSortKey>("sighting");
  const [trailDir, setTrailDir] = useState<Dir>(TRAIL_SORT_DEFAULT_DIR.sighting);
  const [trailFilter, setTrailFilter] = useState<string | null>(null);
  const [targetSpecies, setTargetSpecies] = useState("Barred Owl");
  const [detailTrailId, setDetailTrailId] = useState("raptor");

  const value = useMemo<AppState>(
    () => ({
      discoverSelectedId,
      setDiscoverSelectedId,
      discoverSort,
      cycleDiscoverSort: () =>
        setDiscoverSort((s) =>
          s === "wildlife" ? "distance" : s === "distance" ? "effort" : "wildlife",
        ),
      trailSort,
      trailDir,
      pickTrailSort: (key) =>
        // Re-tap active criterion → invert direction; new criterion → reset to default.
        setTrailSort((prev) => {
          if (prev === key) {
            setTrailDir((d) => (d === "asc" ? "desc" : "asc"));
            return prev;
          }
          setTrailDir(TRAIL_SORT_DEFAULT_DIR[key]);
          return key;
        }),
      trailFilter,
      setTrailFilter,
      targetSpecies,
      setTargetSpecies,
      detailTrailId,
      setDetailTrailId,
    }),
    [discoverSelectedId, discoverSort, trailSort, trailDir, trailFilter, targetSpecies, detailTrailId],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAppState(): AppState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAppState must be used within AppStateProvider");
  return ctx;
}

export type { DiscoverSort };
