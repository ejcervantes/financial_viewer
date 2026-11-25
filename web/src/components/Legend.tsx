import type { Horizon, Mode } from "../types";
import { colorFor, horizonOf } from "../format";

export default function Legend({ horizon, mode }: { horizon: Horizon; mode: Mode }) {
  const s = horizonOf(horizon).scale;
  const stops = Array.from({ length: 11 }, (_, i) => colorFor(-s + (2 * s * i) / 10, s)).join(",");
  return (
    <div className="legend">
      <span className="legend-title">
        {mode === "absolute" ? "Sector return" : "Sector minus benchmark"}, {horizonOf(horizon).long} after day 0
      </span>
      <span className="legend-scale">
        <span>−{s * 100}%</span>
        <span className="legend-bar" style={{ background: `linear-gradient(90deg, ${stops})` }} />
        <span>+{s * 100}%</span>
      </span>
      <span className="legend-item"><span className="swatch insufficient" />Insufficient data</span>
      <span className="legend-item"><span className="swatch in-progress" />In progress (return to date)</span>
    </div>
  );
}
