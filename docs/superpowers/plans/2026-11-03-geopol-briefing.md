# Geopol Briefing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A self-updating personal geopolitics briefing (10:00 and 00:00 Sydney) with storyline heat tracking, "My take" advice with a track record, background explainers, and a permanent archive, published free on GitHub Pages.

**Architecture:** Deterministic Python tools (WAT `tools/`) fetch RSS + prices, validate Claude-written JSON, and build a static site. GitHub Actions (free, public repo) runs fetching on a cron and deploys Pages on every push. A Claude Code cloud routine on the owner's Pro plan follows `workflows/run_briefing.md`: reads the fetched inbox, writes the briefing JSON, runs the validator, commits, pushes. All state lives as JSON in `data/`, committed forever.

**Tech Stack:** Python 3.12, feedparser, requests, Jinja2, markdown, pytest; GitHub Actions + GitHub Pages; Claude Code routines (`/schedule`).

**Spec:** `docs/superpowers/specs/2026-11-03-geopol-briefing-design.md`

## Global Constraints

- Zero money: no Anthropic API key, no paid APIs, no paid hosting, no paid news sources.
- Repo: standalone public `arno0b/geopol`; the parent folder `C:\Users\sakif\Downloads\claude project` and sibling projects are never pushed.
- Every page has `<meta name="robots" content="noindex, nofollow">`; site root has `robots.txt` with `User-agent: *` / `Disallow: /`.
- Briefing slots: 10:00 and 00:00 `Australia/Sydney` (DST-aware via `zoneinfo`). Run id format `YYYY-MM-DD-HHMM` in Sydney local time, e.g. `2026-11-04-1000`, `2026-11-05-0000`.
- Full briefing: 1 story of the day + 2–4 cards. Short briefing (midnight fallback only if Pro limits require): 1–2 cards, no story of the day required.
- Images only if the URL came from the source (feed media/enclosure or the article's `og:image`). Never generated.
- Money angle and My take are optional per item (null allowed); never required.
- Every item cites ≥1 source URL.
- Nothing in `data/` is ever deleted or overwritten in place except `data/storylines.json` (append-only heat history) and background files (append new version).
- Dark theme tokens: bg `#14171c`, panel `#1f242b`, inner `#262c34`; trend colours heating `#e74c3c`, rising `#e67e22`, steady `#95a5a6`, cooling `#2ecc71`, new `#3498db`, quiet `#6c7680`; money box bg `#1e3a2a` text `#b8f0cc`. Body 16–17px, line-height 1.65–1.75; one column below 760px. Reference: `.superpowers/brainstorm/1945-1793693289/content/layout-v3.html`.
- Tools runnable as `python tools/<name>.py` from repo root; intermediates in `.tmp/`; secrets (none expected) in `.env`.
- All text UTF-8 (Bangla script appears in Bangladeshi feeds).

## Review Focus

1. **A feed is down, slow, or returns non-RSS HTML** → that feed is skipped with a logged warning; the other feeds still produce the inbox. If *all* feeds fail, no inbox file is written and the routine stops without writing a briefing. (Task 2 tests.)
2. **The same slot fires twice (DST double cron) or a slot is missed** → second fire is a no-op; a missed slot just leaves a gap, and prev/next links and the archive skip it cleanly. (Tasks 1 and 7 tests.)
3. **Claude writes invalid briefing JSON** (unknown storyline, image not from source, 5 cards, missing source, heat 11) → validator rejects with readable errors and changes nothing on disk. (Task 5 tests.)
4. **Feed text containing `<script>`, quotes, or Bangla** → rendered escaped and correctly encoded. (Task 7 test.)
5. **A storyline with only 1–2 days of history** → sparkline pads with blanks, trend shows "New", no crash. (Task 4 test.)

---

## File Structure

```
geopol/
  config/feeds.json              # feed list: [{name, url, lens}]
  config/seed_storylines.json    # initial storylines: [{slug, name}]
  config/price_symbols.json      # [{key, label, symbol}]
  data/inbox/<run_id>.json       # fetched articles (Task 2)
  data/prices/<run_id>.json      # price snapshot (Task 3)
  data/briefings/<run_id>.json   # Claude-written, validated (Task 5)
  data/storylines.json           # storyline index + heat history (Task 4)
  data/background/<slug>.json    # versioned explainers (Task 6)
  tools/slot.py                  # Sydney time, run ids, slot gating
  tools/fetch_feeds.py
  tools/fetch_prices.py
  tools/og_image.py
  tools/store.py                 # load/save, storylines, heat, trend, sparkline
  tools/validate_briefing.py
  tools/validate_background.py
  tools/build_site.py
  templates/{base,briefing,archive,storyline,background,background_index}.html.j2
  static/style.css
  site/                          # build output (gitignored)
  tests/ + tests/fixtures/
  workflows/run_briefing.md, workflows/write_background.md, workflows/chat_with_archive.md
  .github/workflows/fetch.yml, .github/workflows/deploy.yml
  CLAUDE.md, requirements.txt, .gitignore, pytest.ini
```

---

### Task 1: Environment, repo scaffold, and slot logic

**Files:**
- Create: `requirements.txt`, `.gitignore`, `pytest.ini`, `tools/__init__.py`, `tools/slot.py`, `tests/test_slot.py`

**Interfaces:**
- Produces:
  - `SYDNEY = ZoneInfo("Australia/Sydney")`
  - `run_id_for(dt: datetime) -> str` — Sydney-local slot the moment belongs to: 10:00 slot if local hour in 9–21, else 00:00 slot (00:00 of the *next* day if hour ≥ 22, same day if hour ≤ 8). Returns e.g. `"2026-11-04-1000"`.
  - `parse_run_id(run_id: str) -> datetime` (aware, Sydney)
  - `in_window(dt: datetime, stage: str) -> bool` — stage `"fetch"` true when Sydney local time is 09:00–09:39 or 23:00–23:39; stage `"briefing"` true when 09:30–10:29 or 23:30–00:29.
  - CLI: `python tools/slot.py current` prints run id; `python tools/slot.py check <stage>` exits 0 inside window else exits 3.

- [ ] **Step 1:** Install Python locally (none present on this machine): `winget install -e --id Python.Python.3.12`, reopen shell, confirm `python --version` prints 3.12.x. Create venv `python -m venv .venv`.
- [ ] **Step 2:** `git init -b main` in `geopol/`. `.gitignore`: `.venv/ .tmp/ site/ __pycache__/ .env .superpowers/ credentials.json token.json`. `requirements.txt`: `feedparser requests jinja2 markdown pytest` (pin to current versions after install with `pip freeze`). `pytest.ini`: `[pytest]\ntestpaths = tests\npythonpath = .`
- [ ] **Step 3: Write failing tests** in `tests/test_slot.py`:

```python
from datetime import datetime
from tools.slot import SYDNEY, run_id_for, parse_run_id, in_window

def d(y,m,day,h,mi): return datetime(y,m,day,h,mi,tzinfo=SYDNEY)

def test_morning_slot(): assert run_id_for(d(2026,11,4,9,20)) == "2026-11-04-1000"
def test_late_evening_rolls_to_next_midnight(): assert run_id_for(d(2026,11,4,23,30)) == "2026-11-05-0000"
def test_just_after_midnight(): assert run_id_for(d(2026,11,5,0,10)) == "2026-11-05-0000"
def test_roundtrip(): assert parse_run_id("2026-11-04-1000") == d(2026,11,4,10,0)
def test_fetch_window(): assert in_window(d(2026,11,4,9,20),"fetch") and not in_window(d(2026,11,4,10,20),"fetch")
def test_briefing_window_spans_midnight(): assert in_window(d(2026,11,5,0,15),"briefing")
def test_dst_utc_input():  # 22:20 UTC on 3 Nov = 09:20 AEDT on 4 Nov
    from datetime import timezone
    assert run_id_for(datetime(2026,11,3,22,20,tzinfo=timezone.utc)) == "2026-11-04-1000"
```

- [ ] **Step 4:** `pytest tests/test_slot.py -v` → FAIL (module missing).
- [ ] **Step 5:** Implement `tools/slot.py` per Interfaces (convert any aware input to `SYDNEY` first).
- [ ] **Step 6:** `pytest tests/test_slot.py -v` → 7 passed.
- [ ] **Step 7:** Commit `feat: scaffold repo and Sydney slot logic`.

---

### Task 2: Feed fetching

**Files:**
- Create: `config/feeds.json`, `tools/fetch_feeds.py`, `tests/test_fetch_feeds.py`, `tests/fixtures/feed_bbc.xml`, `tests/fixtures/feed_media.xml`, `tests/fixtures/not_rss.html`

**Interfaces:**
- Consumes: `slot.run_id_for`
- Produces:
  - `parse_feed(raw: bytes, source: str, lens: str) -> list[dict]` — each item `{id, title, link, summary, published, source, lens, image_url}`; `id` = sha1 of normalized link; `image_url` from `media_content`/`media_thumbnail`/image enclosure else `None`; summary HTML stripped, ≤600 chars.
  - `fetch_all(feeds: list[dict], get=requests.get) -> tuple[list[dict], list[str]]` — (deduped items newest first, warnings). Timeout 15s per feed, User-Agent `geopol-briefing/1.0`. Dedupe by `id` and by identical lowercased title.
  - CLI `python tools/fetch_feeds.py [--run-id ID]` writes `data/inbox/<run_id>.json` = `{run_id, fetched_at, items, warnings}`; drops items older than 36h; exits 0 without writing if file already exists ("already fetched"); exits 2 without writing if zero items.

- [ ] **Step 1:** Write `config/feeds.json` with candidates (keep `name`, `url`, `lens`): BBC World `https://feeds.bbci.co.uk/news/world/rss.xml`, BBC Business `https://feeds.bbci.co.uk/news/business/rss.xml`, Al Jazeera `https://www.aljazeera.com/xml/rss/all.xml`, Guardian World `https://www.theguardian.com/world/rss`, Guardian Business `https://www.theguardian.com/uk/business/rss`, DW `https://rss.dw.com/rdf/rss-en-world`, NPR World `https://feeds.npr.org/1004/rss.xml`, CNBC World `https://www.cnbc.com/id/100727362/device/rss/rss.html`, Nikkei Asia `https://asia.nikkei.com/rss/feed/nar`, OilPrice `https://oilprice.com/rss/main`, ABC Australia `https://www.abc.net.au/news/feed/2942460/rss.xml`, The Daily Star BD `https://www.thedailystar.net/frontpage/rss.xml`, Dhaka Tribune, Prothom Alo English, bdnews24 (find current feed URLs), plus Google News RSS searches `https://news.google.com/rss/search?q=Bangladesh+politics&hl=en-US&gl=US&ceid=US:en` and `...q=geopolitics...`. Lenses: `world`, `markets`, `energy`, `asia`, `bangladesh`, `australia`.
- [ ] **Step 2: Write failing tests:** `test_parse_basic` (fixture BBC → titles, links, `image_url` None where absent); `test_parse_media_image` (fixture with `<media:content url=...>` → that URL); `test_strips_html_summary` (`"<p>Hi <b>x</b></p>"` → `"Hi x"`); `test_not_rss_yields_warning` (`fetch_all` with a fake `get` returning `not_rss.html` for one feed and BBC fixture for another → items from BBC only, 1 warning naming the feed); `test_timeout_yields_warning` (fake `get` raises `requests.Timeout`); `test_dedupe_same_link_two_feeds`; `test_cli_no_write_when_all_fail` (monkeypatch `fetch_all` → `([], [...])`, assert exit 2 and no file).
- [ ] **Step 3:** Run → FAIL.
- [ ] **Step 4:** Implement with feedparser on the fetched bytes (fetch via requests so timeouts are ours). Treat `parsed.bozo and not parsed.entries` as failure.
- [ ] **Step 5:** Run → all pass.
- [ ] **Step 6:** Live check: `python tools/fetch_feeds.py --run-id test-live` → prints item count and warnings. Remove feeds that fail or return nothing; ensure ≥2 working Bangladesh sources (fall back to Google News query if needed). Delete `data/inbox/test-live.json`.
- [ ] **Step 7:** Commit `feat: RSS feed fetching with dedupe and failure isolation`.

---

### Task 3: Price snapshot and og:image

**Files:**
- Create: `config/price_symbols.json`, `tools/fetch_prices.py`, `tools/og_image.py`, `tests/test_prices.py`, `tests/test_og_image.py`

**Interfaces:**
- Produces:
  - `fetch_prices(symbols: list[dict], get=requests.get) -> dict` → `{key: {"label", "value": float|None, "as_of": str|None}}`; a failed symbol gets `value: None`, never raises.
  - CLI `python tools/fetch_prices.py [--run-id ID]` writes `data/prices/<run_id>.json` = `{run_id, fetched_at, prices}`; skip if exists.
  - `find_og_image(html: str) -> str|None`; CLI `python tools/og_image.py <run_id> <article_url>` fetches the page, and if an og:image exists, sets `image_url` on the matching inbox item (by link) and saves; prints the URL or `none`.

- [ ] **Step 1:** `config/price_symbols.json` keys: `brent, wti, gold, audusd, dxy, spx, asx200, nikkei, btc`. Source: a free no-key endpoint — try Stooq CSV quotes first (`https://stooq.com/q/l/?s=<sym>&f=sd2t2c&h&e=csv`); if Stooq now needs a key, use Yahoo's chart JSON (`https://query1.finance.yahoo.com/v8/finance/chart/<sym>?range=1d&interval=1d`). Record the chosen source and symbols in the file. Decide by a live request during Step 6.
- [ ] **Step 2: Failing tests:** `test_parses_quote` (fake `get` returns canned CSV/JSON → float value); `test_failed_symbol_is_none` (one symbol 500s → `value is None`, others fine); `test_og_image_found` (`<meta property="og:image" content="https://x/y.jpg">` → URL); `test_og_image_missing` → None; `test_og_cli_updates_inbox` (tmp inbox file, monkeypatched fetch → item's `image_url` set).
- [ ] **Step 3:** Run → FAIL. **Step 4:** Implement. **Step 5:** Run → pass.
- [ ] **Step 6:** Live: `python tools/fetch_prices.py --run-id test-live` → ≥7 of 9 values non-null. Delete the test file.
- [ ] **Step 7:** Commit `feat: free price snapshot and og:image lookup`.

---

### Task 4: Storyline store, heat, trend, sparkline

**Files:**
- Create: `config/seed_storylines.json`, `tools/store.py`, `tests/test_store.py`

**Interfaces:**
- Produces (all paths relative to a `root: Path` param defaulting to repo root, so tests use `tmp_path`):
  - `load_json(path) / save_json(path, obj)` — UTF-8, `ensure_ascii=False`, indent 2, atomic write (temp file + `os.replace`).
  - `load_storylines(root) -> dict[slug, dict]`; storyline = `{name, created: run_id, heat: {run_id: int}, runs: [run_id]}`. If missing, initialised from `config/seed_storylines.json` with `created` = `"seed"` and empty heat.
  - `daily_heat(story: dict, today: date, days: int = 14) -> list[int|None]` — per Sydney date, max heat recorded that day; None where no record.
  - `trend(story: dict, latest_run_id: str) -> str` — one of `new, heating, rising, steady, cooling, quiet`. Rules: `new` if `created` within the last 2 days; `quiet` if latest daily heat ≤ 2 or no heat in last 3 days; else diff = mean(last 3 non-null days) − mean(previous 4 non-null days); diff ≥ 1.5 → `heating` if latest ≥ 7 else `rising`; diff ≤ −1.5 → `cooling`; else `steady`. With fewer than 2 values, `steady` unless new.
  - `sparkline(values: list[int|None]) -> str` — map 0–10 to `▁▂▃▄▅▆▇█` (`round(v/10*7)`), None → `·`. Always `len(values)` chars.
- Seed slugs (names in `config/seed_storylines.json`): `us-china`, `taiwan`, `russia-ukraine`, `middle-east`, `oil-energy`, `fed-rates-dollar`, `india`, `southeast-asia`, `africa-resources`, `ai-tech-power`, `critical-minerals`, `bangladesh-politics`, `bangladesh-economy`, `climate-food-water`.

- [ ] **Step 1: Failing tests:** `test_seed_init` (no file → 14 storylines, heat empty); `test_daily_heat_takes_max_per_day` (heats 4 @ `2026-11-04-1000` and 7 @ `2026-11-05-0000` and 5 @ `2026-11-05-1000` → day 5 = 7); `test_sparkline_pads` (`[None]*12+[3,9]` → 14 chars, starts with `·`, ends with `█`); `test_trend_heating` (days 2,2,3,3 then 7,8,9 → `heating`); `test_trend_cooling`; `test_trend_new_with_one_point` (created yesterday, one value → `new`); `test_trend_quiet`; `test_atomic_save_roundtrip_bangla` (save `{"name": "বাংলাদেশ"}` → load equal).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → pass.
- [ ] **Step 5:** Commit `feat: storyline store with heat trend and sparkline`.

---

### Task 5: Briefing validator and merge

**Files:**
- Create: `tools/validate_briefing.py`, `tests/test_validate_briefing.py`, `tests/fixtures/briefing_ok.json`

**Interfaces:**
- Consumes: `store.*`, `data/inbox/<run_id>.json`, `data/prices/<run_id>.json`
- Briefing JSON (Claude writes this to `.tmp/briefing_<run_id>.json`):

```json
{
  "run_id": "2026-11-04-1000", "kind": "full",
  "story_of_day": Item, "cards": [Item],
  "watch": {"title": "...", "text": "..."} | null,
  "takes_review": [{"take_id": "...", "verdict": "right|wrong|mixed|open", "text": "..."}],
  "heat": {"<slug>": 0-10}
}
Item = {
  "storyline": "<slug>", "new_storyline_name": "..." | null,
  "headline": "...", "story": "...", "so_what": "...",
  "last_time": {"run_id": "...", "text": "..."} | null,
  "money_angle": "..." | null,
  "my_take": {"text": "...", "reasoning": "...", "confidence": "low|medium|high", "wrong_if": "..."} | null,
  "image": {"url": "...", "credit": "..."} | null,
  "sources": [{"name": "...", "url": "..."}]
}
```

- Produces:
  - `validate(briefing: dict, root: Path) -> list[str]` — empty list means valid. Rules: `run_id` matches `YYYY-MM-DD-HHMM` and an inbox exists for it; `kind` full → `story_of_day` present and 2–4 cards; short → 1–2 cards; each item: storyline slug exists, or `new_storyline_name` given with a new kebab-case slug; non-empty headline/story/so_what; ≥1 source with http(s) URL; `image.url` equals some inbox item's `image_url`; `last_time.run_id` exists in `data/briefings/`; `confidence` in the enum; `takes_review[].take_id` exists in an earlier briefing; heat values int 0–10 for known/new slugs. Error strings name the field path, e.g. `cards[1].image.url not from any source`.
  - `merge(briefing: dict, root: Path) -> Path` — only after `validate` is empty: assigns each `my_take` an id `<run_id>-<n>` and `prices_at` copied from `data/prices/<run_id>.json` (or `{}` if missing); adds new storylines (`created` = run_id); writes heat + appends run_id to `runs` for each storyline touched; writes `data/briefings/<run_id>.json`. Refuses (raises) if that file already exists.
  - CLI `python tools/validate_briefing.py <path>` → on errors prints each and exits 1 with no writes; on success merges, prints `ok <run_id>`.

- [ ] **Step 1: Failing tests:** `test_valid_fixture_passes`; `test_five_cards_rejected`; `test_unknown_storyline_rejected`; `test_new_storyline_accepted_and_created`; `test_image_not_from_source_rejected`; `test_missing_source_rejected`; `test_heat_out_of_range_rejected`; `test_invalid_changes_nothing` (snapshot every file under tmp root before/after CLI → identical); `test_merge_assigns_take_ids_and_prices`; `test_merge_refuses_existing_run`; `test_short_kind_allows_no_story_of_day`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → pass.
- [ ] **Step 5:** Commit `feat: briefing validation and merge into archive`.

---

### Task 6: Background explainers store

**Files:**
- Create: `tools/validate_background.py`, `tests/test_background.py`

**Interfaces:**
- Background input (Claude writes `.tmp/background_<slug>.json`): `{slug, how_we_got_here, players: [{name, wants}], stakes, current_state, watch_next, timeline: [{date, event}], sources: [{name, url}], change_note: str|null}` — prose fields are Markdown.
- Produces:
  - `validate_background(doc: dict, root: Path) -> list[str]` — slug exists in storylines; all prose fields non-empty; ≥3 timeline entries; ≥2 sources.
  - `add_version(doc: dict, root: Path, date: str) -> Path` — appends `{date, ...doc}` to `data/background/<slug>.json` `{"slug", "versions": [...]}`; never edits earlier versions.
  - CLI `python tools/validate_background.py <path> [--date YYYY-MM-DD]` (default today Sydney) → exit 1 + errors, or `ok <slug> v<n>`.

- [ ] **Step 1: Failing tests:** `test_valid_background`; `test_too_few_timeline_rejected`; `test_unknown_slug_rejected`; `test_second_version_appends_keeps_first`.
- [ ] **Step 2:** FAIL → **Step 3:** implement → **Step 4:** pass.
- [ ] **Step 5:** Commit `feat: versioned background explainers`.

---

### Task 7: Static site build

**Files:**
- Create: `tools/build_site.py`, `templates/*.html.j2`, `static/style.css`, `tests/test_build_site.py`

**Interfaces:**
- Consumes: `store.load_storylines`, `daily_heat`, `trend`, `sparkline`; `data/briefings/*.json`; `data/background/*.json`
- Produces: `build(root: Path, out: Path) -> None` writing:
  - `index.html` = latest briefing (same content as its page)
  - `b/<run_id>.html` per briefing with header "Tue 4 Nov · 10:00 AM Sydney", prev/next links to the adjacent *existing* briefings
  - `archive.html` — all briefings newest first, grouped by month, headline of story of the day
  - `s/<slug>.html` — storyline page: name, 14-day sparkline, trend, every item ever written on it newest first (linking to its briefing), and every My take on it with its later review verdicts
  - `background/index.html` and `background/<slug>.html` — latest version rendered (Markdown → HTML), timeline, "Updated <date>: <change_note>" and links to older versions (`background/<slug>-v<n>.html`)
  - `robots.txt`, `static/style.css` copy
  - Left storyline column on briefing pages: storylines with heat in the last 14 days, sorted by latest heat desc, each linking to `s/<slug>.html` and "Background →" if an explainer exists.
  - Each item panel: label "STORYLINE · TREND", optional image (with credit, linking to source), headline, story, inner boxes LAST TIME / SO WHAT / 💰 MONEY ANGLE / MY TAKE (text, reasoning, confidence, "Wrong if…", one line: "This is Claude's reasoning, not financial advice — the call is yours."), sources. Boxes with null content are omitted.
  - Jinja2 `autoescape=True`; Markdown output only for background prose (from Claude, trusted) — feed-derived strings never pass through `|safe`.
- CLI `python tools/build_site.py [--out site]`.

- [ ] **Step 1: Failing tests** (build from fixtures into `tmp_path`): `test_index_matches_latest`; `test_noindex_on_every_page` (glob all `.html`, each contains the robots meta); `test_robots_txt`; `test_prev_next_skip_gaps` (briefings for 04-1000 and 05-1000 only → 04's next is 05-1000); `test_script_in_text_escaped` (headline `<script>x</script>` → `&lt;script&gt;` present, raw tag absent); `test_bangla_renders` (UTF-8 meta, text present); `test_null_money_box_omitted`; `test_storyline_page_lists_history`; `test_background_versions_linked`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement templates + CSS per Global Constraints design tokens (panels, inner boxes, colour per trend, ≥16px body, 1.7 line-height, `@media (max-width:760px)` single column, images `max-width:100%`). **Step 4:** pass.
- [ ] **Step 5:** Visual check: build from fixtures, open `site/index.html` in the browser, compare against `layout-v3.html` at desktop and phone width (devtools). Fix spacing/contrast until it matches.
- [ ] **Step 6:** Commit `feat: static site with storylines, archive and background`.

---

### Task 8: GitHub repo, Actions, Pages

**Files:**
- Create: `.github/workflows/fetch.yml`, `.github/workflows/deploy.yml`

**Interfaces:**
- `fetch.yml`: `schedule` crons covering both Sydney offsets for 09:20 and 23:20 local — `20 22,23 * * *` (09:20 AEDT/AEST) and `20 12,13 * * *` (23:20) — plus `workflow_dispatch`. Steps: checkout, setup-python 3.12, `pip install -r requirements.txt`, `python tools/slot.py check fetch || exit 0` (skip on dispatch with input `force: true`), `python tools/fetch_feeds.py`, `python tools/fetch_prices.py`, commit `data/inbox data/prices` as `geopol-bot` if changed, push. `permissions: contents: write`.
- `deploy.yml`: on push to `main` (any path) + `workflow_dispatch`: build with `python tools/build_site.py --out site`, `actions/upload-pages-artifact` (path `site`), `actions/deploy-pages`. `permissions: pages: write, id-token: write`.

- [ ] **Step 1:** Write both workflows.
- [ ] **Step 2:** **Confirm with owner before this step** (creates a public repo): `gh repo create arno0b/geopol --public --source . --remote origin` then `git push -u origin main`. Verify `git ls-files` contains nothing from outside `geopol/` and no `.superpowers/` or `.env`.
- [ ] **Step 3:** Enable Pages with Actions as source: `gh api -X POST repos/arno0b/geopol/pages -f build_type=workflow`.
- [ ] **Step 4:** `gh workflow run fetch.yml -f force=true` → `gh run watch` succeeds; a new `data/inbox/*.json` commit appears.
- [ ] **Step 5:** Deploy runs on that push → `https://arno0b.github.io/geopol/` loads (empty-state page: "First briefing coming soon" when no briefings exist — add this case to `build` + a test `test_empty_state` if not already covered).
- [ ] **Step 6:** Commit any fixes `ci: fetch and deploy workflows`.

---

### Task 9: SOPs, CLAUDE.md, and the routine

**Files:**
- Create: `workflows/run_briefing.md`, `workflows/write_background.md`, `workflows/chat_with_archive.md`
- Modify: `CLAUDE.md` (create in `geopol/`: commands, data layout, pointers to workflows)

**Interfaces:**
- `run_briefing.md` steps the routine follows exactly:
  1. `git pull`; `python tools/slot.py current` → RUN_ID. If `data/briefings/RUN_ID.json` exists → stop ("already done"). If `data/inbox/RUN_ID.json` missing → run `python tools/fetch_feeds.py` and `python tools/fetch_prices.py` itself; if still missing → stop and report.
  2. Read the inbox, `data/storylines.json`, and the last 6 briefings. Pick the 3–5 threads that genuinely moved (Bangladesh included whenever something moved there). Optional web search to deepen a story — any URL used goes in `sources`.
  3. For a story worth an image with no `image_url`, run `python tools/og_image.py RUN_ID <url>`; use the image only if one is returned.
  4. Write `.tmp/briefing_RUN_ID.json` per the Task 5 schema. Style rules from the spec: compelling, short; Money angle and My take only when real; My take gives a real call with reasoning, confidence, and what would prove it wrong; review any past take whose outcome is now visible; heat for every storyline touched (0–10, and lower the heat on storylines that went quiet).
  5. `python tools/validate_briefing.py .tmp/briefing_RUN_ID.json`; fix and retry on errors (max 3 tries).
  6. New storyline created → also write its background per `write_background.md`. A storyline whose situation shifted in a big way (heat jumped ≥3 or a turning point) → add a new background version with an updated `current_state` and a `change_note`.
  7. Commit `briefing: RUN_ID` and push (triggers deploy).
  - Pro fallback note: if usage limits bite, the 00:00 run uses `"kind": "short"`.
- `write_background.md`: how to write one explainer (Task 6 schema, ~5-minute read, timeline ≥3 dates, ≥2 sources, web search allowed), validate with `tools/validate_background.py`, commit.
- `chat_with_archive.md`: when the owner asks questions, read `data/` (briefings, storylines, takes, background) and answer citing run ids and links to pages on the site.

- [ ] **Step 1:** Write the three SOPs and `CLAUDE.md`.
- [ ] **Step 2: Verify routines on Pro.** Ask the claude-code-guide agent (or read `/schedule` docs): Are cloud routines available on Pro? Daily run limits? Do they get network access and push rights to `arno0b/geopol`? Timezone support or UTC-only cron? Record answers in `workflows/run_briefing.md` under "Routine notes".
- [ ] **Step 3:** If available: create two routines with `/schedule` on `arno0b/geopol`, prompt `Follow workflows/run_briefing.md exactly.` at 09:30 and 23:30 Sydney (if cron is UTC-only, schedule both DST offsets; the slot/already-done checks make the extra fire a no-op). If **not** available on Pro: stop and tell the owner; fallback is Windows Task Scheduler running `claude -p "Follow workflows/run_briefing.md exactly."` locally (computer must be on).
- [ ] **Step 4:** Trigger one routine run manually → a `briefing:` commit lands, deploy succeeds, the page shows it. Check the briefing reads well and validates.
- [ ] **Step 5:** Commit `docs: briefing SOPs and routine setup`.

---

### Task 10: Seed background explainers and first briefing

**Files:**
- Create: `data/background/<slug>.json` for all 14 seed storylines

- [ ] **Step 1:** Interactively in Claude Code (not a routine), follow `workflows/write_background.md` for each seed slug, Bangladesh slugs first. Split across sessions if Pro limits are hit; commit after each explainer (`background: <slug>`).
- [ ] **Step 2:** `pytest` → all green; `python tools/build_site.py` → `background/index.html` lists 14 explainers.
- [ ] **Step 3:** Push; confirm `https://arno0b.github.io/geopol/background/` shows them and each storyline panel links "Background →".
- [ ] **Step 4:** Watch the next scheduled 10:00 run land on its own. Report the live URL to the owner.
