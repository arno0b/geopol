# Workflow: Run a briefing

**Objective:** Produce one briefing for the current Sydney slot (10:00 or 00:00), merge it into the archive, and publish it.

**Who runs this:** the scheduled Claude Code routine (prompt: `Follow workflows/run_briefing.md exactly.`), or Claude in an interactive session when the owner says "run my briefing".

**Inputs:** `data/inbox/<RUN_ID>.json` (fetched by GitHub Actions at 09:20 / 23:20 Sydney), `data/prices/<RUN_ID>.json`, `data/storylines.json`, recent `data/briefings/*.json`.

**Output:** `data/briefings/<RUN_ID>.json` + updated `data/storylines.json`, committed and pushed to `main`. The push triggers the Pages deploy.

## Steps

1. **Find the slot.**
   - `git pull`
   - `python tools/slot.py current` → this is RUN_ID.
   - If `data/briefings/RUN_ID.json` already exists → stop: "already done".
   - If `data/inbox/RUN_ID.json` is missing → run `python tools/fetch_feeds.py` and `python tools/fetch_prices.py` yourself. If the inbox is still missing (exit 2: every feed failed) → stop and report. Never write a briefing without an inbox.

2. **Read.** The inbox items, `data/storylines.json`, and the last 6 briefings (newest first). Note open My takes (takes not yet reviewed as right/wrong/mixed).

3. **Choose 3–5 threads that genuinely moved.** Not the loudest headlines: the ones that change the picture. Bangladesh is a first-class lens: include it whenever something there really moved. Australia relevance is a plus. You may use web search to deepen a story; every URL you rely on goes in that item's `sources`.

4. **Images.** Use an item's `image_url` from the inbox if it has one. For an important story without one, run `python tools/og_image.py RUN_ID <article link>` and use the URL it prints. If it prints `none`, there is no image. Never invent, generate or use an image from anywhere else.

5. **Write `.tmp/briefing_RUN_ID.json`** using the schema in `tools/validate_briefing.py` (see `tests/fixtures/briefing_ok.json` for a complete example).
   - `kind: "full"`: one `story_of_day` plus 2–4 `cards`. Use `kind: "short"` (1–2 cards, `story_of_day` may be null) only for the 00:00 run when Pro usage limits are tight.
   - **Style:** compelling story, not a news feed. Short. Plain words. Each `story` is 2–4 sentences, `so_what` 1–2.
   - `last_time`: when a storyline was covered before, link the most recent run and say what changed since.
   - `money_angle`: only when there is a real market link. Otherwise null. Never hype.
   - `my_take`: only for a real opportunity or risk. Give an actual call (what you would consider doing), the reasoning, `confidence` low/medium/high, and `wrong_if` (what would prove it wrong). The owner wants real advice with reasoning; the page adds the "your call" line itself.
   - `takes_review`: revisit any earlier take whose outcome is now visible (`right`, `wrong`, `mixed`, or `open` if still too early but worth an update). Use the prices recorded with the take (`prices_at`) against today's `data/prices/RUN_ID.json`. Be honest about misses.
   - `heat`: a 0–10 score for every storyline you covered, **and** lower scores for storylines that went quiet (so they cool on the page). 0–2 quiet, 3–4 simmering, 5–6 active, 7–8 hot, 9–10 crisis.
   - A new storyline: set `storyline` to a new kebab-case slug and `new_storyline_name` to its display name.
   - `watch`: one thing to watch in the coming days, or null.

6. **Validate:** `python tools/validate_briefing.py .tmp/briefing_RUN_ID.json`. On errors, fix the JSON and retry (at most 3 tries). Success prints `ok RUN_ID`.

7. **Background upkeep** (see `workflows/write_background.md`):
   - A new storyline gets an explainer.
   - A storyline that shifted in a big way (heat jumped by 3 or more, or a clear turning point) gets a new background version with an updated `current_state` and a `change_note`.

8. **Publish:**
   - `git add data/briefings data/storylines.json data/background data/inbox`
   - `git commit -m "briefing: RUN_ID"`
   - `git push` (if it is rejected, `git pull --rebase` then push again).

## Edge cases

- **Missed slot:** never back-fill an old slot. The archive simply has a gap.
- **Validator rejects an image:** drop the image (set it to null) rather than looking for another one.
- **Only a few items fetched (fewer than 30):** write a `short` briefing and mention that sources were thin.

## Routine notes

(Filled in after verifying routine capabilities on the Pro plan.)
