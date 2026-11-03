"""Snapshot free market prices into data/prices/<run_id>.json.

Usage:
    python tools/fetch_prices.py [--run-id ID]

Symbols and source live in config/price_symbols.json. A symbol that fails
gets value null; the snapshot is still written.
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.slot import run_id_for  # noqa: E402
from tools.store import load_json, save_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1d"
HEADERS = {"User-Agent": "Mozilla/5.0 geopol-briefing/1.0"}


def _quote(symbol: str, get) -> tuple[float, str]:
    resp = get(CHART_URL.format(symbol=symbol), headers=HEADERS, timeout=15)
    resp.raise_for_status()
    meta = resp.json()["chart"]["result"][0]["meta"]
    as_of = datetime.fromtimestamp(meta["regularMarketTime"], tz=timezone.utc).isoformat()
    return float(meta["regularMarketPrice"]), as_of


def fetch_prices(symbols: list[dict], get=requests.get) -> dict:
    prices = {}
    for s in symbols:
        try:
            value, as_of = _quote(s["symbol"], get)
        except Exception as exc:
            print(f"warning: {s['key']}: {exc}", file=sys.stderr)
            value, as_of = None, None
        prices[s["key"]] = {"label": s["label"], "value": value, "as_of": as_of}
    return prices


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id")
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args(argv)
    root = Path(args.root)
    run_id = args.run_id or run_id_for(datetime.now(timezone.utc))
    out = root / "data" / "prices" / f"{run_id}.json"
    if out.exists():
        print(f"already fetched prices for {run_id}")
        return 0
    symbols = load_json(root / "config" / "price_symbols.json")["symbols"]
    prices = fetch_prices(symbols)
    save_json(out, {"run_id": run_id, "fetched_at": datetime.now(timezone.utc).isoformat(), "prices": prices})
    ok = sum(1 for p in prices.values() if p["value"] is not None)
    print(f"wrote {ok}/{len(prices)} prices to {out.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
