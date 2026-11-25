import type { Horizon, Market, Mode, Reaction, Status } from "./types";

export const HORIZONS: { id: Horizon; label: string; long: string; sessions: number; scale: number }[] = [
  { id: "1w", label: "1W", long: "1 week", sessions: 5, scale: 0.1 },
  { id: "1m", label: "1M", long: "1 month", sessions: 21, scale: 0.2 },
  { id: "3m", label: "3M", long: "3 months", sessions: 63, scale: 0.3 },
];
export const horizonOf = (h: Horizon) => HORIZONS.find((x) => x.id === h)!;
export const MARKETS: Market[] = ["us", "eu", "cn"];
export const MARKET_CODE: Record<Market, string> = { us: "US", eu: "EU", cn: "CN" };

export const pct = (x: number | null | undefined, digits = 1) =>
  x == null ? "—" : `${x > 0 ? "+" : x < 0 ? "−" : ""}${Math.abs(x * 100).toFixed(digits)}%`;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function fmtDate(iso: string | null | undefined, withYear = true) {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${d} ${MONTHS[m - 1]}${withYear ? ` ${y}` : ""}`;
}
export function fmtDateTimeUTC(iso: string) {
  const d = new Date(iso);
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${fmtDate(iso)}, ${hh}:${mm} UTC`;
}

export function cellValue(r: Reaction | undefined, mode: Mode, h: Horizon): { value: number | null; status: Status } {
  if (!r) return { value: null, status: "insufficient" };
  const status = mode === "absolute" ? r.status[h] : r.status_vs_market[h];
  return { value: r[mode][h], status };
}

// Diverging scale: red (negative) → warm neutral → green (positive), saturating at ±scale.
const NEG = [179, 38, 30];
const MID = [244, 243, 239];
const POS = [31, 111, 63];
const lerp = (a: number[], b: number[], t: number) => a.map((v, i) => Math.round(v + (b[i] - v) * t));

export function colorFor(value: number, scale: number): string {
  const t = Math.max(-1, Math.min(1, value / scale));
  const c = t < 0 ? lerp(MID, NEG, -t) : lerp(MID, POS, t);
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

// Categorical palette for sector lines — no red or green, which are reserved for returns.
export const SECTOR_COLORS: Record<string, string> = {
  tech: "#2459c4",
  energy: "#d98a00",
  industrials: "#6b4fbb",
  auto: "#0f8aa3",
  banks: "#1c2333",
  staples: "#c0508a",
  defense: "#8a6a3b",
  metals: "#8995a8",
};
