"""Validate a background explainer and append it as a new version.

Usage:
    python tools/validate_background.py .tmp/background_<slug>.json [--date YYYY-MM-DD]

Versions are append-only in data/background/<slug>.json; older ones are kept.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.slot import SYDNEY  # noqa: E402
from tools.store import ROOT, load_json, load_storylines, save_json  # noqa: E402

PROSE = ("how_we_got_here", "stakes", "current_state", "watch_next")
MIN_TIMELINE = 3
MIN_SOURCES = 2


def validate_background(doc: dict, root: Path = ROOT) -> list[str]:
    errors = []
    if doc.get("slug") not in load_storylines(root):
        errors.append(f"slug '{doc.get('slug')}' is not a known storyline")
    for field in PROSE:
        if not isinstance(doc.get(field), str) or not doc[field].strip():
            errors.append(f"{field} is required")
    players = doc.get("players") or []
    if not players or any(not p.get("name") or not p.get("wants") for p in players):
        errors.append("players needs at least one {name, wants}")
    timeline = doc.get("timeline") or []
    if len(timeline) < MIN_TIMELINE or any(not t.get("date") or not t.get("event") for t in timeline):
        errors.append(f"timeline needs at least {MIN_TIMELINE} {{date, event}} entries")
    sources = doc.get("sources") or []
    if len(sources) < MIN_SOURCES or any(not str(s.get("url", "")).startswith(("http://", "https://")) for s in sources):
        errors.append(f"sources needs at least {MIN_SOURCES} entries with http(s) links")
    return errors


def add_version(doc: dict, root: Path, date: str) -> Path:
    path = Path(root) / "data" / "background" / f"{doc['slug']}.json"
    record = load_json(path) if path.exists() else {"slug": doc["slug"], "versions": []}
    record["versions"].append({"date": date, **{k: v for k, v in doc.items() if k != "slug"}})
    save_json(path, record)
    return path


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--date", default=datetime.now(SYDNEY).strftime("%Y-%m-%d"))
    args = ap.parse_args(argv)
    try:
        doc = load_json(args.path)
    except json.JSONDecodeError as exc:
        print(f"error: {args.path} is not valid JSON: {exc}")
        return 1
    errors = validate_background(doc, Path(args.root))
    if errors:
        for e in errors:
            print(f"error: {e}")
        return 1
    path = add_version(doc, Path(args.root), args.date)
    print(f"ok {doc['slug']} v{len(load_json(path)['versions'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
