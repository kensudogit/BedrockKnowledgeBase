"""Cognito / 開発 JWT / API キー認証と request.state.principal。"""
from __future__ import annotations

from typing import Callable

from fastapi import Header, HTTPException, Request

from src.config import get_settings
from src.services.auth_principal import (
    AuthPrincipal,
    principal_from_api_key_project,
    principal_from_cognito,
    principal_from_dev_jwt,
)
from src.services.cognito_auth import CognitoAuthError, verify_cognito_access_token
from src.services.projects import resolve_project, seed_default_project


def project_from_headers(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_project_id: str | None = Header(default=None, alias="X-Project-Id"),
) -> dict:
    """ヘッダーからプロジェクトを解決し、API キーを検証する。"""
    settings = get_settings()
    if not settings.require_api_key and not settings.api_keys.strip():
        return resolve_project(x_api_key, x_project_id) or seed_default_project()

    allowed = {k.strip() for k in settings.api_keys.split(",") if k.strip()}
    if settings.require_api_key and not x_api_key:
        raise HTTPException(401, "X-API-Key required")
    if allowed and x_api_key and x_api_key not in allowed:
        proj = resolve_project(x_api_key, x_project_id)
        if not proj:
            raise HTTPException(403, "invalid API key")
        return proj
    proj = resolve_project(x_api_key, x_project_id)
    if not proj:
        raise HTTPException(403, "project not found")
    return proj


def _resolve_bearer_principal(auth_header: str, settings) -> AuthPrincipal | None:
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None

    if settings.cognito_configured:
        try:
            claims = verify_cognito_access_token(token)
            return principal_from_cognito(claims)
        except CognitoAuthError:
            if settings.auth_enforce and not settings.dev_jwt_allowed:
                return None
        except Exception:
            if settings.auth_enforce and not settings.dev_jwt_allowed:
                return None

    if settings.dev_jwt_allowed:
        from src.services.jwt_tokens import verify_access_token

        claims = verify_access_token(token)
        if claims:
            return principal_from_dev_jwt(claims)
    return None


def install_auth_middleware(app) -> None:
    """Bearer / API キーを検証し request.state.principal を設定する。"""

    @app.middleware("http")
    async def _auth_mw(request: Request, call_next: Callable):
        settings = get_settings()
        path = request.url.path
        public = path in (
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/auth/config",
        ) or path.startswith("/docs")

        auth = request.headers.get("Authorization") or ""
        key = request.headers.get("X-API-Key")
        pid = request.headers.get("X-Project-Id")

        principal: AuthPrincipal | None = _resolve_bearer_principal(auth, settings)

        if principal is None and key:
            proj = resolve_project(key, pid)
            if proj:
                allowed = {k.strip() for k in settings.api_keys.split(",") if k.strip()}
                if allowed and key not in allowed:
                    # プロジェクトスコープキーのみ許可
                    if not proj.get("api_key_hash"):
                        from fastapi.responses import JSONResponse

                        return JSONResponse({"detail": "invalid API key"}, status_code=403)
                principal = principal_from_api_key_project(proj)

        if (
            settings.auth_enforce
            and principal is None
            and path.startswith("/api/")
            and not public
            and path != "/api/auth/token"
        ):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                {"detail": "Bearer Cognito/JWT or X-API-Key required"},
                status_code=401,
            )

        if principal is None:
            principal = AuthPrincipal.anonymous_dev()

        request.state.project = resolve_project(key, pid) or seed_default_project()
        request.state.jwt_claims = principal.claims if principal.provider != "anonymous" else None
        request.state.principal = principal
        return await call_next(request)
