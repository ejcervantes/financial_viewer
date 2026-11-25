import { useEffect, useMemo, useState } from "react";
import type { AppData, EventSeries, Horizon, Market, Mode } from "../types";
import { loadEventSeries } from "../data";
import { FONT, useChart } from "../echarts";
import { cellValue, fmtDate, fmtDateTimeUTC, horizonOf, MARKET_CODE, MARKETS, pct, SECTOR_COLORS } from "../format";
import { AnalysisBlock, ContextBlock } from "./Texts";

interface Props {
  data: AppData;
  eventId: string;
  market: Market;
  setMarket: (m: Market) => void;
  mode: Mode;
  horizon: Horizon;
  onClose: () => void;
  onEpisode: (id: string) => void;
}

export default function EventPanel({ data, eventId, market, setMarket, mode, horizon, onClose, onEpisode }: Props) {
  const ev = data.meta.events.find((e) => e.id === eventId)!;
  const episode = data.meta.episodes.find((e) => e.id === ev.episode_id);
  const category = data.meta.categories.find((c) => c.id === ev.category);
  const [series, setSeries] = useState<EventSeries | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setSeries(null); setError(false);
    loadEventSeries(eventId).then(setSeries).catch(() => setError(true));
  }, [eventId]);

  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);

  const H = horizonOf(horizon).sessions;
  const option = useMemo(() => {
    if (!series) return null;
    const lines: any[] = [];
    let bench: [number, number][] | null = null;
    let dateByOffset: Record<number, string> = {};
    for (const s of data.meta.sectors) {
      const p = series[s.id]?.[market];
      if (!p) continue;
      const pts: [number, number | null][] = [];
      p.offsets.forEach((o, i) => {
        if (o > H) return;
        dateByOffset[o] ??= p.dates[i];
        const v = p.sector[i];
        const b = p.benchmark[i];
        pts.push([o, v == null ? null : mode === "absolute" ? v : b == null ? null : v - b]);
      });
      if (!bench && mode === "absolute") {
        bench = p.offsets.map((o, i) => [o, p.benchmark[i]] as [number, number]).filter(([o, b]) => o <= H && b != null);
      }
      lines.push({
        name: s.name, type: "line", data: pts, showSymbol: false, connectNulls: false,
        lineStyle: { width: 1.75, color: SECTOR_COLORS[s.id] }, itemStyle: { color: SECTOR_COLORS[s.id] },
        emphasis: { focus: "series", lineStyle: { width: 2.5 } },
      });
    }
    if (bench) {
      lines.push({
        name: `Benchmark (${data.meta.markets[market].benchmark})`, type: "line", data: bench, showSymbol: false,
        lineStyle: { width: 1.5, type: "dashed", color: "#1c1f24" }, itemStyle: { color: "#1c1f24" },
      });
    }
    if (lines.length) {
      lines[0].markLine = {
        silent: true, symbol: "none", label: { fontFamily: FONT, fontSize: 11, color: "#5b6472", formatter: "{b}" },
        lineStyle: { color: "#9aa1ab", type: "solid", width: 1 },
        data: [{ xAxis: 0, name: "Day 0" }, { yAxis: 0, name: "", lineStyle: { color: "#c9c6bd" }, label: { show: false } }],
      };
    }
    return {
      animation: false,
      textStyle: { fontFamily: FONT },
      grid: { left: 44, right: 12, top: 12, bottom: 64 },
      legend: { bottom: 0, type: "scroll", textStyle: { fontSize: 11, color: "#3a3f47" }, itemWidth: 14, itemHeight: 8 },
      tooltip: {
        trigger: "axis", confine: true, order: "valueDesc", textStyle: { fontSize: 12 },
        axisPointer: { type: "line", lineStyle: { color: "#9aa1ab" } },
        formatter: (ps: any[]) => {
          const o = ps[0]?.data?.[0];
          const head = `<b>${o === 0 ? "Day 0" : o > 0 ? `Day +${o}` : `Day ${o}`}</b> · ${fmtDate(dateByOffset[o])}`;
          return head + ps.filter((p) => p.data[1] != null)
            .sort((a, b) => b.data[1] - a.data[1])
            .map((p) => `<br/>${p.marker}${p.seriesName}: <b>${pct(p.data[1])}</b>`).join("");
        },
      },
      xAxis: {
        type: "value", min: -5, max: H, interval: H <= 5 ? 1 : H <= 21 ? 5 : 10,
        axisLabel: { fontSize: 11, color: "#5b6472", formatter: (v: number) => (v === 0 ? "0" : v > 0 ? `+${v}` : `${v}`) },
        name: "sessions from day 0", nameLocation: "middle", nameGap: 24, nameTextStyle: { fontSize: 11, color: "#5b6472" },
        splitLine: { show: false }, axisLine: { lineStyle: { color: "#c9c6bd" } },
      },
      yAxis: {
        type: "value", axisLabel: { fontSize: 11, color: "#5b6472", formatter: (v: number) => `${Math.round(v * 100)}%` },
        splitLine: { lineStyle: { color: "#ece9e1" } },
      },
      series: lines,
    };
  }, [series, market, mode, H, data.meta]);
  const chartRef = useChart(option);
  const hasAny = series && data.meta.sectors.some((s) => series[s.id]?.[market]);
  const texts = data.texts[eventId];
  const r0 = data.reactions[eventId];
  const anyRow = r0 && Object.values(r0).map((x) => x[market]).find((x) => x?.day0);

  return (
    <div className="overlay" onClick={onClose}>
      <aside className="panel" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="ev-title">
        <button className="close" onClick={onClose} aria-label="Close">×</button>
        <div className={`panel-kicker cat-${ev.category}`}>
          <span className="chip-dot" />{category?.name}
          {episode && <> · <button className="link" onClick={() => onEpisode(episode.id)}>{episode.title}</button></>}
        </div>
        <h2 id="ev-title">{ev.title}</h2>
        <p className="panel-date">{fmtDateTimeUTC(ev.announced_at_utc)}</p>
        {ev.description && <p className="panel-desc">{ev.description}</p>}

        <div className="panel-tabs" role="tablist" aria-label="Market">
          {MARKETS.map((m) => (
            <button key={m} role="tab" aria-selected={m === market} className={m === market ? "on" : ""} onClick={() => setMarket(m)}>
              {data.meta.markets[m].name}
            </button>
          ))}
        </div>
        <p className="muted small">
          {mode === "absolute" ? "Cumulative return" : "Cumulative return minus benchmark"} from the last close before the announcement
          {anyRow ? ` (${fmtDate(anyRow.base_date)}); day 0 = ${fmtDate(anyRow.day0)}` : ""}.
        </p>
        <div className="chart-box">
          {error ? <p className="muted">Could not load the price paths.</p>
            : series && !hasAny ? <p className="muted">No {MARKET_CODE[market]} data for this date.</p> : null}
          <div ref={chartRef} className="chart" style={{ visibility: hasAny ? "visible" : "hidden" }} />
        </div>

        <table className="react-table">
          <thead><tr><th>{MARKET_CODE[market]} sector</th><th>Absolute</th><th>vs. market</th><th>n</th></tr></thead>
          <tbody>
            {data.meta.sectors.map((s) => {
              const r = r0?.[s.id]?.[market];
              const a = cellValue(r, "absolute", horizon);
              const v = cellValue(r, "vs_market", horizon);
              return (
                <tr key={s.id}>
                  <td><span className="line-key" style={{ background: SECTOR_COLORS[s.id] }} />{s.name}</td>
                  <td className={sign(a.value)}>{pct(a.value)}{a.status === "in_progress" && a.value != null ? "*" : ""}</td>
                  <td className={sign(v.value)}>{pct(v.value)}{v.status === "in_progress" && v.value != null ? "*" : ""}</td>
                  <td className="muted">{s.markets[market].type === "basket" ? r?.constituents ?? "—" : "ETF"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="muted small">{horizonOf(horizon).long} = {horizonOf(horizon).sessions} sessions after day 0. * horizon not complete yet: return to date.</p>

        <ContextBlock t={texts} />
        <AnalysisBlock t={texts} />

        {ev.official_sources.length > 0 && (
          <section className="panel-section">
            <h3>Official sources</h3>
            <ul className="headlines">
              {ev.official_sources.map((s) => (
                <li key={s.url}><a href={s.url} target="_blank" rel="noopener noreferrer">{s.label}</a></li>
              ))}
            </ul>
          </section>
        )}
      </aside>
    </div>
  );
}

const sign = (v: number | null) => (v == null ? "muted" : v > 0 ? "pos" : v < 0 ? "neg" : "");
