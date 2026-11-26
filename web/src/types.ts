export type Market = "us" | "eu" | "cn";
export type Horizon = "1w" | "1m" | "3m";
export type Mode = "absolute" | "vs_market";
export type Status = "ok" | "insufficient" | "in_progress";
export type IndicatorKey = "epu" | "gpr" | "vix";

export interface SectorMeta {
  id: string;
  name: string;
  note: string | null;
  markets: Record<Market, { type: "etf" | "basket"; tickers: string[]; benchmark: string }>;
}

export interface EpisodeMeta {
  id: string;
  title: string;
  start: string;
  end: string | null;
}

export interface EventMeta {
  id: string;
  title: string;
  announced_at_utc: string;
  category: string;
  episode_id: string | null;
  description: string | null;
  timing: string | null;
  verified: boolean;
  official_sources: { label: string; url: string }[];
}

export interface Meta {
  generated_at: string;
  data_through: string | null;
  markets: Record<Market, { name: string; flag: string; benchmark: string }>;
  sectors: SectorMeta[];
  categories: { id: string; name: string }[];
  episodes: EpisodeMeta[];
  events: EventMeta[];
}

type ByHorizon<T> = Record<Horizon, T>;

export interface Reaction {
  base_date: string | null;
  day0: string | null;
  absolute: ByHorizon<number | null>;
  vs_market: ByHorizon<number | null>;
  benchmark: ByHorizon<number | null>;
  end_dates: ByHorizon<string | null>;
  status: ByHorizon<Status>;
  status_vs_market: ByHorizon<Status>;
  constituents: number | null;
}

export type Reactions = Record<string, Record<string, Record<Market, Reaction>>>;

export interface EpisodeStats {
  drawdown: number | null;
  peak_date: string | null;
  trough_date: string | null;
  total_return: number | null;
  bench_total_return: number | null;
  from_date: string | null;
  partial?: boolean;
  status: Status;
}
export type EpisodesStats = Record<string, Record<string, Record<Market, EpisodeStats>>>;

export interface Indicator {
  label: string;
  short: string;
  note: string;
  source: string;
  dates: string[];
  values: number[];
}
export type Indicators = Partial<Record<IndicatorKey, Indicator>>;

export interface AIText {
  text: string;
  written_at: string;
  author: string;
  as_of?: string;
}
export interface EventTexts {
  headlines?: { title: string; source: string; date: string; url: string }[];
  context?: AIText;
  analysis?: AIText;
}
export type Texts = Record<string, EventTexts>;

export interface EventPath {
  offsets: number[];
  dates: string[];
  sector: (number | null)[];
  benchmark: (number | null)[];
}
export type EventSeries = Record<string, Partial<Record<Market, EventPath>>>;

export interface EpisodePath {
  dates: string[];
  sector: (number | null)[];
  benchmark: (number | null)[];
}
export type EpisodeSeries = Record<string, Partial<Record<Market, EpisodePath>>>;

export interface AppData {
  meta: Meta;
  reactions: Reactions;
  episodes: EpisodesStats;
  indicators: Indicators;
  texts: Texts;
}
