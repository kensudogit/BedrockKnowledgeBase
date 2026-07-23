"""GCP 認証情報ヘルパー（REST 向け、重い SDK 不要）。"""
from __future__ import annotations

from typing import Any

from src.config import get_settings


def gcp_status() -> dict[str, Any]:
    """Vertex / GCS の設定状態と利用可能モードを返す。"""
    s = get_settings()
    mock_ok = bool(s.use_vertex_mock)
    live_ok = bool(
        s.gcp_configured
        and (s.gcp_access_token.strip() or s.google_application_credentials.strip())
        and not s.use_vertex_mock
    )
    return {
        "configured": s.gcp_configured,
        "project_id": s.gcp_project_id or None,
        "region": s.gcp_region,
        "vertex_model": s.vertex_text_model_id,
        "gcs_bucket": s.gcs_documents_bucket or None,
        "access_token_set": bool(s.gcp_access_token.strip()),
        "credentials_file_set": bool(s.google_application_credentials.strip()),
        "use_vertex_mock": s.use_vertex_mock,
        "prefer_vertex": s.prefer_vertex,
        "vertex_ready": s.vertex_ready,
        "mock_available": mock_ok,
        "live_available": live_ok,
        "mode": "live" if live_ok else "mock" if mock_ok else "unavailable",
        "hint": (
            "USE_VERTEX_MOCK=true — 未設定でも /gcp でモック生成・GCS ローカル保存可"
            if mock_ok and not s.gcp_configured
            else "本番 Vertex — USE_VERTEX_MOCK=false + GCP_PROJECT_ID + GCP_ACCESS_TOKEN"
            if live_ok
            else "GCP_PROJECT_ID とトークンを設定するか USE_VERTEX_MOCK=true にしてください"
        ),
        "provider_hint": "vertex" if s.gcp_configured or mock_ok else None,
    }


def resolve_access_token() -> str | None:
    """Vertex/GCS REST 用 Bearer トークンを返す。モックパスでは None。"""
    s = get_settings()
    token = s.gcp_access_token.strip()
    if token:
        return token
    # 任意: google-auth があれば ADC JSON から取得
    cred_path = s.google_application_credentials.strip()
    if not cred_path:
        return None
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            cred_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        creds.refresh(Request())
        return creds.token
    except Exception:
        return None
