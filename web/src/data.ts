import type { AppData, EpisodeSeries, EventSeries } from "./types";

const base = `${import.meta.env.BASE_URL}data/`;

async function get<T>(path: string): Promise<T> {
  const r = await fetch(base + path);
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json() as Promise<T>;
}

export async function loadAll(): Promise<AppData> {
  const [meta, reactions, episodes, indicators, texts] = await Promise.all([
    get<AppData["meta"]>("meta.json"),
    get<AppData["reactions"]>("reactions.json"),
    get<AppData["episodes"]>("episodes.json"),
    get<AppData["indicators"]>("indicators.json"),
    get<AppData["texts"]>("texts.json"),
  ]);
  return { meta, reactions, episodes, indicators, texts };
}

const cache = new Map<string, Promise<unknown>>();
function cached<T>(path: string): Promise<T> {
  if (!cache.has(path)) cache.set(path, get<T>(path).catch((e) => { cache.delete(path); throw e; }));
  return cache.get(path) as Promise<T>;
}

export const loadEventSeries = (id: string) => cached<EventSeries>(`events/${id}.json`);
export const loadEpisodeSeries = (id: string) => cached<EpisodeSeries>(`episodes/${id}.json`);
