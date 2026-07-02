import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { BottomNav } from "../components/BottomNav";
import { BirdGlyph, HeartIcon } from "../components/icons";
import { CenterMessage } from "../components/CenterMessage";
import { SearchField } from "../components/SearchField";
import { useTrails } from "../data/TrailsProvider";
import { useNearbySpecies, type NearbySpeciesItem } from "../data/useNearbySpecies";
import { useSpeciesSearch } from "../data/useSpeciesSearch";
import { likelihoodColor } from "../data/trails";
import { useAppState } from "../state/AppState";
import { useProfile } from "../state/ProfileContext";
import common from "../styles/common.module.css";
import s from "./TargetingScreen.module.css";

const SEGMENTS = ["A species", "Most wildlife", "Rarest"] as const;

export function TargetingScreen() {
  const navigate = useNavigate();
  const { location } = useTrails();
  const { setSpeciesFilter } = useAppState();
  const { isWishlisted, toggleWishlist } = useProfile();
  const [segment, setSegment] = useState(0);
  // Selection is tagged with its segment so switching modes falls back to that mode's top pick.
  const [selected, setSelected] = useState<{ seg: number; item: NearbySpeciesItem } | null>(null);
  const [query, setQuery] = useState("");

  const usesPicker = segment !== 1; // "Most wildlife" ranks every trail, no species needed
  const { species } = useNearbySpecies(location.lat, location.lon, segment === 2);
  const { results: taxonomyResults } = useSpeciesSearch(usesPicker ? query : "");

  // Filter the nearby-species picker by name (client-side over what's reported near you).
  const q = query.trim().toLowerCase();
  const filtered = q
    ? (species ?? []).filter((sp) => sp.common_name.toLowerCase().includes(q))
    : (species ?? []);

  // Species the full eBird taxonomy turns up that aren't already in the nearby list - lets a
  // rider target something with zero current local reports (odds will read as unranked).
  const localCodes = new Set(filtered.map((sp) => sp.species_code));
  const extra: NearbySpeciesItem[] = q
    ? taxonomyResults
        .filter((r) => !localCodes.has(r.species_code))
        .map((r) => ({
          species_code: r.species_code,
          common_name: r.common_name,
          last_observed: null,
          notable: false,
          observations: 0,
          likelihood: 0,
          like: "Med",
        }))
    : [];

  const active =
    selected?.seg === segment
      ? selected.item
      : usesPicker
        ? filtered[0] ?? extra[0] ?? null
        : null;

  // `reportedNearby` switches between the normal odds badge and a plain "not reported" row for
  // taxonomy-only matches (no nearby sightings to grade them by).
  const renderSpeciesCard = (sp: NearbySpeciesItem, reportedNearby: boolean) => {
    const isSel = (active?.species_code ?? "") === sp.species_code;
    return (
      <button
        key={sp.species_code}
        className={`${s.card} ${isSel ? s.cardActive : s.cardIdle}`}
        onClick={() => setSelected({ seg: segment, item: sp })}
      >
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: 12,
            flex: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: isSel ? "rgba(255,255,255,0.15)" : "var(--sage-tint-strong)",
          }}
        >
          <BirdGlyph fill={reportedNearby ? likelihoodColor(sp.like) : "var(--text-muted)"} eyeFill="#fff" size={20} />
        </div>
        <div style={{ flex: 1 }}>
          <div className={s.spName} style={{ color: isSel ? "#fff" : "var(--ink)" }}>
            {sp.common_name}
          </div>
          <div className={s.spSub} style={{ color: isSel ? "var(--sage-on-dark)" : "var(--text-muted)" }}>
            {reportedNearby ? `${sp.notable ? "Notable" : "Reported"} · ${sp.likelihood}% odds` : "Not reported nearby"}
          </div>
        </div>
        {reportedNearby && (
          <div className={s.like} style={{ color: likelihoodColor(sp.like) }}>
            {sp.like}
          </div>
        )}
      </button>
    );
  };

  const apply = () => {
    setSpeciesFilter(usesPicker && active ? { code: active.species_code, name: active.common_name } : null);
    navigate("/trails");
  };

  const applyLabel = !usesPicker
    ? "Show the most-active trails"
    : active
      ? `Best trails for ${active.common_name}`
      : "Pick a species";

  return (
    <div className={common.screen}>
      <div className={s.scroll}>
        <div className={s.bigTitle}>
          What do you want
          <br />
          to see?
        </div>
        <div className={s.subtitle}>We'll rank trails near you by your odds, from eBird.</div>

        <div className={s.segmented}>
          {SEGMENTS.map((label, i) => (
            <button
              key={label}
              className={`${s.segment} ${i === segment ? s.segmentActive : ""}`}
              onClick={() => setSegment(i)}
            >
              {label}
            </button>
          ))}
        </div>

        {!usesPicker ? (
          <div className={s.subtitle} style={{ marginTop: 18 }}>
            We'll rank every trail near {location.label} by overall wildlife activity — the recency-
            and season-weighted score across all reported species.
          </div>
        ) : (
          <>
            <div style={{ marginTop: 16 }}>
              <SearchField value={query} onChange={setQuery} placeholder="Search species by name" />
            </div>
            <div className={common.sectionLabel} style={{ marginTop: 20 }}>
              {segment === 2 ? "NOTABLE NEAR YOU" : "LIKELY NEAR YOU"} · {location.label}
            </div>
            {species === null ? (
              <CenterMessage title="Loading species…" />
            ) : filtered.length === 0 && extra.length === 0 ? (
              q ? (
                <CenterMessage title={`No species match “${query.trim()}”`} detail="Try a different name or mode." />
              ) : (
                <CenterMessage title="No species reported nearby" detail="Try the other modes." />
              )
            ) : (
              <>
                {filtered.length > 0 && (
                  <div className={s.cards}>{filtered.map((sp) => renderSpeciesCard(sp, true))}</div>
                )}
                {extra.length > 0 && (
                  <>
                    <div className={common.sectionLabel} style={{ marginTop: 20 }}>
                      ALL SPECIES MATCHING “{query.trim()}”
                    </div>
                    <div className={s.cards}>{extra.map((sp) => renderSpeciesCard(sp, false))}</div>
                  </>
                )}
              </>
            )}
          </>
        )}
      </div>

      <div className={s.applyBar} style={{ display: "flex", gap: 10 }}>
        {usesPicker && active && (
          <button
            onClick={() => toggleWishlist({ code: active.species_code, name: active.common_name })}
            aria-label={isWishlisted(active.species_code) ? "Remove from wishlist" : "Add to wishlist"}
            style={{
              flex: "none",
              width: 52,
              height: 52,
              borderRadius: "var(--radius-card)",
              border: "1.5px solid var(--terracotta)",
              background: isWishlisted(active.species_code) ? "var(--terracotta)" : "var(--white)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
            }}
          >
            <HeartIcon
              color={isWishlisted(active.species_code) ? "#fff" : "var(--terracotta)"}
              filled={isWishlisted(active.species_code)}
              size={22}
            />
          </button>
        )}
        <button className={s.applyBtn} onClick={apply} disabled={usesPicker && !active}>
          {applyLabel}
        </button>
      </div>

      <BottomNav active="birbs" />
    </div>
  );
}
