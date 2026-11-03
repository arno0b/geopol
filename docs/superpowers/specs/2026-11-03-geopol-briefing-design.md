# Geopol Briefing — Design

**Date:** 2026-11-03
**Owner:** Sakif (GitHub: `arno0b`), based in Sydney
**Status:** Draft for approval

## Intent and the why

A personal, self-updating intelligence briefing on geopolitics and everything linked to it (markets, energy, tech, resources, elections). The owner got the idea from Instagram reels and wants their *own* source — one that picks what matters instead of an algorithm — to give them an edge in three ways: making money / investing, understanding the world better, and sharpening their own perception and vision over time.

The defining quality is **evolution**: it remembers what it said before, tracks storylines as they heat up and cool down, and checks its own past calls. Reading it over months should feel like watching the world move — and watching their own judgment grow.

It must read like a **compelling story with not too much information**.

## Goals

1. **Two briefings a day**, at **10:00 and 00:00 (midnight) Sydney time**, produced automatically.
2. Each briefing: **one Story of the Day + 2–4 short cards**. Each item has: what happened, "Last time" (link to earlier coverage of that storyline, when there is one), "So what", and a "💰 Money angle" *only when there genuinely is one*.
3. **Storylines** with a **heat score** tracked daily. Each storyline shows a 14-day heat sparkline and a trend (heating / rising / steady / cooling / quiet). New storylines get flagged "🆕 New storyline". Clicking a storyline shows every update on it from the start.
4. **"My take" advice** where there's a real opportunity or risk: what Claude would consider doing, the reasoning, a confidence level, and what would prove it wrong. Later briefings **revisit past takes** ("On 4 Nov we said X — here's how it played out") so the owner can judge the track record. One short line noting the decision is the owner's. The owner explicitly wants actual advice with reasoning, not hedged non-answers.
5. **Permanent archive.** Every briefing, storyline, heat value and take is retained forever and browsable (prev/next + archive page).
6. **Images** only when the news source already supplies a real photo (e.g. RSS media/enclosure or the article's og:image). Never generated images. No image → no image slot.
7. **Chat** with the archive: the owner opens Claude Code (or Claude app with the repo) in the project and asks questions; Claude answers from the saved history. Free on their plan.

## Coverage (owner delegated this choice)

Default lenses; each briefing picks only the 3–5 threads that actually moved:
- Big powers: US–China (trade, tariffs, Taiwan, chips), Russia–Ukraine & NATO, Middle East (Israel, Iran, Gulf, shipping lanes).
- Rising players: India, Southeast Asia, Africa resource races.
- Money signals: oil/energy, US Fed & rates, the dollar, gold, major indices, crypto when geopolitics moves it.
- Long trends: AI/tech power, critical minerals, food & water, climate shocks, direction-changing elections.
- **Bangladesh politics and related stories** (owner request, first-class lens): domestic politics, elections and government transitions, economy (garments/exports, remittances, IMF, inflation, taka), relations with India, China, the US and Myanmar (incl. the Rohingya situation), and climate/water. Bangladesh-specific outlets are added to the feeds (e.g. The Daily Star, Dhaka Tribune, Prothom Alo English, bdnews24, where free feeds exist). Bangladesh storylines compete for space like any other, but it should appear whenever something there genuinely moved.
- Australia relevance is a natural plus (owner is in Sydney) — *builder's/editor's judgment*, not a hard requirement.

## Background section ("Catch up")

The owner wants to get the background on every topic, up to now, so the daily briefings make sense.

- A separate **Background** section of the site, linked from the header next to Archive.
- **One explainer per storyline**: how we got here (key history and turning points), who the main players are and what each wants, what's at stake (including the money angle), the current state as of today, and what to watch next. Same compelling, not-too-much style; aim for about a 5-minute read each, with a short timeline of key dates.
- **Seeded at launch:** before the first daily briefing, Claude writes background explainers for every default coverage storyline (including Bangladesh), so the owner can catch up from day one. This is a one-off, larger run. On Pro it can be split over a few sessions, or done interactively in Claude Code rather than as a routine.
- **Kept current:** when a storyline is new, it gets an explainer. When something big shifts, the "current state" part of the explainer is updated and the change is dated. Older versions are kept so history isn't lost.
- Each storyline panel and card links to its explainer ("Background →").

## Constraints

- **Zero money.** No Anthropic API key, no paid APIs, no paid hosting, no paid news sources. Everything runs on the owner's existing Claude plan plus free services. Briefing runs consume the plan's normal usage limits — that's accepted.
- **Runs without the owner's computer on.** Scheduled via **Claude Code cloud routines** (`/schedule`) using the owner's plan.
- **Storage and hosting:** a **public GitHub repo** under `arno0b` holding data + site, published with **GitHub Pages** (free requires public repo). Unlisted URL; add `noindex` meta + `robots.txt` disallow. Owner accepted public-but-unlisted in exchange for zero cost (my call, stated to them; a free private path such as Cloudflare Pages + Access can come later).
- **News gathering is deterministic Python** (WAT framework): free RSS feeds from reputable outlets (e.g. BBC World, Al Jazeera, Reuters/AP where free feeds exist, Guardian, FT/Economist free headline feeds, Nikkei Asia, oilprice/energy feeds). Claude does the reasoning and writing; scripts do fetching, storage, and site generation.
- Follow the project's WAT conventions (see `CLAUDE.md`): tools in `tools/`, SOPs in `workflows/`, intermediates in `.tmp/`, secrets (if any ever) in `.env`.

## Look and feel (approved via mockup)

- **Dark theme.** Background ~`#14171c`, panels ~`#1f242b`, inner boxes ~`#262c34`.
- **Layout:** left column of storyline panels (name, 14-day sparkline, trend label); right column with Story of the Day on top, then a 2-column grid of cards. Stacks to one column on phone.
- **Every block its own shaded panel**; "Last time", "So what", "Money angle", "My take" each in their own inner box. Generous spacing: body ~16–17px, line-height ~1.65–1.75. Owner found tight, all-white text hard to read — this is a firm requirement.
- **Colour code:** red = heating, orange = rising, grey = steady, green = cooling, blue = new storyline. Money angle box in green tint.
- Header: date + run (e.g. "Tue 4 Nov · 10:00 AM Sydney"), prev/next run, link to archive.
- Sources listed small under each item, linked.
- Reference mockup: `.superpowers/brainstorm/*/content/layout-v3.html`.

## Non-goals

- Push notifications, email, or phone alerts.
- Live/streaming market prices or charts beyond what's mentioned in text.
- Automated trading or connecting to any brokerage.
- A chat box on the web page (chat happens in Claude itself, to stay free).

## Anti-goals (would be a failure even if it works)

- Long, noisy briefings that read like a news feed or every other news site.
- Forcing a money angle or a "take" onto every story; hyping market moves daily.
- Making up facts, prices, or images. Every claim should trace to a fetched source.
- Losing history, or storylines that don't connect across days.
- Costing money.

## Plan limits

- Owner is on **Claude Pro**. Builder must first confirm that Pro allows cloud routines and how many runs a day fit within limits.
- If two full runs a day don't fit: **keep both runs**, and make the **midnight run a short update** (heat refresh + 1–2 cards) while the 10am run stays the full briefing. Only drop a run as a last resort, and tell the owner.

## Calls made by Claude (owner can override)

- **Standalone repo.** `geopol/` becomes its own public repo with its own `tools/`, `workflows/`, `CLAUDE.md`. The parent WAT scaffold and sibling projects are never pushed.
- **Split work if needed.** Deterministic steps (feed fetching, price snapshot, site build, Pages deploy) may run in **GitHub Actions** (free on public repos) on a cron just before each briefing; the Claude routine then only reads the fetched data, writes the briefing/storyline JSON, and commits. If the routine can do everything itself, one pipeline is fine. Builder verifies routine capabilities (outbound HTTP, git push, run limits) first.
- **Price snapshot tool.** A deterministic tool saves free market closes each run (e.g. Brent/WTI oil, gold, AUD/USD, DXY, S&P 500, ASX 200, Nikkei, BTC) from a free no-key source. Every "My take" stores the prices at the time, so later reviews of the take are judged against recorded numbers.
- **Web search allowed.** During a run Claude may use its own web search/fetch to deepen a story, but every URL it relies on is saved with the briefing's sources. RSS remains the primary input.

## What's left to the builder

- Exact feed list and parsing; dedupe/clustering of articles.
- Data format (e.g. JSON per run + storyline index) and folder layout.
- Heat score method (e.g. Claude-assigned 0–10 per run, smoothed) and trend thresholds.
- Static site generator approach (plain Python + HTML templates is fine).
- How the routine commits/pushes and how Pages deploys.
- Handling Sydney daylight saving in the schedule (AEDT UTC+11 / AEST UTC+10).
- Workflow SOP(s) in `workflows/` for running a briefing and for chatting with the archive, plus updating `CLAUDE.md` with commands.
- Failure handling (feeds down, routine fails): a skipped run should not corrupt history.
