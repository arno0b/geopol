import json

import pytest

from tests.conftest import write
from tools import validate_briefing
from tools.store import load_json, load_storylines
from tools.validate_briefing import merge, validate


def snapshot(root):
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_valid_fixture_passes(briefing, root):
    assert validate(briefing, root) == []


def test_five_cards_rejected(briefing, root):
    briefing["cards"] = (briefing["cards"] * 3)[:5]
    errors = validate(briefing, root)
    assert any(e.startswith("cards") and "2–4" in e for e in errors)


def test_unknown_storyline_rejected(briefing, root):
    briefing["cards"][0]["storyline"] = "atlantis"
    assert any(e.startswith("cards[0].storyline") for e in validate(briefing, root))


def test_new_storyline_accepted_and_created(briefing, root):
    briefing["cards"][0]["storyline"] = "arctic-shipping"
    briefing["cards"][0]["new_storyline_name"] = "Arctic shipping"
    briefing["heat"]["arctic-shipping"] = 4
    assert validate(briefing, root) == []
    merge(briefing, root)
    stories = load_storylines(root)
    assert stories["arctic-shipping"]["created"] == "2026-11-04-1000"
    assert stories["arctic-shipping"]["name"] == "Arctic shipping"


def test_new_storyline_bad_slug_rejected(briefing, root):
    briefing["cards"][0]["storyline"] = "Arctic Shipping"
    briefing["cards"][0]["new_storyline_name"] = "Arctic shipping"
    assert any("kebab-case" in e for e in validate(briefing, root))


def test_image_not_from_source_rejected(briefing, root):
    briefing["cards"][0]["image"] = {"url": "https://made-up.example/ai.png", "credit": "?"}
    assert "cards[0].image.url not from any source" in validate(briefing, root)


def test_missing_source_rejected(briefing, root):
    briefing["story_of_day"]["sources"] = []
    assert any(e.startswith("story_of_day.sources") for e in validate(briefing, root))


def test_non_http_source_rejected(briefing, root):
    briefing["cards"][1]["sources"][0]["url"] = "javascript:alert(1)"
    assert any(e.startswith("cards[1].sources[0].url") for e in validate(briefing, root))


def test_heat_out_of_range_rejected(briefing, root):
    briefing["heat"]["middle-east"] = 11
    assert any(e.startswith("heat.middle-east") for e in validate(briefing, root))


def test_missing_inbox_rejected(briefing, root):
    briefing["run_id"] = "2026-11-05-0000"
    assert any(e.startswith("run_id") for e in validate(briefing, root))


def test_last_time_must_exist(briefing, root):
    briefing["cards"][0]["last_time"] = {"run_id": "2026-10-01-1000", "text": "We flagged it."}
    assert any(e.startswith("cards[0].last_time.run_id") for e in validate(briefing, root))


def test_bad_confidence_rejected(briefing, root):
    briefing["story_of_day"]["my_take"]["confidence"] = "certain"
    assert any(e.startswith("story_of_day.my_take.confidence") for e in validate(briefing, root))


def test_unknown_take_review_rejected(briefing, root):
    briefing["takes_review"] = [{"take_id": "2026-10-01-1000-1", "verdict": "right", "text": "x"}]
    assert any(e.startswith("takes_review[0].take_id") for e in validate(briefing, root))


def test_invalid_changes_nothing(briefing, root, capsys):
    briefing["cards"] = []
    path = root / "bad.json"
    write(path, briefing)
    before = snapshot(root)
    assert validate_briefing.main([str(path), "--root", str(root)]) == 1
    assert snapshot(root) == before
    assert "cards" in capsys.readouterr().out


def test_not_json_reports_error(root, capsys):
    path = root / "broken.json"
    path.write_text("{ not json", encoding="utf-8")
    assert validate_briefing.main([str(path), "--root", str(root)]) == 1
    assert "not valid JSON" in capsys.readouterr().out


def test_merge_assigns_take_ids_and_prices(briefing, root):
    out = merge(briefing, root)
    saved = load_json(out)
    take = saved["story_of_day"]["my_take"]
    assert take["id"] == "2026-11-04-1000-1"
    assert take["prices_at"]["brent"]["value"] == 106.68
    stories = load_storylines(root)
    assert stories["middle-east"]["heat"] == {"2026-11-04-1000": 8}
    assert stories["middle-east"]["runs"] == ["2026-11-04-1000"]


def test_heat_only_storyline_gets_heat_but_no_run(briefing, root):
    briefing["heat"]["taiwan"] = 1
    merge(briefing, root)
    stories = load_storylines(root)
    assert stories["taiwan"]["heat"] == {"2026-11-04-1000": 1}
    assert stories["taiwan"]["runs"] == []


def test_merge_refuses_existing_run(briefing, root):
    merge(briefing, root)
    with pytest.raises(FileExistsError):
        merge(briefing, root)


def test_cli_success(briefing, root, capsys):
    path = root / "ok.json"
    write(path, briefing)
    assert validate_briefing.main([str(path), "--root", str(root)]) == 0
    assert "ok 2026-11-04-1000" in capsys.readouterr().out
    assert (root / "data" / "briefings" / "2026-11-04-1000.json").exists()


def test_review_of_earlier_take_accepted(briefing, root):
    merge(briefing, root)
    later = json.loads(json.dumps(briefing))
    later["run_id"] = "2026-11-05-0000"
    write(root / "data" / "inbox" / "2026-11-05-0000.json", {"run_id": "2026-11-05-0000", "items": []})
    later["story_of_day"]["image"] = None
    later["story_of_day"]["last_time"] = {"run_id": "2026-11-04-1000", "text": "We flagged the tankers."}
    later["takes_review"] = [{"take_id": "2026-11-04-1000-1", "verdict": "open", "text": "Too early to tell."}]
    assert validate(later, root) == []


def test_short_kind_allows_no_story_of_day(briefing, root):
    briefing["kind"] = "short"
    briefing["story_of_day"] = None
    briefing["cards"] = briefing["cards"][:1]
    briefing["heat"] = {"us-china": 5}
    assert validate(briefing, root) == []
