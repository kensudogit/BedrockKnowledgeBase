from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.services import persist

_DEFAULT_SEEDED = False


def _hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def seed_default_project() -> dict[str, Any]:
    global _DEFAULT_SEEDED
    items = persist.load("projects")
    if items:
        _DEFAULT_SEEDED = True
        return items[0]
    proj = {
        "project_id": str(uuid4()),
        "name": "default",
        "client_name": "internal",
        "env": "development",
        "api_key": "bkb-dev-key",
        "api_key_hash": _hash_key("bkb-dev-key"),
        "notes": "ローカル/デモ用デフォルトプロジェクト",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    persist.append("projects", proj)
    _DEFAULT_SEEDED = True
    return proj


def list_projects() -> list[dict[str, Any]]:
    items = persist.load("projects")
    if not items:
        return [seed_default_project()]
    # never return raw hash only — mask api_key for list
    out = []
    for p in items:
        out.append(
            {
                "project_id": p["project_id"],
                "name": p.get("name"),
                "client_name": p.get("client_name"),
                "env": p.get("env"),
                "has_api_key": bool(p.get("api_key_hash")),
                "notes": p.get("notes"),
                "created_at": p.get("created_at"),
            }
        )
    return out


def create_project(
    *,
    name: str,
    client_name: str = "",
    env: str = "development",
    api_key: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    key = api_key or f"bkb-{uuid4().hex[:16]}"
    proj = {
        "project_id": str(uuid4()),
        "name": name,
        "client_name": client_name,
        "env": env,
        "api_key": key,
        "api_key_hash": _hash_key(key),
        "notes": notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    persist.append("projects", proj)
    return {
        "project_id": proj["project_id"],
        "name": name,
        "client_name": client_name,
        "env": env,
        "api_key": key,
        "notes": notes,
        "created_at": proj["created_at"],
    }


def resolve_project(api_key: str | None = None, project_id: str | None = None) -> dict[str, Any] | None:
    items = persist.load("projects")
    if not items:
        items = [seed_default_project()]
    if project_id:
        for p in items:
            if p.get("project_id") == project_id:
                return p
    if api_key:
        h = _hash_key(api_key)
        for p in items:
            if p.get("api_key_hash") == h or p.get("api_key") == api_key:
                return p
    return items[0] if items else None
