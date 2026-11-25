"""AI texts per event (spec §8): Context (from headlines) and Analysis (from real numbers).

Writes data/texts.json — the human-reviewed source of truth. New or regenerated texts
always get `reviewed: false`; only `reviewed: true` texts are exported to the site.

Never runs in the browser. Run manually (or via the texts.yml workflow):
  python -m pipeline.generate_texts                 # events missing texts, + stale in-progress analyses
  python -m pipeline.generate_texts --only brexit_2016 --force
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

import anthropic

from pipeline.common import DATA, OUT, load_episodes, load_events, load_sectors, read_json, write_json

TEXTS = DATA / "texts.json"
MODEL = os.environ.get("LLM_MODEL", "claude-opus-5-5")

RULES = """Rules:
- Explain only plausible mechanisms. Do not invent facts, quotes, numbers or dates.
- Use only information present in the input; if the input doesn't support a claim, leave it out.
- Signal uncertainty where it exists (e.g. other news in the same window, small baskets, thin data).
- No investment advice, no predictions, no recommendations.
- Plain English for a general reader. No headings, no bullet points, no markdown."""

CONTEXT_SYSTEM = f"""You write short context notes for a public dashboard that shows how stock-market sectors reacted to political and economic events.
Write 2-3 sentences: what happened, and what the press was saying in the weeks before, based only on the headlines and abstracts provided.
{RULES}"""

ANALYSIS_SYSTEM = f"""You write short analysis notes for a public dashboard that shows how stock-market sectors in the US, Europe and China reacted to political and economic events.
Write 3-4 sentences explaining why sectors plausibly reacted the way the numbers show. Refer to the largest and most telling moves.
"Absolute" is the sector's own return; "vs. market" is the sector return minus its market benchmark's return over the same window.
Longer horizons include other news, so be careful attributing them to this single event.
{RULES}"""


def client() -> anthropic.Anthropic:
    key = os.environ.get("LLM_API_KEY")
    return anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()


def ask(c: anthropic.Anthropic, system: str, user: str) -> str:
    response = c.beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=system,
        output_config={"effort": "medium"},
        # On a safety decline, the API re-runs the request on a fallback model it picks.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": user}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("model declined")
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        raise RuntimeError(f"empty response (stop_reason={response.stop_reason})")
    return text


def fmt_pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:+.1f}%"


def numbers_table(ev_reactions: dict, sectors: dict) -> tuple[str, bool]:
    lines, in_progress = [], False
    names = {s["id"]: s["name"] for s in sectors["sectors"]}
    for sid, by_market in ev_reactions.items():
        for m, r in by_market.items():
            if all(v == "insufficient" for v in r["status"].values()):
                continue
            parts = []
            for h in ("1w", "1m", "3m"):
                st = r["status"][h]
                in_progress |= st == "in_progress"
                tag = " (so far)" if st == "in_progress" else ""
                parts.append(f"{h}: abs {fmt_pct(r['absolute'][h])}, vs mkt {fmt_pct(r['vs_market'][h])}{tag}")
            n = r.get("constituents")
            lines.append(f"{names[sid]} / {m.upper()} (n={n}): " + "; ".join(parts))
    return "\n".join(lines), in_progress


def entry(text: str, **extra) -> dict:
    return {"text": text, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "model": MODEL, "reviewed": False, **extra}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="regenerate even if texts exist")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--dry-run", action="store_true", help="print prompts, don't call the API")
    args = ap.parse_args()

    events = load_events()
    episodes = {e["id"]: e["title"] for e in load_episodes()}
    sectors = load_sectors()
    # Fresh local build if present, else the published (committed) copy.
    reactions = read_json(DATA / "derived" / "reactions.json") or read_json(OUT / "reactions.json", {})
    texts = read_json(TEXTS, {})
    today = dt.date.today().isoformat()
    c = None if args.dry_run else client()

    for ev in events:
        eid = ev["id"]
        if args.only and eid not in args.only:
            continue
        cur = texts.setdefault(eid, {})
        news = read_json(DATA / "news" / f"{eid}.json", {})
        headlines = news.get("headlines", [])
        if headlines:
            cur["headlines"] = [{k: h[k] for k in ("title", "source", "date", "url")} for h in headlines]
        header = (f"Event: {ev['title']}\nAnnounced (UTC): {ev['announced_at_utc']}\nCategory: {ev['category']}\n"
                  + (f"Episode: {episodes[ev['episode_id']]}\n" if ev.get("episode_id") else "")
                  + f"Description: {ev.get('description', '')}\n")

        # Context
        if headlines and (args.force or "context" not in cur):
            press = "\n".join(f"- [{h['source']}, {h['date']}] {h['title']} — {h['abstract']}" for h in news.get("candidates", [])[:12])
            prompt = f"{header}\nPress coverage in the four weeks before the event:\n{press}"
            if args.dry_run:
                print(f"--- CONTEXT {eid}\n{prompt}\n")
            else:
                try:
                    cur["context"] = entry(ask(c, CONTEXT_SYSTEM, prompt))
                    print(f"{eid}: context ✓")
                except Exception as exc:
                    print(f"{eid}: context failed: {exc}", file=sys.stderr)

        # Analysis
        if eid not in reactions:
            continue
        table, in_progress = numbers_table(reactions[eid], sectors)
        # An "as of" analysis is regenerated once all horizons have closed (spec §8.2).
        stale = bool(cur.get("analysis", {}).get("as_of")) and not in_progress
        if args.force or "analysis" not in cur or stale:
            prompt = (f"{header}\nSector reactions (returns in local currency, base = last close before the announcement):\n"
                      f"{table}")
            if in_progress:
                prompt += f"\n\nSome horizons have not finished yet; describe them as 'as of {today}'."
            if args.dry_run:
                print(f"--- ANALYSIS {eid}\n{prompt}\n")
            else:
                try:
                    extra = {"as_of": today} if in_progress else {}
                    cur["analysis"] = entry(ask(c, ANALYSIS_SYSTEM, prompt), **extra)
                    print(f"{eid}: analysis ✓")
                except Exception as exc:
                    print(f"{eid}: analysis failed: {exc}", file=sys.stderr)

        if not args.dry_run:
            write_json(TEXTS, texts)  # save as we go
    if not args.dry_run:
        # pretty-print for human review in PRs
        with open(TEXTS, "w", encoding="utf-8") as f:
            json.dump(texts, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
