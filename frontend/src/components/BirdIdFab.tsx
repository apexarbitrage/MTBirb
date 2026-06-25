import { useNavigate } from "react-router-dom";

/*
 * Floating entry point to the on-trail Bird ID screen. The prototype reaches
 * Bird ID by scrolling between frames; a real app needs a discoverable hook, so
 * this terracotta mic/waveform button floats above the bottom chrome.
 */
export function BirdIdFab({ bottom = 100 }: { bottom?: number }) {
  const navigate = useNavigate();
  return (
    <button
      onClick={() => navigate("/bird-id")}
      aria-label="Identify a bird"
      style={{
        position: "absolute",
        right: 18,
        bottom,
        width: 54,
        height: 54,
        borderRadius: "50%",
        background: "var(--terracotta)",
        boxShadow: "var(--shadow-button)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 3,
        zIndex: 6,
      }}
    >
      <span style={{ width: 3, height: 12, borderRadius: 2, background: "#fff" }} />
      <span style={{ width: 3, height: 20, borderRadius: 2, background: "#fff" }} />
      <span style={{ width: 3, height: 14, borderRadius: 2, background: "#fff" }} />
      <span style={{ width: 3, height: 22, borderRadius: 2, background: "#fff" }} />
      <span style={{ width: 3, height: 10, borderRadius: 2, background: "#fff" }} />
    </button>
  );
}
