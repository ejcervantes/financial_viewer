# Sector Reactions *(working name)*

A one-page dashboard showing how 8 sectors in 3 markets (US, Europe, China) reacted to elections, trade, geopolitical, central-bank and crisis events since 1998. Spec: [`spec-dashboard-eventos.md`](spec-dashboard-eventos.md).

The site is static (GitHub Pages). A daily GitHub Actions job downloads prices from Yahoo Finance, recomputes everything, commits the JSON under `web/public/data/` and redeploys. The browser never calls Yahoo or any API.

## Layout

```
config/            sectors.yaml · events.yaml · episodes.yaml   ← curated inputs
pipeline/          fetch_prices → build_series → compute_reactions → fetch_indicators → export
                   fetch_news + generate_texts (manual, AI texts)
tests/             day-0 rule (spec §3.4) and dynamic baskets
data/texts.json    AI texts — the human-reviewed source of truth (committed)
data/news/         headline candidates per event (committed)
web/               Vite + React + TypeScript + ECharts; reads web/public/data/*.json
.github/workflows/ daily.yml · texts.yml · deploy.yml
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

## AI texts

```bash
GUARDIAN_API_KEY=… NYT_API_KEY=… .venv/bin/python -m pipeline.fetch_news --only lehman_2008
```

```bash
LLM_API_KEY=… .venv/bin/python -m pipeline.generate_texts --only lehman_2008
```

`generate_texts` uses the Anthropic SDK (model `claude-opus-5-5`, override with `LLM_MODEL`). Every new text is saved with `reviewed: false`. Read it, edit if needed, set `reviewed: true` in `data/texts.json`, then run `python -m pipeline.export --texts-only`. Only reviewed texts reach the site; the rest show "coming soon". `--dry-run` prints the prompts without calling the API.

In GitHub, **Actions → texts → Run workflow** does the same and opens a PR for review.

## GitHub setup

1. **Settings → Pages → Source: GitHub Actions.**
2. **Settings → Secrets → Actions:** `LLM_API_KEY`, `NYT_API_KEY`, `GUARDIAN_API_KEY`, and optionally `FRED_API_KEY` (EPU falls back to FRED's public CSV, then to policyuncertainty.com).
3. **Settings → Actions → General:** allow workflows to *read and write* and to *create pull requests* (for `texts.yml`).

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
- [ ] Review NYT and Guardian terms on passing content to an LLM (attribution is already in the footer)
- [ ] Get API keys, run `texts.yml`, review all texts
- [ ] Add 2026 events after verification
