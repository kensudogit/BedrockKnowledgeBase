"""Amazon Cognito User Pool アクセストークン検証（RS256 / JWKS）。"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient

from src.config import get_settings


class CognitoAuthError(Exception):
    pass


@lru_cache
def _issuer() -> str:
    settings = get_settings()
    pool = settings.cognito_user_pool_id.strip()
    region = settings.aws_region.strip()
    if not pool or not region:
        raise CognitoAuthError("Cognito is not configured")
    custom = settings.cognito_issuer.strip()
    if custom:
        return custom.rstrip("/")
    return f"https://cognito-idp.{region}.amazonaws.com/{pool}"


@lru_cache
def _jwks_client() -> PyJWKClient:
    issuer = _issuer()
    return PyJWKClient(f"{issuer}/.well-known/jwks.json", cache_keys=True)


def verify_cognito_access_token(token: str) -> dict[str, Any]:
    """アクセストークンの署名・iss・exp・token_use・client_id を検証する。"""
    settings = get_settings()
    client_id = settings.cognito_app_client_id.strip()
    if not client_id:
        raise CognitoAuthError("COGNITO_APP_CLIENT_ID is not set")

    issuer = _issuer()
    try:
        key = _jwks_client().get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=issuer,
            options={
                "verify_aud": False,
                "require": ["exp", "iat", "iss", "sub", "token_use", "client_id"],
            },
            leeway=30,
        )
    except jwt.PyJWTError as exc:
        raise CognitoAuthError("invalid token") from exc
    except OSError as exc:
        raise CognitoAuthError("jwks unavailable") from exc

    if claims.get("token_use") != "access":
        raise CognitoAuthError("ID token cannot be used for API auth")
    if claims.get("client_id") != client_id:
        raise CognitoAuthError("wrong app client")
    return claims
