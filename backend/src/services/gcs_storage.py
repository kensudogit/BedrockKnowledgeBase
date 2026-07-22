"""GCS document upload (REST) with local mock fallback."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from src.config import get_settings
from src.gcp_clients import resolve_access_token
from src.services import persist


def upload_document(
    *,
    filename: str,
    content: str | bytes,
    content_type: str = "text/plain",
    project_id: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    object_name = f"documents/{datetime.now(timezone.utc).strftime('%Y%m%d')}/{uuid4().hex[:12]}_{filename}"
    raw = content.encode("utf-8") if isinstance(content, str) else content
    bucket = settings.gcs_documents_bucket.strip()
    token = resolve_access_token()

    if settings.use_vertex_mock or not bucket or not token or not settings.gcp_configured:
        root = Path(__file__).resolve().parents[2] / "data" / "gcs_mock"
        root.mkdir(parents=True, exist_ok=True)
        dest = root / object_name.replace("/", "_")
        dest.write_bytes(raw)
        item = {
            "object_id": str(uuid4()),
            "filename": filename,
            "object_name": object_name,
            "bucket": bucket or "mock-gcs",
            "bytes": len(raw),
            "content_type": content_type,
            "gcs_uri": f"gs://{bucket or 'mock-gcs'}/{object_name}",
            "local_path": str(dest),
            "mock": True,
            "provider": "gcs",
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        persist.append("gcs_uploads", item)
        return item

    url = f"https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o"
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            url,
            params={"uploadType": "media", "name": object_name},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": content_type,
            },
            content=raw,
        )
        resp.raise_for_status()
        payload = resp.json()

    item = {
        "object_id": str(uuid4()),
        "filename": filename,
        "object_name": object_name,
        "bucket": bucket,
        "bytes": len(raw),
        "content_type": content_type,
        "gcs_uri": f"gs://{bucket}/{object_name}",
        "mock": False,
        "provider": "gcs",
        "project_id": project_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "raw": {
            "name": payload.get("name"),
            "md5Hash": payload.get("md5Hash"),
            "size": payload.get("size"),
        },
    }
    persist.append("gcs_uploads", item)
    return item


def list_uploads(limit: int = 50) -> list[dict[str, Any]]:
    items = persist.load("gcs_uploads")
    return items[-limit:]


def encode_preview(content: str, max_chars: int = 200) -> str:
    raw = content[:max_chars].encode("utf-8")
    return base64.b64encode(raw).decode("ascii")
