"""Press coverage in the 4 weeks before each event (spec §6) → data/news/<event_id>.json.

Sources: The Guardian Open Platform and NYT Article Search. Only headline, abstract,
date, URL and source are stored — never article bodies.

Usage:
  python -m pipeline.fetch_news              # events without a news file yet
  python -m pipeline.fetch_news --force      # refetch everything
  python -m pipeline.fetch_news --only lehman_2008 brexit_2016
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
import time

import requests

from pipeline.calendar_rules import parse_utc
from pipeline.common import DATA, load_events, read_json, write_json

NEWS = DATA / "news"
WINDOW_DAYS = 28
MAX_CANDIDATES = 20
PICK = 5
MAX_PER_SOURCE = 3

GUARDIAN_URL = "https://content.guardianapis.com/search"
NYT_URL = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
GUARDIAN_SECTIONS = "business|world|politics|us-news|money|technology|uk-news"
NYT_DESKS = ("Business", "Foreign", "Financial", "Washington", "Politics", "Business Day", "Economy", "World", "U.S.")


def _query(keywords: list[str]) -> str:
    return " OR ".join(f'"{k}"' if " " in k else k for k in keywords)


def guardian(keywords: list[str], start: dt.date, end: dt.date, key: str) -> list[dict]:
    params = {
        "q": _query(keywords), "from-date": start.isoformat(), "to-date": end.isoformat(),
        "section": GUARDIAN_SECTIONS, "order-by": "relevance", "page-size": 30,
        "show-fields": "trailText,headline", "api-key": key,
    }
    r = requests.get(GUARDIAN_URL, params=params, timeout=30)
    r.raise_for_status()
    out = []
    for it in r.json()["response"].get("results", []):
        f = it.get("fields", {})
        out.append({
            "title": f.get("headline") or it["webTitle"],
            "abstract": re.sub(r"<[^>]+>", "", f.get("trailText", "")),
            "date": it["webPublicationDate"][:10],
            "url": it["webUrl"],
            "source": "Guardian",
        })
    return out


def nyt(keywords: list[str], start: dt.date, end: dt.date, key: str) -> list[dict]:
    out = []
    for page in (0, 1):
        params = {
            "q": " ".join(keywords), "begin_date": start.strftime("%Y%m%d"), "end_date": end.strftime("%Y%m%d"),
            "sort": "relevance", "page": page, "api-key": key,
        }
        r = requests.get(NYT_URL, params=params, timeout=30)
        if r.status_code == 429:
            time.sleep(12)
            r = requests.get(NYT_URL, params=params, timeout=30)
        r.raise_for_status()
        docs = (r.json().get("response") or {}).get("docs") or []
        for d in docs:
            desk = d.get("news_desk") or d.get("section_name") or ""
            if desk and not any(x.lower() in desk.lower() for x in NYT_DESKS):
                continue
            out.append({
                "title": (d.get("headline") or {}).get("main", ""),
                "abstract": d.get("abstract") or d.get("snippet") or d.get("lead_paragraph", ""),
                "date": (d.get("pub_date") or "")[:10],
                "url": d.get("web_url"),
                "source": "NYT",
            })
        time.sleep(12)  # NYT allows ~5 requests/minute
        if len(docs) < 10:
            break
    return out


def score(item: dict, keywords: list[str], event_date: dt.date) -> float:
    title, abstract = item["title"].lower(), item["abstract"].lower()
    s = 0.0
    for k in keywords:
        k = k.lower()
        s += 2.0 * (k in title) + 1.0 * (k in abstract)
    try:
        days_before = (event_date - dt.date.fromisoformat(item["date"])).days
        s += max(0.0, 1.0 - days_before / WINDOW_DAYS)  # closer to the event is more relevant
    except ValueError:
        pass
    return s


def pick(cands: list[dict]) -> list[dict]:
    chosen, per_source = [], {}
    for c in cands:
        if per_source.get(c["source"], 0) >= MAX_PER_SOURCE:
            continue
        chosen.append(c)
        per_source[c["source"]] = per_source.get(c["source"], 0) + 1
        if len(chosen) == PICK:
            break
    return sorted(chosen, key=lambda c: c["date"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()

    g_key, n_key = os.environ.get("GUARDIAN_API_KEY"), os.environ.get("NYT_API_KEY")
    if not (g_key or n_key):
        print("Set GUARDIAN_API_KEY and/or NYT_API_KEY", file=sys.stderr)
        return 1

    for ev in load_events():
        if args.only and ev["id"] not in args.only:
            continue
        path = NEWS / f"{ev['id']}.json"
        if path.exists() and not args.force:
            continue
        a = parse_utc(ev["announced_at_utc"])
        end = a.date()
        start = end - dt.timedelta(days=WINDOW_DAYS)
        kws = ev.get("news_keywords") or [ev["title"]]
        cands: list[dict] = []
        for name, fn, key in (("Guardian", guardian, g_key), ("NYT", nyt, n_key)):
            if not key:
                continue
            try:
                cands += fn(kws, start, end, key)
            except Exception as exc:
                print(f"{ev['id']}: {name} failed: {exc}", file=sys.stderr)
        seen, uniq = set(), []
        for c in cands:
            norm = re.sub(r"\W+", " ", c["title"].lower()).strip()
            if c["url"] and norm and norm not in seen:
                seen.add(norm)
                uniq.append(c)
        uniq.sort(key=lambda c: score(c, kws, end), reverse=True)
        uniq = uniq[:MAX_CANDIDATES]
        write_json(path, {
            "event_id": ev["id"], "window": [start.isoformat(), end.isoformat()],
            "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "candidates": uniq, "headlines": pick(uniq),
        })
        print(f"{ev['id']}: {len(uniq)} candidates, {len(pick(uniq))} headlines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
