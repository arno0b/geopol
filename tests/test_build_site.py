import copy
import json

import pytest

from tests.conftest import write
from tools.build_site import build
from tools.validate_briefing import merge


def add_briefing(root, briefing, run_id, **changes):
    b = copy.deepcopy(briefing)
    b["run_id"] = run_id
    b.update(changes)
    if not (root / "data" / "inbox" / f"{run_id}.json").exists():
        write(root / "data" / "inbox" / f"{run_id}.json", {"run_id": run_id, "items": []})
    merge(b, root)
    return b


@pytest.fixture
def site(root, briefing, tmp_path):
    add_briefing(root, briefing, "2026-11-04-1000")
    later = copy.deepcopy(briefing)
    later["story_of_day"]["headline"] = "Hormuz: insurers double premiums"
    later["story_of_day"]["image"] = None
    later["story_of_day"]["last_time"] = {"run_id": "2026-11-04-1000", "text": "We flagged the reroutes."}
    later["takes_review"] = [{"take_id": "2026-11-04-1000-1", "verdict": "open", "text": "Too early."}]
    add_briefing(root, later, "2026-11-05-1000")
    out = tmp_path / "site"
    build(root, out)
    return out


def read(path):
    return path.read_text(encoding="utf-8")


def test_index_matches_latest(site):
    index = read(site / "index.html")
    assert "Hormuz: insurers double premiums" in index
    assert "Thu 5 Nov · 10:00 AM Sydney" in index


def test_noindex_on_every_page(site):
    pages = list(site.rglob("*.html"))
    assert len(pages) >= 6
    for page in pages:
        assert '<meta name="robots" content="noindex, nofollow">' in read(page), page


def test_robots_txt(site):
    assert read(site / "robots.txt") == "User-agent: *\nDisallow: /\n"


def test_css_copied(site):
    assert (site / "static" / "style.css").exists()


def test_prev_next_skip_gaps(site):
    first = read(site / "b" / "2026-11-04-1000.html")
    assert 'href="2026-11-05-1000.html"' in first
    second = read(site / "b" / "2026-11-05-1000.html")
    assert 'href="2026-11-04-1000.html"' in second


def test_script_in_text_escaped(root, briefing, tmp_path):
    briefing["cards"][0]["headline"] = "<script>alert(1)</script>"
    add_briefing(root, briefing, "2026-11-04-1000")
    build(root, tmp_path / "site")
    page = read(tmp_path / "site" / "index.html")
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_bangla_renders(root, briefing, tmp_path):
    briefing["cards"][1]["headline"] = "ঢাকায় নির্বাচন প্রস্তুতি"
    add_briefing(root, briefing, "2026-11-04-1000")
    build(root, tmp_path / "site")
    page = read(tmp_path / "site" / "index.html")
    assert '<meta charset="utf-8">' in page
    assert "ঢাকায় নির্বাচন প্রস্তুতি" in page


def test_null_money_box_omitted(root, briefing, tmp_path):
    briefing["story_of_day"]["money_angle"] = None
    add_briefing(root, briefing, "2026-11-04-1000")
    build(root, tmp_path / "site")
    assert "MONEY ANGLE" not in read(tmp_path / "site" / "index.html")


def test_money_and_take_boxes_shown(site):
    first = read(site / "b" / "2026-11-04-1000.html")
    assert "MONEY ANGLE" in first and "Brent up 2%" in first
    assert "MY TAKE" in first and "Wrong if" in first
    assert "not financial advice" in first


def test_image_rendered_with_credit(site):
    first = read(site / "b" / "2026-11-04-1000.html")
    assert 'src="https://img.example/hormuz.jpg"' in first
    assert "BBC" in first


def test_last_time_and_review_shown(site):
    second = read(site / "b" / "2026-11-05-1000.html")
    assert "LAST TIME" in second and "We flagged the reroutes." in second
    assert "Too early." in second


def test_sidebar_lists_heated_storylines(site):
    index = read(site / "index.html")
    assert 'href="s/middle-east.html"' in index
    assert 'href="s/taiwan.html"' not in index  # no heat recorded


def test_storyline_page_lists_history(site):
    page = read(site / "s" / "middle-east.html")
    assert "Hormuz: insurers double premiums" in page
    assert "The Strait gets tense again" in page
    assert page.index("Hormuz: insurers") < page.index("The Strait gets tense")
    assert "Energy shippers look like the cleaner way" in page  # take listed
    assert "Too early." in page  # with its later review


def test_archive_lists_all(site):
    archive = read(site / "archive.html")
    assert "November 2026" in archive
    assert 'href="b/2026-11-04-1000.html"' in archive and 'href="b/2026-11-05-1000.html"' in archive


def test_background_versions_linked(root, briefing, tmp_path):
    add_briefing(root, briefing, "2026-11-04-1000")
    doc = {"date": "2026-11-03", "how_we_got_here": "It <b>began</b> in **2024**.", "players": [{"name": "A", "wants": "B"}],
           "stakes": "s", "current_state": "Old state", "watch_next": "w",
           "timeline": [{"date": "2024", "event": "e"}] * 3, "sources": [{"name": "n", "url": "https://x.example"}] * 2,
           "change_note": None}
    newer = dict(doc, date="2026-11-20", current_state="New state", change_note="Election date set")
    write(root / "data" / "background" / "middle-east.json", {"slug": "middle-east", "versions": [doc, newer]})
    out = tmp_path / "site"
    build(root, out)
    latest = read(out / "background" / "middle-east.html")
    assert "New state" in latest and "Election date set" in latest
    assert 'href="middle-east-v1.html"' in latest
    assert "<strong>2024</strong>" in latest  # markdown rendered
    assert "<b>began</b>" not in latest  # raw html escaped
    assert "Old state" in read(out / "background" / "middle-east-v1.html")
    assert 'href="middle-east.html"' in read(out / "background" / "index.html")
    assert 'href="../background/middle-east.html"' in read(out / "s" / "middle-east.html")


def test_empty_state(root, tmp_path):
    out = tmp_path / "site"
    build(root, out)
    assert "First briefing coming soon" in read(out / "index.html")
    assert (out / "archive.html").exists()


def test_midnight_label(root, briefing, tmp_path):
    add_briefing(root, briefing, "2026-11-05-0000")
    build(root, tmp_path / "site")
    assert "Thu 5 Nov · 12:00 AM Sydney" in read(tmp_path / "site" / "index.html")
