import { useState } from "react";
import { BackButton } from "../components/BackButton";
import { useCatalogTrails } from "../data/useCatalogTrails";
import common from "../styles/common.module.css";
import s from "./CatalogScreen.module.css";

/*
 * Browses the real TrailAPI catalog by location. Northern California is seeded, so those
 * presets resolve instantly; others (e.g. Bend) are fetched and cached on first view.
 */
const PRESETS = [
  { label: "Bay Area", lat: 37.55, lon: -122.31 },
  { label: "Tahoe", lat: 39.1, lon: -120.03 },
  { label: "Mt. Shasta", lat: 41.31, lon: -122.31 },
  { label: "Bend, OR", lat: 44.06, lon: -121.31 },
];

export function CatalogScreen() {
  const [sel, setSel] = useState(0);
  const place = PRESETS[sel];
  const { trails, loading, error, fetchedNow } = useCatalogTrails(place.lat, place.lon);

  return (
    <div className={common.screen}>
      <div className={common.scrollArea}>
        <div className={s.backRow}>
          <BackButton bg="rgba(45,59,45,0.1)" stroke="var(--forest)" blur={false} />
        </div>
        <div className={common.eyebrow}>TrailAPI catalog</div>
        <div className={common.title}>Browse trails</div>

        <div className={s.chipRow}>
          {PRESETS.map((p, i) => (
            <button
              key={p.label}
              className={`${s.chip} ${i === sel ? s.chipActive : s.chipIdle}`}
              onClick={() => setSel(i)}
            >
              {p.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className={s.note}>Loading trails near {place.label}…</div>
        ) : error ? (
          <div className={s.note}>Couldn't load trails. {error}</div>
        ) : trails.length === 0 ? (
          <div className={s.note}>No trails cached near {place.label} yet.</div>
        ) : (
          <>
            <div className={s.count}>
              {trails.length} trails near {place.label}
              {fetchedNow > 0 ? ` · fetched ${fetchedNow} new` : ""}
            </div>
            <div className={s.list}>
              {trails.map((t) => (
                <a
                  key={t.id}
                  className={s.card}
                  href={t.url ?? undefined}
                  target="_blank"
                  rel="noreferrer"
                >
                  <div className={s.name}>{t.name}</div>
                  <div className={s.meta}>
                    {[t.difficulty, t.lengthMi != null ? `${t.lengthMi} mi` : null, t.city]
                      .filter(Boolean)
                      .join(" · ")}
                  </div>
                </a>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
