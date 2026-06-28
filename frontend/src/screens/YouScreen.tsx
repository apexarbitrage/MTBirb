import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BottomNav } from "../components/BottomNav";
import { DifficultyMarker } from "../components/DifficultyMarker";
import { ProfileSheet } from "../components/ProfileSheet";
import { normalizeDifficulty } from "../data/trails";
import { useTrips } from "../data/useTrips";
import { useAppState } from "../state/AppState";
import { useProfile, type WishlistBird } from "../state/ProfileContext";
import common from "../styles/common.module.css";
import s from "./YouScreen.module.css";

const emptyNote: React.CSSProperties = {
  fontSize: 13,
  color: "var(--text-muted)",
  padding: "2px 2px 4px",
};

export function YouScreen() {
  const navigate = useNavigate();
  const { profile, favorites, wishlist, toggleWishlist } = useProfile();
  const { trips, stats } = useTrips();
  const { setSpeciesFilter, setDetailTrailId } = useAppState();
  const [editing, setEditing] = useState(false);

  const miles = useMemo(
    () => Math.round(trips.reduce((sum, t) => sum + (t.miles ?? 0), 0)),
    [trips],
  );

  // Unique birds the user has logged across all rides, most-logged first.
  const loggedBirds = useMemo(() => {
    const byKey = new Map<string, { name: string; count: number }>();
    for (const t of trips) {
      for (const b of t.birds) {
        const key = b.speciesCode ?? b.commonName.toLowerCase().trim();
        const entry = byKey.get(key);
        if (entry) entry.count += 1;
        else byKey.set(key, { name: b.commonName, count: 1 });
      }
    }
    return [...byKey.values()].sort((a, b) => b.count - a.count);
  }, [trips]);

  const statTiles = [
    { num: String(stats.rides), label: "RIDES" },
    { num: String(miles), label: "MILES" },
    { num: String(stats.birds), label: "BIRDS" },
    { num: String(stats.lifeList), label: "LIFE LIST", accent: true },
  ];

  const openTrail = (id: string) => {
    setDetailTrailId(id);
    navigate("/trail");
  };
  const findForBird = (b: WishlistBird) => {
    setSpeciesFilter({ code: b.code, name: b.name });
    navigate("/trails");
  };

  return (
    <div className={common.screen}>
      <div className={common.scrollArea}>
        <button
          className={s.profileRow}
          onClick={() => setEditing(true)}
          style={{ background: "none", border: "none", padding: 0, width: "100%", textAlign: "left", cursor: "pointer" }}
        >
          {profile?.photo ? (
            <img src={profile.photo} alt="" style={avatar} />
          ) : (
            <div style={avatarFallback}>{(profile?.firstName?.[0] ?? "?").toUpperCase()}</div>
          )}
          <div>
            <div className={s.name}>{profile?.name ?? "Set up your profile"}</div>
            <div className={s.sub}>
              {stats.rides} ride{stats.rides === 1 ? "" : "s"} · {stats.lifeList} life birds · tap to edit
            </div>
          </div>
        </button>

        <div className={s.statGroup}>
          {statTiles.map((st) => (
            <div key={st.label} className={s.statTile}>
              <div className={s.statNum} style={st.accent ? { color: "var(--terracotta)" } : undefined}>
                {st.num}
              </div>
              <div className={s.statLabel}>{st.label}</div>
            </div>
          ))}
        </div>

        <div className={common.sectionLabel}>FAVORITE TRAILS</div>
        {favorites.length === 0 ? (
          <div style={emptyNote}>Tap the ♥ on a trail's page to save it here.</div>
        ) : (
          <div className={common.card} style={{ overflow: "hidden" }}>
            {favorites.map((t) => {
              const diff = normalizeDifficulty(t.difficulty);
              return (
                <button
                  key={t.id}
                  className={s.savedRow}
                  onClick={() => openTrail(t.id)}
                  style={{ background: "none", border: "none", width: "100%", textAlign: "left", cursor: "pointer" }}
                >
                  {diff && <DifficultyMarker diff={diff} size={10} />}
                  <div className={s.savedName}>{t.name}</div>
                  <div className={common.monoMeta}>{t.miles != null ? `${t.miles} mi` : ""}</div>
                </button>
              );
            })}
          </div>
        )}

        <div className={common.sectionLabel}>BIRD WISHLIST</div>
        {wishlist.length === 0 ? (
          <div style={emptyNote}>Tap the ♥ on the Birbs tab to add a species you want to see.</div>
        ) : (
          <div className={s.wishlist}>
            {wishlist.map((w) => (
              <span key={w.code} className={s.wishPill} style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
                <button
                  onClick={() => findForBird(w)}
                  style={{ background: "none", border: "none", padding: 0, font: "inherit", color: "inherit", cursor: "pointer" }}
                >
                  {w.name}
                </button>
                <button
                  onClick={() => toggleWishlist(w)}
                  aria-label={`Remove ${w.name}`}
                  style={{ background: "none", border: "none", padding: 0, color: "var(--text-muted)", cursor: "pointer", fontSize: 13, lineHeight: 1 }}
                >
                  ✕
                </button>
              </span>
            ))}
          </div>
        )}

        <div className={common.sectionLabel}>BIRDS LOGGED</div>
        {loggedBirds.length === 0 ? (
          <div style={emptyNote}>Birds you log on a ride get catalogued here.</div>
        ) : (
          <div className={s.wishlist}>
            {loggedBirds.map((b) => (
              <span key={b.name} className={s.wishPill}>
                {b.name}
                {b.count > 1 ? ` ×${b.count}` : ""}
              </span>
            ))}
          </div>
        )}
      </div>

      <BottomNav active="you" />
      {editing && <ProfileSheet onClose={() => setEditing(false)} />}
    </div>
  );
}

const avatar: React.CSSProperties = {
  width: 64,
  height: 64,
  borderRadius: "50%",
  objectFit: "cover",
  flex: "none",
  border: "2px solid var(--white)",
};
const avatarFallback: React.CSSProperties = {
  width: 64,
  height: 64,
  borderRadius: "50%",
  flex: "none",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "var(--sage-tint-strong)",
  color: "var(--sage-text-deep)",
  fontSize: 26,
  fontWeight: 800,
};
