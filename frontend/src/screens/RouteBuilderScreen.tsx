import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { BackButton } from "../components/BackButton";
import { useRouteNeighbors } from "../data/useRouteNeighbors";
import { createTrailRoute } from "../data/useTrailRoutes";
import { useAppState } from "../state/AppState";
import s from "./RouteBuilderScreen.module.css";

/*
 * The route builder: an interactive map seeded with the current trail, showing every trail whose
 * OSM line touches the chain built so far (dashed sage) - tap one to add it, and the candidate set
 * expands outward from the new chain. Solid terracotta is the route so far. Candidates only exist
 * where OSM lines are cached, so the backend background-enriches nearby un-lined trails and we
 * poll while that warms (the "finding connecting trails" pulse). Save posts the ordered chain;
 * the server re-validates connectivity with the same predicate that offered the candidates.
 */

const TERRACOTTA = "#c2703d";
const SAGE = "#a9bd77";
const MAX_MEMBERS = 20;

export function RouteBuilderScreen() {
  const navigate = useNavigate();
  const { detailTrailId, setDetailRouteId, setTripsSegment } = useAppState();
  // Seed once from the trail this screen was opened from; membership then evolves locally.
  const [memberIds, setMemberIds] = useState<string[]>(() => (detailTrailId ? [detailTrailId] : []));
  const { members, candidates, enriching, loading, error } = useRouteNeighbors(memberIds);
  const [showSave, setShowSave] = useState(false);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveErr, setSaveErr] = useState<string | null>(null);

  const mapEl = useRef<HTMLDivElement>(null);
  const mapObj = useRef<L.Map | null>(null);
  const layers = useRef<L.LayerGroup | null>(null);
  const fittedKey = useRef<string | null>(null);

  const addMember = (id: string) =>
    setMemberIds((prev) => (prev.includes(id) || prev.length >= MAX_MEMBERS ? prev : [...prev, id]));
  const undo = () => setMemberIds((prev) => (prev.length > 1 ? prev.slice(0, -1) : prev));

  // Create the interactive map once (same proxied TomTom sat+hybrid stack as TrailMap, but with
  // default gestures - this screen is all about touching the map). Attribution stays on.
  useEffect(() => {
    if (!mapEl.current || mapObj.current) return;
    const map = L.map(mapEl.current, { zoomControl: false, attributionControl: true }).setView(
      [37.5, -122.3],
      11,
    );
    map.attributionControl.setPrefix(false);
    const credit =
      '© TomTom · Trail data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors';
    L.tileLayer("/api/map/tile/{z}/{x}/{y}?layer=sat", { minZoom: 3, maxZoom: 18, attribution: credit }).addTo(map);
    L.tileLayer("/api/map/tile/{z}/{x}/{y}?layer=hybrid", { minZoom: 3, maxZoom: 18 }).addTo(map);
    mapObj.current = map;
    requestAnimationFrame(() => map.invalidateSize());
    return () => {
      map.remove();
      mapObj.current = null;
    };
  }, []);

  // (Re)draw the chain + candidates whenever the data changes. Candidates get a fat transparent
  // "hit" polyline on top so a 4px dashed line is actually tappable on a phone; Leaflet's own
  // drag-vs-click discrimination keeps map panning from adding trails.
  useEffect(() => {
    const map = mapObj.current;
    if (!map) return;
    layers.current?.remove();
    const group = L.layerGroup();
    const all: [number, number][] = [];

    for (const m of members) {
      if (!m.linePoints || m.linePoints.length < 2) continue;
      const latlngs = m.linePoints.map(([lon, lat]) => [lat, lon] as [number, number]);
      all.push(...latlngs);
      L.polyline(latlngs, { color: "#10160d", weight: 8, opacity: 0.45 }).addTo(group);
      L.polyline(latlngs, { color: TERRACOTTA, weight: 4.5 }).addTo(group);
    }
    for (const c of candidates) {
      if (!c.linePoints || c.linePoints.length < 2) continue;
      const latlngs = c.linePoints.map(([lon, lat]) => [lat, lon] as [number, number]);
      all.push(...latlngs);
      L.polyline(latlngs, { color: SAGE, weight: 4, dashArray: "6 7", opacity: 0.9 }).addTo(group);
      L.polyline(latlngs, { weight: 24, opacity: 0.03, color: SAGE })
        .on("click", () => addMember(c.id))
        .bindTooltip(c.name, { sticky: true, direction: "top" })
        .addTo(group);
    }
    group.addTo(map);
    layers.current = group;

    // Refit only when membership changes - candidates popping in from background enrichment
    // must not yank the viewport mid-tap.
    const key = memberIds.join("|");
    if (all.length > 1 && fittedKey.current !== key) {
      map.fitBounds(L.latLngBounds(all), { paddingTopLeft: [30, 150], paddingBottomRight: [30, 190] });
      fittedKey.current = key;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [members, candidates]);

  // Running totals over the members we have data for (nominal length fills unmapped members).
  const miles = members.reduce((sum, m) => sum + (m.metricLengthMi ?? m.lengthMi ?? 0), 0);
  const climb = members.reduce((sum, m) => sum + (m.ascentFt ?? 0), 0);
  const defaultName = members.length
    ? `${members[0].name}${members.length > 1 ? ` +${members.length - 1} more` : ""}`
    : "";

  const save = async () => {
    setSaving(true);
    setSaveErr(null);
    try {
      const route = await createTrailRoute(name.trim() || defaultName, memberIds);
      setTripsSegment("routes");
      setDetailRouteId(route.id);
      navigate("/route", { replace: true });
    } catch (e) {
      setSaveErr(e instanceof Error ? e.message : "Couldn't save the route");
      setSaving(false);
    }
  };

  const hint = loading
    ? "Loading the trail map…"
    : error
      ? error
      : candidates.length === 0 && !enriching
        ? "No connecting trails found nearby yet."
        : "Tap a dashed trail to add it to your route.";

  return (
    <div className={s.screen}>
      <div ref={mapEl} className={s.map} />

      <div className={s.topRow} style={{ zIndex: 1000 }}>
        <BackButton bg="rgba(45,59,45,0.92)" stroke="#fff" />
        <div className={s.panel}>
          <div className={s.panelLabel}>BUILDING A ROUTE</div>
          <div className={s.panelStats}>
            {members.length} trail{members.length === 1 ? "" : "s"}
            {miles > 0 ? ` · ${miles.toFixed(1)} mi` : ""}
            {climb > 0 ? ` · ↑ ${climb.toLocaleString()} ft` : ""}
          </div>
          <div className={`${s.panelSub} ${enriching ? s.pulse : ""}`}>
            {enriching ? "Finding connecting trails…" : hint}
          </div>
        </div>
      </div>

      <div className={s.bottomCard} style={{ zIndex: 1000 }}>
        <div className={s.chipRow}>
          {members.map((m, i) => (
            <span key={m.id} className={s.memberChip}>
              <span className={s.chipNum}>{i + 1}</span>
              {m.name}
            </span>
          ))}
        </div>
        <div className={s.buttonRow}>
          <button className={s.undoBtn} onClick={undo} disabled={memberIds.length < 2} style={{ opacity: memberIds.length < 2 ? 0.45 : 1 }}>
            Undo
          </button>
          <button className={s.saveBtn} disabled={memberIds.length < 2} onClick={() => { setName(defaultName); setShowSave(true); }}>
            Save route{memberIds.length >= 2 ? ` · ${memberIds.length} trails` : ""}
          </button>
        </div>
      </div>

      {showSave && (
        <div onClick={() => !saving && setShowSave(false)} style={overlay}>
          <div onClick={(e) => e.stopPropagation()} style={sheet}>
            <div style={{ fontWeight: 800, fontSize: 18, color: "var(--ink)" }}>Name your route</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)", margin: "4px 0 14px" }}>
              {members.length} trails · {miles.toFixed(1)} mi
            </div>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={200}
              placeholder={defaultName}
              style={input}
            />
            {saveErr && <div style={{ color: "var(--terracotta)", fontSize: 13, marginTop: 10 }}>{saveErr}</div>}
            <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
              <button onClick={() => setShowSave(false)} disabled={saving} style={cancelBtn}>
                Cancel
              </button>
              <button onClick={save} disabled={saving} style={{ ...saveSheetBtn, opacity: saving ? 0.7 : 1 }}>
                {saving ? "Saving…" : "Save route"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const overlay: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(33,48,42,0.45)",
  display: "flex",
  alignItems: "flex-end",
  zIndex: 2000,
};
const sheet: React.CSSProperties = {
  width: "100%",
  background: "var(--sand)",
  borderRadius: "20px 20px 0 0",
  padding: "18px 18px calc(24px + env(safe-area-inset-bottom, 0px))",
};
const input: React.CSSProperties = {
  width: "100%",
  border: "1px solid var(--card-tile-divider)",
  borderRadius: 10,
  padding: "11px 12px",
  fontSize: 15,
  background: "var(--white)",
  color: "var(--ink)",
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
const saveSheetBtn: React.CSSProperties = {
  flex: 1,
  padding: "12px 18px",
  borderRadius: 12,
  border: "none",
  background: "var(--terracotta)",
  color: "#fff",
  fontWeight: 800,
  cursor: "pointer",
};
