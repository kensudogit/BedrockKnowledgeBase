"""ローカルドキュメントのアップロード・一覧・削除。"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.services.auth_principal import AuthPrincipal
from src.services.document_acl import (
    default_upload_acl,
    principal_can_read,
    write_acl,
)
from src.services import rag as rag_module

_DOCS: dict[str, dict[str, Any]] = {}


def _safe_name(name: str) -> str:
    base = Path(name).name
    base = re.sub(r"[^\w.\u3040-\u30ff\u3400-\u9fff-]+", "_", base)
    return base[:180] or f"doc-{uuid4().hex[:8]}.txt"


def list_documents(*, principal: AuthPrincipal | None = None) -> list[dict[str, Any]]:
    """メモリ上およびディスク上のドキュメント一覧を返す（ACL でフィルタ）。"""
    root = rag_module.uploads_dir()
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
    if principal is None:
        return items
    filtered: list[dict[str, Any]] = []
    for doc in items:
        acl = doc.get("acl") or default_upload_acl(
            tenant_id=str(doc.get("tenant_id") or "default"),
            subject=str(doc.get("owner_subject") or ""),
        )
        if principal_can_read(principal, acl):
            filtered.append(doc)
    return filtered


def ingest_text(
    *,
    filename: str,
    content: str,
    content_type: str = "text/plain",
    principal: AuthPrincipal | None = None,
) -> dict[str, Any]:
    """テキスト内容をファイルとして保存し、ローカル索引を更新する。"""
    root = rag_module.uploads_dir()
    safe = _safe_name(filename if "." in filename else f"{filename}.md")
    doc_id = uuid4().hex[:12]
    dest = root / f"{doc_id}_{safe}"
    text = content.strip()
    dest.write_text(text, encoding="utf-8")
    tenant_id = principal.tenant_id if principal else "default"
    subject = principal.subject if principal else "anonymous"
    acl = default_upload_acl(tenant_id=tenant_id, subject=subject)
    write_acl(dest, acl)
    meta = {
        "document_id": doc_id,
        "filename": dest.name,
        "original_name": filename,
        "bytes": len(text.encode("utf-8")),
        "content_type": content_type,
        "status": "indexed",
        "path": str(dest),
        "tenant_id": tenant_id,
        "owner_subject": subject,
        "acl": acl,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _DOCS[doc_id] = meta
    rag_module.invalidate_local_index()
    return meta


def delete_document(document_id: str) -> bool:
    """指定 ID のドキュメントを削除する。成功時 True。"""
    meta = _DOCS.pop(document_id, None)
    root = rag_module.uploads_dir()
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
        rag_module.invalidate_local_index()
    return removed
