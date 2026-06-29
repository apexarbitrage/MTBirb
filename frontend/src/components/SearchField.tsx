import type { CSSProperties } from "react";
import { SearchIcon } from "./icons";

/*
 * A small rounded search input shared by the Trails and Birbs tabs: a magnifier, the field, and a
 * clear (✕) button once there's text. Filtering is the caller's job - this is presentation only.
 */
export function SearchField({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <div style={wrap}>
      <SearchIcon size={18} />
      <input
        type="text"
        enterKeyHint="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        style={input}
      />
      {value && (
        <button type="button" onClick={() => onChange("")} aria-label="Clear search" style={clearBtn}>
          ✕
        </button>
      )}
    </div>
  );
}

const wrap: CSSProperties = {
  height: 44,
  borderRadius: "var(--radius-tile)",
  background: "var(--white)",
  boxShadow: "var(--shadow-card-sm)",
  display: "flex",
  alignItems: "center",
  gap: 10,
  padding: "0 12px",
};
const input: CSSProperties = {
  flex: 1,
  minWidth: 0,
  border: "none",
  outline: "none",
  background: "transparent",
  fontSize: 15,
  color: "var(--ink)",
};
const clearBtn: CSSProperties = {
  flex: "none",
  border: "none",
  background: "transparent",
  color: "var(--text-muted)",
  fontSize: 14,
  lineHeight: 1,
  cursor: "pointer",
  padding: 4,
};
