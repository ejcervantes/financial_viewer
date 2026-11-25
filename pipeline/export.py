"""Assemble the JSON the site reads → web/public/data/.

  meta.json        sectors, markets, categories, episodes, events (+ generated_at)
  reactions.json   compact reactions per event
  episodes.json    drawdowns per episode
  indicators.json  EPU / GPR / VIX
  texts.json       ONLY reviewed texts; headlines always
  events/<id>.json daily paths for the detail chart
  episodes/<id>.json daily paths for the episode view
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil

from pipeline.calendar_rules import parse_utc
from pipeline.common import DATA, OUT, load_episodes, load_events, load_sectors, read_json, write_json

CATEGORIES = [
    {"id": "elections", "name": "Elections"},
    {"id": "trade", "name": "Trade"},
    {"id": "geopolitics", "name": "Geopolitics"},
    {"id": "central_banks", "name": "Central Banks"},
    {"id": "crises", "name": "Crises & Bubbles"},
]


def iso(v) -> str | None:
    if v is None:
        return None
    return v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else str(v)


def export_texts() -> dict:
    """Publish only reviewed texts (spec §8.2); headlines are links and always published."""
    texts = read_json(DATA / "texts.json", {})
    public = {}
    for eid, t in texts.items():
        out = {"headlines": t.get("headlines", [])}
        for kind in ("context", "analysis"):
            item = t.get(kind)
            if item and item.get("reviewed"):
                out[kind] = {k: item[k] for k in ("text", "generated_at", "model", "as_of") if k in item}
        public[eid] = out
    write_json(OUT / "texts.json", public)
    return public


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--texts-only", action="store_true", help="only rebuild texts.json (used by deploy)")
    if ap.parse_args().texts_only:
        public = export_texts()
        print(f"texts.json: {sum(1 for t in public.values() if 'analysis' in t)} reviewed analyses")
        return
    derived = DATA / "derived"
    cfg = load_sectors()
    events = sorted(load_events(), key=lambda e: parse_utc(e["announced_at_utc"]))
    episodes = load_episodes()
    coverage = read_json(DATA / "raw" / "ticker_coverage.json", {})

    markets = {k: {"name": v["name"], "flag": v["flag"], "benchmark": v["benchmark"]} for k, v in cfg["markets"].items()}
    sectors = []
    for s in cfg["sectors"]:
        sectors.append({
            "id": s["id"], "name": s["name"], "note": s.get("note"),
            "markets": {m: {"type": spec["type"], "tickers": spec["tickers"],
                            "benchmark": spec.get("benchmark", cfg["markets"][m]["benchmark"])}
                        for m, spec in s["markets"].items()},
        })

    meta = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "data_through": max((c["last"] for c in coverage.get("coverage", {}).values()), default=None),
        "markets": markets,
        "sectors": sectors,
        "categories": CATEGORIES,
        "episodes": [{"id": e["id"], "title": e["title"], "start": iso(e["start"]), "end": iso(e.get("end"))} for e in episodes],
        "events": [{
            "id": e["id"], "title": e["title"], "announced_at_utc": parse_utc(e["announced_at_utc"]).isoformat().replace("+00:00", "Z"),
            "category": e["category"], "episode_id": e.get("episode_id"), "description": e.get("description"),
            "timing": e.get("timing"), "verified": bool(e.get("verified")),
            "official_sources": e.get("official_sources") or [],
        } for e in events],
    }
    write_json(OUT / "meta.json", meta)

    for name in ("reactions.json", "episodes.json", "indicators.json"):
        write_json(OUT / name, read_json(derived / name, {}))

    public = export_texts()

    for sub_in, sub_out in (("event_series", "events"), ("episode_series", "episodes")):
        dst = OUT / sub_out
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True)
        for f in (derived / sub_in).glob("*.json"):
            shutil.copy(f, dst / f.name)

    n_rev = sum(1 for t in public.values() if "analysis" in t)
    print(f"exported {len(events)} events, {len(episodes)} episodes, {n_rev} reviewed analyses → {OUT}")


if __name__ == "__main__":
    main()
