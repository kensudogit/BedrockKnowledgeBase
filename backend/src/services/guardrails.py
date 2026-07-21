from __future__ import annotations

from typing import Any

from src.config import get_settings
from src.services.mock_ai import mock_guardrail


def apply_guardrails(text: str, *, source: str = "OUTPUT") -> dict[str, Any]:
    settings = get_settings()
    if settings.mock_mode or not settings.bedrock_guardrail_id:
        return mock_guardrail(text)

    # Bedrock ApplyGuardrail API
    from src.aws_clients import bedrock_runtime

    src = source if source in ("INPUT", "OUTPUT") else "OUTPUT"
    resp = bedrock_runtime().apply_guardrail(
        guardrailIdentifier=settings.bedrock_guardrail_id,
        guardrailVersion=settings.bedrock_guardrail_version,
        source=src,
        content=[{"text": {"text": text}}],
    )
    return {
        "action": resp.get("action"),
        "outputs": resp.get("outputs", []),
        "assessments": resp.get("assessments", []),
        "mock": False,
    }
