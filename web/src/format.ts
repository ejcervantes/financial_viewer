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

// Diverging scale red → yellow → green (based on ColorBrewer RdYlGn), saturating at ±scale.
// The midpoint is a clear pale yellow so "about zero" never reads as the grey of missing data.
const STOPS: [number, number[]][] = [
  [-1, [165, 0, 38]],
  [-0.66, [215, 48, 39]],
  [-0.33, [244, 128, 72]],
  [-0.12, [252, 200, 110]],
  [0, [250, 232, 140]],
  [0.12, [214, 234, 130]],
  [0.33, [145, 207, 96]],
  [0.66, [61, 160, 80]],
  [1, [0, 104, 55]],
];

export function colorFor(value: number, scale: number): string {
  const t = Math.max(-1, Math.min(1, value / scale));
  let i = 0;
  while (i < STOPS.length - 2 && t > STOPS[i + 1][0]) i++;
  const [t0, c0] = STOPS[i];
  const [t1, c1] = STOPS[i + 1];
  const f = (t - t0) / (t1 - t0);
  const c = c0.map((v, k) => Math.round(v + (c1[k] - v) * f));
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
