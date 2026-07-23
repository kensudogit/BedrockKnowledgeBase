"""チャットセッションのインメモリ管理（メッセージ履歴・RAG 用 history）。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

_SESSIONS: dict[str, dict[str, Any]] = {}


def create_session(use_case: str = "document_search", title: str | None = None) -> dict[str, Any]:
    """新規チャットセッションを作成する。"""
    sid = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    sess = {
        "session_id": sid,
        "title": title or "新規セッション",
        "use_case": use_case,
        "messages": [],
        "created_at": now,
        "updated_at": now,
    }
    _SESSIONS[sid] = sess
    return {
        "session_id": sid,
        "title": sess["title"],
        "use_case": use_case,
        "created_at": now,
    }


def get_session(session_id: str) -> dict[str, Any] | None:
    """session_id のセッション全体を返す。"""
    return _SESSIONS.get(session_id)


def list_sessions(limit: int = 30) -> list[dict[str, Any]]:
    """更新日時降順でセッション概要一覧を返す。"""
    items = sorted(_SESSIONS.values(), key=lambda s: s.get("updated_at", ""), reverse=True)
    return [
        {
            "session_id": s["session_id"],
            "title": s["title"],
            "use_case": s["use_case"],
            "updated_at": s["updated_at"],
            "message_count": len(s.get("messages") or []),
        }
        for s in items[:limit]
    ]


def append_message(
    session_id: str,
    *,
    role: str,
    content: str,
    citations: list[dict[str, Any]] | None = None,
    meta: dict[str, Any] | None = None,
    use_case: str = "document_search",
) -> dict[str, Any]:
    """セッションにメッセージを追加する（存在しなければ自動作成）。"""
    sess = _SESSIONS.get(session_id)
    if not sess:
        now = datetime.now(timezone.utc).isoformat()
        sess = {
            "session_id": session_id,
            "title": "新規セッション",
            "use_case": use_case,
            "messages": [],
            "created_at": now,
            "updated_at": now,
        }
        _SESSIONS[session_id] = sess

    msg = {
        "role": role,
        "content": content,
        "citations": citations or [],
        "meta": meta or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    sess["messages"].append(msg)
    if role == "user" and sess.get("title") in (None, "", "新規セッション"):
        sess["title"] = (content or "")[:48] or "新規セッション"
    sess["use_case"] = use_case or sess.get("use_case")
    sess["updated_at"] = msg["created_at"]
    return msg


def history_for_rag(session_id: str | None, limit: int = 8) -> list[dict[str, str]]:
    """RAG 用に直近 limit 件の user/assistant 履歴を返す。"""
    if not session_id:
        return []
    sess = _SESSIONS.get(session_id)
    if not sess:
        return []
    out = []
    for m in sess.get("messages") or []:
        if m.get("role") in ("user", "assistant"):
            out.append({"role": m["role"], "content": m.get("content", "")})
    return out[-limit:]
