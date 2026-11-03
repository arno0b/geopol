"""Build the static site from data/ into site/.

Usage:
    python tools/build_site.py [--out site]
"""
import argparse
import html
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.store import ROOT, daily_heat, load_json, load_storylines, sparkline, trend  # noqa: E402

CODE_ROOT = Path(__file__).resolve().parent.parent
ROBOTS = "User-agent: *\nDisallow: /\n"
TREND_LABELS = {
    "new": "🆕 New storyline",
    "heating": "▲ Heating up",
    "rising": "▲ Rising",
    "steady": "▬ Steady",
    "cooling": "▼ Cooling",
    "quiet": "Quiet",
}


def run_label(run_id: str) -> str:
    dt = datetime.strptime(run_id, "%Y-%m-%d-%H%M")
    clock = "10:00 AM" if dt.hour == 10 else "12:00 AM"
    return f"{dt:%a} {dt.day} {dt:%b} · {clock} Sydney"


def md(text: str) -> Markup:
    """Render Markdown from Claude-written prose, with any raw HTML escaped first."""
    return Markup(markdown.markdown(html.escape(text or "", quote=False)))


def _items(briefing: dict) -> list[dict]:
    return ([briefing["story_of_day"]] if briefing.get("story_of_day") else []) + list(briefing.get("cards") or [])


class Site:
    def __init__(self, root: Path, out: Path):
        self.root, self.out = Path(root), Path(out)
        self.stories = load_storylines(self.root)
        self.briefings = [load_json(p) for p in sorted((self.root / "data" / "briefings").glob("*.json"))]
        bg_dir = self.root / "data" / "background"
        self.backgrounds = {p.stem: load_json(p) for p in sorted(bg_dir.glob("*.json"))} if bg_dir.exists() else {}
        self.latest = self.briefings[-1]["run_id"] if self.briefings else None
        self.reviews = defaultdict(list)  # take_id -> [(run_id, review)]
        for b in self.briefings:
            for review in b.get("takes_review") or []:
                self.reviews[review["take_id"]].append((b["run_id"], review))
        self.env = Environment(
            loader=FileSystemLoader(CODE_ROOT / "templates"),
            autoescape=select_autoescape(["html", "j2"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.filters["md"] = md
        self.env.globals.update(run_label=run_label, trend_labels=TREND_LABELS, story_meta=self.story_meta)

    def story_meta(self, slug: str, as_of: str | None = None) -> dict:
        story = self.stories[slug]
        as_of = as_of or self.latest
        today = datetime.strptime(as_of, "%Y-%m-%d-%H%M").date()
        values = daily_heat(story, today)
        return {
            "slug": slug,
            "name": story["name"],
            "trend": trend(story, as_of),
            "spark": sparkline(values),
            "latest_heat": next((v for v in reversed(values) if v is not None), None),
            "has_heat": any(v is not None for v in values),
            "has_background": slug in self.backgrounds,
        }

    def render(self, rel: str, template: str, **ctx) -> None:
        path = self.out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        base = "../" * rel.count("/")
        bprefix = "" if rel.startswith("b/") else base + "b/"
        html_text = self.env.get_template(template).render(base=base, bprefix=bprefix, latest=self.latest, **ctx)
        path.write_text(html_text, encoding="utf-8", newline="\n")

    def sidebar(self, as_of: str) -> list[dict]:
        metas = [self.story_meta(slug, as_of) for slug in self.stories]
        metas = [m for m in metas if m["has_heat"]]
        return sorted(metas, key=lambda m: -(m["latest_heat"] or 0))

    def build_briefings(self) -> None:
        for n, b in enumerate(self.briefings):
            ctx = {
                "b": b,
                "prev": self.briefings[n - 1]["run_id"] if n > 0 else None,
                "next": self.briefings[n + 1]["run_id"] if n + 1 < len(self.briefings) else None,
                "sidebar": self.sidebar(b["run_id"]),
            }
            self.render(f"b/{b['run_id']}.html", "briefing.html.j2", **ctx)
            if b["run_id"] == self.latest:
                self.render("index.html", "briefing.html.j2", **ctx)
        if not self.briefings:
            self.render("index.html", "empty.html.j2")

    def build_archive(self) -> None:
        months = defaultdict(list)
        for b in reversed(self.briefings):
            dt = datetime.strptime(b["run_id"], "%Y-%m-%d-%H%M")
            lead = _items(b)[0] if _items(b) else None
            months[f"{dt:%B %Y}"].append({"run_id": b["run_id"], "headline": lead["headline"] if lead else ""})
        self.render("archive.html", "archive.html.j2", months=months)

    def build_storylines(self) -> None:
        for slug in self.stories:
            entries, takes = [], []
            for b in reversed(self.briefings):
                for item in _items(b):
                    if item["storyline"] != slug:
                        continue
                    entries.append({"run_id": b["run_id"], "item": item})
                    if item.get("my_take"):
                        takes.append({"run_id": b["run_id"], "take": item["my_take"],
                                      "reviews": self.reviews.get(item["my_take"].get("id"), [])})
            meta = self.story_meta(slug) if self.latest else {"slug": slug, "name": self.stories[slug]["name"],
                                                               "trend": "quiet", "spark": "", "has_background": slug in self.backgrounds}
            self.render(f"s/{slug}.html", "storyline.html.j2", meta=meta, entries=entries, takes=takes)

    def build_background(self) -> None:
        listing = []
        for slug, record in self.backgrounds.items():
            versions = record["versions"]
            name = self.stories.get(slug, {}).get("name", slug)
            for n, version in enumerate(versions, start=1):
                is_latest = n == len(versions)
                rel = f"background/{slug}.html" if is_latest else f"background/{slug}-v{n}.html"
                self.render(rel, "background.html.j2", slug=slug, name=name, v=version, n=n,
                            versions=versions, is_latest=is_latest)
            listing.append({"slug": slug, "name": name, "updated": versions[-1]["date"]})
        listing.sort(key=lambda x: x["name"])
        self.render("background/index.html", "background_index.html.j2", listing=listing)

    def build(self) -> None:
        if self.out.exists():
            shutil.rmtree(self.out)
        self.out.mkdir(parents=True)
        self.build_briefings()
        self.build_archive()
        self.build_storylines()
        self.build_background()
        (self.out / "robots.txt").write_text(ROBOTS, encoding="utf-8", newline="\n")
        (self.out / "static").mkdir(exist_ok=True)
        shutil.copy(CODE_ROOT / "static" / "style.css", self.out / "static" / "style.css")
        (self.out / ".nojekyll").write_text("", encoding="utf-8")


def build(root: Path, out: Path) -> None:
    Site(root, out).build()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--out", default=str(ROOT / "site"))
    args = ap.parse_args(argv)
    build(Path(args.root), Path(args.out))
    print(f"built site into {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
