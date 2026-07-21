from __future__ import annotations

import json
from typing import Any

from src.config import get_settings
from src.services.mock_ai import mock_text


def generate_text(
    prompt: str,
    *,
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
    apply_guardrail: bool = True,
) -> dict[str, Any]:
    settings = get_settings()
    if settings.mock_mode:
        out = mock_text(prompt, system=system)
        if apply_guardrail and settings.enable_guardrails:
            from src.services.guardrails import apply_guardrails

            gr = apply_guardrails(out["text"])
            out["guardrail"] = gr
            if gr.get("action") == "GUARDRAIL_INTERVENED":
                out["text"] = gr["outputs"][0]["text"]
        return out

    from src.aws_clients import bedrock_runtime

    body: dict[str, Any] = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system

    kwargs: dict[str, Any] = {
        "modelId": settings.bedrock_text_model_id,
        "contentType": "application/json",
        "accept": "application/json",
        "body": json.dumps(body),
    }
    if (
        apply_guardrail
        and settings.enable_guardrails
        and settings.bedrock_guardrail_id
    ):
        kwargs["guardrailIdentifier"] = settings.bedrock_guardrail_id
        kwargs["guardrailVersion"] = settings.bedrock_guardrail_version

    resp = bedrock_runtime().invoke_model(**kwargs)
    payload = json.loads(resp["body"].read())
    text = ""
    for block in payload.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")
    return {
        "text": text or json.dumps(payload, ensure_ascii=False),
        "model": settings.bedrock_text_model_id,
        "mock": False,
        "raw": payload,
    }
