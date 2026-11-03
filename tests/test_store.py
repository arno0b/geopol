from tools.store import load_json, save_json


def test_atomic_save_roundtrip_bangla(tmp_path):
    path = tmp_path / "nested" / "x.json"
    save_json(path, {"name": "বাংলাদেশ"})
    assert load_json(path) == {"name": "বাংলাদেশ"}
    assert "বাংলাদেশ" in path.read_text(encoding="utf-8")
    assert list(path.parent.iterdir()) == [path]


from datetime import date

from tools.store import daily_heat, load_storylines, sparkline, trend


def story(values, created="seed", start=date(2026, 11, 1)):
    """One 10:00 heat value per day starting at `start`."""
    from datetime import timedelta
    heat = {}
    for n, v in enumerate(values):
        if v is not None:
            heat[(start + timedelta(days=n)).strftime("%Y-%m-%d") + "-1000"] = v
    return {"name": "x", "created": created, "heat": heat, "runs": list(heat)}


def test_seed_init(tmp_path):
    (tmp_path / "config").mkdir()
    import shutil
    from tools.store import ROOT
    shutil.copy(ROOT / "config" / "seed_storylines.json", tmp_path / "config")
    stories = load_storylines(tmp_path)
    assert len(stories) == 14
    assert stories["bangladesh-politics"] == {"name": "Bangladesh politics", "created": "seed", "heat": {}, "runs": []}


def test_daily_heat_takes_max_per_day():
    s = {"name": "x", "created": "seed", "runs": [],
         "heat": {"2026-11-04-1000": 4, "2026-11-05-0000": 7, "2026-11-05-1000": 5}}
    values = daily_heat(s, date(2026, 11, 5), days=3)
    assert values == [None, 4, 7]


def test_sparkline_pads():
    line = sparkline([None] * 12 + [3, 10])
    assert len(line) == 14
    assert line.startswith("·") and line.endswith("█")


def test_sparkline_zero_and_ten():
    assert sparkline([0, 10]) == "▁█"


def test_trend_heating():
    assert trend(story([2, 2, 3, 3, 7, 8, 9]), "2026-11-07-1000") == "heating"


def test_trend_rising():
    assert trend(story([2, 2, 2, 2, 4, 5, 5]), "2026-11-07-1000") == "rising"


def test_trend_cooling():
    assert trend(story([8, 8, 7, 7, 3, 4, 3]), "2026-11-07-1000") == "cooling"


def test_trend_steady():
    assert trend(story([5, 5, 6, 5, 5, 6, 5]), "2026-11-07-1000") == "steady"


def test_trend_quiet_low_heat():
    assert trend(story([5, 4, 3, 2, 1, 1, 1]), "2026-11-07-1000") == "quiet"


def test_trend_quiet_no_recent_heat():
    assert trend(story([6, 6, 6, 6, None, None, None]), "2026-11-07-1000") == "quiet"


def test_trend_new_with_one_point():
    s = story([None] * 6 + [6], created="2026-11-07-1000")
    assert trend(s, "2026-11-07-1000") == "new"


def test_trend_not_new_after_two_days():
    s = story([None] * 4 + [6, 6, 6], created="2026-11-05-1000")
    assert trend(s, "2026-11-07-1000") == "steady"


def test_trend_single_seed_point_is_steady():
    assert trend(story([None] * 6 + [6]), "2026-11-07-1000") == "steady"
