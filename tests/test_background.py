import pytest

from tests.conftest import write
from tools import validate_background as background_cli
from tools.store import load_json
from tools.validate_background import add_version, validate_background


@pytest.fixture
def doc():
    return {
        "slug": "bangladesh-politics",
        "how_we_got_here": "In **August 2024** mass protests ended Sheikh Hasina's rule.",
        "players": [{"name": "Interim government", "wants": "A credible election."}],
        "stakes": "Direction of a 170-million-person economy.",
        "current_state": "Parties are preparing for the vote.",
        "watch_next": "Candidate lists and turnout.",
        "timeline": [
            {"date": "2024-07", "event": "Quota protests begin"},
            {"date": "2024-08-05", "event": "Hasina leaves office"},
            {"date": "2024-08-08", "event": "Interim government sworn in"},
        ],
        "sources": [
            {"name": "BBC", "url": "https://www.bbc.co.uk/news/a"},
            {"name": "Dhaka Tribune", "url": "https://www.dhakatribune.com/b"},
        ],
        "change_note": None,
    }


def test_valid_background(doc, root):
    assert validate_background(doc, root) == []


def test_too_few_timeline_rejected(doc, root):
    doc["timeline"] = doc["timeline"][:2]
    assert any(e.startswith("timeline") for e in validate_background(doc, root))


def test_too_few_sources_rejected(doc, root):
    doc["sources"] = doc["sources"][:1]
    assert any(e.startswith("sources") for e in validate_background(doc, root))


def test_empty_prose_rejected(doc, root):
    doc["stakes"] = "  "
    assert "stakes is required" in validate_background(doc, root)


def test_unknown_slug_rejected(doc, root):
    doc["slug"] = "atlantis"
    assert any(e.startswith("slug") for e in validate_background(doc, root))


def test_second_version_appends_keeps_first(doc, root):
    add_version(doc, root, "2026-11-03")
    second = dict(doc, current_state="Election date announced.", change_note="Election date set")
    path = add_version(second, root, "2026-11-20")
    versions = load_json(path)["versions"]
    assert [v["date"] for v in versions] == ["2026-11-03", "2026-11-20"]
    assert versions[0]["current_state"] == "Parties are preparing for the vote."
    assert versions[1]["change_note"] == "Election date set"


def test_cli_invalid_writes_nothing(doc, root, capsys):
    doc["timeline"] = []
    path = root / "bg.json"
    write(path, doc)
    assert background_cli.main([str(path), "--root", str(root)]) == 1
    assert not (root / "data" / "background").exists()
    assert "timeline" in capsys.readouterr().out


def test_cli_ok(doc, root, capsys):
    path = root / "bg.json"
    write(path, doc)
    assert background_cli.main([str(path), "--root", str(root), "--date", "2026-11-03"]) == 0
    assert "ok bangladesh-politics v1" in capsys.readouterr().out
