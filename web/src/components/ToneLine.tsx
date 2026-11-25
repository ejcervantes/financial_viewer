import { useMemo } from "react";
import type { EventMeta, Indicator } from "../types";
import { FONT, useChart } from "../echarts";
import { fmtDate } from "../format";

const DAY = 86400000;
const BUCKETS = 14; // points drawn per gap between two event columns

/**
 * The indicator on a non-linear time axis: each event column's center sits at its event
 * date, and the daily series between two events is stretched to fit between their columns.
 */
export function compressSeries(ind: Indicator, events: EventMeta[]) {
  const times = ind.dates.map((d) => Date.parse(d));
  const ev = events.map((e) => Date.parse(e.announced_at_utc.slice(0, 10)));
  const line: [number, number, string][] = [];
  const marks: [number, number, string][] = [];
  const valueAt = (t: number) => {
    let lo = 0, hi = times.length - 1;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (times[mid] <= t) lo = mid; else hi = mid - 1; }
    return times[lo] <= t ? lo : -1;
  };
  for (let i = 0; i < ev.length; i++) {
    const k = valueAt(ev[i]);
    if (k >= 0 && ev[i] - times[k] < 10 * DAY) marks.push([i + 0.5, ind.values[k], events[i].title]);
    if (i === ev.length - 1) break;
    const t0 = ev[i], t1 = ev[i + 1];
    if (t1 <= t0) continue;
    const a = valueAt(t0), b = valueAt(t1);
    if (a < 0 || b <= a) continue;
    const step = Math.max(1, Math.ceil((b - a) / BUCKETS));
    for (let j = a; j < b; j += step) {
      const end = Math.min(j + step, b);
      let sum = 0;
      for (let q = j; q < end; q++) sum += ind.values[q];
      const mid = (times[j] + times[end - 1]) / 2;
      line.push([i + 0.5 + (mid - t0) / (t1 - t0), sum / (end - j), ind.dates[j]]);
    }
  }
  return { line, marks };
}

export default function ToneLine({ indicator, events, width, height }: {
  indicator: Indicator | undefined; events: EventMeta[]; width: number; height: number;
}) {
  const option = useMemo(() => {
    if (!indicator || !events.length) return null;
    const { line, marks } = compressSeries(indicator, events);
    return {
      animation: false,
      textStyle: { fontFamily: FONT },
      grid: { left: 0, right: 0, top: 6, bottom: 4 },
      xAxis: { type: "value", min: 0, max: events.length, show: false },
      yAxis: { type: "value", show: false, scale: true },
      tooltip: {
        trigger: "item", confine: true, textStyle: { fontSize: 12 },
        formatter: (p: any) => `${p.data[2]}<br/><b>${indicator.short} ${p.data[1].toFixed(1)}</b>`,
      },
      series: [
        {
          type: "line", data: line, showSymbol: false, silent: true,
          lineStyle: { color: "#5b6472", width: 1.25 },
          areaStyle: { color: "rgba(91,100,114,0.08)" },
        },
        {
          type: "scatter", data: marks, symbol: "rect", symbolSize: [2, 7],
          itemStyle: { color: "#1c1f24" },
          tooltip: { formatter: (p: any) => `${p.data[2]}<br/><b>${indicator.short} ${p.data[1].toFixed(1)}</b>` },
        },
      ],
    };
  }, [indicator, events]);
  const ref = useChart(option);
  return <div ref={ref} style={{ width, height }} aria-label={indicator ? `${indicator.label} line` : undefined} />;
}

export function indicatorRange(ind: Indicator | undefined) {
  if (!ind) return "";
  return `${fmtDate(ind.dates[0], true).split(" ").pop()}–${fmtDate(ind.dates[ind.dates.length - 1])}`;
}
