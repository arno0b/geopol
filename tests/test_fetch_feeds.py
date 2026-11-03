import json
from pathlib import Path

import requests

from tools import fetch_feeds
from tools.fetch_feeds import fetch_all, parse_feed

FIX = Path(__file__).parent / "fixtures"
BBC = (FIX / "feed_bbc.xml").read_bytes()
MEDIA = (FIX / "feed_media.xml").read_bytes()
NOT_RSS = (FIX / "not_rss.html").read_bytes()


class FakeResponse:
    def __init__(self, content, status=200):
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


def fake_get(mapping):
    def get(url, **kwargs):
        value = mapping[url]
        if isinstance(value, Exception):
            raise value
        return FakeResponse(value)
    return get


def test_parse_basic():
    items = parse_feed(BBC, "BBC World", "world")
    assert [i["title"] for i in items] == ["Tankers reroute near Hormuz", "Chip talks stall"]
    assert items[0]["link"] == "https://www.bbc.co.uk/news/world-1"
    assert items[0]["image_url"] is None
    assert items[0]["source"] == "BBC World" and items[0]["lens"] == "world"
    assert items[0]["published"].startswith("2026-11-03T20:00")


def test_parse_media_image():
    items = parse_feed(MEDIA, "Daily Star", "bangladesh")
    assert items[0]["image_url"] == "https://images.thedailystar.net/1.jpg"
    assert items[0]["title"] == "ঢাকায় নির্বাচন প্রস্তুতি"


def test_parse_enclosure_image():
    items = parse_feed(MEDIA, "Daily Star", "bangladesh")
    assert items[1]["image_url"] == "https://other.example/h.jpg"


def test_strips_html_summary():
    items = parse_feed(BBC, "BBC World", "world")
    assert items[0]["summary"] == "Two tankers changed course."


def test_not_rss_yields_warning():
    feeds = [{"name": "Broken", "url": "u1", "lens": "world"}, {"name": "BBC", "url": "u2", "lens": "world"}]
    items, warnings = fetch_all(feeds, get=fake_get({"u1": NOT_RSS, "u2": BBC}))
    assert len(items) == 2
    assert len(warnings) == 1 and "Broken" in warnings[0]


def test_timeout_yields_warning():
    feeds = [{"name": "Slow", "url": "u1", "lens": "world"}, {"name": "BBC", "url": "u2", "lens": "world"}]
    items, warnings = fetch_all(feeds, get=fake_get({"u1": requests.Timeout("t"), "u2": BBC}))
    assert len(items) == 2 and "Slow" in warnings[0]


def test_dedupe_same_link_two_feeds():
    feeds = [{"name": "A", "url": "u1", "lens": "world"}, {"name": "B", "url": "u2", "lens": "world"}]
    items, _ = fetch_all(feeds, get=fake_get({"u1": BBC, "u2": BBC}))
    assert len(items) == 2


def test_dedupe_same_title_different_outlet():
    feeds = [{"name": "A", "url": "u1", "lens": "world"}, {"name": "B", "url": "u2", "lens": "bangladesh"}]
    items, _ = fetch_all(feeds, get=fake_get({"u1": BBC, "u2": MEDIA}))
    titles = [i["title"].lower() for i in items]
    assert titles.count("tankers reroute near hormuz") == 1
    assert len(items) == 3


def test_per_feed_cap_keeps_newest():
    feeds = [{"name": "A", "url": "u1", "lens": "world"}]
    items, _ = fetch_all(feeds, get=fake_get({"u1": BBC}), max_per_feed=1)
    assert [i["title"] for i in items] == ["Tankers reroute near Hormuz"]


def test_newest_first():
    feeds = [{"name": "A", "url": "u1", "lens": "world"}, {"name": "B", "url": "u2", "lens": "bangladesh"}]
    items, _ = fetch_all(feeds, get=fake_get({"u1": BBC, "u2": MEDIA}))
    published = [i["published"] for i in items]
    assert published == sorted(published, reverse=True)


def test_cli_no_write_when_all_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_feeds, "fetch_all", lambda feeds, **kw: ([], ["all down"]))
    code = fetch_feeds.main(["--run-id", "2026-11-04-1000", "--root", str(tmp_path)], feeds=[])
    assert code == 2
    assert not (tmp_path / "data" / "inbox" / "2026-11-04-1000.json").exists()


def test_cli_skips_when_already_fetched(tmp_path, monkeypatch):
    inbox = tmp_path / "data" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "2026-11-04-1000.json").write_text('{"keep": true}', encoding="utf-8")
    monkeypatch.setattr(fetch_feeds, "fetch_all", lambda feeds, **kw: (_ for _ in ()).throw(AssertionError("fetched")))
    code = fetch_feeds.main(["--run-id", "2026-11-04-1000", "--root", str(tmp_path)], feeds=[])
    assert code == 0
    assert json.loads((inbox / "2026-11-04-1000.json").read_text(encoding="utf-8")) == {"keep": True}
