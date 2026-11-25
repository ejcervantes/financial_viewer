"""Reactions per event × sector × market (2 modes × 3 horizons) and episode drawdowns.

Outputs (data/derived/):
  reactions.json          spec §10.3 shape (+ status_vs_market, dates per horizon)
  event_series/<id>.json  per-event daily paths from t-5 to t+63 for the detail chart
  episodes.json           drawdown + total return per sector × market, per episode
  episode_series/<id>.json daily normalized paths for the episode view
"""
from __future__ import annotations

import datetime as dt
import math

import pandas as pd

from pipeline.calendar_rules import Session, anchor, parse_utc
from pipeline.common import DATA, HORIZONS, RAW, load_episodes, load_events, load_sectors, market_spec, write_json

DERIVED = DATA / "derived"
PRE_WINDOW = 5      # sessions before day 0 shown in the event chart
MAX_H = max(HORIZONS.values())


def r4(x: float | None) -> float | None:
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 5)


class SeriesView:
    """One sector × market series restricted to its own calendar."""

    def __init__(self, df: pd.DataFrame, key: str, spec: dict):
        cols = {c.split("|")[2]: df[c] for c in df.columns if c.startswith(key + "|")}
        frame = pd.DataFrame(cols)
        frame = frame[frame["cal"] == 1.0]
        self.dates = frame.index
        self.level = frame["level"].to_numpy()
        self.n = frame["n"].to_numpy()
        self.bench = frame["bench"].to_numpy()
        self.min_n = spec["min_constituents"]
        self.session = Session(spec["timezone"], spec["open"], spec["close"])

    def sufficient(self, i0: int, i1: int) -> bool:
        """Every daily return in (i0, i1] has enough constituents, and the base level exists."""
        if i0 < 0 or i1 <= i0:
            return False
        return bool((self.n[i0:i1 + 1] >= self.min_n).all())

    def bench_ok(self, i0: int, i1: int) -> bool:
        b = self.bench[[i0, i1]]
        return not (math.isnan(b[0]) or math.isnan(b[1]))

    def ret(self, i0: int, i1: int) -> float:
        return self.level[i1] / self.level[i0] - 1

    def bret(self, i0: int, i1: int) -> float:
        return self.bench[i1] / self.bench[i0] - 1

    def day(self, i: int) -> str:
        return self.dates[i].date().isoformat()


def reaction(sv: SeriesView, announced: dt.datetime) -> tuple[dict, dict | None]:
    a = anchor(announced, sv.dates, sv.session)
    last = len(sv.dates) - 1
    out = {
        "base_date": sv.day(a.base_idx) if a.base_idx is not None else None,
        "day0": sv.day(a.day0_idx) if a.day0_idx is not None else None,
        "absolute": {}, "vs_market": {}, "benchmark": {},
        "end_dates": {}, "status": {}, "status_vs_market": {},
        "constituents": int(sv.n[a.day0_idx]) if a.day0_idx is not None else None,
    }
    path = None
    b = a.base_idx
    if b is None:  # event predates the series
        out["day0"] = out["constituents"] = None
        for h in HORIZONS:
            for k in ("absolute", "vs_market", "benchmark", "end_dates"):
                out[k][h] = None
            out["status"][h] = out["status_vs_market"][h] = "insufficient"
        return out, None

    for h, n_sess in HORIZONS.items():
        if a.day0_idx is None:  # announcement after the latest available session
            end, status = None, "in_progress"
        else:
            target = a.day0_idx + n_sess
            end, status = (target, "ok") if target <= last else (last, "in_progress")
        if end is None or not sv.sufficient(b, end):
            out["absolute"][h] = out["vs_market"][h] = out["benchmark"][h] = None
            out["end_dates"][h] = sv.day(end) if end is not None else None
            out["status"][h] = "in_progress" if end is None else "insufficient"
            out["status_vs_market"][h] = out["status"][h]
            continue
        r = sv.ret(b, end)
        out["absolute"][h] = r4(r)
        out["end_dates"][h] = sv.day(end)
        out["status"][h] = status
        if sv.bench_ok(b, end):
            br = sv.bret(b, end)
            out["benchmark"][h] = r4(br)
            out["vs_market"][h] = r4(r - br)
            out["status_vs_market"][h] = status
        else:
            out["benchmark"][h] = out["vs_market"][h] = None
            out["status_vs_market"][h] = "insufficient"

    # Daily path for the detail chart: offsets -PRE_WINDOW .. +MAX_H relative to day 0,
    # cumulative return vs the base close.
    if a.day0_idx is not None and sv.n[b] >= sv.min_n:
        i_start = max(a.day0_idx - PRE_WINDOW, 0)
        i_end = min(a.day0_idx + MAX_H, last)
        offs, sec, ben = [], [], []
        for i in range(i_start, i_end + 1):
            if i > b and sv.n[i] < sv.min_n:
                break
            offs.append(i - a.day0_idx)
            sec.append(r4(sv.level[i] / sv.level[b] - 1))
            ben.append(r4(sv.bench[i] / sv.bench[b] - 1) if not math.isnan(sv.bench[b]) and not math.isnan(sv.bench[i]) else None)
        # If the pre-window crosses the series' start, values before base would be meaningless.
        path = {"offsets": offs, "sector": sec, "benchmark": ben,
                "dates": [sv.day(i_start + k) for k in range(len(offs))]}
    return out, path


