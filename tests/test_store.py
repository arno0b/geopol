from tools.store import load_json, save_json


def test_atomic_save_roundtrip_bangla(tmp_path):
    path = tmp_path / "nested" / "x.json"
    save_json(path, {"name": "বাংলাদেশ"})
    assert load_json(path) == {"name": "বাংলাদেশ"}
    assert "বাংলাদেশ" in path.read_text(encoding="utf-8")
    assert list(path.parent.iterdir()) == [path]
