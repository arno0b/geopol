"""Validate a Claude-written briefing and merge it into the archive.

Usage:
    python tools/validate_briefing.py .tmp/briefing_<run_id>.json

On errors: prints each one, exits 1, and changes nothing on disk.
On success: writes data/briefings/<run_id>.json, updates data/storylines.json,
prints "ok <run_id>".
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.store import ROOT, load_json, load_storylines, save_json, save_storylines  # noqa: E402

RUN_ID = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{4}$")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CONFIDENCE = {"low", "medium", "high"}
VERDICTS = {"right", "wrong", "mixed", "open"}
CARD_LIMITS = {"full": (2, 4), "short": (1, 2)}


def _items(briefing: dict) -> list[tuple[str, dict]]:
    items = []
    if briefing.get("story_of_day"):
        items.append(("story_of_day", briefing["story_of_day"]))
    for n, card in enumerate(briefing.get("cards") or []):
        items.append((f"cards[{n}]", card))
    return items


def _briefing_paths(root: Path) -> list[Path]:
    return sorted((root / "data" / "briefings").glob("*.json"))


def _known_take_ids(root: Path) -> set[str]:
    ids = set()
    for path in _briefing_paths(root):
        for _, item in _items(load_json(path)):
            if item.get("my_take") and item["my_take"].get("id"):
                ids.add(item["my_take"]["id"])
    return ids


def _is_http(url) -> bool:
    return isinstance(url, str) and url.startswith(("http://", "https://"))


def _check_item(path: str, item: dict, known: set, inbox_images: set, root: Path) -> list[str]:
    errors = []
    slug = item.get("storyline")
    if not isinstance(slug, str) or (slug not in known and not item.get("new_storyline_name")):
        errors.append(f"{path}.storyline '{slug}' is not a known storyline (set new_storyline_name to create one)")
    elif slug not in known and not SLUG.match(slug):
        errors.append(f"{path}.storyline '{slug}' must be kebab-case, e.g. 'arctic-shipping'")
    for field in ("headline", "story", "so_what"):
        if not isinstance(item.get(field), str) or not item[field].strip():
            errors.append(f"{path}.{field} is required")
    sources = item.get("sources") or []
    if not sources:
        errors.append(f"{path}.sources needs at least one source")
    for n, src in enumerate(sources):
        if not _is_http(src.get("url")):
            errors.append(f"{path}.sources[{n}].url must be an http(s) link")
        if not src.get("name"):
            errors.append(f"{path}.sources[{n}].name is required")
    image = item.get("image")
    if image is not None and image.get("url") not in inbox_images:
        errors.append(f"{path}.image.url not from any source")
    last = item.get("last_time")
    if last is not None:
        if not (root / "data" / "briefings" / f"{last.get('run_id')}.json").exists():
            errors.append(f"{path}.last_time.run_id '{last.get('run_id')}' is not an archived briefing")
        if not last.get("text"):
            errors.append(f"{path}.last_time.text is required")
    take = item.get("my_take")
    if take is not None:
        for field in ("text", "reasoning", "wrong_if"):
            if not take.get(field):
                errors.append(f"{path}.my_take.{field} is required")
        if take.get("confidence") not in CONFIDENCE:
            errors.append(f"{path}.my_take.confidence must be one of low, medium, high")
    return errors


def validate(briefing: dict, root: Path = ROOT) -> list[str]:
    root = Path(root)
    errors = []
    run_id = briefing.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID.match(run_id):
        return [f"run_id '{run_id}' must look like 2026-11-04-1000"]
    inbox_path = root / "data" / "inbox" / f"{run_id}.json"
    if not inbox_path.exists():
        return [f"run_id {run_id} has no inbox at data/inbox/{run_id}.json"]
    inbox_images = {i["image_url"] for i in load_json(inbox_path)["items"] if i.get("image_url")}

    kind = briefing.get("kind")
    if kind not in CARD_LIMITS:
        errors.append("kind must be 'full' or 'short'")
    else:
        if kind == "full" and not briefing.get("story_of_day"):
            errors.append("story_of_day is required for a full briefing")
        low, high = CARD_LIMITS[kind]
        count = len(briefing.get("cards") or [])
        if not low <= count <= high:
            errors.append(f"cards: a {kind} briefing needs {low}–{high} cards, got {count}")

    known = set(load_storylines(root))
    new_slugs = set()
    for path, item in _items(briefing):
        errors += _check_item(path, item, known, inbox_images, root)
        if item.get("storyline") not in known and item.get("new_storyline_name"):
            new_slugs.add(item["storyline"])

    for slug, value in (briefing.get("heat") or {}).items():
        if slug not in known and slug not in new_slugs:
            errors.append(f"heat.{slug} is not a known or new storyline")
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 10:
            errors.append(f"heat.{slug} must be a whole number 0–10, got {value!r}")

    take_ids = _known_take_ids(root) if briefing.get("takes_review") else set()
    for n, review in enumerate(briefing.get("takes_review") or []):
        if review.get("take_id") not in take_ids:
            errors.append(f"takes_review[{n}].take_id '{review.get('take_id')}' is not an earlier take")
        if review.get("verdict") not in VERDICTS:
            errors.append(f"takes_review[{n}].verdict must be one of right, wrong, mixed, open")
        if not review.get("text"):
            errors.append(f"takes_review[{n}].text is required")
    return errors


def merge(briefing: dict, root: Path = ROOT) -> Path:
    root = Path(root)
    run_id = briefing["run_id"]
    out = root / "data" / "briefings" / f"{run_id}.json"
    if out.exists():
        raise FileExistsError(f"{out} already exists; briefings are never overwritten")
    prices_path = root / "data" / "prices" / f"{run_id}.json"
    prices = load_json(prices_path)["prices"] if prices_path.exists() else {}

    stories = load_storylines(root)
    take_n = 0
    for _, item in _items(briefing):
        slug = item["storyline"]
        if slug not in stories:
            stories[slug] = {"name": item["new_storyline_name"], "created": run_id, "heat": {}, "runs": []}
        if run_id not in stories[slug]["runs"]:
            stories[slug]["runs"].append(run_id)
        if item.get("my_take"):
            take_n += 1
            item["my_take"]["id"] = f"{run_id}-{take_n}"
            item["my_take"]["prices_at"] = prices
    for slug, value in (briefing.get("heat") or {}).items():
        stories[slug]["heat"][run_id] = value

    save_json(out, briefing)
    save_storylines(stories, root)
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args(argv)
    try:
        briefing = load_json(args.path)
    except json.JSONDecodeError as exc:
        print(f"error: {args.path} is not valid JSON: {exc}")
        return 1
    errors = validate(briefing, Path(args.root))
    if errors:
        for e in errors:
            print(f"error: {e}")
        return 1
    try:
        merge(briefing, Path(args.root))
    except FileExistsError as exc:
        print(f"error: {exc}")
        return 1
    print(f"ok {briefing['run_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
