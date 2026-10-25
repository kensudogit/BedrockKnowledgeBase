"""認証済み利用者（テナント・ロール）— クライアント指定の tenant_id は信用しない。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True)
class AuthPrincipal:
    subject: str
    tenant_id: str
    roles: frozenset[str]
    provider: str  # cognito | jwt_dev | api_key | anonymous
    claims: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def anonymous_dev(*, tenant_id: str = "default") -> AuthPrincipal:
        return AuthPrincipal(
            subject="anonymous-dev",
            tenant_id=tenant_id,
            roles=frozenset({"admin"}),
            provider="anonymous",
            claims={},
        )

    def has_role(self, *names: str) -> bool:
        if "admin" in self.roles:
            return True
        if "*" in self.roles:
            return True
        return any(n in self.roles for n in names)


def roles_from_claims(claims: dict[str, Any]) -> frozenset[str]:
    """Cognito groups / カスタム roles / scope からロール集合を作る。"""
    found: set[str] = set()
    groups = claims.get("cognito:groups")
    if isinstance(groups, list):
        found.update(str(g).strip() for g in groups if str(g).strip())
    elif isinstance(groups, str) and groups.strip():
        found.add(groups.strip())
    raw_roles = claims.get("roles") or claims.get("role")
    if isinstance(raw_roles, str):
        found.update(r.strip() for r in raw_roles.split(",") if r.strip())
    elif isinstance(raw_roles, list):
        found.update(str(r).strip() for r in raw_roles if str(r).strip())
    scope = claims.get("scope") or ""
    if isinstance(scope, str):
        found.update(s.strip() for s in scope.split() if s.strip())
    if not found:
        found.add("viewer")
    return frozenset(found)


def tenant_from_claims(claims: dict[str, Any], *, fallback: str = "default") -> str:
    for key in ("custom:tenant_id", "tenant_id", "tenant"):
        val = claims.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return fallback


def principal_from_dev_jwt(claims: dict[str, Any]) -> AuthPrincipal:
    sub = str(claims.get("sub") or "bkb-user")
    tenant = tenant_from_claims(claims, fallback="default")
    return AuthPrincipal(
        subject=sub,
        tenant_id=tenant,
        roles=roles_from_claims(claims),
        provider="jwt_dev",
        claims=claims,
    )


def principal_from_cognito(claims: dict[str, Any]) -> AuthPrincipal:
    sub = str(claims.get("sub") or "")
    tenant = tenant_from_claims(claims, fallback="default")
    return AuthPrincipal(
        subject=sub,
        tenant_id=tenant,
        roles=roles_from_claims(claims),
        provider="cognito",
        claims=claims,
    )


def principal_from_api_key_project(project: dict[str, Any]) -> AuthPrincipal:
    tid = (project.get("client_name") or project.get("project_id") or "default").strip()
    return AuthPrincipal(
        subject=f"project:{project.get('project_id', 'unknown')}",
        tenant_id=tid or "default",
        roles=frozenset({"api_key", "admin"}),
        provider="api_key",
        claims={"project_id": project.get("project_id")},
    )
