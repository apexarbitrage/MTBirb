import { BottomNav } from "../components/BottomNav";
import { DifficultyMarker } from "../components/DifficultyMarker";
import { Photo } from "../components/Photo";
import { CheckBadge } from "../components/icons";
import { AVATAR_IMG } from "../data/trails";
import { PROFILE } from "../data/profile";
import common from "../styles/common.module.css";
import s from "./YouScreen.module.css";

const STATS = [
  { num: "47", label: "RIDES" },
  { num: "312", label: "MILES" },
  { num: "38.4k", label: "FT CLIMB" },
  { num: "84", label: "LIFE LIST", accent: true },
];

const SAVED = [
  { name: "Raptor Ridge", diff: "Advanced" as const, miles: "8.4 mi" },
  { name: "Owl Hollow", diff: "Intermediate" as const, miles: "5.5 mi" },
];

const WISHLIST = ["Red Fox", "American Dipper", "Harlequin Duck"];

export function YouScreen() {
  return (
    <div className={common.screen}>
      <div className={common.scrollArea}>
        <div className={s.profileRow}>
          <Photo
            src={AVATAR_IMG}
            alt={PROFILE.name}
            shape="circle"
            style={{ width: 64, height: 64, flex: "none" }}
            label="Photo"
          />
          <div>
            <div className={s.name}>{PROFILE.name}</div>
            <div className={s.sub}>
              {PROFILE.homeLocation} · since {PROFILE.memberSince}
            </div>
          </div>
        </div>

        <div className={s.statGroup}>
          {STATS.map((st) => (
            <div key={st.label} className={s.statTile}>
              <div className={s.statNum} style={st.accent ? { color: "var(--terracotta)" } : undefined}>
                {st.num}
              </div>
              <div className={s.statLabel}>{st.label}</div>
            </div>
          ))}
        </div>

        <div className={common.sectionLabel}>SAVED TRAILS</div>
        <div className={common.card} style={{ overflow: "hidden" }}>
          {SAVED.map((t) => (
            <div key={t.name} className={s.savedRow}>
              <DifficultyMarker diff={t.diff} size={10} />
              <div className={s.savedName}>{t.name}</div>
              <div className={common.monoMeta}>{t.miles}</div>
            </div>
          ))}
        </div>

        <div className={common.sectionLabel}>BIRD WISHLIST</div>
        <div className={s.wishlist}>
          {WISHLIST.map((w) => (
            <span key={w} className={s.wishPill}>
              {w}
            </span>
          ))}
        </div>

        <div className={common.sectionLabel}>CONNECTIONS</div>
        <div className={common.card} style={{ overflow: "hidden" }}>
          <div className={s.connRow}>
            <div className={s.connBadge} style={{ background: "var(--forest)", fontSize: 13 }}>
              TF
            </div>
            <div style={{ flex: 1 }}>
              <div className={s.connName}>Trailforks</div>
              <div className={s.connStatus}>Connected</div>
            </div>
            <CheckBadge />
          </div>
          <div className={s.connRow}>
            <div className={s.connBadge} style={{ background: "var(--garmin)", fontSize: 11 }}>
              GAR
            </div>
            <div style={{ flex: 1 }}>
              <div className={s.connName}>Garmin Connect</div>
              <div className={s.connStatus}>Connected · auto-export routes</div>
            </div>
            <CheckBadge />
          </div>
        </div>
      </div>

      <BottomNav active="you" />
    </div>
  );
}
