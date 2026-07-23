"""ユーザー回答フィードバック（👍/👎）の記録と集計。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.services import persist


def add_feedback(
    *,
    rating: int,
    session_id: str | None = None,
    message_index: int | None = None,
    comment: str = "",
    use_case: str | None = None,
    model_id: str | None = None,
    answer_preview: str = "",
    project_id: str | None = None,
) -> dict[str, Any]:
    """評価（-1 または 1）と任意コメントを永続化する。"""
    if rating not in (-1, 1):
        raise ValueError("rating must be -1 or 1")
    item = {
        "feedback_id": str(uuid4()),
        "project_id": project_id,
        "session_id": session_id,
        "message_index": message_index,
        "rating": rating,
        "comment": comment,
        "use_case": use_case,
        "model_id": model_id,
        "answer_preview": (answer_preview or "")[:400],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    persist.append("feedback", item)
    return item


def list_feedback(limit: int = 100) -> list[dict[str, Any]]:
    """フィードバック履歴を新しい順に返す。"""
    items = persist.load("feedback")
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items[:limit]


def feedback_summary() -> dict[str, Any]:
    """件数・賛否数・承認率のサマリを返す。"""
    items = persist.load("feedback")
    up = sum(1 for i in items if i.get("rating") == 1)
    down = sum(1 for i in items if i.get("rating") == -1)
    n = len(items)
    return {
        "n": n,
        "up": up,
        "down": down,
        "approval_rate": round(up / n, 3) if n else None,
    }
