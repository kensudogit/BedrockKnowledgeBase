"""GCP credential / status helpers (REST-friendly, no heavy SDK required)."""
from __future__ import annotations

from typing import Any

from src.config import get_settings


def gcp_status() -> dict[str, Any]:
    s = get_settings()
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
        "provider_hint": "vertex" if s.gcp_configured else None,
    }


def resolve_access_token() -> str | None:
    """Return Bearer token for Vertex/GCS REST, or None for mock path."""
    s = get_settings()
    token = s.gcp_access_token.strip()
    if token:
        return token
    # Optional: load from ADC JSON via google-auth if installed
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
