"""Fetch the RSS feeds in config/feeds.json into data/inbox/<run_id>.json.

Usage:
    python tools/fetch_feeds.py [--run-id ID] [--max-age-hours 36]

Exit codes: 0 written or already fetched, 2 nothing fetched (no file written).
"""
import argparse
import hashlib
import html
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import feedparser
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.slot import run_id_for  # noqa: E402
from tools.store import load_json, save_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HEADERS = {"User-Agent": "geopol-briefing/1.0 (+https://github.com/arno0b/geopol)"}
TIMEOUT = 15
SUMMARY_MAX = 600
MAX_PER_FEED = 25


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _item_id(link: str) -> str:
    parts = urlsplit(link.strip())
    normalized = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def _image(entry) -> str | None:
    for key in ("media_content", "media_thumbnail"):
        for media in entry.get(key) or []:
            if media.get("url") and media.get("medium", "image") == "image":
                return media["url"]
    for enc in entry.get("enclosures") or []:
        if enc.get("href") and (enc.get("type") or "").startswith("image/"):
            return enc["href"]
    return None


def _published(entry) -> str | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()


def parse_feed(raw: bytes, source: str, lens: str) -> list[dict]:
    parsed = feedparser.parse(raw)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"not a feed ({parsed.get('bozo_exception', 'unparseable')})")
    items = []
    for entry in parsed.entries:
        link = entry.get("link")
        title = _clean(entry.get("title", ""))
        if not link or not title:
            continue
        items.append({
            "id": _item_id(link),
            "title": title,
            "link": link,
            "summary": _clean(entry.get("summary", ""))[:SUMMARY_MAX],
            "published": _published(entry),
            "source": source,
            "lens": lens,
            "image_url": _image(entry),
        })
    return items


def fetch_all(feeds: list[dict], get=requests.get, max_per_feed: int = MAX_PER_FEED) -> tuple[list[dict], list[str]]:
    items, warnings = [], []
    seen_ids, seen_titles = set(), set()
    for feed in feeds:
        try:
            resp = get(feed["url"], headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            parsed = parse_feed(resp.content, feed["name"], feed["lens"])
        except Exception as exc:  # one broken feed must never stop the rest
            warnings.append(f"{feed['name']}: {exc}")
            continue
        if not parsed:
            warnings.append(f"{feed['name']}: no items")
        parsed.sort(key=lambda i: i["published"] or "", reverse=True)
        for item in parsed[:max_per_feed]:
            title_key = item["title"].lower()
            if item["id"] in seen_ids or title_key in seen_titles:
                continue
            seen_ids.add(item["id"])
            seen_titles.add(title_key)
            items.append(item)
    items.sort(key=lambda i: i["published"] or "", reverse=True)
    return items, warnings


def main(argv: list[str], feeds: list[dict] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--max-age-hours", type=float, default=36)
    args = ap.parse_args(argv)
    root = Path(args.root)
    run_id = args.run_id or run_id_for(datetime.now(timezone.utc))
    out = root / "data" / "inbox" / f"{run_id}.json"
    if out.exists():
        print(f"already fetched {run_id}")
        return 0
    if feeds is None:
        feeds = load_json(root / "config" / "feeds.json")
    items, warnings = fetch_all(feeds)
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=args.max_age_hours)).isoformat()
    items = [i for i in items if i["published"] is None or i["published"] >= cutoff]
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if not items:
        print(f"no items fetched for {run_id}; nothing written", file=sys.stderr)
        return 2
    save_json(out, {
        "run_id": run_id,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
        "warnings": warnings,
    })
    print(f"wrote {len(items)} items to {out.relative_to(root)} ({len(warnings)} warnings)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
