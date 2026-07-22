import os

from src.config import get_settings
from src.services.jwt_tokens import issue_access_token, verify_access_token


def test_issue_and_verify_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret")
    get_settings.cache_clear()
    tok = issue_access_token(subject="alice", expires_in_sec=60)
    assert tok["token_type"] == "bearer"
    claims = verify_access_token(tok["access_token"])
    assert claims is not None
    assert claims["sub"] == "alice"


def test_verify_rejects_tampered(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret")
    get_settings.cache_clear()
    tok = issue_access_token(subject="bob")["access_token"]
    bad = tok[:-4] + "xxxx"
    assert verify_access_token(bad) is None


def test_verify_without_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "")
    get_settings.cache_clear()
    assert verify_access_token("a.b.c") is None
