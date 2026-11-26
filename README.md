# Sector Reactions *(working name)*

A one-page dashboard showing how 8 sectors in 3 markets (US, Europe, China) reacted to elections, trade, geopolitical, central-bank and crisis events since 1998. Spec: [`spec-dashboard-eventos.md`](spec-dashboard-eventos.md).

The site is static (GitHub Pages). A daily GitHub Actions job downloads prices from Yahoo Finance, recomputes everything, commits the JSON under `web/public/data/` and redeploys. The browser never calls Yahoo or any API.

## Layout

```
config/            sectors.yaml · events.yaml · episodes.yaml   ← curated inputs
pipeline/          fetch_prices → build_series → compute_reactions → fetch_indicators → export
                   text_brief (numbers per event, to write its texts) · fetch_news (headline links)
tests/             day-0 rule (spec §3.4) and dynamic baskets
data/texts.json    Context + Analysis per event (committed, source of truth)
data/news/         headline links per event: NYT + Guardian (committed)
web/               Vite + React + TypeScript + ECharts; reads web/public/data/*.json
.github/workflows/ daily.yml · news.yml · deploy.yml
```

## Run locally

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/python -m pipeline.fetch_prices && .venv/bin/python -m pipeline.build_series && .venv/bin/python -m pipeline.compute_reactions && .venv/bin/python -m pipeline.fetch_indicators && .venv/bin/python -m pipeline.export
```

```bash
.venv/bin/python -m pytest -q tests
```

```bash
cd web && npm install && npm run dev
```

## Event texts

Context and Analysis are written by Claude in a Claude Code session, not through an API: no keys, no cost per call. To add or refresh texts, ask Claude Code to write them; it starts from:

```bash
.venv/bin/python -m pipeline.text_brief
```

That prints, for every event missing a text (or with an "as of" analysis whose horizons have now closed), the event and its returns per sector × market. Texts go in `data/texts.json` (`context` and `analysis`, each with `text`, `written_at`, `author`, `reviewed`, and `as_of` while a horizon is still open). `reviewed: true` publishes a text; set it to `false` to hide one. Then run `python -m pipeline.export --texts-only`, or just push: the deploy rebuilds `texts.json`.

Rules for the texts (spec §8): explain only plausible mechanisms, cite the real numbers, flag other news in the same window and small baskets, no invented facts, no advice or predictions.

## Headlines and the article window

Each event lists up to 5 headlines (at most 3 per outlet) from The New York Times (Article Search API) and The Guardian (Content API), published between 28 days before and 2 days after the announcement. Clicking one opens a reader window:

- **NYT:** headline, date, the NYT's own short abstract and a button to the full article on nytimes.com. The NYT doesn't allow its pages inside other sites, and its API has no article text.
- **Guardian:** the full article text, unedited, with headline, byline, copyright notice, a link to the original and the "Powered by The Guardian" logo, as the Guardian Open Platform terms require for the free developer key (non-commercial use only).

The Guardian terms allow keeping article text for **24 hours at most**. So the text is never stored in the repo: `pipeline.fetch_guardian` downloads it inside the deploy job into `web/public/data/guardian.json` (git-ignored), and `deploy.yml` runs every day at 05:00 UTC to replace it. If that daily deploy stops running, the published text would go stale; take the site down or remove the Guardian key until it runs again. Never pass Guardian text to an AI model (terms §6(g)).

`data/news/<event>.json` (committed) stores only title, outlet, date, URL, the NYT abstract and the Guardian content id. In GitHub: **Actions → news → Run workflow** (empty `only` = every event without headlines; tick `force` to refetch all). It commits `data/news/` and redeploys. A full run takes about 20 minutes because of the NYT rate limit (~5 requests/minute, 500/day). Locally:

```bash
NYT_API_KEY=… GUARDIAN_API_KEY=… .venv/bin/python -m pipeline.fetch_news --only lehman_2008
```

## GitHub setup

1. **Settings → Pages → Source: GitHub Actions.**
2. **Settings → Secrets → Actions** (repository secrets): `NYT_API_KEY` (the app's Key, not its Secret) and `GUARDIAN_API_KEY`; optionally `FRED_API_KEY` (EPU falls back to FRED's public CSV, then to policyuncertainty.com).
3. **Settings → Actions → General:** allow workflows to *read and write* (the daily job commits data).

## Decisions and deviations from the spec

| Topic | What was done | Why |
|---|---|---|
| China Defense benchmark | Shanghai Composite `000001.SS` instead of CSI 300 | `000300.SS` has only 1 day of history on Yahoo; no other CSI 300 symbol works |
| Dongfeng `0489.HK` | Removed from China Auto basket (4 names left) | Delisted from HKEX; no Yahoo data |
| Europe coverage | Starts 2008-01, not ~2001 | Yahoo's history for the iShares STOXX sector ETFs (`EXV*`, `EXH*`, `EXSA`) begins 2008-01-02. EU Defense (a basket of single stocks) goes back to 1998 |
| US Auto | From 2010-06 | Needs ≥2 of TSLA/GM/F; GM relisted Nov 2010, TSLA listed Jun 2010 |
| Horizon count | t_h = day 0 + 5 / 21 / 63 sessions | Literal reading of spec §5.2 ("sessions after day 0") |
| Basket calendar | The benchmark's sessions; before the benchmark exists, the union of constituents' sessions | Keeps Shanghai holidays from becoming Hong Kong sessions in mixed baskets. Stale prices carry at most 5 sessions |
| Episode drawdown with late data | Computed on the covered tail and marked † with its start date | Otherwise Europe is blank for the GFC (ETFs start Jan 2008) |
| Tone line | Daily series on a non-linear axis: each event column sits at its date; the data between two events is stretched to fit between their columns | Makes the line line up with the event columns (spec §7). EPU and GPR shown as 7-day averages |
| Reactions JSON | Adds `status_vs_market` and `end_dates` per horizon | A sector can have data while its benchmark doesn't (e.g. EU Defense before 2008) |

## Still to do (spec §12)

- [ ] **Project name** — change `web/src/config.ts` and `web/index.html`
- [ ] **Verify every event's date and UTC time** against a primary source. All events in `config/events.yaml` are `verified: false`; times are estimates from the spec's WE/AC/ID notes. ⚠ items: Greece deficit 2009, Nvidia $5T 2025, rare earths 2025
- [ ] Add `official_sources` links per event (only "whatever it takes" has one)
- [ ] Review the 85 texts written on 2026-11-26 (all published); rewrite `us_midterms_2026` once its horizons close
- [ ] Check the fetched headlines; refetch or fix by hand in `data/news/` where a pick is off-topic
- [ ] Add 2026 events after verification