def max_drawdown(levels: pd.Series) -> float:
    peak = levels.cummax()
    return float((levels / peak - 1).min())


def episode_stats(sv: SeriesView, start: dt.date, end: dt.date | None) -> tuple[dict, dict | None]:
    dates = sv.dates
    i0 = dates.searchsorted(pd.Timestamp(start), side="left") - 1  # last close before the start
    i1 = (dates.searchsorted(pd.Timestamp(end), side="right") - 1) if end else len(dates) - 1
    in_progress = end is None
    empty = {"drawdown": None, "total_return": None, "trough_date": None, "peak_date": None,
             "bench_total_return": None, "from_date": None, "status": "insufficient"}
    if i1 <= 0:
        return empty, None
    i0 = max(i0, 0)
    partial = False
    if not sv.sufficient(i0, i1):
        # The series starts (or regains coverage) inside the episode: use the longest
        # fully covered tail, if it spans at least a quarter of the episode.
        bad = [i for i in range(i0, i1 + 1) if sv.n[i] < sv.min_n]
        i0_new = bad[-1] + 1
        if i1 - i0_new < max(20, (i1 - i0) // 4):
            return empty, None
        i0, partial = i0_new, True
    lv = pd.Series(sv.level[i0:i1 + 1], index=dates[i0:i1 + 1])
    dd_series = lv / lv.cummax() - 1
    trough = dd_series.idxmin()
    peak = lv.loc[:trough].idxmax()
    stats = {
        "drawdown": r4(dd_series.min()),
        "peak_date": peak.date().isoformat(),
        "trough_date": trough.date().isoformat(),
        "total_return": r4(sv.ret(i0, i1)),
        "bench_total_return": r4(sv.bret(i0, i1)) if sv.bench_ok(i0, i1) else None,
        "from_date": sv.day(i0),
        "partial": partial,
        "status": "in_progress" if in_progress else "ok",
    }
    path = {
        "dates": [d.date().isoformat() for d in lv.index],
        "sector": [r4(x) for x in (lv / lv.iloc[0] - 1)],
        "benchmark": [r4(sv.bench[i] / sv.bench[i0] - 1) if sv.bench_ok(i0, i) else None for i in range(i0, i1 + 1)],
    }
    return stats, path


def main() -> None:
    cfg = load_sectors()
    events = load_events()
    episodes = load_episodes()
    df = pd.read_parquet(RAW / "series.parquet")

    views: dict[tuple[str, str], SeriesView] = {}
    for sector in cfg["sectors"]:
        for m in sector["markets"]:
            views[(sector["id"], m)] = SeriesView(df, f"{sector['id']}|{m}", market_spec(cfg, sector, m))

    reactions: dict = {}
    for ev in events:
        announced = parse_utc(ev["announced_at_utc"])
        reactions[ev["id"]] = {}
        paths: dict = {}
        for (sid, m), sv in views.items():
            out, path = reaction(sv, announced)
            reactions[ev["id"]].setdefault(sid, {})[m] = out
            if path:
                paths.setdefault(sid, {})[m] = path
        write_json(DERIVED / "event_series" / f"{ev['id']}.json", paths)
    write_json(DERIVED / "reactions.json", reactions)

    ep_out: dict = {}
    for ep in episodes:
        start = ep["start"] if isinstance(ep["start"], dt.date) else dt.date.fromisoformat(str(ep["start"]))
        end = ep.get("end")
        end = end if (end is None or isinstance(end, dt.date)) else dt.date.fromisoformat(str(end))
        ep_out[ep["id"]] = {}
        paths = {}
        for (sid, m), sv in views.items():
            stats, path = episode_stats(sv, start, end)
            ep_out[ep["id"]].setdefault(sid, {})[m] = stats
            if path:
                paths.setdefault(sid, {})[m] = path
        write_json(DERIVED / "episode_series" / f"{ep['id']}.json", paths)
    write_json(DERIVED / "episodes.json", ep_out)

    # Coverage summary
    total = ok = 0
    for ev in reactions.values():
        for sec in ev.values():
            for r in sec.values():
                total += 1
                ok += r["status"]["1w"] != "insufficient"
    print(f"{len(events)} events, {len(episodes)} episodes; 1W cells with data: {ok}/{total}")


if __name__ == "__main__":
    main()
