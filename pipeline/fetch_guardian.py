"""Full text of the Guardian headlines in data/news → web/public/data/guardian.json (deploy time only).

The Guardian Open Platform terms (developer key) allow publishing the article text on
this site, but OP Content must not be kept for more than 24 hours. So:
  * this file is written only inside the deploy job and is git-ignored, never committed;
  * deploy.yml runs at least once a day, replacing the published copy;
  * the text is shown unedited, with headline, byline, copyright notice, a link to the
    original and the "Powered by The Guardian" logo (web/src/components/ArticleModal.tsx).
Never pass this text to an AI model (terms §6(g)).

If the key is missing or the API fails, an empty file is written and the site falls back
to plain links.

  GUARDIAN_API_KEY=… python -m pipeline.fetch_guardian
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

import requests

from pipeline.common import DATA, OUT

URL = "https://content.guardianapis.com/search"
BATCH = 50  # max page-size
FIELDS = "headline,byline,body,firstPublicationDate"


def guardian_ids() -> list[str]:
    ids = []
    for f in sorted((DATA / "news").glob("*.json")):
        for h in json.loads(f.read_text()).get("headlines", []):
            if h.get("id") and h["id"] not in ids:
                ids.append(h["id"])
    return ids


def fetch(ids: list[str], key: str) -> dict:
    articles = {}
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        r = requests.get(URL, params={"ids": ",".join(chunk), "page-size": BATCH,
                                      "show-fields": FIELDS, "api-key": key}, timeout=60)
        r.raise_for_status()
        for it in r.json()["response"].get("results", []):
            f = it.get("fields") or {}
            if not f.get("body"):
                continue
            articles[it["id"]] = {
                "headline": f.get("headline") or it.get("webTitle"),
                "byline": f.get("byline") or "",
                "date": (f.get("firstPublicationDate") or it.get("webPublicationDate") or "")[:10],
                "url": it["webUrl"],
                "body": f["body"],
            }
    return articles


def main() -> int:
    out = OUT / "guardian.json"
    payload = {"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "articles": {}}
    key = os.environ.get("GUARDIAN_API_KEY")
    ids = guardian_ids()
    if not key:
        print("GUARDIAN_API_KEY not set: Guardian headlines will show as links only", file=sys.stderr)
    elif ids:
        try:
            payload["articles"] = fetch(ids, key)
        except Exception as exc:  # never block a deploy on this
            print(f"Guardian fetch failed: {exc}", file=sys.stderr)
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"guardian.json: {len(payload['articles'])}/{len(ids)} articles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
