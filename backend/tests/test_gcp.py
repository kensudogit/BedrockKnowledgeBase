"""GCP/Vertex AI連携（ステータス、テキスト生成、GCSアップロード）のテスト。"""

from src.config import Settings
from src.gcp_clients import gcp_status
from src.services.gcs_storage import list_uploads, upload_document
from src.services.vertex_text import generate_text_vertex


# --- GCPステータス ---


def test_gcp_status_unconfigured(monkeypatch):
    """GCP未設定時のステータスとモックモードを確認する。"""
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.setenv("USE_VERTEX_MOCK", "true")
    from src.config import get_settings

    get_settings.cache_clear()
    s = Settings(_env_file=None)
    assert s.gcp_configured is False
    assert s.vertex_ready is True  # mock path
    st = gcp_status()
    assert st["configured"] is False
    assert st["mock_available"] is True
    assert st["mode"] == "mock"
    get_settings.cache_clear()


# --- LLMプロバイダー ---


def test_llm_provider_vertex_when_preferred(monkeypatch):
    """PREFER_VERTEX設定時にvertexプロバイダーが選ばれることを確認する。"""
    monkeypatch.setenv("USE_BEDROCK_MOCK", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.setenv("GCP_PROJECT_ID", "demo-gcp")
    monkeypatch.setenv("USE_VERTEX_MOCK", "true")
    monkeypatch.setenv("PREFER_VERTEX", "true")
    s = Settings(_env_file=None)
    assert s.llm_provider == "vertex"
    assert s.vertex_ready is True


# --- Vertexテキスト生成 ---


def test_vertex_text_mock_without_project(monkeypatch):
    """プロジェクト未設定でもモックテキスト生成が動作することを確認する。"""
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.setenv("USE_VERTEX_MOCK", "true")
    from src.config import get_settings

    get_settings.cache_clear()
    out = generate_text_vertex("hello vertex", system="sys")
    assert out["provider"] == "vertex"
    assert out["mock"] is True
    assert out["gcp_project"] == "mock-gcp"
    assert out["text"]
    get_settings.cache_clear()


def test_vertex_text_mock(monkeypatch):
    """GCPプロジェクト設定下でモックテキスト生成が動作することを確認する。"""
    monkeypatch.setenv("GCP_PROJECT_ID", "demo-gcp")
    monkeypatch.setenv("USE_VERTEX_MOCK", "true")
    from src.config import get_settings

    get_settings.cache_clear()
    out = generate_text_vertex("hello vertex", system="sys")
    assert out["provider"] == "vertex"
    assert out["mock"] is True
    assert out["gcp_project"] == "demo-gcp"
    assert out["text"]
    get_settings.cache_clear()


# --- GCSアップロード ---


def test_gcs_upload_mock(monkeypatch, tmp_path):
    """モックGCSへの文書アップロードと一覧取得を確認する。"""
    monkeypatch.setenv("GCP_PROJECT_ID", "demo-gcp")
    monkeypatch.setenv("USE_VERTEX_MOCK", "true")
    monkeypatch.delenv("GCS_DOCUMENTS_BUCKET", raising=False)
    from src.config import get_settings

    get_settings.cache_clear()
    item = upload_document(filename="note.md", content="# hello", content_type="text/markdown")
    assert item["mock"] is True
    assert item["gcs_uri"].startswith("gs://")
    assert item["bytes"] > 0
    assert any(u["object_id"] == item["object_id"] for u in list_uploads())
    get_settings.cache_clear()
