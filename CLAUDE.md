# CLAUDE.md

Geopol is the owner's personal geopolitics briefing. It runs twice a day (10:00 and 00:00 Sydney), tracks storylines as they heat up and cool down, gives "My take" advice with a track record, keeps background explainers, and archives everything forever. It's published free at https://arno0b.github.io/geopol/ (public but unlisted, noindex).

Spec: `docs/superpowers/specs/2026-11-03-geopol-briefing-design.md`. Plan: `docs/superpowers/plans/2026-11-03-geopol-briefing.md`.

This repo follows the WAT framework: workflows (`workflows/`) say what to do, tools (`tools/`) do the deterministic work, and Claude decides and writes.

## Workflows

- `workflows/run_briefing.md`: produce one briefing (what the scheduled routine follows).
- `workflows/write_background.md`: write or update a background explainer.
- `workflows/chat_with_archive.md`: answer the owner's questions from the saved history.

## Commands

On Windows, use `.venv\Scripts\python`. In CI and routines, plain `python`.

```
pip install -r requirements.txt
python -m pytest -q                                   # full test suite
python tools/slot.py current                          # current run id, e.g. 2026-11-04-1000
python tools/slot.py check fetch|briefing             # exit 0 inside the Sydney window
python tools/fetch_feeds.py [--run-id ID]             # → data/inbox/ID.json (exit 2 if nothing fetched)
python tools/fetch_prices.py [--run-id ID]            # → data/prices/ID.json
python tools/og_image.py ID <article_url>             # record the article's og:image on the inbox item
python tools/validate_briefing.py .tmp/briefing_ID.json     # validate + merge into data/
python tools/validate_background.py .tmp/background_SLUG.json
python tools/build_site.py [--out site]               # static site → site/
```

## Data (append-only, never delete)

- `data/inbox/`, `data/prices/`: fetched each slot by `.github/workflows/fetch.yml`.
- `data/briefings/`: one file per run. The validator refuses to overwrite one.
- `data/storylines.json`: storylines + heat per run (seeded from `config/seed_storylines.json`).
- `data/background/<slug>.json`: explainer versions.

## Conventions

- Feeds: `config/feeds.json`. Prices: `config/price_symbols.json` (Yahoo chart API, free, no key).
- Zero cost: no API keys, no paid services. Claude runs on the owner's Pro plan.
- Images only if the source provides them (feed media or og:image). The validator enforces this.
- `deploy.yml` runs the tests before publishing, so a failing suite blocks the deploy.
