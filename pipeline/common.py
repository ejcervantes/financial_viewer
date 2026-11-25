"""Shared paths and config loaders."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
DATA = ROOT / "data"
RAW = DATA / "raw"
OUT = ROOT / "web" / "public" / "data"

MARKETS = ("us", "eu", "cn")
HORIZONS = {"1w": 5, "1m": 21, "3m": 63}


def load_yaml(name: str) -> Any:
    with open(CONFIG / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_sectors() -> dict:
    return load_yaml("sectors.yaml")


def load_events() -> list[dict]:
    return load_yaml("events.yaml")


def load_episodes() -> list[dict]:
    return load_yaml("episodes.yaml")


def market_spec(cfg: dict, sector: dict, market: str) -> dict:
    """Merge market defaults (benchmark, timezone, hours) with per-sector overrides."""
    spec = dict(cfg["markets"][market])
    spec.update(sector["markets"][market])
    spec.setdefault("min_constituents", 1)
    return spec


def all_tickers(cfg: dict) -> list[str]:
    tickers: set[str] = set()
    for m in cfg["markets"].values():
        tickers.add(m["benchmark"])
    for s in cfg["sectors"]:
        for spec in s["markets"].values():
            tickers.update(spec["tickers"])
            if "benchmark" in spec:
                tickers.add(spec["benchmark"])
    return sorted(tickers)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), default=_default)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _default(o: Any) -> Any:
    if isinstance(o, (dt.date, dt.datetime)):
        return o.isoformat()
    raise TypeError(f"Not serializable: {type(o)}")
