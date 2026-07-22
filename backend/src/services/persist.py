"""Durable JSON persistence under data/ops (works without Postgres)."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()


def _root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (
        here.parents[3] / "data" / "ops",
        here.parents[2] / "data" / "ops",
        Path("/app/data/ops"),
        Path.cwd() / "data" / "ops",
    ):
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    p = here.parents[3] / "data" / "ops"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _path(collection: str) -> Path:
    return _root() / f"{collection}.jsonl"


def append(collection: str, item: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        with _path(collection).open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return item


def load(collection: str, limit: int | None = None) -> list[dict[str, Any]]:
    p = _path(collection)
    if not p.exists():
        return []
    items: list[dict[str, Any]] = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if limit is not None:
        return items[-limit:]
    return items


def rewrite(collection: str, items: list[dict[str, Any]]) -> None:
    with _LOCK:
        with _path(collection).open("w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
