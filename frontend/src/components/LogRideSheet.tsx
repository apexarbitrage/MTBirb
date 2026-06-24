import { useMemo, useState } from "react";
import { logRide, type TripBird } from "../data/useTrips";

interface SpeciesOption {
  speciesCode: string | null;
  commonName: string;
}

interface Props {
  trail: { id: string; name: string; difficulty: string | null; miles: number | null };
  /** Candidate species to check off (the trail's likely/notable/recent eBird birds). */
  options: SpeciesOption[];
  onClose: () => void;
  onLogged: () => void;
}

const today = () => new Date().toISOString().slice(0, 10);

/** A bottom sheet to log a ride: pick a date, check off the birds you saw, add your own. */
export function LogRideSheet({ trail, options, onClose, onLogged }: Props) {
  // De-dupe the candidate species by name (likely/notable are name-only; recent carry a code).
  const candidates = useMemo(() => {
    const byName = new Map<string, SpeciesOption>();
    for (const o of options) {
      if (!o.commonName) continue;
      const existing = byName.get(o.commonName);
      if (!existing || (!existing.speciesCode && o.speciesCode)) byName.set(o.commonName, o);
    }
    return [...byName.values()];
  }, [options]);

  const [date, setDate] = useState(today);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [extra, setExtra] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const toggle = (name: string) =>
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });

  const addExtra = () => {
    const name = draft.trim();
    if (name && !extra.includes(name) && !candidates.some((c) => c.commonName === name)) {
      setExtra((e) => [...e, name]);
    }
    setDraft("");
  };

  const submit = async () => {
    setSaving(true);
    setErr(null);
    const birds: TripBird[] = [
      ...candidates
        .filter((c) => checked.has(c.commonName))
        .map((c) => ({ speciesCode: c.speciesCode, commonName: c.commonName })),
      ...extra.map((name) => ({ speciesCode: null, commonName: name })),
    ];
    try {
      await logRide({
        trailExternalId: trail.id,
        trailName: trail.name,
        difficulty: trail.difficulty,
        miles: trail.miles,
        riddenOn: date,
        birds,
      });
      onLogged();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Couldn't log ride");
      setSaving(false);
    }
  };

  const count = checked.size + extra.length;

  return (
    <div onClick={onClose} style={overlay}>
      <div onClick={(e) => e.stopPropagation()} style={sheet}>
        <div style={handle} />
        <div style={{ fontWeight: 800, fontSize: 18, color: "var(--ink)" }}>Log this ride</div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)", marginBottom: 14 }}>
          {trail.name}
        </div>

        <label style={fieldLabel}>DATE</label>
        <input type="date" value={date} max={today()} onChange={(e) => setDate(e.target.value)} style={input} />

        <label style={{ ...fieldLabel, marginTop: 16 }}>BIRDS YOU SAW</label>
        <div style={chipWrap}>
          {candidates.map((c) => {
            const on = checked.has(c.commonName);
            return (
              <button key={c.commonName} onClick={() => toggle(c.commonName)} style={chip(on)}>
                {on ? "✓ " : ""}
                {c.commonName}
              </button>
            );
          })}
          {extra.map((name) => (
            <span key={name} style={chip(true)}>
              ✓ {name}
            </span>
          ))}
          {candidates.length === 0 && extra.length === 0 && (
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
              No eBird species cached here yet — add your own below.
            </span>
          )}
        </div>

        <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addExtra()}
            placeholder="Add another species…"
            style={{ ...input, flex: 1 }}
          />
          <button onClick={addExtra} style={addBtn}>
            Add
          </button>
        </div>

        {err && <div style={{ color: "var(--terracotta)", fontSize: 13, marginTop: 12 }}>{err}</div>}

        <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
          <button onClick={onClose} style={cancelBtn}>
            Cancel
          </button>
          <button onClick={submit} disabled={saving} style={saveBtn(saving)}>
            {saving ? "Saving…" : `Log ride${count ? ` · ${count} bird${count > 1 ? "s" : ""}` : ""}`}
          </button>
        </div>
      </div>
    </div>
  );
}

const overlay: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(33,48,42,0.45)",
  display: "flex",
  alignItems: "flex-end",
  zIndex: 50,
};
const sheet: React.CSSProperties = {
  width: "100%",
  maxHeight: "82vh",
  overflowY: "auto",
  background: "var(--sand)",
  borderRadius: "20px 20px 0 0",
  padding: "12px 18px 24px",
};
const handle: React.CSSProperties = {
  width: 38,
  height: 4,
  borderRadius: 2,
  background: "var(--card-tile-divider)",
  margin: "2px auto 14px",
};
const fieldLabel: React.CSSProperties = {
  display: "block",
  fontFamily: "var(--font-mono)",
  fontSize: 10,
  letterSpacing: 0.5,
  color: "var(--text-muted)",
  marginBottom: 6,
};
const input: React.CSSProperties = {
  border: "1px solid var(--card-tile-divider)",
  borderRadius: 10,
  padding: "9px 11px",
  fontSize: 14,
  background: "var(--white)",
  color: "var(--ink)",
};
const chipWrap: React.CSSProperties = { display: "flex", flexWrap: "wrap", gap: 7 };
const chip = (on: boolean): React.CSSProperties => ({
  fontSize: 12,
  fontWeight: 600,
  padding: "6px 11px",
  borderRadius: 9,
  border: "none",
  cursor: "pointer",
  background: on ? "var(--forest)" : "var(--sand-bird-chip)",
  color: on ? "var(--sand)" : "var(--tan-accent)",
});
const addBtn: React.CSSProperties = {
  border: "none",
  borderRadius: 10,
  padding: "0 16px",
  fontWeight: 700,
  background: "var(--sage)",
  color: "#fff",
  cursor: "pointer",
};
const cancelBtn: React.CSSProperties = {
  flex: "none",
  padding: "12px 18px",
  borderRadius: 12,
  border: "1px solid var(--card-tile-divider)",
  background: "transparent",
  color: "var(--text-muted)",
  fontWeight: 700,
  cursor: "pointer",
};
const saveBtn = (saving: boolean): React.CSSProperties => ({
  flex: 1,
  padding: "12px 18px",
  borderRadius: 12,
  border: "none",
  background: "var(--terracotta)",
  color: "#fff",
  fontWeight: 800,
  cursor: saving ? "default" : "pointer",
  opacity: saving ? 0.7 : 1,
});
