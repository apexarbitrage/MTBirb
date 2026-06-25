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

  // Targeting → Trails filter: rank trails by one species' live odds (null = no filter).
  speciesFilter: { code: string; name: string } | null;
  setSpeciesFilter: (species: { code: string; name: string } | null) => void;

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
  const [speciesFilter, setSpeciesFilter] = useState<{ code: string; name: string } | null>(null);
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
      pickTrailSort: (key) => {
        // Re-tap active criterion → invert direction; new criterion → reset to default.
        if (trailSort === key) {
          setTrailDir(trailDir === "asc" ? "desc" : "asc");
        } else {
          setTrailSort(key);
          setTrailDir(TRAIL_SORT_DEFAULT_DIR[key]);
        }
      },
      speciesFilter,
      setSpeciesFilter,
      detailTrailId,
      setDetailTrailId,
    }),
    [discoverSelectedId, discoverSort, trailSort, trailDir, speciesFilter, detailTrailId],
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
