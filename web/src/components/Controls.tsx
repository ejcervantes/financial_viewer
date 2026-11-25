import type { Horizon, Market, Mode } from "../types";
import { HORIZONS } from "../format";

interface Props {
  mode: Mode; setMode: (m: Mode) => void;
  horizon: Horizon; setHorizon: (h: Horizon) => void;
  categories: { id: string; name: string }[];
  activeCats: Set<string>; toggleCat: (id: string) => void;
  market: Market | "all"; setMarket: (m: Market | "all") => void;
}

function Segmented<T extends string>({ label, value, options, onChange }: {
  label: string; value: T; options: { id: T; label: string }[]; onChange: (v: T) => void;
}) {
  return (
    <div className="control">
      <span className="control-label">{label}</span>
      <div className="segmented" role="radiogroup" aria-label={label}>
        {options.map((o) => (
          <button key={o.id} role="radio" aria-checked={value === o.id}
            className={value === o.id ? "on" : ""} onClick={() => onChange(o.id)}>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Controls(p: Props) {
  return (
    <div className="controls">
      <Segmented label="Mode" value={p.mode} onChange={p.setMode}
        options={[{ id: "absolute", label: "Absolute" }, { id: "vs_market", label: "vs. market" }]} />
      <Segmented label="Horizon" value={p.horizon} onChange={p.setHorizon}
        options={HORIZONS.map((h) => ({ id: h.id, label: h.label }))} />
      <Segmented label="Market" value={p.market} onChange={p.setMarket}
        options={[{ id: "all", label: "All" }, { id: "us", label: "US" }, { id: "eu", label: "EU" }, { id: "cn", label: "CN" }]} />
      <div className="control">
        <span className="control-label">Categories</span>
        <div className="chips">
          {p.categories.map((c) => (
            <button key={c.id} className={`chip cat-${c.id} ${p.activeCats.has(c.id) ? "on" : ""}`}
              aria-pressed={p.activeCats.has(c.id)} onClick={() => p.toggleCat(c.id)}>
              <span className="chip-dot" />{c.name}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
