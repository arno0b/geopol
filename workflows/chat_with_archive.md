# Workflow: Chat with the archive

**Objective:** Answer the owner's questions ("why does Hormuz matter for Australia?", "what did we say about chips last month?", "how have your takes done?") from the saved history, with reasoning.

## Where things are

- `data/briefings/<run_id>.json`: every briefing (story of the day, cards, takes, reviews, heat).
- `data/storylines.json`: every storyline with its heat history by run.
- `data/background/<slug>.json`: versioned explainers.
- `data/prices/<run_id>.json`: market snapshot at each run (to judge takes).
- Site pages: `https://arno0b.github.io/geopol/b/<run_id>.html`, `/s/<slug>.html`, `/background/<slug>.html`.

## How to answer

1. `git pull` first, so the answer includes the latest runs.
2. Search the data (Grep across `data/briefings` for the topic or slug) and read the relevant runs.
3. Answer briefly, citing the runs you used ("on 4 Nov 10:00 we said…") with links to the site pages.
4. For "how are the takes doing": list each take with its verdicts from later `takes_review` entries, and compare `prices_at` with the latest prices.
5. Advice is welcome: give a real view with reasoning and what would change it. The decision is the owner's.
6. Use web search when the question goes beyond the archive, and say which parts came from outside it.
