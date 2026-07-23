"""API キー / JWT によるプロジェクト認可とミドルウェア設定。"""
from __future__ import annotations

from typing import Callable

from fastapi import Header, HTTPException, Request

from src.config import get_settings
from src.services.projects import resolve_project, seed_default_project


def project_from_headers(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_project_id: str | None = Header(default=None, alias="X-Project-Id"),
) -> dict:
    """ヘッダーからプロジェクトを解決し、API キーを検証する。"""
    settings = get_settings()
    # 認証任意: API_KEYS / require_api_key が無効な場合
    if not settings.require_api_key and not settings.api_keys.strip():
        return resolve_project(x_api_key, x_project_id) or seed_default_project()

    allowed = {k.strip() for k in settings.api_keys.split(",") if k.strip()}
    if settings.require_api_key and not x_api_key:
        raise HTTPException(401, "X-API-Key required")
    if allowed and x_api_key and x_api_key not in allowed:
        # プロジェクトスコープのキーは引き続き許可
        proj = resolve_project(x_api_key, x_project_id)
        if not proj:
            raise HTTPException(403, "invalid API key")
        return proj
    proj = resolve_project(x_api_key, x_project_id)
    if not proj:
        raise HTTPException(403, "project not found")
    return proj


def install_auth_middleware(app) -> None:
    """任意のソフト認証: キー/JWT がある場合に request.state にプロジェクトを付与する。"""

    @app.middleware("http")
    async def _auth_mw(request: Request, call_next: Callable):
        key = request.headers.get("X-API-Key")
        pid = request.headers.get("X-Project-Id")
        settings = get_settings()
        path = request.url.path
        public = path in (
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/auth/token",
        ) or path.startswith("/docs")

        auth = request.headers.get("Authorization") or ""
        jwt_claims = None
        if auth.lower().startswith("bearer ") and settings.jwt_configured:
            from src.services.jwt_tokens import verify_access_token

            jwt_claims = verify_access_token(auth.split(" ", 1)[1].strip())
            if jwt_claims is None and settings.require_api_key and path.startswith("/api/") and not public:
                from fastapi.responses import JSONResponse

                return JSONResponse({"detail": "invalid or expired JWT"}, status_code=401)

        if (
            settings.require_api_key
            and not key
            and jwt_claims is None
            and path.startswith("/api/")
            and not public
        ):
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": "X-API-Key or Bearer JWT required"}, status_code=401)
        request.state.project = resolve_project(key, pid) or seed_default_project()
        request.state.jwt_claims = jwt_claims
        return await call_next(request)
