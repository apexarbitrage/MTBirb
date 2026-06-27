import { useState, type CSSProperties } from "react";
import { makeThumb } from "../data/photo";
import { useProfile } from "../state/ProfileContext";

/*
 * Bottom sheet to create (first load) or edit the rider profile: a name + an optional photo
 * (downscaled to a thumbnail, kept in localStorage). In onboarding mode it can't be dismissed
 * without saving a name. Mirrors the LogRideSheet sheet styling.
 */
export function ProfileSheet({ onClose, onboarding = false }: { onClose: () => void; onboarding?: boolean }) {
  const { profile, saveProfile } = useProfile();
  const [name, setName] = useState(profile?.name ?? "");
  const [photo, setPhoto] = useState<string | null>(profile?.photo ?? null);
  const [reading, setReading] = useState(false);

  const pick = async (files: FileList | null) => {
    const file = files?.[0];
    if (!file) return;
    setReading(true);
    try {
      setPhoto(await makeThumb(file));
    } finally {
      setReading(false);
    }
  };

  const canSave = name.trim().length > 0;
  const submit = () => {
    if (!canSave) return;
    saveProfile(name, photo);
    onClose();
  };

  return (
    <div onClick={onboarding ? undefined : onClose} style={overlay}>
      <div onClick={(e) => e.stopPropagation()} style={sheet}>
        <div style={handle} />
        <div style={{ fontWeight: 800, fontSize: 18, color: "var(--ink)" }}>
          {onboarding ? "Welcome to MTBirb" : "Edit profile"}
        </div>
        <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 18 }}>
          {onboarding ? "Set up your rider profile to get started." : "Update your name and photo."}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 18 }}>
          <label style={{ cursor: "pointer", flex: "none" }}>
            {photo ? (
              <img src={photo} alt="" style={avatar} />
            ) : (
              <div style={avatarFallback}>{(name.trim()[0] ?? "🚵").toUpperCase()}</div>
            )}
            <input type="file" accept="image/*" onChange={(e) => pick(e.target.files)} style={{ display: "none" }} />
          </label>
          <div style={{ fontSize: 13, color: "var(--sage-text-deep)", fontWeight: 600 }}>
            {reading ? "Reading…" : "Tap to add a photo"}
          </div>
        </div>

        <label style={fieldLabel}>YOUR NAME</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="Your name"
          style={{ ...input, width: "100%", boxSizing: "border-box" }}
          autoFocus
        />

        <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
          {!onboarding && (
            <button onClick={onClose} style={cancelBtn}>
              Cancel
            </button>
          )}
          <button onClick={submit} disabled={!canSave} style={saveBtn(!canSave)}>
            {onboarding ? "Get started" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

const overlay: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(33,48,42,0.45)",
  display: "flex",
  alignItems: "flex-end",
  zIndex: 60,
};
const sheet: CSSProperties = {
  width: "100%",
  background: "var(--sand)",
  borderRadius: "20px 20px 0 0",
  padding: "12px 18px 26px",
};
const handle: CSSProperties = {
  width: 38,
  height: 4,
  borderRadius: 2,
  background: "var(--card-tile-divider)",
  margin: "2px auto 14px",
};
const fieldLabel: CSSProperties = {
  display: "block",
  fontFamily: "var(--font-mono)",
  fontSize: 10,
  letterSpacing: 0.5,
  color: "var(--text-muted)",
  marginBottom: 6,
};
const input: CSSProperties = {
  border: "1px solid var(--card-tile-divider)",
  borderRadius: 10,
  padding: "10px 11px",
  fontSize: 15,
  background: "var(--white)",
  color: "var(--ink)",
};
const avatar: CSSProperties = {
  width: 64,
  height: 64,
  borderRadius: "50%",
  objectFit: "cover",
  display: "block",
  border: "2px solid var(--white)",
};
const avatarFallback: CSSProperties = {
  width: 64,
  height: 64,
  borderRadius: "50%",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "var(--sage-tint-strong)",
  color: "var(--sage-text-deep)",
  fontSize: 26,
  fontWeight: 800,
};
const cancelBtn: CSSProperties = {
  flex: "none",
  padding: "12px 18px",
  borderRadius: 12,
  border: "1px solid var(--card-tile-divider)",
  background: "transparent",
  color: "var(--text-muted)",
  fontWeight: 700,
  cursor: "pointer",
};
const saveBtn = (disabled: boolean): CSSProperties => ({
  flex: 1,
  padding: "12px 18px",
  borderRadius: 12,
  border: "none",
  background: "var(--terracotta)",
  color: "#fff",
  fontWeight: 800,
  cursor: disabled ? "default" : "pointer",
  opacity: disabled ? 0.5 : 1,
});
