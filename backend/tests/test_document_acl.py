"""文書 ACL と RAG フィルタの単体・結合テスト。"""
from __future__ import annotations

from src.services.auth_principal import AuthPrincipal
from src.services.document_acl import default_upload_acl, principal_can_read
from src.services.rag import retrieve_local


def test_tenant_isolation_on_acl():
    acl_a = default_upload_acl(tenant_id="tenant-a", subject="user-a")
    principal_b = AuthPrincipal(
        subject="user-b",
        tenant_id="tenant-b",
        roles=frozenset({"viewer"}),
        provider="jwt_dev",
    )
    assert not principal_can_read(principal_b, acl_a)


def test_shared_tenant_readable():
    acl = {"tenant_id": "shared", "allowed_roles": ["*"], "allowed_subjects": []}
    p = AuthPrincipal("u", "any-tenant", frozenset({"viewer"}), "jwt_dev")
    assert principal_can_read(p, acl)


def test_rag_local_respects_acl_after_ingest(monkeypatch, tmp_path):
    """取り込み文書は他テナントの retrieve に出ない。"""
    monkeypatch.setenv("JWT_SECRET", "acl-test")
    from src.services import rag as rag_mod
    from src.services.documents import ingest_text

    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    empty_samples = tmp_path / "samples"
    empty_samples.mkdir()
    monkeypatch.setattr(rag_mod, "uploads_dir", lambda: upload_root)
    monkeypatch.setattr(rag_mod, "_samples_dir", lambda: empty_samples)

    pa = AuthPrincipal("a", "tenant-a", frozenset({"admin"}), "jwt_dev")
    pb = AuthPrincipal("b", "tenant-b", frozenset({"admin"}), "jwt_dev")

    ingest_text(
        filename="secret-a.md",
        content="tenant-a-only billing policy alpha unique token xyz123",
        principal=pa,
    )
    rag_mod.invalidate_local_index()

    hits_a = retrieve_local("billing policy alpha xyz123", top_k=5, principal=pa)
    hits_b = retrieve_local("billing policy alpha xyz123", top_k=5, principal=pb)
    assert any("secret-a" in (h.get("source") or "") for h in hits_a)
    assert not any("secret-a" in (h.get("source") or "") for h in hits_b)
