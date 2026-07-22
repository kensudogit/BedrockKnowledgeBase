from fastapi.testclient import TestClient

from src.main import app
from src.services.persist import append, load, rewrite


def test_persist_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_BEDROCK_MOCK", "true")
    # use real persist path; unique collection name
    name = "unit_persist_demo"
    rewrite(name, [])
    append(name, {"n": 1})
    append(name, {"n": 2})
    items = load(name)
    assert len(items) >= 2
    assert items[-1]["n"] == 2
    rewrite(name, [{"n": 9}])
    assert load(name) == [{"n": 9}]


def test_health_endpoint():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["app"] == "bedrock-knowledge-base"
    assert "llm_provider" in body
    assert "features" in body


def test_auth_token_requires_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "")
    from src.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    r = client.post("/api/auth/token", json={"subject": "x"})
    assert r.status_code == 503


def test_auth_token_ok(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "api-test-secret")
    from src.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)
    r = client.post("/api/auth/token", json={"subject": "carol", "expires_in_sec": 120})
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["claims"]["sub"] == "carol"
