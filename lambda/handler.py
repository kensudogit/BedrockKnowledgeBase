"""
API Gateway (HTTP API) → Lambda → Bedrock の薄いプロキシ。

ローカル開発は FastAPI (backend/) を使い、本番は本ハンドラをデプロイします。
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


INTERNAL_API = os.getenv("INTERNAL_FASTAPI_URL", "")


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "content-type": "application/json",
            "access-control-allow-origin": "*",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath") or event.get("path") or "/"
    body_raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64

        body_raw = base64.b64decode(body_raw).decode("utf-8")

    # オプション: 既存 FastAPI へ転送（コンテナ併設時）
    if INTERNAL_API:
        req = urllib.request.Request(
            f"{INTERNAL_API}{path}",
            data=body_raw.encode("utf-8") if method in ("POST", "PUT", "PATCH") else None,
            headers={"content-type": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=50) as resp:
                return {
                    "statusCode": resp.status,
                    "headers": {"content-type": "application/json", "access-control-allow-origin": "*"},
                    "body": resp.read().decode("utf-8"),
                }
        except Exception as exc:  # noqa: BLE001
            return _response(502, {"error": str(exc)})

    # スタンドアロン最小実装
    if path.endswith("/health") or path == "/health":
        return _response(
            200,
            {
                "status": "ok",
                "runtime": "lambda",
                "mock": os.getenv("USE_BEDROCK_MOCK", "false"),
            },
        )

    return _response(
        200,
        {
            "message": "Deploy backend package or set INTERNAL_FASTAPI_URL",
            "path": path,
            "method": method,
        },
    )
