"""テキスト/画像/表形式/RAG 分析の実験トラッキング。"""
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
    """分析実行のパラメータ・メトリクス・アーティファクトを永続化する。"""
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
    """実験履歴を新しい順に返す。modality でフィルタ可能。"""
    items = persist.load("experiments")
    if modality:
        items = [i for i in items if i.get("modality") == modality]
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items[:limit]


def get_experiment(experiment_id: str) -> dict[str, Any] | None:
    """指定 ID の実験レコードを取得する。"""
    for i in persist.load("experiments"):
        if i.get("experiment_id") == experiment_id:
            return i
    return None
