"""Shared storage helpers: JSON files, storylines, heat history, trends."""
import json
import os
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BARS = "▁▂▃▄▅▆▇█"
TRENDS = ("new", "heating", "rising", "steady", "cooling", "quiet")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _run_date(run_id: str) -> date:
    return datetime.strptime(run_id, "%Y-%m-%d-%H%M").date()


def load_storylines(root=ROOT) -> dict:
    root = Path(root)
    path = root / "data" / "storylines.json"
    if path.exists():
        return load_json(path)
    seed = load_json(root / "config" / "seed_storylines.json")
    return {s["slug"]: {"name": s["name"], "created": "seed", "heat": {}, "runs": []} for s in seed}


def save_storylines(stories: dict, root=ROOT) -> None:
    save_json(Path(root) / "data" / "storylines.json", stories)


def daily_heat(story: dict, today: date, days: int = 14) -> list:
    by_day: dict[date, int] = {}
    for run_id, value in story["heat"].items():
        day = _run_date(run_id)
        by_day[day] = max(value, by_day.get(day, value))
    return [by_day.get(today - timedelta(days=n)) for n in range(days - 1, -1, -1)]


def trend(story: dict, latest_run_id: str) -> str:
    today = _run_date(latest_run_id)
    if story["created"] != "seed" and (today - _run_date(story["created"])).days < 2:
        return "new"
    window = daily_heat(story, today)
    recent = [v for v in window[-3:] if v is not None]
    if not recent or recent[-1] <= 2:
        return "quiet"
    values = [v for v in window if v is not None]
    last3, prev4 = values[-3:], values[-7:-3]
    if len(values) < 2 or not prev4:
        return "steady"
    diff = sum(last3) / len(last3) - sum(prev4) / len(prev4)
    if diff >= 1.5:
        return "heating" if values[-1] >= 7 else "rising"
    if diff <= -1.5:
        return "cooling"
    return "steady"


def sparkline(values: list) -> str:
    return "".join("·" if v is None else BARS[round(max(0, min(10, v)) / 10 * 7)] for v in values)
