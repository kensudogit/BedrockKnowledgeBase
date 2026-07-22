"""OpenAI Chat Completions via httpx (Railway OPENAI_API_KEY)."""
from __future__ import annotations

from typing import Any

import httpx

from src.config import get_settings


def generate_text_openai(
    prompt: str,
    *,
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> dict[str, Any]:
    settings = get_settings()
    key = settings.openai_api_key.strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    model = settings.openai_text_model_id
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        resp.raise_for_status()
        payload = resp.json()

    text = ""
    choices = payload.get("choices") or []
    if choices:
        text = (choices[0].get("message") or {}).get("content") or ""

    usage = payload.get("usage") or {}
    return {
        "text": text,
        "model": model,
        "mock": False,
        "provider": "openai",
        "usage": {
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
        },
        "raw": payload,
    }
