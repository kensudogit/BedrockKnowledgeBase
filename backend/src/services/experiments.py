"""Experiment tracking for text / image / tabular / RAG analysis."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.services import persist


def log_experiment(
    *,
    name: str,
    modality: str,
    params: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
    project_id: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    item = {
        "experiment_id": str(uuid4()),
        "name": name,
        "modality": modality,  # text | image | tabular | rag | multimodal
        "params": params or {},
        "metrics": metrics or {},
        "artifacts": artifacts or {},
        "project_id": project_id,
        "notes": notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    persist.append("experiments", item)
    return item


def list_experiments(limit: int = 50, modality: str | None = None) -> list[dict[str, Any]]:
    items = persist.load("experiments")
    if modality:
        items = [i for i in items if i.get("modality") == modality]
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items[:limit]


def get_experiment(experiment_id: str) -> dict[str, Any] | None:
    for i in persist.load("experiments"):
        if i.get("experiment_id") == experiment_id:
            return i
    return None
