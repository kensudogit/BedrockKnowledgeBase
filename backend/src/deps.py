"""FastAPI 依存: request.state から認証主体を取得。"""
from __future__ import annotations

from fastapi import HTTPException, Request

from src.config import get_settings
from src.services.auth_principal import AuthPrincipal


def get_principal(request: Request) -> AuthPrincipal:
    principal = getattr(request.state, "principal", None)
    if isinstance(principal, AuthPrincipal):
        return principal
    settings = get_settings()
    if settings.auth_enforce:
        raise HTTPException(401, "Authentication required")
    return AuthPrincipal.anonymous_dev()


def require_admin(principal: AuthPrincipal) -> AuthPrincipal:
    if not principal.has_role("admin"):
        raise HTTPException(403, "admin role required")
    return principal
