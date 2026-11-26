"""Headline links per event from The New York Times and The Guardian → data/news/<event_id>.json.

Stored per headline: title, outlet, date, URL, plus the NYT's own short abstract (shown
with a link to the article) or the Guardian content id. Guardian article text is never
stored here: pipeline.fetch_guardian downloads it at deploy time (the Guardian's terms
allow keeping it for 24 hours at most). Nothing is sent to an AI model.

Window: from 28 days before the announcement to 2 days after, so the coverage of the
event itself is included.

  python -m pipeline.fetch_news                      # events without a news file yet
  python -m pipeline.fetch_news --force              # refetch everything
  python -m pipeline.fetch_news --only lehman_2008 brexit_2016

Keys: NYT_API_KEY (Article Search API), GUARDIAN_API_KEY (Content API).
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
from pipeline.common import DATA, load_events, write_json

NEWS = DATA / "news"
DAYS_BEFORE, DAYS_AFTER = 28, 2
PICK, MAX_PER_SOURCE = 5, 3
NYT, GUARDIAN = "The New York Times", "The Guardian"

GUARDIAN_URL = "https://content.guardianapis.com/search"
NYT_URL = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
GUARDIAN_SECTIONS = "business|world|politics|us-news|money|technology|uk-news|global-development"
NYT_DESKS = ("business", "foreign", "financial", "washington", "politics", "economy", "world", "u.s.", "national", "technology")
NYT_PAUSE = 12.5  # Article Search allows ~5 requests per minute


class Fatal(Exception):
    """Auth or quota errors: stop instead of failing every remaining event."""


def _check(r: requests.Response, name: str) -> None:
    if r.status_code in (401, 403):
        raise Fatal(f"{name}: HTTP {r.status_code} (check the API key and that the API is enabled)")
    if r.status_code == 429:
        raise Fatal(f"{name}: rate limit or daily quota reached")
    r.raise_for_status()


def guardian(keywords: list[str], start: dt.date, end: dt.date, key: str) -> list[dict]:
    q = " OR ".join(f'"{k}"' if " " in k else k for k in keywords)
    params = {"q": q, "from-date": start.isoformat(), "to-date": end.isoformat(),
              "section": GUARDIAN_SECTIONS, "order-by": "relevance", "page-size": 30,
              "show-fields": "headline", "api-key": key}
    r = requests.get(GUARDIAN_URL, params=params, timeout=30)
    _check(r, "Guardian")
    out = []
    for it in r.json()["response"].get("results", []):
        out.append({"title": (it.get("fields") or {}).get("headline") or it["webTitle"],
                    "source": GUARDIAN, "date": it["webPublicationDate"][:10], "url": it["webUrl"], "id": it["id"]})
    return out


def nyt(keywords: list[str], start: dt.date, end: dt.date, key: str) -> list[dict]:
    params = {"q": " ".join(keywords), "begin_date": start.strftime("%Y%m%d"),
              "end_date": end.strftime("%Y%m%d"), "sort": "relevance", "api-key": key}
    r = requests.get(NYT_URL, params=params, timeout=30)
    if r.status_code == 429:  # per-minute limit: wait once and retry
        time.sleep(60)
        r = requests.get(NYT_URL, params=params, timeout=30)
    _check(r, "NYT")
    out = []
    for d in (r.json().get("response") or {}).get("docs") or []:
        desk = (d.get("news_desk") or d.get("section_name") or "").lower()
        if desk and not any(x in desk for x in NYT_DESKS):
            continue
        title = (d.get("headline") or {}).get("main") or ""
        if d.get("web_url") and title:
            out.append({"title": title, "source": NYT, "date": (d.get("pub_date") or "")[:10], "url": d["web_url"],
                        "abstract": (d.get("abstract") or d.get("snippet") or "").strip()})
    return out


def score(item: dict, keywords: list[str], event_date: dt.date) -> float:
    title = item["title"].lower()
    s = sum(2.0 for k in keywords if k.lower() in title)
    try:
        gap = abs((event_date - dt.date.fromisoformat(item["date"])).days)
        s += max(0.0, 1.0 - gap / DAYS_BEFORE)  # closer to the event ranks higher
    except ValueError:
        pass
    return s


def pick(ranked: list[dict]) -> list[dict]:
    chosen, per_source = [], {}
    for c in ranked:
        if per_source.get(c["source"], 0) < MAX_PER_SOURCE:
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

    keys = {GUARDIAN: os.environ.get("GUARDIAN_API_KEY"), NYT: os.environ.get("NYT_API_KEY")}
    if not any(keys.values()):
        print("Set NYT_API_KEY and/or GUARDIAN_API_KEY", file=sys.stderr)
        return 1
    disabled: set[str] = set()
    done = 0
    for ev in load_events():
        eid = ev["id"]
        if args.only and eid not in args.only:
            continue
        path = NEWS / f"{eid}.json"
        if path.exists() and not args.force:
            continue
        day = parse_utc(ev["announced_at_utc"]).date()
        start, end = day - dt.timedelta(days=DAYS_BEFORE), min(day + dt.timedelta(days=DAYS_AFTER), dt.date.today())
        kws = ev.get("news_keywords") or [ev["title"]]
        cands, failed = [], []
        for name, fn in ((GUARDIAN, guardian), (NYT, nyt)):
            if not keys[name] or name in disabled:
                continue
            try:
                cands += fn(kws, start, end, keys[name])
            except Fatal as exc:
                print(f"{eid}: {exc}; skipping {name} from now on", file=sys.stderr)
                disabled.add(name)
                failed.append(name)
            except Exception as exc:
                print(f"{eid}: {name} failed: {exc}", file=sys.stderr)
                failed.append(name)
            if name == NYT:
                time.sleep(NYT_PAUSE)
        if disabled:
            break  # a key or quota problem: stop, nothing more can be fetched in full
        if failed:
            continue  # leave the event for the next run so it gets both outlets
        seen, uniq = set(), []
        for c in cands:
            norm = re.sub(r"\W+", " ", c["title"].lower()).strip()
            if norm and norm not in seen:
                seen.add(norm)
                uniq.append(c)
        uniq.sort(key=lambda c: score(c, kws, day), reverse=True)
        headlines = pick(uniq)
        write_json(path, {"event_id": eid, "window": [start.isoformat(), end.isoformat()],
                          "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                          "sources": [n for n in keys if keys[n]], "headlines": headlines})
        done += 1
        print(f"{eid}: {len(uniq)} found, {len(headlines)} kept")
    print(f"{done} events written")
    return 1 if disabled else 0


if __name__ == "__main__":
    sys.exit(main())
