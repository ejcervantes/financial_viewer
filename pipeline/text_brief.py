"""Compact brief of an event's numbers, for writing its Context and Analysis by hand (spec §8).

No API calls. Texts are written in data/texts.json (see README → "Event texts").

  python -m pipeline.text_brief                 # events with missing or stale texts
  python -m pipeline.text_brief lehman_2008     # brief for specific events
  python -m pipeline.text_brief --all
"""
from __future__ import annotations

import argparse

from pipeline.common import DATA, HORIZONS, OUT, load_episodes, load_events, load_sectors, read_json


def pct(x: float | None) -> str:
    return "  n/a" if x is None else f"{x * 100:+5.1f}"


def needs_text(eid: str, texts: dict, reactions: dict) -> bool:
    t = texts.get(eid, {})
    if "context" not in t or "analysis" not in t:
        return True
    # An "as of" analysis must be rewritten once every horizon has closed (spec §8.2).
    return bool(t["analysis"].get("as_of")) and not in_progress(reactions.get(eid, {}))


def in_progress(ev_reactions: dict) -> bool:
    return any(st == "in_progress" for sec in ev_reactions.values() for r in sec.values() for st in r["status"].values())


def brief(ev: dict, ev_reactions: dict, sectors: dict, episodes: dict) -> str:
    names = {s["id"]: s["name"] for s in sectors["sectors"]}
    hs = list(HORIZONS)
    out = [f"## {ev['id']} — {ev['title']}",
           f"{ev['announced_at_utc']} · {ev['category']}" + (f" · {episodes[ev['episode_id']]}" if ev.get("episode_id") else ""),
           ev.get("description", "")]
    # Benchmarks, taken from the first sector that has them.
    for m in ("us", "eu", "cn"):
        for sec in ev_reactions.values():
            r = sec.get(m)
            if r and r["benchmark"].get("1w") is not None:
                out.append(f"  bench {m.upper()}  day0 {r['day0']}  " + " ".join(f"{h} {pct(r['benchmark'][h])}" for h in hs))
                break
    out.append("  sector        mkt  n   abs " + " ".join(f"{h:>5}" for h in hs) + "   vs " + " ".join(f"{h:>5}" for h in hs))
    for sid, by_m in ev_reactions.items():
        for m, r in by_m.items():
            if all(v == "insufficient" for v in r["status"].values()):
                continue
            flag = " *" if any(v == "in_progress" for v in r["status"].values()) else ""
            out.append(f"  {names[sid]:<13} {m.upper():<3} {r['constituents'] or '-':>2}      "
                       + " ".join(pct(r["absolute"][h]) for h in hs) + "      "
                       + " ".join(pct(r["vs_market"][h]) for h in hs) + flag)
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    reactions = read_json(DATA / "derived" / "reactions.json") or read_json(OUT / "reactions.json", {})
    texts = read_json(DATA / "texts.json", {})
    sectors, episodes = load_sectors(), {e["id"]: e["title"] for e in load_episodes()}
    for ev in load_events():
        eid = ev["id"]
        if args.ids and eid not in args.ids:
            continue
        if not args.ids and not args.all and not needs_text(eid, texts, reactions):
            continue
        print(brief(ev, reactions.get(eid, {}), sectors, episodes) + "\n")
    print("(* = horizon still in progress; returns in %, local currency, base = last close before the announcement)")


if __name__ == "__main__":
    main()
