import { Fragment, useEffect, useMemo, useState } from "react";
import type { AppData, EpisodeSeries, IndicatorKey, Market } from "../types";
import { loadEpisodeSeries } from "../data";
import { FONT, useChart } from "../echarts";
import { fmtDate, MARKET_CODE, MARKETS, pct, SECTOR_COLORS } from "../format";

interface Props {
  data: AppData;
  episodeId: string;
  indicator: IndicatorKey;
  onClose: () => void;
  onEvent: (id: string) => void;
}

const AXIS = { fontSize: 11, color: "#5b6472" };

export default function EpisodeView({ data, episodeId, indicator, onClose, onEvent }: Props) {
  const ep = data.meta.episodes.find((e) => e.id === episodeId)!;
  const milestones = data.meta.events.filter((e) => e.episode_id === episodeId);
  const [market, setMarket] = useState<Market>("us");
  const [series, setSeries] = useState<EpisodeSeries | null>(null);

  useEffect(() => { setSeries(null); loadEpisodeSeries(episodeId).then(setSeries).catch(() => setSeries({})); }, [episodeId]);
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);

  const range = useMemo(() => {
    const start = Date.parse(ep.start) - 7 * 86400000;
    const end = ep.end ? Date.parse(ep.end) + 7 * 86400000 : Date.now();
    return [start, end] as const;
  }, [ep]);

  const option = useMemo(() => {
    if (!series) return null;
    const lines: any[] = data.meta.sectors.filter((s) => series[s.id]?.[market]).map((s) => {
      const p = series[s.id]![market]!;
      return {
        name: s.name, type: "line", showSymbol: false, data: p.dates.map((d, i) => [d, p.sector[i]]),
        lineStyle: { width: 1.5, color: SECTOR_COLORS[s.id] }, itemStyle: { color: SECTOR_COLORS[s.id] },
        emphasis: { focus: "series" },
      };
    });
    const any = data.meta.sectors.map((s) => series[s.id]?.[market]).find(Boolean);
    if (any) {
      lines.push({
        name: `Benchmark (${data.meta.markets[market].benchmark})`, type: "line", showSymbol: false,
        data: any.dates.map((d, i) => [d, any.benchmark[i]]),
        lineStyle: { width: 1.25, type: "dashed", color: "#1c1f24" }, itemStyle: { color: "#1c1f24" },
      });
      lines[0].markLine = {
        symbol: "none", lineStyle: { color: "#b8b4aa", width: 1, type: "dotted" },
        label: { show: false },
        emphasis: { label: { show: true, formatter: "{b}", fontFamily: FONT, fontSize: 11, color: "#1c1f24", backgroundColor: "#fff", padding: 4 } },
        data: milestones.map((m) => ({ xAxis: m.announced_at_utc.slice(0, 10), name: m.title })),
      };
    }
    return {
      animation: false, textStyle: { fontFamily: FONT },
      grid: { left: 48, right: 16, top: 16, bottom: 64 },
      legend: { bottom: 0, type: "scroll", textStyle: { fontSize: 11, color: "#3a3f47" }, itemWidth: 14, itemHeight: 8 },
      tooltip: {
        trigger: "axis", confine: true, textStyle: { fontSize: 12 },
        formatter: (ps: any[]) => `<b>${fmtDate(ps[0]?.data?.[0])}</b>` + ps.filter((p) => p.data[1] != null)
          .sort((a, b) => b.data[1] - a.data[1]).map((p) => `<br/>${p.marker}${p.seriesName}: <b>${pct(p.data[1])}</b>`).join(""),
      },
      xAxis: { type: "time", min: range[0], max: range[1], axisLabel: AXIS, axisLine: { lineStyle: { color: "#c9c6bd" } }, splitLine: { show: false } },
      yAxis: { type: "value", axisLabel: { ...AXIS, formatter: (v: number) => `${Math.round(v * 100)}%` }, splitLine: { lineStyle: { color: "#ece9e1" } } },
      series: lines,
    };
  }, [series, market, data.meta, milestones, range]);

  const ind = data.indicators[indicator];
  const toneOption = useMemo(() => {
    if (!ind) return null;
    const pts: [string, number][] = [];
    ind.dates.forEach((d, i) => { const t = Date.parse(d); if (t >= range[0] && t <= range[1]) pts.push([d, ind.values[i]]); });
    return {
      animation: false, textStyle: { fontFamily: FONT },
      grid: { left: 48, right: 16, top: 8, bottom: 24 },
      tooltip: { trigger: "axis", textStyle: { fontSize: 12 }, formatter: (ps: any[]) => `${fmtDate(ps[0].data[0])}<br/><b>${ind.short} ${ps[0].data[1].toFixed(1)}</b>` },
      xAxis: { type: "time", min: range[0], max: range[1], axisLabel: AXIS, axisLine: { lineStyle: { color: "#c9c6bd" } } },
      yAxis: { type: "value", scale: true, axisLabel: AXIS, splitLine: { lineStyle: { color: "#ece9e1" } }, splitNumber: 2 },
      series: [{
        type: "line", data: pts, showSymbol: false, lineStyle: { color: "#5b6472", width: 1.25 }, areaStyle: { color: "rgba(91,100,114,0.08)" },
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: "#b8b4aa", type: "dotted" },
          data: milestones.map((m) => ({ xAxis: m.announced_at_utc.slice(0, 10) })) },
      }],
    };
  }, [ind, range, milestones]);

  const chartRef = useChart(option);
  const toneRef = useChart(toneOption);
  const stats = data.episodes[episodeId] ?? {};

  return (
    <div className="overlay center" onClick={onClose}>
      <div className="episode" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="ep-title">
        <button className="close" onClick={onClose} aria-label="Close">×</button>
        <div className="panel-kicker">Episode</div>
        <h2 id="ep-title">{ep.title}</h2>
        <p className="panel-date">{fmtDate(ep.start)} – {ep.end ? fmtDate(ep.end) : "in progress"}</p>

        <div className="panel-tabs" role="tablist" aria-label="Market">
          {MARKETS.map((m) => (
            <button key={m} role="tab" aria-selected={m === market} className={m === market ? "on" : ""} onClick={() => setMarket(m)}>
              {data.meta.markets[m].name}
            </button>
          ))}
        </div>
        <p className="muted small">Cumulative return from the last close before the episode starts. Dotted lines mark the milestones; hover one to see its name.</p>
        <div ref={chartRef} className="chart tall" />
        <p className="tone-caption"><b>{ind?.label}</b> <span className="muted">· {ind?.note}</span></p>
        <div ref={toneRef} className="chart short" />

        <div className="episode-grid">
          <div>
            <h3>Maximum drawdown and total return</h3>
            <table className="react-table dd">
              <thead>
                <tr><th rowSpan={2}>Sector</th>{MARKETS.map((m) => <th key={m} colSpan={2}>{MARKET_CODE[m]}</th>)}</tr>
                <tr>{MARKETS.map((m) => <Fragment key={m}><th>Max DD</th><th>Total</th></Fragment>)}</tr>
              </thead>
              <tbody>
                {data.meta.sectors.map((s) => (
                  <tr key={s.id}>
                    <td><span className="line-key" style={{ background: SECTOR_COLORS[s.id] }} />{s.name}</td>
                    {MARKETS.map((m) => {
                      const st = stats[s.id]?.[m];
                      return <Fragment key={m}>
                        <td className={st?.drawdown != null ? "neg" : "muted"}
                          title={st?.peak_date ? `Peak ${fmtDate(st.peak_date)} → trough ${fmtDate(st.trough_date)}${st.partial ? ` (data from ${fmtDate(st.from_date)})` : ""}` : "Insufficient data"}>
                          {pct(st?.drawdown ?? null, 0)}{st?.partial ? "†" : ""}</td>
                        <td className={st?.total_return == null ? "muted" : st.total_return > 0 ? "pos" : "neg"}
                          title={st?.partial ? `From ${fmtDate(st.from_date)}` : undefined}>
                          {pct(st?.total_return ?? null, 0)}{st?.partial ? "†" : ""}</td>
                      </Fragment>;
                    })}
                  </tr>
                ))}
                <tr className="bench-row">
                  <td>Benchmark</td>
                  {MARKETS.map((m) => {
                    const full = data.meta.sectors.map((s) => stats[s.id]?.[m]).find((x) => x && !x.partial && x.bench_total_return != null);
                    const b = full?.bench_total_return ?? null;
                    return <Fragment key={m}><td /><td className={b == null ? "muted" : b > 0 ? "pos" : "neg"}>{pct(b, 0)}</td></Fragment>;
                  })}
                </tr>
              </tbody>
            </table>
            <p className="muted small">Max drawdown = largest peak-to-trough fall inside the episode. † Data starts after the episode began; figures cover the available part (hover for the date). {ep.end ? "" : "Episode in progress: figures to date."}</p>
          </div>
          <div>
            <h3>Milestones</h3>
            <ol className="milestones">
              {milestones.map((m) => (
                <li key={m.id}>
                  <span className="muted">{fmtDate(m.announced_at_utc)}</span>
                  <button className="link" onClick={() => onEvent(m.id)}>{m.title}</button>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
