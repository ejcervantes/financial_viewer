import { useCallback, useEffect, useMemo, useState } from "react";
import type { AppData, Horizon, IndicatorKey, Market, Mode } from "./types";
import { loadAll } from "./data";
import { MARKETS } from "./format";
import { SITE_NAME, SITE_TAGLINE } from "./config";
import Controls from "./components/Controls";
import Legend from "./components/Legend";
import Heatmap from "./components/Heatmap";
import EventPanel from "./components/EventPanel";
import EpisodeView from "./components/EpisodeView";
import Footer from "./components/Footer";

// View state lives in the URL so any view can be shared as a link.
function readParams() {
  const q = new URLSearchParams(window.location.search);
  const pick = <T extends string>(k: string, ok: readonly T[], d: T): T => (ok.includes(q.get(k) as T) ? (q.get(k) as T) : d);
  return {
    mode: pick<Mode>("mode", ["absolute", "vs_market"], "absolute"),
    horizon: pick<Horizon>("h", ["1w", "1m", "3m"], "1w"),
    market: pick<Market | "all">("mkt", ["all", "us", "eu", "cn"], "all"),
    indicator: pick<IndicatorKey>("tone", ["epu", "gpr", "vix"], "vix"),
    cats: q.get("cats")?.split(",").filter(Boolean) ?? null,
    event: q.get("event"),
    panelMarket: pick<Market>("pm", ["us", "eu", "cn"], "us"),
    episode: q.get("episode"),
  };
}

export default function App() {
  const init = useMemo(readParams, []);
  const [data, setData] = useState<AppData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>(init.mode);
  const [horizon, setHorizon] = useState<Horizon>(init.horizon);
  const [market, setMarket] = useState<Market | "all">(init.market);
  const [indicator, setIndicator] = useState<IndicatorKey>(init.indicator);
  const [activeCats, setActiveCats] = useState<Set<string> | null>(init.cats ? new Set(init.cats) : null);
  const [eventId, setEventId] = useState<string | null>(init.event);
  const [panelMarket, setPanelMarket] = useState<Market>(init.panelMarket);
  const [episodeId, setEpisodeId] = useState<string | null>(init.episode);

  useEffect(() => { loadAll().then(setData).catch((e) => setError(String(e))); }, []);

  const cats = activeCats ?? new Set(data?.meta.categories.map((c) => c.id) ?? []);

  useEffect(() => {
    if (!data) return;
    const q = new URLSearchParams();
    if (mode !== "absolute") q.set("mode", mode);
    if (horizon !== "1w") q.set("h", horizon);
    if (market !== "all") q.set("mkt", market);
    if (indicator !== "vix") q.set("tone", indicator);
    if (activeCats && activeCats.size !== data.meta.categories.length) q.set("cats", [...activeCats].join(","));
    if (eventId) { q.set("event", eventId); q.set("pm", panelMarket); }
    if (episodeId) q.set("episode", episodeId);
    const s = q.toString();
    window.history.replaceState(null, "", s ? `?${s}` : window.location.pathname);
  }, [data, mode, horizon, market, indicator, activeCats, eventId, panelMarket, episodeId]);

  const toggleCat = (id: string) => {
    const next = new Set(cats);
    if (next.has(id)) next.delete(id); else next.add(id);
    setActiveCats(next);
  };

  const events = useMemo(() => data?.meta.events.filter((e) => cats.has(e.category)) ?? [], [data, cats]);
  const markets = market === "all" ? MARKETS : [market];

  const openEvent = useCallback((id: string, m?: Market) => {
    setEpisodeId(null);
    setEventId(id);
    if (m) setPanelMarket(m);
    else if (market !== "all") setPanelMarket(market);
  }, [market]);
  const closeEvent = useCallback(() => setEventId(null), []);
  const openEpisode = useCallback((id: string) => { setEventId(null); setEpisodeId(id); }, []);
  const closeEpisode = useCallback(() => setEpisodeId(null), []);

  if (error) return <main className="page"><p className="error">Could not load data: {error}</p></main>;
  if (!data) return <main className="page"><p className="loading">Loading…</p></main>;

  return (
    <main className="page">
      <header className="header">
        <div className="brand">
          <h1>{SITE_NAME}</h1>
          <p className="tagline">{SITE_TAGLINE}</p>
        </div>
        <Controls mode={mode} setMode={setMode} horizon={horizon} setHorizon={setHorizon}
          categories={data.meta.categories} activeCats={cats} toggleCat={toggleCat}
          market={market} setMarket={setMarket} />
      </header>

      <Legend horizon={horizon} mode={mode} />

      <Heatmap events={events} sectors={data.meta.sectors} markets={markets} episodes={data.meta.episodes}
        reactions={data.reactions} indicators={data.indicators} indicator={indicator} setIndicator={setIndicator}
        mode={mode} horizon={horizon} onEvent={openEvent} onEpisode={openEpisode} />

      <Footer meta={data.meta} />

      {eventId && data.meta.events.some((e) => e.id === eventId) && (
        <EventPanel data={data} eventId={eventId} market={panelMarket} setMarket={setPanelMarket}
          mode={mode} horizon={horizon} onClose={closeEvent} onEpisode={openEpisode} />
      )}
      {episodeId && data.meta.episodes.some((e) => e.id === episodeId) && (
        <EpisodeView data={data} episodeId={episodeId} indicator={indicator} onClose={closeEpisode}
          onEvent={(id) => openEvent(id)} />
      )}
    </main>
  );
}
