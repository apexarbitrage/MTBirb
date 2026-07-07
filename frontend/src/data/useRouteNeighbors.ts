/*
 * The route builder's data source: given the chain built so far, GET /api/trail-routes/candidates
 * returns the members (with lines), every lined trail within the chain tolerance (the tappable
 * candidates), and kicks a bounded background line-enrichment for nearby un-lined trails. While
 * `enrichingCount` > 0 we poll (same 2.5s x budget pattern as useCatalogDetail) so newly-lined
 * trails pop into the candidate set; the budget resets whenever the membership changes.
 */

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";
import type { RouteTrailLite } from "./useTrailRoutes";

interface CandidatesResponse {
  members: RouteTrailLite[];
  candidates: RouteTrailLite[];
  enrichingCount: number;
}

const POLL_MS = 2500;
const POLL_BUDGET = 8;

export function useRouteNeighbors(memberIds: string[]) {
  const key = memberIds.join("|");
  const [state, setState] = useState<{
    key: string;
    members: RouteTrailLite[];
    candidates: RouteTrailLite[];
    enriching: boolean;
    error: string | null;
  } | null>(null);

  useEffect(() => {
    if (!key) return;
    const c = new AbortController();
    let attempts = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const qs = memberIds.map((i) => `ids=${encodeURIComponent(i)}`).join("&");

    const load = () => {
      apiGet<CandidatesResponse>(`/trail-routes/candidates?${qs}`, c.signal)
        .then((d) => {
          if (c.signal.aborted) return;
          // Keep polling only while lines are still landing and there's budget left; then drop
          // `enriching` so the "finding trails" pulse doesn't spin forever on un-lineable trails.
          const stillTrying = d.enrichingCount > 0 && attempts < POLL_BUDGET;
          setState({ key, members: d.members, candidates: d.candidates, enriching: stillTrying, error: null });
          if (stillTrying) {
            attempts += 1;
            timer = setTimeout(load, POLL_MS);
          }
        })
        .catch((e) => {
          if (!c.signal.aborted)
            setState({
              key,
              members: [],
              candidates: [],
              enriching: false,
              error: e instanceof Error ? e.message : "Failed to load connecting trails",
            });
        });
    };
    load();
    return () => {
      c.abort();
      if (timer) clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const s = state && state.key === key ? state : null;
  return {
    members: s?.members ?? [],
    candidates: s?.candidates ?? [],
    enriching: s?.enriching ?? false,
    loading: s === null,
    error: s?.error ?? null,
  };
}
