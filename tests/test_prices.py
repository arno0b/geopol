import json

import requests

from tools import og_image
from tools.fetch_prices import fetch_prices
from tools.og_image import find_og_image

SYMBOLS = [
    {"key": "brent", "label": "Brent", "symbol": "BZ=F"},
    {"key": "gold", "label": "Gold", "symbol": "GC=F"},
]


class FakeResponse:
    def __init__(self, payload=None, status=200, text=""):
        self._payload = payload
        self.status_code = status
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return self._payload


def chart(price, ts=1793694887):
    return {"chart": {"result": [{"meta": {"regularMarketPrice": price, "regularMarketTime": ts}}]}}


def test_parses_quote():
    prices = fetch_prices(SYMBOLS, get=lambda url, **kw: FakeResponse(chart(106.68)))
    assert prices["brent"]["value"] == 106.68
    assert prices["brent"]["label"] == "Brent"
    assert prices["brent"]["as_of"].startswith("2026-11-0")


def test_failed_symbol_is_none():
    def get(url, **kw):
        return FakeResponse(status=500) if "BZ" in url else FakeResponse(chart(4000.5))
    prices = fetch_prices(SYMBOLS, get=get)
    assert prices["brent"]["value"] is None and prices["brent"]["as_of"] is None
    assert prices["gold"]["value"] == 4000.5


def test_malformed_payload_is_none():
    prices = fetch_prices(SYMBOLS[:1], get=lambda url, **kw: FakeResponse({"chart": {"result": None}}))
    assert prices["brent"]["value"] is None


def test_og_image_found():
    html = '<html><head><meta property="og:image" content="https://x.example/y.jpg"></head></html>'
    assert find_og_image(html) == "https://x.example/y.jpg"


def test_og_image_attribute_order_swapped():
    html = "<meta content='https://x.example/z.jpg' property='og:image' />"
    assert find_og_image(html) == "https://x.example/z.jpg"


def test_og_image_missing():
    assert find_og_image("<html><head><title>t</title></head></html>") is None


def test_og_cli_updates_inbox(tmp_path, monkeypatch):
    inbox = tmp_path / "data" / "inbox"
    inbox.mkdir(parents=True)
    path = inbox / "2026-11-04-1000.json"
    path.write_text(json.dumps({"items": [
        {"link": "https://a.example/story", "image_url": None},
        {"link": "https://b.example/other", "image_url": None},
    ]}), encoding="utf-8")
    page = '<meta property="og:image" content="https://a.example/img.jpg">'
    monkeypatch.setattr(og_image, "_fetch_html", lambda url: page)
    code = og_image.main(["2026-11-04-1000", "https://a.example/story", "--root", str(tmp_path)])
    assert code == 0
    items = json.loads(path.read_text(encoding="utf-8"))["items"]
    assert items[0]["image_url"] == "https://a.example/img.jpg"
    assert items[1]["image_url"] is None
