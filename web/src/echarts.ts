import { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import { LineChart, ScatterChart } from "echarts/charts";
import {
  GridComponent, TooltipComponent, MarkLineComponent, MarkAreaComponent, LegendComponent, DataZoomComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsCoreOption } from "echarts/core";

echarts.use([
  LineChart, ScatterChart, GridComponent, TooltipComponent, MarkLineComponent, MarkAreaComponent,
  LegendComponent, DataZoomComponent, CanvasRenderer,
]);

export const FONT = "'IBM Plex Sans', system-ui, sans-serif";

/** Mount an ECharts instance on a div and keep it in sync with `option`. */
export function useChart(option: EChartsCoreOption | null, onClick?: (p: any) => void) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const c = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chart.current = c;
    const ro = new ResizeObserver(() => c.resize());
    ro.observe(ref.current);
    return () => { ro.disconnect(); c.dispose(); chart.current = null; };
  }, []);

  useEffect(() => {
    if (chart.current && option) chart.current.setOption(option, { notMerge: true });
  }, [option]);

  useEffect(() => {
    const c = chart.current;
    if (!c || !onClick) return;
    c.on("click", onClick);
    return () => { c.off("click", onClick); };
  }, [onClick]);

  return ref;
}
