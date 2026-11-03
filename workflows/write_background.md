# Workflow: Write a background explainer

**Objective:** Give the owner the background on one storyline: how it got here, who wants what, what's at stake, and what to watch. It should take about 5 minutes to read, in the same compelling, not-too-much style as the briefings.

**When:** at launch for every seed storyline (Bangladesh first), whenever a new storyline is created, and when a storyline shifts in a big way (see `run_briefing.md` step 7).

## Steps

1. Read the storyline's entries in recent briefings (if any) and its latest background version in `data/background/<slug>.json` (if any).
2. Research with web search. Prefer reputable outlets and primary sources; note every URL you use.
3. Write `.tmp/background_<slug>.json`:

```json
{
  "slug": "bangladesh-politics",
  "how_we_got_here": "Markdown. The story so far: key history and turning points.",
  "players": [{"name": "…", "wants": "…"}],
  "stakes": "Markdown. What's at stake, including the money angle.",
  "current_state": "Markdown. Where things stand as of today.",
  "watch_next": "Markdown. What to watch in the coming weeks and months.",
  "timeline": [{"date": "2024-08-05", "event": "…"}],
  "sources": [{"name": "…", "url": "https://…"}],
  "change_note": null
}
```

   - At least 3 timeline entries and 2 sources. Prose fields are Markdown; raw HTML is shown as text.
   - For an update, keep what still holds, rewrite `current_state` (and anything else that changed), and set `change_note` to one line saying what changed.
4. `python tools/validate_background.py .tmp/background_<slug>.json` → `ok <slug> v<n>`. Fix and retry on errors.
5. `git add data/background && git commit -m "background: <slug>"` and push.

Earlier versions are never edited; each run appends a new version, and the site links to all of them.
