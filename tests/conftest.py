import copy
import json
import shutil
from pathlib import Path

import pytest

from tools.store import ROOT

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture
def briefing():
    return copy.deepcopy(json.loads((FIX / "briefing_ok.json").read_text(encoding="utf-8")))


@pytest.fixture
def root(tmp_path):
    """A minimal repo root: seed storylines, one inbox, one price snapshot."""
    (tmp_path / "config").mkdir()
    shutil.copy(ROOT / "config" / "seed_storylines.json", tmp_path / "config")
    write(tmp_path / "data" / "inbox" / "2026-11-04-1000.json", {
        "run_id": "2026-11-04-1000",
        "items": [{"link": "https://www.bbc.co.uk/news/world-1", "image_url": "https://img.example/hormuz.jpg"}],
    })
    write(tmp_path / "data" / "prices" / "2026-11-04-1000.json", {
        "run_id": "2026-11-04-1000",
        "prices": {"brent": {"label": "Brent", "value": 106.68, "as_of": "2026-11-03T22:00:00+00:00"}},
    })
    return tmp_path


def write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
