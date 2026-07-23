"""設定（Settings）とデータベースURL正規化のテスト。"""

from src.config import Settings, normalize_database_url


def test_normalize_database_url():
    """postgres URLがpostgresql形式に正規化されることを確認する。"""
    assert normalize_database_url("postgres://u:p@h/db").startswith("postgresql://")
    assert normalize_database_url("postgresql://u:p@h/db") == "postgresql://u:p@h/db"


# --- LLMプロバイダー選択 ---


def test_llm_provider_mock_by_default(monkeypatch):
    """デフォルトでmockプロバイダーが選択されることを確認する。"""
    monkeypatch.setenv("USE_BEDROCK_MOCK", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    s = Settings(_env_file=None)
    assert s.llm_provider == "mock"
    assert s.mock_mode is True


def test_llm_provider_openai(monkeypatch):
    """OpenAI APIキー設定時にopenaiプロバイダーが選ばれることを確認する。"""
    monkeypatch.setenv("USE_BEDROCK_MOCK", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    s = Settings(_env_file=None)
    assert s.openai_configured is True
    assert s.llm_provider == "openai"


# --- DynamoDBエンドポイント ---


def test_effective_dynamodb_endpoint_strips_localhost_in_prod(monkeypatch):
    """本番環境でlocalhost DynamoDBエンドポイントが無効化されることを確認する。"""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DYNAMODB_ENDPOINT", "http://localhost:8001")
    s = Settings(_env_file=None)
    assert s.effective_dynamodb_endpoint == ""
