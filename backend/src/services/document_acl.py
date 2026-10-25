"""文書 ACL — 取り込み時に正規化し、RAG 検索側で強制する。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.services.auth_principal import AuthPrincipal

SHARED_TENANT = "shared"
DEFAULT_UPLOAD_ROLES = ("viewer", "editor", "admin", "*")


def default_shared_acl() -> dict[str, Any]:
    return {
        "tenant_id": SHARED_TENANT,
        "visibility": "tenant",
        "allowed_roles": ["*"],
        "allowed_subjects": [],
    }


def default_upload_acl(*, tenant_id: str, subject: str) -> dict[str, Any]:
    return {
        "tenant_id": tenant_id,
        "visibility": "tenant",
        "allowed_roles": list(DEFAULT_UPLOAD_ROLES),
        "allowed_subjects": [subject] if subject else [],
    }


def acl_sidecar_path(document_path: Path) -> Path:
    return document_path.with_suffix(document_path.suffix + ".acl.json")


def write_acl(document_path: Path, acl: dict[str, Any]) -> None:
    sidecar = acl_sidecar_path(document_path)
    sidecar.write_text(json.dumps(acl, ensure_ascii=False, indent=2), encoding="utf-8")


def read_acl(document_path: Path, *, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    sidecar = acl_sidecar_path(document_path)
    if sidecar.exists():
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return _normalize_acl(data)
        except Exception:
            pass
    if fallback:
        return _normalize_acl(fallback)
    # samples/ 等: 認証済みテナント共通
    return default_shared_acl()


def _normalize_acl(raw: dict[str, Any]) -> dict[str, Any]:
    tenant = str(raw.get("tenant_id") or SHARED_TENANT).strip() or SHARED_TENANT
    roles = raw.get("allowed_roles") or ["*"]
    if isinstance(roles, str):
        roles = [r.strip() for r in roles.split(",") if r.strip()]
    subs = raw.get("allowed_subjects") or []
    if isinstance(subs, str):
        subs = [subs.strip()] if subs.strip() else []
    return {
        "tenant_id": tenant,
        "visibility": raw.get("visibility") or "tenant",
        "allowed_roles": roles,
        "allowed_subjects": list(subs),
    }


def principal_can_read(principal: AuthPrincipal, acl: dict[str, Any]) -> bool:
    """テナント境界とロールで読み取り可否を判定する。"""
    acl = _normalize_acl(acl)
    doc_tenant = acl["tenant_id"]
    if doc_tenant != SHARED_TENANT and doc_tenant != principal.tenant_id:
        return False
    if acl.get("visibility") == "private":
        allowed_subs = {str(s) for s in acl.get("allowed_subjects") or []}
        if principal.subject not in allowed_subs and not principal.has_role("admin"):
            return False
    allowed_roles = acl.get("allowed_roles") or ["*"]
    if "*" in allowed_roles:
        return True
    if principal.has_role("admin"):
        return True
    return bool(principal.roles.intersection(set(str(r) for r in allowed_roles)))


def bedrock_metadata_filter(principal: AuthPrincipal) -> dict[str, Any] | None:
    """Bedrock KB の vectorSearch filter（tenant_id 一致 or shared）。"""
    return {
        "orAll": [
            {"equals": {"key": "tenant_id", "value": principal.tenant_id}},
            {"equals": {"key": "tenant_id", "value": SHARED_TENANT}},
        ]
    }
