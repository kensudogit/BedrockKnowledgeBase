"""Vertex AI text generation via REST (Gemini), with mock fallback."""
from __future__ import annotations

from typing import Any

import httpx

from src.config import get_settings
from src.gcp_clients import resolve_access_token
from src.services.mock_ai import mock_text


def generate_text_vertex(
    prompt: str,
    *,
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.gcp_configured:
        raise RuntimeError("GCP_PROJECT_ID is not set")

    if settings.use_vertex_mock or not resolve_access_token():
        out = mock_text(prompt, system=system)
        out["provider"] = "vertex"
        out["model"] = settings.vertex_text_model_id
        out["mock"] = True
        out["gcp_project"] = settings.gcp_project_id
        out["gcp_region"] = settings.gcp_region
        return out

    token = resolve_access_token()
    assert token
    region = settings.gcp_region
    project = settings.gcp_project_id
    model = settings.vertex_text_model_id
    url = (
        f"https://{region}-aiplatform.googleapis.com/v1/"
        f"projects/{project}/locations/{region}/publishers/google/models/{model}:generateContent"
    )

    parts: list[dict[str, str]] = []
    if system:
        parts.append({"text": f"[system]\n{system}\n\n[user]\n{prompt}"})
    else:
        parts.append({"text": prompt})

    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }

    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        payload = resp.json()

    text = ""
    for cand in payload.get("candidates") or []:
        content = cand.get("content") or {}
        for part in content.get("parts") or []:
            if "text" in part:
                text += part["text"]

    usage = payload.get("usageMetadata") or {}
    return {
        "text": text,
        "model": model,
        "mock": False,
        "provider": "vertex",
        "gcp_project": project,
        "gcp_region": region,
        "usage": {
            "input_tokens": usage.get("promptTokenCount"),
            "output_tokens": usage.get("candidatesTokenCount"),
        },
        "raw": payload,
    }
