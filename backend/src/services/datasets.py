from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.services import persist


def _datasets_dir() -> Path:
    here = Path(__file__).resolve()
    for candidate in (
        here.parents[2] / "datasets",
        here.parents[3] / "backend" / "datasets",
        Path("/app/datasets"),
        Path.cwd() / "datasets",
    ):
        if candidate.exists():
            return candidate
    p = here.parents[2] / "datasets"
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_datasets() -> list[dict[str, Any]]:
    out = []
    for path in sorted(_datasets_dir().glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        out.append(
            {
                "dataset_id": data.get("dataset_id") or path.stem,
                "name": data.get("name") or path.stem,
                "version": data.get("version"),
                "description": data.get("description"),
                "n_items": len(data.get("items") or []),
                "path": path.name,
            }
        )
    # custom datasets registered via API
    for d in persist.load("datasets"):
        if not any(x["dataset_id"] == d.get("dataset_id") for x in out):
            out.append(
                {
                    "dataset_id": d.get("dataset_id"),
                    "name": d.get("name"),
                    "version": d.get("version"),
                    "description": d.get("description"),
                    "n_items": len(d.get("items") or []),
                    "path": "persisted",
                }
            )
    return out


def get_dataset(dataset_id: str) -> dict[str, Any] | None:
    for path in _datasets_dir().glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("dataset_id") == dataset_id or path.stem == dataset_id:
            return data
    for d in persist.load("datasets"):
        if d.get("dataset_id") == dataset_id:
            return d
    return None


def save_dataset(
    *,
    name: str,
    items: list[dict[str, Any]],
    dataset_id: str | None = None,
    description: str = "",
    version: str = "1.0.0",
) -> dict[str, Any]:
    did = dataset_id or f"ds-{uuid4().hex[:10]}"
    data = {
        "dataset_id": did,
        "name": name,
        "version": version,
        "description": description,
        "items": items,
    }
    # persist registry + write file for DS visibility
    persist.append("datasets", data)
    path = _datasets_dir() / f"{did}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "dataset_id": did,
        "name": name,
        "version": version,
        "n_items": len(items),
        "path": path.name,
    }
