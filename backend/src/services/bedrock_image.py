from __future__ import annotations

import base64
import json
from typing import Any

from src.config import get_settings
from src.services.mock_ai import mock_image


def generate_image(prompt: str, *, width: int = 512, height: int = 512) -> dict[str, Any]:
    settings = get_settings()
    if settings.mock_mode:
        return mock_image(prompt)

    from src.aws_clients import bedrock_runtime

    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {"text": prompt},
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "height": height,
            "width": width,
            "cfgScale": 8.0,
        },
    }
    resp = bedrock_runtime().invoke_model(
        modelId=settings.bedrock_image_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    payload = json.loads(resp["body"].read())
    images = payload.get("images") or []
    b64 = images[0] if images else ""
    return {
        "image_base64": b64,
        "content_type": "image/png",
        "prompt": prompt,
        "model": settings.bedrock_image_model_id,
        "mock": False,
    }


def decode_preview_data_url(image_base64: str) -> str:
    return f"data:image/png;base64,{image_base64}"
