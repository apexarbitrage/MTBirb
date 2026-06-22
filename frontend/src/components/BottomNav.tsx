import { useLocation, useNavigate } from "react-router-dom";
import { BinocularsIcon, BirdGlyph, BikeIcon, CompassIcon, FaceIcon } from "./icons";
import styles from "./BottomNav.module.css";

type TabKey = "discover" | "birbs" | "trails" | "trips" | "you";

const ACTIVE = "var(--nav-active)";
const INACTIVE = "var(--nav-inactive-icon)";

const TABS: {
  key: TabKey;
  label: string;
  path: string;
  render: (color: string) => React.ReactNode;
}[] = [
  { key: "discover", label: "Discover", path: "/", render: (c) => <BinocularsIcon color={c} /> },
  // Birbs glyph eye matches the sand backdrop so it reads as a cut-out.
  { key: "birbs", label: "Birbs", path: "/birbs", render: (c) => <BirdGlyph fill={c} eyeFill="var(--sand)" /> },
  { key: "trails", label: "Trails", path: "/trails", render: (c) => <BikeIcon color={c} /> },
  { key: "trips", label: "Trips", path: "/trips", render: (c) => <CompassIcon color={c} /> },
  { key: "you", label: "You", path: "/you", render: (c) => <FaceIcon color={c} /> },
];

export function BottomNav({ active }: { active: TabKey }) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <nav className={styles.nav}>
      {TABS.map((tab) => {
        const isActive = tab.key === active;
        const color = isActive ? ACTIVE : INACTIVE;
        return (
          <button
            key={tab.key}
            className={styles.item}
            aria-current={isActive ? "page" : undefined}
            onClick={() => {
              if (location.pathname !== tab.path) navigate(tab.path);
            }}
          >
            {tab.render(color)}
            <span className={isActive ? styles.labelActive : styles.label}>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

export type { TabKey };
