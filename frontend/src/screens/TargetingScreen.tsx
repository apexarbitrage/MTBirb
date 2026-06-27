import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { BottomNav } from "../components/BottomNav";
import { BirdGlyph, HeartIcon } from "../components/icons";
import { CenterMessage } from "../components/CenterMessage";
import { useTrails } from "../data/TrailsProvider";
import { useNearbySpecies, type NearbySpeciesItem } from "../data/useNearbySpecies";
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

  const usesPicker = segment !== 1; // "Most wildlife" ranks every trail, no species needed
  const { species } = useNearbySpecies(location.lat, location.lon, segment === 2);

  const active =
    selected?.seg === segment ? selected.item : usesPicker ? species?.[0] ?? null : null;

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
            <div className={common.sectionLabel} style={{ marginTop: 20 }}>
              {segment === 2 ? "NOTABLE NEAR YOU" : "LIKELY NEAR YOU"} · {location.label}
            </div>
            {species === null ? (
              <CenterMessage title="Loading species…" />
            ) : species.length === 0 ? (
              <CenterMessage title="No species reported nearby" detail="Try the other modes." />
            ) : (
              <div className={s.cards}>
                {species.map((sp) => {
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
                        <BirdGlyph fill={likelihoodColor(sp.like)} eyeFill="#fff" size={20} />
                      </div>
                      <div style={{ flex: 1 }}>
                        <div className={s.spName} style={{ color: isSel ? "#fff" : "var(--ink)" }}>
                          {sp.common_name}
                        </div>
                        <div
                          className={s.spSub}
                          style={{ color: isSel ? "var(--sage-on-dark)" : "var(--text-muted)" }}
                        >
                          {sp.notable ? "Notable" : "Reported"} · {sp.likelihood}% odds
                        </div>
                      </div>
                      <div className={s.like} style={{ color: likelihoodColor(sp.like) }}>
                        {sp.like}
                      </div>
                    </button>
                  );
                })}
              </div>
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
