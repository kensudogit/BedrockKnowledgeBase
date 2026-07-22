from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[2]
_ENV = _ROOT / ".env"


def normalize_database_url(url: str) -> str:
    """Railway often provides postgres://; SQLAlchemy wants postgresql://."""
    u = (url or "").strip()
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://") :]
    return u


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ENV), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"  # development | staging | production
    aws_region: str = "ap-northeast-1"
    cors_origins: str = "http://localhost:3010,*"
    database_url: str = "postgresql://bkb_user:bkb_password@localhost:5435/bkb_db"
    # Empty = real AWS DynamoDB (or in-memory fallback). Local: http://localhost:8001
    dynamodb_endpoint: str = ""
    dynamodb_table_prompts: str = "bkb_prompts"
    dynamodb_table_evals: str = "bkb_evals"
    dynamodb_table_sessions: str = "bkb_sessions"

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""
    aws_endpoint_url: str = ""

    bedrock_text_model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    bedrock_image_model_id: str = "amazon.titan-image-generator-v1"
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v2:0"
    bedrock_knowledge_base_id: str = ""
    bedrock_data_source_id: str = ""
    bedrock_guardrail_id: str = ""
    bedrock_guardrail_version: str = "DRAFT"
    bedrock_agent_id: str = ""
    bedrock_agent_alias_id: str = ""
    s3_documents_bucket: str = ""

    # Railway / shared secrets
    openai_api_key: str = ""
    openai_text_model_id: str = "gpt-4o-mini"
    jwt_secret: str = ""

    # Google Cloud / Vertex AI
    gcp_project_id: str = ""
    gcp_region: str = "asia-northeast1"
    gcp_access_token: str = ""
    google_application_credentials: str = ""
    vertex_text_model_id: str = "gemini-2.0-flash-001"
    gcs_documents_bucket: str = ""
    use_vertex_mock: bool = True
    prefer_vertex: bool = False

    # Auth: comma-separated keys; require_api_key=true for staging/prod client demos
    api_keys: str = ""
    require_api_key: bool = False
    default_project_id: str = ""

    use_bedrock_mock: bool = True
    enable_guardrails: bool = True
    enable_agents: bool = True
    enable_telemetry: bool = True
    eval_fail_under: float = 0.0

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_db(cls, v: object) -> object:
        if isinstance(v, str):
            return normalize_database_url(v)
        return v

    @field_validator("dynamodb_endpoint", mode="before")
    @classmethod
    def _strip_local_dynamo_in_hint(cls, v: object) -> object:
        # Treat blank / whitespace as unset
        if isinstance(v, str):
            return v.strip()
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod", "staging"}

    @property
    def effective_dynamodb_endpoint(self) -> str:
        """Ignore localhost DynamoDB endpoint on Railway/production."""
        ep = (self.dynamodb_endpoint or "").strip()
        if self.is_production and ("localhost" in ep or "127.0.0.1" in ep):
            return ""
        return ep

    @property
    def database_configured(self) -> bool:
        u = self.database_url.lower()
        if not u:
            return False
        # default local template without Railway host
        if "localhost:5435" in u or "127.0.0.1:5435" in u:
            return False
        host = urlparse(u).hostname or ""
        return bool(host) and host not in {"localhost", "127.0.0.1"}

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key.strip())

    @property
    def jwt_configured(self) -> bool:
        return bool(self.jwt_secret.strip())

    @property
    def bedrock_credentials_configured(self) -> bool:
        return bool(self.aws_access_key_id.strip())

    @property
    def gcp_configured(self) -> bool:
        return bool(self.gcp_project_id.strip())

    @property
    def vertex_ready(self) -> bool:
        """Vertex path available (mock or real token/credentials)."""
        if not self.gcp_configured:
            return False
        if self.use_vertex_mock:
            return True
        return bool(self.gcp_access_token.strip() or self.google_application_credentials.strip())

    @property
    def mock_mode(self) -> bool:
        """True when Bedrock Runtime path is mocked / unavailable."""
        return bool(self.use_bedrock_mock) or not (
            self.aws_access_key_id or self.bedrock_knowledge_base_id
        )

    @property
    def llm_provider(self) -> str:
        """Provider used for text generation (chat / RAG answer)."""
        if not self.use_bedrock_mock and self.bedrock_credentials_configured:
            return "bedrock"
        if self.prefer_vertex and self.vertex_ready:
            return "vertex"
        if self.openai_configured:
            return "openai"
        if self.vertex_ready:
            return "vertex"
        return "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
