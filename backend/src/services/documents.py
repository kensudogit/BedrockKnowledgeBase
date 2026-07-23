"""ローカルドキュメントのアップロード・一覧・削除。"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.services.rag import invalidate_local_index, uploads_dir

_DOCS: dict[str, dict[str, Any]] = {}


def _safe_name(name: str) -> str:
    base = Path(name).name
    base = re.sub(r"[^\w.\u3040-\u30ff\u3400-\u9fff-]+", "_", base)
    return base[:180] or f"doc-{uuid4().hex[:8]}.txt"


def list_documents() -> list[dict[str, Any]]:
    """メモリ上およびディスク上のドキュメント一覧を返す。"""
    root = uploads_dir()
    items = list(_DOCS.values())
    # 再起動後など、メモリ未登録のディスクファイルも含める
    known = {d.get("filename") for d in items}
    for path in sorted(root.glob("*")):
        if path.is_file() and path.name not in known and path.suffix.lower() in {".md", ".txt", ".text"}:
            items.append(
                {
                    "document_id": path.stem,
                    "filename": path.name,
                    "bytes": path.stat().st_size,
                    "status": "indexed",
                    "created_at": datetime.fromtimestamp(
                        path.stat().st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            )
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


def ingest_text(
    *,
    filename: str,
    content: str,
    content_type: str = "text/plain",
) -> dict[str, Any]:
    """テキスト内容をファイルとして保存し、ローカル索引を更新する。"""
    root = uploads_dir()
    safe = _safe_name(filename if "." in filename else f"{filename}.md")
    doc_id = uuid4().hex[:12]
    dest = root / f"{doc_id}_{safe}"
    text = content.strip()
    dest.write_text(text, encoding="utf-8")
    meta = {
        "document_id": doc_id,
        "filename": dest.name,
        "original_name": filename,
        "bytes": len(text.encode("utf-8")),
        "content_type": content_type,
        "status": "indexed",
        "path": str(dest),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _DOCS[doc_id] = meta
    invalidate_local_index()
    return meta


def delete_document(document_id: str) -> bool:
    """指定 ID のドキュメントを削除する。成功時 True。"""
    meta = _DOCS.pop(document_id, None)
    root = uploads_dir()
    removed = False
    if meta and meta.get("path"):
        p = Path(meta["path"])
        if p.exists():
            p.unlink()
            removed = True
    for path in root.glob(f"{document_id}_*"):
        path.unlink(missing_ok=True)
        removed = True
    if removed:
        invalidate_local_index()
    return removed
