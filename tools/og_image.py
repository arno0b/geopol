"""Look up an article's og:image and record it on the matching inbox item.

Usage:
    python tools/og_image.py <run_id> <article_url>

Prints the image URL, or "none". Only images the source itself publishes are
ever used, so this is the one way (besides the feed) an image becomes allowed.
"""
import argparse
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.store import load_json, save_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HEADERS = {"User-Agent": "Mozilla/5.0 geopol-briefing/1.0"}
META_TAG = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
ATTR = re.compile(r"""(\w[\w:-]*)\s*=\s*(?:"([^"]*)"|'([^']*)')""")


def find_og_image(html: str) -> str | None:
    for tag in META_TAG.findall(html):
        attrs = {m.group(1).lower(): m.group(2) if m.group(2) is not None else m.group(3) for m in ATTR.finditer(tag)}
        if attrs.get("property", attrs.get("name", "")).lower() == "og:image" and attrs.get("content", "").startswith("http"):
            return attrs["content"]
    return None


def _fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_id")
    ap.add_argument("url")
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args(argv)
    path = Path(args.root) / "data" / "inbox" / f"{args.run_id}.json"
    inbox = load_json(path)
    matches = [i for i in inbox["items"] if i["link"] == args.url]
    if not matches:
        print(f"error: {args.url} is not in inbox {args.run_id}", file=sys.stderr)
        return 1
    try:
        image = find_og_image(_fetch_html(args.url))
    except Exception as exc:
        print(f"warning: {exc}", file=sys.stderr)
        image = None
    if image is None:
        print("none")
        return 0
    for item in matches:
        item["image_url"] = image
    save_json(path, inbox)
    print(image)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
