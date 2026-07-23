"""HS256 JWT の発行・検証（Railway JWT_SECRET、標準ライブラリのみ）。"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from src.config import get_settings


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_json(obj: dict[str, Any]) -> str:
    return _b64url(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _sign(message: bytes, secret: str) -> str:
    dig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return _b64url(dig)


def issue_access_token(
    *,
    subject: str = "bkb-user",
    expires_in_sec: int = 3600,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """アクセストークン（JWT）を発行する。JWT_SECRET 未設定時は RuntimeError。"""
    settings = get_settings()
    secret = settings.jwt_secret.strip()
    if not secret:
        raise RuntimeError("JWT_SECRET is not set")

    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_in_sec,
        "iss": "bedrock-knowledge-base",
    }
    if extra:
        payload.update(extra)

    unsigned = f"{_b64url_json(header)}.{_b64url_json(payload)}"
    token = f"{unsigned}.{_sign(unsigned.encode('ascii'), secret)}"
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in_sec,
    }


def verify_access_token(token: str) -> dict[str, Any] | None:
    """JWT の署名と有効期限を検証する。無効時は None。"""
    settings = get_settings()
    secret = settings.jwt_secret.strip()
    if not secret or not token:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    unsigned = f"{parts[0]}.{parts[1]}"
    expected = _sign(unsigned.encode("ascii"), secret)
    if not hmac.compare_digest(expected, parts[2]):
        return None
    try:
        pad = "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + pad))
    except Exception:
        return None
    if int(payload.get("exp") or 0) < int(time.time()):
        return None
    return payload
