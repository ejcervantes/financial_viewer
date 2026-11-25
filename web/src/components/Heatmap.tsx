import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { EpisodeMeta, EventMeta, Horizon, Indicator, IndicatorKey, Indicators, Market, Mode, Reactions, SectorMeta } from "../types";
import { cellValue, colorFor, fmtDate, horizonOf, MARKET_CODE, pct } from "../format";
import ToneLine from "./ToneLine";

interface Props {
  events: EventMeta[];
  sectors: SectorMeta[];
  markets: Market[];
  episodes: EpisodeMeta[];
  reactions: Reactions;
  indicators: Indicators;
  indicator: IndicatorKey;
  setIndicator: (k: IndicatorKey) => void;
  mode: Mode;
  horizon: Horizon;
  onEvent: (id: string, market?: Market) => void;
  onEpisode: (id: string) => void;
}

const ROW_H = 16;
const GROUP_GAP = 6;
const TONE_H = 64;

function useColW() {
  return typeof window !== "undefined" && window.innerWidth < 700 ? 20 : 24;
}

interface Hover { x: number; y: number; e: number; s?: string; m?: Market }

export default function Heatmap(p: Props) {
  const COL_W = useColW();
  const LABEL_W = COL_W === 20 ? 104 : 148;
  const N = p.events.length;
  const width = N * COL_W;
  const [hover, setHover] = useState<Hover | null>(null);
  const scale = horizonOf(p.horizon).scale;
  const episodesById = useMemo(() => Object.fromEntries(p.episodes.map((e) => [e.id, e])), [p.episodes]);

  // Contiguous runs of the same episode among the visible columns (spec §3.3: a band is cut
  // by any column that doesn't belong to it).
  const bands = useMemo(() => {
    const out: { id: string; start: number; len: number }[] = [];
    p.events.forEach((e, i) => {
      const last = out[out.length - 1];
      if (!e.episode_id) return;
      if (last && last.id === e.episode_id && last.start + last.len === i) last.len++;
      else out.push({ id: e.episode_id, start: i, len: 1 });
    });
    return out;
  }, [p.events]);

  // Year marks at the first column of each year; short form ('11) when the next mark is close.
  const years = useMemo(() => {
    const firsts = p.events.map((e, i) => {
      const y = e.announced_at_utc.slice(0, 4);
      return i === 0 || p.events[i - 1].announced_at_utc.slice(0, 4) !== y ? y : null;
    });
    return firsts.map((y, i) => {
      if (!y) return null;
      let next = i + 1;
      while (next < firsts.length && !firsts[next]) next++;
      return next - i >= 2 ? y : `’${y.slice(2)}`;
    });
  }, [p.events]);

  const grid = useMemo(() => (
    <Grid events={p.events} sectors={p.sectors} markets={p.markets} reactions={p.reactions}
      mode={p.mode} horizon={p.horizon} colW={COL_W} scale={scale} />
  ), [p.events, p.sectors, p.markets, p.reactions, p.mode, p.horizon, COL_W, scale]);

  const scroller = useRef<HTMLDivElement>(null);
  // Open on the most recent events (right end); keep the user's position afterwards.
  const scrolled = useRef(false);
  useEffect(() => {
    const el = scroller.current;
    if (el && !scrolled.current && N > 0) { el.scrollLeft = el.scrollWidth; scrolled.current = true; }
  }, [N]);
  const onMove = useCallback((ev: React.MouseEvent) => {
    const t = (ev.target as HTMLElement).closest<HTMLElement>("[data-e]");
    if (!t) { setHover(null); return; }
    setHover({ x: ev.clientX, y: ev.clientY, e: Number(t.dataset.e), s: t.dataset.s, m: t.dataset.m as Market | undefined });
  }, []);
  const onClick = useCallback((ev: React.MouseEvent) => {
    const t = (ev.target as HTMLElement).closest<HTMLElement>("[data-e]");
    if (t) p.onEvent(p.events[Number(t.dataset.e)].id, t.dataset.m as Market | undefined);
  }, [p.onEvent, p.events]);

  const ind: Indicator | undefined = p.indicators[p.indicator];

  if (!N) return <p className="empty">No events match the selected categories.</p>;

  return (
    <div className="hm-outer">
      <div className="hm-scroll" ref={scroller} onMouseMove={onMove} onMouseLeave={() => setHover(null)} onClick={onClick}>
        <div className="hm" style={{ width: width + LABEL_W, ["--label-w" as string]: `${LABEL_W}px` }}>
          {/* Tone line */}
          <div className="hm-row">
            <div className="hm-label tone-label" style={{ height: TONE_H }}>
              <select value={p.indicator} onChange={(e) => p.setIndicator(e.target.value as IndicatorKey)}
                aria-label="Tone indicator" onClick={(e) => e.stopPropagation()}>
                {(["epu", "gpr", "vix"] as IndicatorKey[]).filter((k) => p.indicators[k]).map((k) => (
                  <option key={k} value={k}>{p.indicators[k]!.short}</option>
                ))}
              </select>
              <span className="tone-sub">{ind?.label}{ind?.note ? `, ${ind.note}` : ""}</span>
            </div>
            <ToneLine indicator={ind} events={p.events} width={width} height={TONE_H} />
          </div>

          {/* Episode bands */}
          <div className="hm-row">
            <div className="hm-label band-label">Episodes</div>
            <div className="bands" style={{ width }}>
              {bands.map((b) => (
                <button key={`${b.id}-${b.start}`} className="band"
                  style={{ left: b.start * COL_W + 1, width: b.len * COL_W - 2 }}
                  title={`${episodesById[b.id]?.title} — open episode view`}
                  onClick={(e) => { e.stopPropagation(); p.onEpisode(b.id); }}>
                  <span>{episodesById[b.id]?.title}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Column headers */}
          <div className="hm-row">
            <div className="hm-label head-label">
              <span>Events, oldest → newest</span>
              <span className="muted">Click a column for details</span>
            </div>
            <div className="heads" style={{ width }}>
              {p.events.map((e, i) => (
                <div key={e.id} className={`head cat-${e.category}`} style={{ width: COL_W }} data-e={i}>
                  <span className="head-title">{e.title}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="hm-row">
            <div className="hm-label" />
            <div className="years" style={{ width }}>
              {years.map((y, i) => y && (
                <span key={i} style={{ left: i * COL_W }} className="year">{y}</span>
              ))}
            </div>
          </div>

          {grid}

          {hover && (
            <div className="col-hl" style={{ left: LABEL_W + hover.e * COL_W, width: COL_W }} />
          )}
        </div>
      </div>
      {hover && <Tooltip h={hover} {...p} />}
    </div>
  );
}

const Grid = memo(function Grid({ events, sectors, markets, reactions, mode, horizon, colW, scale }: {
  events: EventMeta[]; sectors: SectorMeta[]; markets: Market[]; reactions: Reactions;
  mode: Mode; horizon: Horizon; colW: number; scale: number;
}) {
  return (
    <div className="grid">
      {sectors.map((s) => (
        <div key={s.id} className="group" style={{ marginTop: GROUP_GAP }}>
          {markets.map((m, mi) => (
            <div key={m} className="hm-row">
              <div className="hm-label row-label" style={{ height: ROW_H }}>
                <span className="sector-name">{mi === 0 ? s.name : ""}</span>
                <span className="mkt">{MARKET_CODE[m]}</span>
              </div>
              {events.map((e, i) => {
                const { value, status } = cellValue(reactions[e.id]?.[s.id]?.[m], mode, horizon);
                const bg = value == null ? undefined : colorFor(value, scale);
                const cls = value == null ? (status === "in_progress" ? "cell pending" : "cell na") : status === "in_progress" ? "cell prog" : "cell";
                return <div key={e.id} className={cls} style={{ width: colW, height: ROW_H, background: bg }}
                  data-e={i} data-s={s.id} data-m={m} />;
              })}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
});

function Tooltip({ h, events, sectors, reactions, mode, horizon }: { h: Hover } & Props) {
  const ev = events[h.e];
  if (!ev) return null;
  const left = Math.min(h.x + 14, window.innerWidth - 300);
  const top = h.y + 16 + 220 > window.innerHeight ? h.y - 230 : h.y + 16;
  const r = h.s && h.m ? reactions[ev.id]?.[h.s]?.[h.m] : undefined;
  const sector = sectors.find((s) => s.id === h.s);
  const st = r ? (mode === "absolute" ? r.status[horizon] : r.status_vs_market[horizon]) : null;
  return (
    <div className="tooltip" style={{ left, top }} role="tooltip">
      <div className="tt-title">{ev.title}</div>
      <div className="tt-sub">{fmtDate(ev.announced_at_utc)}</div>
      {sector && h.m && (
        <>
          <div className="tt-sector">{sector.name} · {MARKET_CODE[h.m]}</div>
          {!r || r.absolute[horizon] == null ? (
            <div className="tt-na">
              {st === "in_progress" ? "No sessions yet after the event"
                : `Insufficient data${r?.constituents != null && sector.markets[h.m].type === "basket" ? ` (${r.constituents} listed, minimum 2)` : ""}`}
            </div>
          ) : (
            <table className="tt-table"><tbody>
              <tr><td>Sector</td><td>{pct(r.absolute[horizon])}</td></tr>
              <tr><td>Benchmark ({sector.markets[h.m].benchmark})</td><td>{pct(r.benchmark[horizon])}</td></tr>
              <tr className="tt-strong"><td>Difference</td><td>{pct(r.vs_market[horizon])}</td></tr>
              <tr><td>From (t−1 close)</td><td>{fmtDate(r.base_date)}</td></tr>
              <tr><td>Day 0</td><td>{fmtDate(r.day0)}</td></tr>
              <tr><td>To ({horizonOf(horizon).sessions} sessions)</td><td>{fmtDate(r.end_dates[horizon])}{st === "in_progress" ? " · in progress" : ""}</td></tr>
              <tr><td>Companies</td><td>{sector.markets[h.m].type === "basket" ? r.constituents : `ETF (${sector.markets[h.m].tickers[0]})`}</td></tr>
            </tbody></table>
          )}
        </>
      )}
      {!sector && <div className="tt-sub">{ev.description}</div>}
    </div>
  );
}
