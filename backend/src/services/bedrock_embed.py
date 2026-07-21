from __future__ import annotations

import json
from typing import Any

from src.config import get_settings
from src.services.mock_ai import mock_embed


def embed_texts(texts: list[str]) -> dict[str, Any]:
    settings = get_settings()
    if not texts:
        return {"embeddings": [], "dimensions": 0, "model": settings.bedrock_embed_model_id, "mock": settings.mock_mode}
    if settings.mock_mode:
        return mock_embed(texts)

    from src.aws_clients import bedrock_runtime

    vectors = []
    for t in texts:
        body = {"inputText": t}
        resp = bedrock_runtime().invoke_model(
            modelId=settings.bedrock_embed_model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        payload = json.loads(resp["body"].read())
        vectors.append(payload.get("embedding") or payload.get("embeddings") or [])
    dim = len(vectors[0]) if vectors else 0
    return {
        "embeddings": vectors,
        "dimensions": dim,
        "model": settings.bedrock_embed_model_id,
        "mock": False,
    }
