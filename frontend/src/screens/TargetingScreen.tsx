import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { BottomNav } from "../components/BottomNav";
import { Photo } from "../components/Photo";
import { SearchIcon } from "../components/icons";
import {
  SPECIES,
  SPECIES_NEARBY_COUNT,
  likelihoodColor,
  speciesByName,
} from "../data/trails";
import { useAppState } from "../state/AppState";
import common from "../styles/common.module.css";
import s from "./TargetingScreen.module.css";

const SEGMENTS = ["A species", "Most wildlife", "Rarest"];

export function TargetingScreen() {
  const navigate = useNavigate();
  const { targetSpecies, setTargetSpecies, setTrailFilter } = useAppState();
  // Segment selection gives tactile feedback; "A species" is the built mode.
  const [segment, setSegment] = useState(0);

  const targetEntry = speciesByName(targetSpecies) ?? SPECIES[0];
  const applyLabel = `Show ${targetEntry.trails.length} trails for ${targetEntry.name}`;

  const apply = () => {
    setTrailFilter(targetEntry.name);
    navigate("/trails");
  };

  return (
    <div className={common.screen}>
      <div className={s.scroll}>
        <div className={s.bigTitle}>
          What do you want
          <br />
          to see?
        </div>
        <div className={s.subtitle}>We'll rank trails by your odds, calibrated from eBird.</div>

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

        <div className={s.search}>
          <SearchIcon innerFill="#fff" />
          <span className={s.searchPlaceholder}>Search {SPECIES_NEARBY_COUNT} species nearby</span>
        </div>

        <div className={common.sectionLabel}>LIKELY NEAR YOU THIS WEEK</div>

        <div className={s.cards}>
          {SPECIES.map((sp) => {
            const selected = sp.name === targetEntry.name;
            return (
              <button
                key={sp.name}
                className={`${s.card} ${selected ? s.cardActive : s.cardIdle}`}
                onClick={() => setTargetSpecies(sp.name)}
              >
                <Photo
                  src={sp.img}
                  alt={sp.name}
                  shape="rounded"
                  radius={12}
                  style={{ width: 46, height: 46, flex: "none" }}
                  label="Photo"
                />
                <div style={{ flex: 1 }}>
                  <div className={s.spName} style={{ color: selected ? "#fff" : "var(--ink)" }}>
                    {sp.name}
                  </div>
                  <div
                    className={s.spSub}
                    style={{ color: selected ? "var(--sage-on-dark)" : "var(--text-muted)" }}
                  >
                    {sp.sci} · {sp.trails.length} trails
                  </div>
                </div>
                <div className={s.like} style={{ color: likelihoodColor(sp.like) }}>
                  {sp.like}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className={s.applyBar}>
        <button className={s.applyBtn} onClick={apply}>
          {applyLabel}
        </button>
      </div>

      <BottomNav active="birbs" />
    </div>
  );
}
